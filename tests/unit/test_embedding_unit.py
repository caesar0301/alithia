from unittest.mock import Mock

import numpy as np
import pytest

from alithia.core.embedding import EmbeddingService, cosine_similarity_matrix


@pytest.mark.unit
def test_cosine_similarity_matrix_basic():
    a = np.array([[1.0, 0.0], [0.0, 1.0]])
    b = np.array([[1.0, 0.0]])
    sim = cosine_similarity_matrix(a, b)
    assert sim.shape == (2, 1)
    assert sim[0, 0] == 1.0
    assert sim[1, 0] == 0.0


@pytest.mark.unit
def test_rerank_with_mock_reranker():
    service = EmbeddingService.__new__(EmbeddingService)
    service.reranker = Mock()
    # scores correspond to candidates in order
    service.reranker.predict.return_value = [0.1, 0.9, 0.5]

    candidates = [
        {"text": "c0", "id": 0},
        {"text": "c1", "id": 1},
        {"text": "c2", "id": 2},
    ]

    ranked = EmbeddingService.rerank(service, "q", candidates, top_k=2)
    assert [c["id"] for c in ranked] == [1, 2]
    assert ranked[0]["rerank_score"] >= ranked[1]["rerank_score"]


@pytest.mark.unit
def test_rerank_with_empty_candidates():
    service = EmbeddingService.__new__(EmbeddingService)
    ranked = EmbeddingService.rerank(service, "q", [], top_k=3)
    assert ranked == []
