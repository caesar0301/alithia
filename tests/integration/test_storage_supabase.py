"""
Integration tests for Supabase storage backend.

These tests require a configured Supabase instance and should only run
when TEST_SUPABASE_URL and TEST_SUPABASE_KEY environment variables are set.
"""

import uuid
from datetime import datetime

import pytest


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
