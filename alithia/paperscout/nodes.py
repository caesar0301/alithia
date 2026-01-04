"""
Agent nodes for the research agent workflow.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from cogents_core.utils import get_logger

from alithia.config_loader import load_config
from alithia.researcher import ResearcherProfile
from alithia.storage.base import StorageBackend
from alithia.storage.factory import get_storage_backend
from alithia.utils.arxiv_paper_fetcher import fetch_arxiv_papers
from alithia.utils.arxiv_paper_utils import extract_affiliations, generate_tldr, get_code_url
from alithia.utils.email_utils import send_email
from alithia.utils.llm_utils import get_llm_client
from alithia.utils.zotero_client import filter_corpus, get_zotero_corpus

from .email import construct_email_content
from .models import ScoredPaper
from .reranker import PaperReranker
from .state import AgentState

logger = get_logger(__name__)

# Module-level storage backend (initialized once)
_storage_backend: Optional[StorageBackend] = None


def get_or_create_storage(config_path: Optional[str] = None) -> Optional[StorageBackend]:
    """Get or create storage backend instance."""
    global _storage_backend

    if _storage_backend is None:
        try:
            config = load_config(config_path)
            _storage_backend = get_storage_backend(config)
            logger.info("Storage backend initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize storage backend: {e}. Continuing without storage.")
            _storage_backend = None

    return _storage_backend


def _validate_user_profile(user_profile: ResearcherProfile) -> List[str]:
    """Validate the profile configuration."""
    errors = []

    if not user_profile.zotero.zotero_id:
        errors.append("Zotero ID is required")
    if not user_profile.zotero.zotero_key:
        errors.append("Zotero API key is required")
    if not user_profile.email_notification.smtp_server:
        errors.append("SMTP server is required")
    if not user_profile.email_notification.sender:
        errors.append("Sender email is required")
    if not user_profile.email:
        errors.append("Researcher email is required for notifications")
    if not user_profile.llm.openai_api_key:
        errors.append("OpenAI API key is required when using LLM API")

    return errors


def profile_analysis_node(state: AgentState) -> dict:
    """
    Initialize and analyze user research profile.

    Args:
        state: Current agent state

    Returns:
        Dictionary with updated state fields
    """
    logger.info("Analyzing user profile...")

    if not state.config.user_profile:
        state.add_error("No profile provided")
        return {"current_step": "profile_analysis_error", "error_log": state.error_log}

    errors = _validate_user_profile(state.config.user_profile)
    if errors:
        for error in errors:
            state.add_error(error)
        return {"current_step": "profile_validation_error", "error_log": state.error_log}

    logger.info(f"Profile validated for user: {state.config.user_profile.email}")
    return {"current_step": "profile_analysis_complete"}


def data_collection_node(state: AgentState) -> dict:
    """
    Collect papers from ArXiv and Zotero with storage caching.

    Args:
        state: Current agent state

    Returns:
        Dictionary with updated state fields
    """
    logger.info("Collecting data from ArXiv and Zotero...")

    if not state.config.user_profile:
        state.add_error("No profile available for data collection")
        return {"current_step": "data_collection_error", "error_log": state.error_log}

    # Initialize storage backend
    storage = get_or_create_storage()
    user_id = state.config.user_profile.email or "default_user"

    try:
        # Get Zotero corpus (with caching if storage available)
        corpus = None
        if storage:
            logger.info("Checking for cached Zotero corpus...")
            corpus = storage.get_zotero_papers(user_id, max_age_hours=24)

        if corpus:
            logger.info(f"Using cached Zotero corpus ({len(corpus)} papers)")
        else:
            logger.info("Retrieving Zotero corpus from API...")
            corpus = get_zotero_corpus(
                state.config.user_profile.zotero.zotero_id, state.config.user_profile.zotero.zotero_key
            )
            logger.info(f"Retrieved {len(corpus)} papers from Zotero")

            # Cache for future use
            if storage:
                try:
                    storage.cache_zotero_papers(user_id, corpus)
                    logger.info("Cached Zotero corpus for future use")
                except Exception as e:
                    logger.warning(f"Failed to cache Zotero corpus: {e}")

        # Apply ignore patterns
        if state.config.ignore_patterns:
            ignore_patterns = "\n".join(state.config.ignore_patterns)
            logger.info(f"Applying ignore patterns: {ignore_patterns}")
            corpus = filter_corpus(corpus, ignore_patterns)
            logger.info(f"Filtered corpus: {len(corpus)} papers remaining")

        # Get ArXiv papers for date range (00:00 to 24:00)
        # Use config dates if provided, otherwise default to yesterday
        if state.config.from_date:
            try:
                from_dt = datetime.strptime(state.config.from_date, "%Y-%m-%d")
                # If to_date is not provided, use from_date (single day query)
                if state.config.to_date:
                    to_dt = datetime.strptime(state.config.to_date, "%Y-%m-%d")
                    logger.info(f"Using configured date range: {state.config.from_date} to {state.config.to_date}")
                else:
                    to_dt = from_dt
                    logger.info(f"Using configured date: {state.config.from_date} (single day)")
            except ValueError as e:
                logger.error(f"Invalid date format in config: {e}. Using default (yesterday).")
                from_dt = datetime.now() - timedelta(days=1)
                to_dt = from_dt
        else:
            # Default to yesterday
            from_dt = datetime.now() - timedelta(days=1)
            to_dt = from_dt
            logger.info("Using default date range (yesterday)")

        from_date = from_dt.strftime("%Y%m%d")
        to_date = to_dt.strftime("%Y%m%d")
        from_time = from_date + "0000"
        to_time = to_date + "2359"

        logger.info(
            f"Date range: {from_time} to {to_time} " f"({from_dt.strftime('%Y-%m-%d')} to {to_dt.strftime('%Y-%m-%d')})"
        )
        logger.info(f"Query categories: {state.config.query}")

        # Check if this date range was already processed
        if storage:
            processed_ranges = storage.get_processed_ranges(user_id, state.config.query, days_back=7)
            already_processed = any(
                r.get("from_date") == from_date and r.get("to_date") == to_date for r in processed_ranges
            )

            if already_processed:
                logger.info(f"Date range {from_date}-{to_date} was already processed, skipping")
                return {"discovered_papers": [], "zotero_corpus": corpus, "current_step": "data_collection_complete"}

        # Use enhanced paper fetcher with automatic fallback
        try:
            papers = fetch_arxiv_papers(
                arxiv_query=state.config.query,
                from_time=from_time,
                to_time=to_time,
                max_results=state.config.max_papers_queried,
                debug=state.debug_mode,
                max_retries=3,
                enable_web_fallback=True,
            )
            logger.info(f"Retrieved {len(papers)} valid papers from ArXiv")
        except Exception as e:
            logger.error(f"Failed to fetch papers even with fallback: {e}")
            state.add_error(f"Paper fetching failed: {str(e)}")
            return {"current_step": "data_collection_error", "error_log": state.error_log}

        # Mark this date range as processed
        if storage:
            try:
                storage.mark_date_range_processed(user_id, from_date, to_date, state.config.query, len(papers))
                logger.info(f"Marked date range {from_date}-{to_date} as processed")
            except Exception as e:
                logger.warning(f"Failed to mark date range as processed: {e}")

        # Filter out papers that were already emailed
        if storage and papers:
            arxiv_ids = [paper.arxiv_id for paper in papers]
            emailed_papers = storage.get_emailed_papers(user_id, arxiv_ids, days_back=30)
            emailed_ids = {p.get("arxiv_id") for p in emailed_papers}

            if emailed_ids:
                filtered_papers = [p for p in papers if p.arxiv_id not in emailed_ids]
                logger.info(f"Filtered out {len(papers) - len(filtered_papers)} papers " f"that were already emailed")
                papers = filtered_papers

        # Log paper details for debugging
        for i, paper in enumerate(papers):
            logger.info(f"Paper {i+1}: {paper.title[:50]}... (ID: {paper.arxiv_id})")

        # Validate that we have papers to work with
        if not papers:
            logger.info("No new papers to process after filtering")

        logger.info(f"Successfully collected {len(papers)} papers for processing")
        return {"discovered_papers": papers, "zotero_corpus": corpus, "current_step": "data_collection_complete"}

    except Exception as e:
        state.add_error(f"Data collection failed: {str(e)}")
        return {"current_step": "data_collection_error", "error_log": state.error_log}


def relevance_assessment_node(state: AgentState) -> dict:
    """
    Score papers based on relevance to user's research.

    Args:
        state: Current agent state

    Returns:
        Dictionary with updated state fields
    """
    logger.info("Assessing paper relevance...")

    if not state.discovered_papers:
        logger.info("No papers discovered")
        return {"current_step": "relevance_assessment_complete"}

    if not state.zotero_corpus:
        logger.warning("No Zotero corpus available, using basic scoring")
        scored_papers = [
            ScoredPaper(paper=paper, score=5.0, relevance_factors={"basic": 5.0}) for paper in state.discovered_papers
        ]
    else:
        try:
            preranker = PaperReranker(state.discovered_papers, state.zotero_corpus)
            scored_papers = preranker.rerank_sentence_transformer()
            logger.info(f"Scored {len(scored_papers)} papers")
        except Exception as e:
            state.add_error(f"Relevance assessment failed: {str(e)}")
            # Fallback to basic scoring
            scored_papers = [
                ScoredPaper(paper=paper, score=5.0, relevance_factors={"fallback": 5.0})
                for paper in state.discovered_papers
            ]
            return {
                "scored_papers": scored_papers,
                "current_step": "relevance_assessment_complete",
                "error_log": state.error_log,
            }

    # Apply paper limit
    if state.config and state.config.max_papers > 0:
        scored_papers = scored_papers[: state.config.max_papers]
        logger.info(f"Limited to {len(scored_papers)} papers")

    return {"scored_papers": scored_papers, "current_step": "relevance_assessment_complete"}


def content_generation_node(state: AgentState) -> dict:
    """
    Generate TLDR summaries and email content.

    Args:
        state: Current agent state

    Returns:
        Dictionary with updated state fields
    """
    logger.info("Generating content...")

    if not state.scored_papers:
        logger.info("No papers to process")
        return {"current_step": "content_generation_complete"}

    if not state.config.user_profile:
        state.add_error("No profile available for content generation")
        return {"current_step": "content_generation_error", "error_log": state.error_log}

    try:
        llm = get_llm_client(state.config.user_profile.llm)

        # Generate TLDR and enrich paper data
        for i, scored_paper in enumerate(state.scored_papers):
            paper = scored_paper.paper
            logger.info(f"Processing paper {i+1}/{len(state.scored_papers)}: {paper.title[:50]}...")

            # Generate TLDR
            if not paper.tldr:
                paper.tldr = generate_tldr(paper, llm)

            # Extract affiliations
            if not paper.affiliations:
                paper.affiliations = extract_affiliations(paper, llm)

            # Get code URL
            if not paper.code_url:
                paper.code_url = get_code_url(paper)

        # Construct email content
        email_content = construct_email_content(state.scored_papers)

        logger.info("Content generation complete")
        return {"email_content": email_content, "current_step": "content_generation_complete"}

    except Exception as e:
        state.add_error(f"Content generation failed: {str(e)}")
        return {"current_step": "content_generation_error", "error_log": state.error_log}


def communication_node(state: AgentState) -> dict:
    """
    Send email with recommendations and track emailed papers.

    Args:
        state: Current agent state

    Returns:
        Dictionary with updated state fields
    """
    if state.debug_mode:
        logger.info("Debug mode: Email delivery would be sent with recommendations")
        return {"current_step": "workflow_complete"}

    logger.info("Preparing email delivery...")

    if not state.config.user_profile:
        state.add_error("No profile available for email delivery")
        return {"current_step": "communication_error", "error_log": state.error_log}

    # Check if we should send empty email
    if not state.email_content or (hasattr(state.email_content, "is_empty") and state.email_content.is_empty()):
        if not state.config.send_empty:
            logger.info("No papers found and SEND_EMPTY=False, skipping email")
            return {"current_step": "workflow_complete"}
        else:
            logger.info("No papers found but SEND_EMPTY=True, sending empty email")

    try:
        # Send email
        success = send_email(
            sender=state.config.user_profile.email_notification.sender,
            receiver=state.config.user_profile.email,
            password=state.config.user_profile.email_notification.sender_password,
            smtp_server=state.config.user_profile.email_notification.smtp_server,
            smtp_port=state.config.user_profile.email_notification.smtp_port,
            html_content=(
                state.email_content
                if isinstance(state.email_content, str)
                else state.email_content.html_content if state.email_content else ""
            ),
        )

        if success:
            logger.info("Email sent successfully")

            # Track emailed papers in storage
            if state.scored_papers:
                storage = get_or_create_storage()
                if storage:
                    user_id = state.config.user_profile.email or "default_user"
                    try:
                        papers_data = []
                        for scored_paper in state.scored_papers:
                            paper = scored_paper.paper
                            papers_data.append(
                                {
                                    "arxiv_id": paper.arxiv_id,
                                    "title": paper.title,
                                    "authors": paper.authors,
                                    "summary": paper.summary,
                                    "pdf_url": paper.pdf_url,
                                    "code_url": paper.code_url,
                                    "tldr": paper.tldr,
                                    "relevance_score": scored_paper.score,
                                    "published_date": (
                                        paper.published_date.isoformat() if paper.published_date else None
                                    ),
                                }
                            )

                        storage.save_emailed_papers(user_id, papers_data)
                        logger.info(f"Tracked {len(papers_data)} emailed papers in storage")
                    except Exception as e:
                        logger.warning(f"Failed to track emailed papers in storage: {e}")

            return {"current_step": "workflow_complete"}
        else:
            state.add_error("Email delivery failed")
            return {"current_step": "communication_error", "error_log": state.error_log}

    except Exception as e:
        logger.error(f"Email delivery failed: {str(e)}")
        state.add_error(f"Email delivery failed: {str(e)}")
        return {"current_step": "communication_error", "error_log": state.error_log}
