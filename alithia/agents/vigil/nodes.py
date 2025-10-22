"""
Nodes for the AlithiaVigil agent workflow.
"""

import logging
import os
from typing import List

import feedparser

from alithia.core.email_utils import construct_email_content, send_email
from alithia.core.embedding import EmbeddingService
from alithia.core.paper import ArxivPaper, ScoredPaper
from alithia.core.table_store import SupabaseTableStore
from alithia.core.vector_store import PineconeVectorStore

from .state import AgentState

logger = logging.getLogger(__name__)


def _fetch_arxiv_by_topics(topics: List[str]) -> List[ArxivPaper]:
    results: List[ArxivPaper] = []
    for topic in topics:
        rss = feedparser.parse(f"https://rss.arxiv.org/atom/{topic}")
        ids = [entry.id.removeprefix("oai:arXiv.org:") for entry in rss.entries]
        # Minimal metadata; Vigil primarily needs title/summary/links for alerting
        for e in rss.entries:
            try:
                paper = ArxivPaper(
                    title=getattr(e, "title", ""),
                    summary=getattr(e, "summary", ""),
                    authors=[a.name for a in getattr(e, "authors", [])] if hasattr(e, "authors") else [],
                    arxiv_id=e.id.removeprefix("oai:arXiv.org:") if hasattr(e, "id") else "",
                    pdf_url=getattr(e, "link", ""),
                )
                results.append(paper)
            except Exception:
                continue
    return results


def scan_sources_node(state: AgentState) -> dict:
    """
    Scan sources (ArXiv RSS by topics for now). Store items in Supabase and Pinecone for reuse.
    """
    logger.info(">>> Executing Node: scan_sources <<<")

    topics = state.config.topics or []
    if not topics:
        logger.info("No topics provided to Vigil. Skipping scan.")
        return {"discovered_papers": [], "current_step": "scan_complete"}

    papers = _fetch_arxiv_by_topics(topics)

    # Persist minimal metadata for auditing
    supa = SupabaseTableStore()
    doc_table = os.getenv("SUPABASE_VIGIL_DOC_TABLE", "vigil_items")
    rows = []
    for p in papers:
        rows.append(
            {
                "id": p.arxiv_id or p.title[:120],
                "title": p.title,
                "summary": p.summary,
                "pdf_url": p.pdf_url,
                "source": "arxiv",
            }
        )
    if rows:
        supa.upsert_rows(doc_table, rows)

    return {"discovered_papers": papers, "current_step": "scan_complete"}


def filter_results_node(state: AgentState) -> dict:
    """
    Embed user topic string(s) and filter discovered items by similarity.
    Uses sentence-transformers for both embedding and optional reranking.
    """
    logger.info(">>> Executing Node: filter_results <<<")

    papers: List[ArxivPaper] = state.get("discovered_papers", [])
    if not papers:
        return {"scored_papers": [], "current_step": "filter_complete"}

    topics = state.config.topics or []
    query_text = "; ".join(topics)

    embed = EmbeddingService()

    # Encode papers and query
    paper_texts = [f"{p.title}\n\n{p.summary}" for p in papers]
    paper_emb = embed.embed_texts(paper_texts)
    query_emb = embed.embed_texts([query_text])[0]

    # Persist embeddings in Pinecone for Vigil
    index_name = os.getenv("PINECONE_INDEX", "alithia-research")
    namespace = os.getenv("PINECONE_VIGIL_NAMESPACE", "vigil")
    vector = PineconeVectorStore(index_name=index_name, namespace=namespace)
    docs_for_upsert = []
    for p, text in zip(papers, paper_texts):
        pid = p.arxiv_id or (p.title[:120] if p.title else None)
        if not pid:
            continue
        docs_for_upsert.append(
            {
                "id": pid,
                "text": text,
                "title": p.title,
                "arxiv_id": p.arxiv_id,
                "pdf_url": p.pdf_url,
                "source": "arxiv",
            }
        )
    if docs_for_upsert:
        vector.upsert_documents(docs_for_upsert, paper_emb, id_key="id", text_key="text")

    # Similarity and basic score
    sims = (paper_emb @ query_emb.reshape(-1, 1)).reshape(-1)
    scored = [
        ScoredPaper(paper=p, score=float(s * 10.0), relevance_factors={"topic_similarity": float(s)})
        for p, s in zip(papers, sims)
    ]

    # Rerank top N with CrossEncoder for better fidelity
    scored.sort(key=lambda x: x.score, reverse=True)
    top_candidates = [
        {"text": f"{sp.paper.title}\n\n{sp.paper.summary}", "paper": sp.paper, "base_score": sp.score}
        for sp in scored[:50]
    ]
    reranked = embed.rerank(query_text, top_candidates, top_k=min(20, len(top_candidates)))

    # Map back to ScoredPaper
    final_scored: List[ScoredPaper] = []
    for r in reranked:
        p = r.get("paper")
        score = float(r.get("rerank_score", 0.0) * 10.0)
        final_scored.append(
            ScoredPaper(
                paper=p,
                score=score,
                relevance_factors={
                    "topic_similarity": r.get("base_score", 0.0),
                    "rerank": float(r.get("rerank_score", 0.0)),
                },
            )
        )

    return {"scored_papers": final_scored, "current_step": "filter_complete"}


def send_alert_node(state: AgentState) -> dict:
    """
    Send digest via email using existing email utils.
    """
    logger.info(">>> Executing Node: send_alert <<<")

    scored: List[ScoredPaper] = state.get("scored_papers", [])
    if not scored:
        logger.info("No relevant items; skip sending unless SEND_EMPTY=true in profile.")

    # Reuse email configuration from profile if present
    profile = state.config.user_profile
    if not profile:
        logger.info("No profile provided; skipping email delivery.")
        return {"current_step": "workflow_complete"}

    email_content = construct_email_content(scored)
    try:
        ok = send_email(
            sender=profile.email_notification.sender,
            receiver=profile.email_notification.receiver,
            password=profile.email_notification.sender_password,
            smtp_server=profile.email_notification.smtp_server,
            smtp_port=profile.email_notification.smtp_port,
            html_content=email_content.html_content,
        )
        if ok:
            logger.info("Vigil alert email sent.")
    except Exception as e:
        logger.error(f"Failed to send Vigil alert: {e}")

    return {"current_step": "workflow_complete"}
