from typing import Any, Dict, List

import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer


class EmbeddingService:
    def __init__(
        self,
        embedding_model_name: str = "mixedbread-ai/mxbai-embed-large-v1",
        reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        self.embedder = SentenceTransformer(embedding_model_name)
        self.reranker = CrossEncoder(reranker_model_name)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        embeddings = self.embedder.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )
        return embeddings

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        pairs = [(query, c.get("text", "")) for c in candidates]
        scores = self.reranker.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: float(x[1]), reverse=True)
        return [dict(item[0], rerank_score=float(item[1])) for item in ranked[:top_k]]


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.dot(a, b.T)
