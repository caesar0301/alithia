import numpy as np
import pytest
import requests

from alithia.core.embedding import EmbeddingService


@pytest.mark.integration
@pytest.mark.slow
def test_embedding_service_embed_texts_returns_vectors():
    # Use smaller models to reduce resource usage in CI
    try:
        service = EmbeddingService(
            embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
            reranker_model_name="cross-encoder/ms-marco-MiniLM-L-2-v2",
        )
        texts = ["hello world", "machine learning"]
        embs = service.embed_texts(texts)

        assert isinstance(embs, np.ndarray)
        assert embs.shape[0] == 2
        assert embs.shape[1] > 10
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        pytest.skip(f"Skipping test due to network connection issue: {e}")
