"""
Paper recommendation and reranking utilities.
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from .models import ArxivPaper, ScoredPaper


class PaperReranker:
    def __init__(self, papers: List[ArxivPaper], corpus: List[Dict[str, Any]]):
        self.papers = papers
        self.corpus = corpus

    def rerank_flashrank(self, model_name: str = "ms-marco-MiniLM-L-12-v2") -> List[ScoredPaper]:
        """
        Rerank papers based on relevance to user's research corpus.

        Args:
            papers: List of papers to score
            corpus: User's Zotero corpus for comparison
            model_name: FlashRank model to use (default: ms-marco-MiniLM-L-12-v2)

        Returns:
            List of scored papers sorted by relevance
        """
        try:
            from flashrank import Ranker, RerankRequest
        except ImportError:
            raise ImportError("FlashRank is not installed. Please install it using `pip install flashrank`.")

        if not self.papers or not self.corpus:
            return [ScoredPaper(paper=paper, score=0.0) for paper in self.papers]

        # Initialize FlashRank ranker
        ranker = Ranker(model_name=model_name, cache_dir="/tmp/flashrank_cache")

        # Sort corpus by date (newest first)
        sorted_corpus = sorted(
            self.corpus, key=lambda x: datetime.strptime(x["data"]["dateAdded"], "%Y-%m-%dT%H:%M:%SZ"), reverse=True
        )

        # Calculate time decay weights
        time_decay_weight = 1 / (1 + np.log10(np.arange(len(sorted_corpus)) + 1))
        time_decay_weight = time_decay_weight / time_decay_weight.sum()

        # Prepare corpus abstracts as passages
        corpus_passages = [{"text": paper["data"]["abstractNote"]} for paper in sorted_corpus]

        # Score each paper against the entire corpus
        scored_papers = []
        for paper in self.papers:
            # Create rerank request for this paper against all corpus passages
            rerank_request = RerankRequest(query=paper.summary, passages=corpus_passages)

            # Get reranking results
            results = ranker.rerank(rerank_request)

            # Create a mapping from text to corpus index
            text_to_idx = {paper["data"]["abstractNote"]: idx for idx, paper in enumerate(sorted_corpus)}

            # Calculate weighted score based on corpus relevance and time decay
            weighted_scores = []
            for result in results:
                relevance_score = result["score"]
                # Find which corpus paper this result corresponds to
                idx = text_to_idx[result["text"]]
                weighted_score = relevance_score * time_decay_weight[idx]
                weighted_scores.append(weighted_score)

            # Sum weighted scores and scale
            final_score = sum(weighted_scores) * 10

            scored_paper = ScoredPaper(
                paper=paper,
                score=float(final_score),
                relevance_factors={"corpus_similarity": float(final_score), "corpus_size": len(self.corpus)},
            )
            scored_papers.append(scored_paper)

        # Sort by score (highest first)
        scored_papers.sort(key=lambda x: x.score, reverse=True)

        return scored_papers

    def rerank_sentence_transformer(self, model_name: str = "avsolatorio/GIST-small-Embedding-v0") -> List[ScoredPaper]:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "SentenceTransformer is not installed. Please install it using `pip install sentence-transformers`."
            )

        if not self.papers or not self.corpus:
            return [ScoredPaper(paper=paper, score=0.0) for paper in self.papers]

        # Initialize sentence transformer
        encoder = SentenceTransformer(model_name)

        # Sort corpus by date (newest first)
        sorted_corpus = sorted(
            self.corpus, key=lambda x: datetime.strptime(x["data"]["dateAdded"], "%Y-%m-%dT%H:%M:%SZ"), reverse=True
        )

        # Calculate time decay weights
        time_decay_weight = 1 / (1 + np.log10(np.arange(len(sorted_corpus)) + 1))
        time_decay_weight = time_decay_weight / time_decay_weight.sum()

        # Encode corpus abstracts
        corpus_texts = [paper["data"]["abstractNote"] for paper in sorted_corpus]
        corpus_embeddings = encoder.encode(corpus_texts)

        # Encode paper summaries
        paper_texts = [paper.summary for paper in self.papers]
        paper_embeddings = encoder.encode(paper_texts)

        # Calculate similarity scores
        similarities = encoder.similarity(paper_embeddings, corpus_embeddings)

        # Calculate weighted scores
        scores = (similarities * time_decay_weight).sum(axis=1) * 10

        # Create scored papers
        scored_papers = []
        for paper, score in zip(self.__dir__papers, scores):
            scored_paper = ScoredPaper(
                paper=paper,
                score=float(score),
                relevance_factors={"corpus_similarity": float(score), "corpus_size": len(self.corpus)},
            )
            scored_papers.append(scored_paper)

        # Sort by score (highest first)
        scored_papers.sort(key=lambda x: x.score, reverse=True)

        return scored_papers
