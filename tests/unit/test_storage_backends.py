"""
Unit tests for storage backends.
"""

import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from alithia.storage.sqlite import SQLiteStorage


class TestSQLiteStorage:
    """Tests for SQLite storage backend."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            yield str(db_path)

    @pytest.fixture
    def storage(self, temp_db):
        """Create a SQLite storage instance."""
        storage = SQLiteStorage(temp_db)
        storage.connect()
        yield storage
        storage.disconnect()

    def test_connection(self, storage):
        """Test database connection."""
        assert storage.test_connection()

    def test_zotero_papers_cache(self, storage):
        """Test Zotero papers caching."""
        user_id = "test_user"
        papers = [
            {
                "title": "Test Paper 1",
                "authors": ["Author 1", "Author 2"],
                "abstract": "Test abstract",
                "url": "https://example.com/paper1",
                "zotero_item_key": "ITEM001",
                "tags": ["AI", "ML"],
                "date_added": datetime.utcnow().isoformat(),
            },
            {
                "title": "Test Paper 2",
                "authors": ["Author 3"],
                "abstract": "Another abstract",
                "url": "https://example.com/paper2",
                "zotero_item_key": "ITEM002",
                "tags": ["NLP"],
                "date_added": datetime.utcnow().isoformat(),
            },
        ]

        # Cache papers
        storage.cache_zotero_papers(user_id, papers)

        # Retrieve cached papers
        cached = storage.get_zotero_papers(user_id, max_age_hours=24)
        assert cached is not None
        assert len(cached) == 2
        # Check both papers are present (order may vary)
        titles = {p["title"] for p in cached}
        assert "Test Paper 1" in titles
        assert "Test Paper 2" in titles
        keys = {p["zotero_item_key"] for p in cached}
        assert "ITEM001" in keys
        assert "ITEM002" in keys

    def test_zotero_papers_expiration(self, storage):
        """Test that Zotero cache expires correctly."""
        user_id = "test_user"
        papers = [
            {
                "title": "Old Paper",
                "authors": ["Author"],
                "abstract": "Abstract",
                "url": "https://example.com/paper",
                "zotero_item_key": "OLDITEM",
                "tags": [],
                "date_added": datetime.utcnow().isoformat(),
            }
        ]

        storage.cache_zotero_papers(user_id, papers)

        # Try to get with 0 hour max age (should fail)
        cached = storage.get_zotero_papers(user_id, max_age_hours=0)
        assert cached is None or len(cached) == 0

    def test_arxiv_processed_ranges(self, storage):
        """Test ArXiv processed ranges tracking."""
        from datetime import datetime, timedelta

        user_id = "test_user"
        query_categories = "cs.AI+cs.CV"

        # Use recent dates (yesterday and today)
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")
        today = datetime.utcnow().strftime("%Y%m%d")

        # Mark a range as processed
        storage.mark_date_range_processed(user_id, yesterday, yesterday, query_categories, 50)

        # Retrieve processed ranges
        ranges = storage.get_processed_ranges(user_id, query_categories, days_back=30)
        assert len(ranges) == 1
        assert ranges[0]["from_date"] == yesterday
        assert ranges[0]["papers_found"] == 50

        # Mark another range
        storage.mark_date_range_processed(user_id, today, today, query_categories, 30)

        ranges = storage.get_processed_ranges(user_id, query_categories, days_back=30)
        assert len(ranges) == 2

    def test_arxiv_emailed_papers(self, storage):
        """Test ArXiv emailed papers tracking."""
        user_id = "test_user"
        papers = [
            {
                "arxiv_id": "2301.12345",
                "title": "Test Paper",
                "authors": ["Author 1"],
                "summary": "Abstract",
                "pdf_url": "https://arxiv.org/pdf/2301.12345",
                "code_url": "https://github.com/test/repo",
                "tldr": "This is a test paper",
                "relevance_score": 0.85,
                "published_date": datetime.utcnow().isoformat(),
            }
        ]

        # Save emailed papers
        storage.save_emailed_papers(user_id, papers)

        # Check if paper was emailed
        assert storage.is_paper_emailed(user_id, "2301.12345")
        assert not storage.is_paper_emailed(user_id, "9999.99999")

        # Get emailed papers
        emailed = storage.get_emailed_papers(user_id, days_back=30)
        assert len(emailed) == 1
        assert emailed[0]["arxiv_id"] == "2301.12345"

    def test_parsed_paper_cache(self, storage):
        """Test parsed paper caching."""
        user_id = "test_user"
        file_hash = "abc123def456"
        paper_data = {
            "file_path": "/path/to/paper.pdf",
            "file_name": "paper.pdf",
            "file_hash": file_hash,
            "title": "Test Paper",
            "authors": ["Author 1", "Author 2"],
            "abstract": "Test abstract",
            "full_text": "Full paper text here...",
            "sections": {"Introduction": "Intro text", "Methods": "Methods text"},
            "figures": ["Figure 1", "Figure 2"],
            "tables": ["Table 1"],
        }

        # Cache parsed paper
        paper_id = storage.cache_parsed_paper(user_id, paper_data)
        assert paper_id is not None

        # Retrieve cached paper
        cached = storage.get_parsed_paper(user_id, file_hash)
        assert cached is not None
        assert cached["title"] == "Test Paper"
        assert len(cached["authors"]) == 2
        assert cached["sections"]["Introduction"] == "Intro text"

        # Try to get non-existent paper
        not_found = storage.get_parsed_paper(user_id, "nonexistent_hash")
        assert not_found is None

    def test_query_history(self, storage):
        """Test query history tracking."""
        user_id = "test_user"
        paper_id = str(uuid.uuid4())

        # First, cache a paper to reference
        paper_data = {
            "file_path": "/path/to/paper.pdf",
            "file_name": "paper.pdf",
            "file_hash": "hash123",
            "title": "Test Paper",
            "authors": [],
            "abstract": None,
            "full_text": "Text",
            "sections": {},
            "figures": [],
            "tables": [],
        }
        paper_id = storage.cache_parsed_paper(user_id, paper_data)

        # Save queries
        storage.save_query(
            user_id,
            paper_id,
            "What is machine learning?",
            [{"section": "Introduction", "text": "ML is..."}],
            {"intro": 0.95},
        )

        storage.save_query(
            user_id,
            paper_id,
            "How does the model work?",
            [{"section": "Methods", "text": "The model..."}],
            {"methods": 0.88},
        )

        # Get query history
        history = storage.get_query_history(user_id, paper_id=paper_id, limit=10)
        assert len(history) == 2

        # Get all queries for user
        all_history = storage.get_query_history(user_id, limit=50)
        assert len(all_history) >= 2


@pytest.mark.integration
class TestSupabaseStorage:
    """Integration tests for Supabase storage backend (requires Supabase setup)."""

    @pytest.fixture
    def storage(self):
        """Create a Supabase storage instance (skipped if not configured)."""
        import os

        url = os.getenv("TEST_SUPABASE_URL")
        key = os.getenv("TEST_SUPABASE_KEY")

        if not url or not key:
            pytest.skip("Supabase credentials not configured for testing")

        from alithia.storage.supabase import SupabaseStorage

        storage = SupabaseStorage(url, key)
        try:
            storage.connect()
            yield storage
            storage.disconnect()
        except Exception as e:
            pytest.skip(f"Failed to connect to Supabase: {e}")

    def test_connection(self, storage):
        """Test Supabase connection."""
        # Connection is tested in fixture
        assert storage is not None

    def test_zotero_cache_basic(self, storage):
        """Basic test for Supabase Zotero caching."""
        user_id = f"test_user_{uuid.uuid4()}"
        papers = [
            {
                "title": "Supabase Test Paper",
                "authors": ["Test Author"],
                "abstract": "Test",
                "url": "https://example.com",
                "zotero_item_key": f"TEST_{uuid.uuid4()}",
                "tags": ["test"],
                "date_added": datetime.utcnow().isoformat(),
            }
        ]

        storage.cache_zotero_papers(user_id, papers)
        cached = storage.get_zotero_papers(user_id, max_age_hours=24)

        assert cached is not None
        assert len(cached) >= 1


class TestStorageFactory:
    """Tests for storage factory."""

    def test_sqlite_fallback(self):
        """Test that SQLite is used when Supabase is not configured."""
        from alithia.storage.factory import get_storage_backend

        config = {
            "storage": {
                "backend": "supabase",
                "fallback_to_sqlite": True,
                "sqlite_path": ":memory:",
            },
            "supabase": {},  # Empty Supabase config should trigger fallback
        }

        backend = get_storage_backend(config)
        assert isinstance(backend, SQLiteStorage)
        backend.disconnect()

    def test_sqlite_direct(self):
        """Test direct SQLite backend selection."""
        from alithia.storage.factory import get_storage_backend

        config = {
            "storage": {
                "backend": "sqlite",
                "sqlite_path": ":memory:",
            }
        }

        backend = get_storage_backend(config)
        assert isinstance(backend, SQLiteStorage)
        backend.disconnect()
