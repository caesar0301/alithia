import os
from typing import Any, Dict, List, Optional

import numpy as np
from pinecone import Pinecone


class PineconeVectorStore:
    def __init__(self, index_name: str, namespace: Optional[str] = None) -> None:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY is required in environment for vector store")
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)
        self.namespace = namespace

    def upsert_chunks(self, doc_id: str, chunks: List[Dict[str, Any]], embeddings: np.ndarray) -> None:
        vectors = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}:{chunk['id']}"
            meta = {
                "doc_id": doc_id,
                "page": chunk.get("page"),
                "offset": chunk.get("offset"),
                "text": chunk.get("text"),
            }
            vectors.append({"id": chunk_id, "values": embeddings[i].tolist(), "metadata": meta})
        self.index.upsert(vectors=vectors, namespace=self.namespace)

    def upsert_documents(
        self, docs: List[Dict[str, Any]], embeddings: np.ndarray, id_key: str = "id", text_key: str = "text"
    ) -> None:
        vectors = []
        for i, d in enumerate(docs):
            doc_id = str(d[id_key])
            meta = {k: v for k, v in d.items() if k != text_key}
            meta[text_key] = d.get(text_key)
            vectors.append({"id": doc_id, "values": embeddings[i].tolist(), "metadata": meta})
        self.index.upsert(vectors=vectors, namespace=self.namespace)

    def query(
        self, query_embedding: np.ndarray, top_k: int = 12, filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        res = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            include_metadata=True,
            namespace=self.namespace,
            filter=filter,
        )
        matches = getattr(res, "matches", []) or res.get("matches", [])
        results: List[Dict[str, Any]] = []
        for m in matches:
            meta = m.get("metadata") if isinstance(m, dict) else m.metadata
            score = m.get("score") if isinstance(m, dict) else m.score
            results.append(
                {
                    "id": m.get("id") if isinstance(m, dict) else m.id,
                    "metadata": meta,
                    "score": float(score) if score is not None else None,
                }
            )
        return results
