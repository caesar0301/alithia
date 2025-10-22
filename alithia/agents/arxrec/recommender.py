"""
Paper recommendation and reranking utilities.
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

from ...core.paper import ArxivPaper, ScoredPaper


def rerank_papers(
    papers: List[ArxivPaper], corpus: List[Dict[str, Any]], model_name: str = "avsolatorio/GIST-small-Embedding-v0"
) -> List[ScoredPaper]:
    """
    Rerank papers based on relevance to user's research corpus.

    Args:
        papers: List of papers to score
        corpus: User's Zotero corpus for comparison
        model_name: Sentence transformer model to use

    Returns:
        List of scored papers sorted by relevance
    """
    if not papers or not corpus:
        return [ScoredPaper(paper=paper, score=0.0) for paper in papers]

    # Initialize sentence transformer
    encoder = SentenceTransformer(model_name)

    # Sort corpus by date (newest first)
    sorted_corpus = sorted(
        corpus, key=lambda x: datetime.strptime(x["data"]["dateAdded"], "%Y-%m-%dT%H:%M:%SZ"), reverse=True
    )

    # Calculate time decay weights
    time_decay_weight = 1 / (1 + np.log10(np.arange(len(sorted_corpus)) + 1))
    time_decay_weight = time_decay_weight / time_decay_weight.sum()

    # Encode corpus abstracts
    corpus_texts = [paper["data"]["abstractNote"] for paper in sorted_corpus]
    corpus_embeddings = encoder.encode(corpus_texts)

    # Encode paper summaries
    paper_texts = [paper.summary for paper in papers]
    paper_embeddings = encoder.encode(paper_texts)

    # Calculate similarity scores
    similarities = encoder.similarity(paper_embeddings, corpus_embeddings)

    # Calculate weighted scores
    scores = (similarities * time_decay_weight).sum(axis=1) * 10

    # Create scored papers
    scored_papers = []
    for paper, score in zip(papers, scores):
        scored_paper = ScoredPaper(
            paper=paper,
            score=float(score),
            relevance_factors={"corpus_similarity": float(score), "corpus_size": len(corpus)},
        )
        scored_papers.append(scored_paper)

    # Sort by score (highest first)
    scored_papers.sort(key=lambda x: x.score, reverse=True)

    return scored_papers
