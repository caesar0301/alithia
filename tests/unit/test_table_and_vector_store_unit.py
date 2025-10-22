from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from alithia.core.table_store import SupabaseTableStore
from alithia.core.vector_store import PineconeVectorStore


@pytest.mark.unit
def test_supabase_table_store_env_missing_raises():
    with patch("alithia.core.table_store.os.getenv", return_value=None):
        with pytest.raises(RuntimeError):
            SupabaseTableStore()


@pytest.mark.unit
def test_supabase_table_store_calls_client_methods():
    with (
        patch("alithia.core.table_store.os.getenv", side_effect=["url", "key"]),
        patch("alithia.core.table_store.create_client") as mock_create,
    ):
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        store = SupabaseTableStore()

        store.upsert_document("t", {"id": 1})
        mock_client.table.return_value.upsert.assert_called()

        store.upsert_rows("t", [{"id": 1}])
        mock_client.table.return_value.upsert.assert_called()

        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = {
            "data": [{"id": "x"}]
        }
        doc = store.get_document("t", "x")
        assert doc["id"] == "x"


@pytest.mark.unit
def test_pinecone_vector_store_env_missing_raises():
    with patch("alithia.core.vector_store.os.getenv", return_value=None):
        with pytest.raises(RuntimeError):
            PineconeVectorStore(index_name="idx")


@pytest.mark.unit
def test_pinecone_vector_store_calls_upsert_and_query():
    with (
        patch("alithia.core.vector_store.os.getenv", return_value="abc"),
        patch("alithia.core.vector_store.Pinecone") as mock_pc,
    ):
        mock_index = MagicMock()
        mock_pc.return_value.Index.return_value = mock_index

        store = PineconeVectorStore(index_name="idx", namespace="ns")

        chunks = [{"id": "c0", "text": "hello", "page": 1, "offset": 0}]
        embs = np.array([[0.1, 0.2]])
        store.upsert_chunks("doc", chunks, embs)
        mock_index.upsert.assert_called()

        docs = [{"id": "d0", "text": "hi", "meta": 1}]
        store.upsert_documents(docs, embs)
        assert mock_index.upsert.call_count >= 2

        mock_index.query.return_value = {
            "matches": [
                {"id": "d0", "metadata": {"text": "hi"}, "score": 0.99},
            ]
        }
        res = store.query(embs[0], top_k=1)
        assert res[0]["id"] == "d0"
        assert res[0]["score"] == 0.99
