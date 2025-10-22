"""
Nodes for the AlithiaLens agent workflow.
"""

import logging
import os
from typing import Literal, Optional

from alithia.core.embedding import EmbeddingService
from alithia.core.llm_utils import get_llm
from alithia.core.pdf_processor import PDFProcessor
from alithia.core.researcher.connected import ZoteroConnection
from alithia.core.table_store import SupabaseTableStore
from alithia.core.vector_store import PineconeVectorStore

from .state import AgentState

logger = logging.getLogger(__name__)


def get_user_input_node(state: AgentState) -> dict:
    """
    In production, this should capture user input from CLI/UX layer.
    For now, we keep the scripted flow for compatibility with __main__.py
    """
    logger.info(">>> Executing Node: get_user_input <<<")

    if state.get("last_node") is None:
        user_input = state.get("user_input") or "load 1234.56789"
    elif state.get("last_node") == "load_paper":
        user_input = "What is the main contribution?"
    elif state.get("last_node") == "process_query":
        user_input = "exit"
    else:
        user_input = "exit"

    logger.info(f"User input: '{user_input}'")
    return {"user_input": user_input}


def route_query_node(state: AgentState) -> Literal["load", "interact", "exit"]:
    logger.info(">>> Executing Node: route_query <<<")
    user_input = state.get("user_input", "").lower()

    if user_input.startswith("load"):
        return "load"
    if user_input in ["exit", "quit"]:
        return "exit"
    return "interact"


def _resolve_pdf_path(identifier: str) -> Optional[str]:
    # For ArXiv/DOI/title inputs, an upstream fetcher should retrieve a local PDF.
    # Here we accept local path directly; if it looks like an arxiv id, we expect the
    # caller to provide a local cache path via env or config in future.
    if os.path.isfile(identifier):
        return os.path.abspath(identifier)
    return None


def load_paper_node(state: AgentState) -> dict:
    """
    Load and process a paper: parse PDF via MinerU, embed chunks, and store in Pinecone/Supabase.
    Expects `user_input` of the form: "load <identifier>" where identifier can be a local PDF path.
    """
    logger.info(">>> Executing Node: load_paper <<<")
    raw = state.get("user_input", "")
    identifier = raw.replace("load ", "").strip()

    pdf_path = _resolve_pdf_path(identifier)
    if not pdf_path:
        # For now, fail fast if not a local path. Future: fetch by arxiv/doi/title
        raise ValueError("Lens currently expects a local PDF path for 'load'.")

    # Initialize services
    pdf = PDFProcessor()
    embed = EmbeddingService()

    # Vector store and table store configs from env
    index_name = os.getenv("PINECONE_INDEX", "alithia-lens")
    namespace = os.getenv("PINECONE_NAMESPACE", None)
    vector = PineconeVectorStore(index_name=index_name, namespace=namespace)

    table = SupabaseTableStore()
    doc_table = os.getenv("SUPABASE_DOC_TABLE", "lens_documents")
    chunk_table = os.getenv("SUPABASE_CHUNK_TABLE", "lens_chunks")

    # Derive a document id
    doc_id = os.path.splitext(os.path.basename(pdf_path))[0]

    # Parse PDF into chunks
    chunks = pdf.process(pdf_path)

    # Embed and upsert vectors
    texts = [c["text"] for c in chunks]
    embeddings = embed.embed_texts(texts)
    vector.upsert_chunks(doc_id=doc_id, chunks=chunks, embeddings=embeddings)

    # Upsert table metadata
    table.upsert_document(
        table=doc_table,
        doc={
            "id": doc_id,
            "source_path": pdf_path,
            "num_chunks": len(chunks),
        },
    )
    table.upsert_chunks(
        table=chunk_table,
        chunks=[
            {
                "id": f"{doc_id}:{c['id']}",
                "doc_id": doc_id,
                "page": c.get("page"),
                "offset": c.get("offset"),
                "text": c.get("text"),
            }
            for c in chunks
        ],
    )

    return {
        "current_paper": {"id": doc_id, "title": os.path.basename(pdf_path)},
        "last_node": "load_paper",
    }


def process_query_node(state: AgentState) -> dict:
    """
    Answer a user's question using hybrid retrieval:
    - Encode query with sentence-transformers
    - Retrieve from Pinecone by vector similarity
    - Rerank with CrossEncoder
    - Generate final answer with cogents LLM using top contexts
    """
    logger.info(">>> Executing Node: process_query <<<")
    query = state.get("user_input")
    current = state.get("current_paper", {}) or {}
    doc_id = current.get("id")
    if not doc_id:
        return {"last_response": "No paper loaded yet.", "last_node": "process_query"}

    # Init services
    embed = EmbeddingService()
    index_name = os.getenv("PINECONE_INDEX", "alithia-lens")
    namespace = os.getenv("PINECONE_NAMESPACE", None)
    vector = PineconeVectorStore(index_name=index_name, namespace=namespace)

    # Encode and retrieve
    qvec = embed.embed_texts([query])[0]
    retrieved = vector.query(query_embedding=qvec, top_k=20, filter={"doc_id": {"$eq": doc_id}})

    # Rerank
    reranked = embed.rerank(query, retrieved, top_k=8)

    # Compose context
    [r.get("text", "") for r in reranked]
    context_block = "\n\n".join([f"[p{r.get('page')}] {r.get('text')}" for r in reranked])

    # Generate with LLM (cogents)
    # Reuse profile if available; otherwise create a minimal temporary profile-like obj
    profile = state.get("profile")
    if profile is None:
        from alithia.core.researcher.profile import ResearcherProfile

        profile = ResearcherProfile(
            zotero=ZoteroConnection(
                zotero_id="",
                zotero_key="",
            ),
        )
    llm = get_llm(profile)
    answer = llm.generate(
        messages=[
            {
                "role": "system",
                "content": "You are AlithiaLens, a precise research assistant. Answer with citations to page numbers when possible.",
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nContext from the paper (chunked):\n{context_block}\n\nProvide a concise, accurate answer grounded in the context. If uncertain, say you are unsure.",
            },
        ]
    )

    return {"last_response": str(answer).strip(), "last_node": "process_query"}
