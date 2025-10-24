"""
Agent nodes for the research agent workflow.
"""

from typing import List

from cogents_core.utils import get_logger

from alithia.core.researcher import ResearcherProfile
from alithia.utils.llm_utils import get_llm
from alithia.utils.zotero_client import filter_corpus, get_zotero_corpus

from .arxiv_paper import get_arxiv_papers
from .email_utils import construct_email_content, send_email
from .models import ScoredPaper
from .recommender import rerank_papers
from .state import AgentState

logger = get_logger(__name__)


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
    if not user_profile.email_notification.receiver:
        errors.append("Receiver email is required")
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
        return {"current_step": "profile_analysis_error"}

    errors = _validate_user_profile(state.config.user_profile)
    if errors:
        for error in errors:
            state.add_error(error)
        return {"current_step": "profile_validation_error"}

    logger.info(f"Profile validated for user: {state.config.user_profile.email}")
    return {"current_step": "profile_analysis_complete"}


def data_collection_node(state: AgentState) -> dict:
    """
    Collect papers from ArXiv and Zotero.

    Args:
        state: Current agent state

    Returns:
        Dictionary with updated state fields
    """
    logger.info("Collecting data from ArXiv and Zotero...")

    if not state.config.user_profile:
        state.add_error("No profile available for data collection")
        return {"current_step": "data_collection_error"}

    try:
        # Get Zotero corpus
        logger.info("Retrieving Zotero corpus...")
        corpus = get_zotero_corpus(
            state.config.user_profile.zotero.zotero_id, state.config.user_profile.zotero.zotero_key
        )
        logger.info(f"Retrieved {len(corpus)} papers from Zotero")

        # Apply ignore patterns
        if state.config.ignore_patterns:
            ignore_patterns = "\n".join(state.config.ignore_patterns)
            logger.info(f"Applying ignore patterns: {ignore_patterns}")
            corpus = filter_corpus(corpus, ignore_patterns)
            logger.info(f"Filtered corpus: {len(corpus)} papers remaining")

        # Get ArXiv papers
        logger.info("Retrieving ArXiv papers...")
        papers = get_arxiv_papers(state.config.query, state.debug_mode)
        logger.info(f"Retrieved {len(papers)} valid papers from ArXiv")

        # Log paper details for debugging
        for i, paper in enumerate(papers):
            logger.info(f"Paper {i+1}: {paper.title[:50]}... (ID: {paper.arxiv_id})")

        # Validate that we have papers to work with
        if not papers:
            state.add_error("No valid papers retrieved from ArXiv")
            return {"current_step": "data_collection_error"}

        logger.info(f"Successfully collected {len(papers)} papers for processing")
        return {"discovered_papers": papers, "zotero_corpus": corpus, "current_step": "data_collection_complete"}

    except Exception as e:
        state.add_error(f"Data collection failed: {str(e)}")
        return {"current_step": "data_collection_error"}


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
            scored_papers = rerank_papers(state.discovered_papers, state.zotero_corpus)
            logger.info(f"Scored {len(scored_papers)} papers")
        except Exception as e:
            state.add_error(f"Relevance assessment failed: {str(e)}")
            # Fallback to basic scoring

            scored_papers = [
                ScoredPaper(paper=paper, score=5.0, relevance_factors={"fallback": 5.0})
                for paper in state.discovered_papers
            ]

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
        return {"current_step": "content_generation_error"}

    try:
        llm = get_llm(state.config.user_profile.llm)

        # Generate TLDR and enrich paper data
        for i, scored_paper in enumerate(state.scored_papers):
            paper = scored_paper.paper
            logger.info(f"Processing paper {i+1}/{len(state.scored_papers)}: {paper.title[:50]}...")
            try:
                paper.process(llm)
                logger.info(f"Successfully processed paper: {paper.title[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to process paper {paper.title[:50]}: {str(e)}")
                # Continue with other papers even if one fails
                continue

        # Construct email content
        email_content = construct_email_content(state.scored_papers)

        logger.info("Content generation complete")
        return {"email_content": email_content, "current_step": "content_generation_complete"}

    except Exception as e:
        state.add_error(f"Content generation failed: {str(e)}")
        return {"current_step": "content_generation_error"}


def communication_node(state: AgentState) -> dict:
    """
    Send email with recommendations.

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
        return {"current_step": "communication_error"}

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
            receiver=state.config.user_profile.email_notification.receiver,
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
            return {"current_step": "workflow_complete"}
        else:
            state.add_error("Email delivery failed")
            return {"current_step": "communication_error"}

    except Exception as e:
        logger.error(f"Email delivery failed: {str(e)}")
        state.add_error(f"Email delivery failed: {str(e)}")
        return {"current_step": "communication_error"}
