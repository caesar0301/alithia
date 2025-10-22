"""
Unit tests for ArXiv client functionality.

These tests use mocks to avoid real API calls and external dependencies.
"""

from unittest.mock import Mock, patch

import pytest

from alithia.core.arxiv_client import get_arxiv_papers


class TestArxivClientUnit:
    """Unit tests for ArXiv client functionality."""

    @pytest.mark.unit
    def test_get_arxiv_papers_debug_mode_mocked(self):
        """Test get_arxiv_papers in debug mode with mocked dependencies."""
        # Mock the arxiv client and results
        mock_paper = Mock()
        mock_paper.title = "Test Paper"
        mock_paper.summary = "Test summary"
        mock_author = Mock()
        mock_author.name = "Test Author"
        mock_paper.authors = [mock_author]
        mock_paper.get_short_id.return_value = "1234.5678v1"
        mock_paper.pdf_url = "http://example.com/paper.pdf"
        mock_paper.published = "2024-01-01"

        with patch("alithia.core.arxiv_client.arxiv") as mock_arxiv:
            # Mock the client and search
            mock_client = Mock()
            mock_search = Mock()
            mock_arxiv.Client.return_value = mock_client
            mock_arxiv.Search.return_value = mock_search
            mock_arxiv.SortCriterion.SubmittedDate = "submitted_date"
            mock_client.results.return_value = [mock_paper]

            # Call the function
            papers = get_arxiv_papers("cs.AI", debug=True)

            # Verify the results
            assert len(papers) == 1
            assert papers[0].title == "Test Paper"
            assert papers[0].summary == "Test summary"
            assert papers[0].authors == ["Test Author"]
            assert papers[0].arxiv_id == "1234.5678"
            assert papers[0].pdf_url == "http://example.com/paper.pdf"

    @pytest.mark.unit
    def test_get_arxiv_papers_invalid_query_mocked(self):
        """Test get_arxiv_papers with invalid query using mocked feed."""
        # Mock feedparser to return an error feed
        mock_feed = Mock()
        mock_feed.feed = {"title": "Feed error for query"}

        with patch("alithia.core.arxiv_client.feedparser") as mock_feedparser:
            mock_feedparser.parse.return_value = mock_feed

            # Should raise ValueError for invalid query
            with pytest.raises(ValueError, match="Invalid ARXIV_QUERY"):
                get_arxiv_papers("invalid_query")

    @pytest.mark.unit
    def test_get_arxiv_papers_empty_feed_mocked(self):
        """Test get_arxiv_papers with empty feed results."""
        # Mock feedparser to return empty feed
        mock_feed = Mock()
        mock_feed.feed = {"title": "ArXiv Query Results"}
        mock_feed.entries = []

        with patch("alithia.core.arxiv_client.feedparser") as mock_feedparser:
            mock_feedparser.parse.return_value = mock_feed

            # Should return empty list
            papers = get_arxiv_papers("cs.AI")
            assert papers == []

    @pytest.mark.unit
    def test_get_arxiv_papers_with_papers_mocked(self):
        """Test get_arxiv_papers with mocked paper results."""
        # Mock feed entry
        mock_entry = Mock()
        mock_entry.id = "oai:arXiv.org:1234.5678"
        mock_entry.arxiv_announce_type = "new"

        # Mock feed
        mock_feed = Mock()
        mock_feed.feed = {"title": "ArXiv Query Results"}
        mock_feed.entries = [mock_entry]

        # Mock arxiv paper
        mock_paper = Mock()
        mock_paper.title = "Test Paper"
        mock_paper.summary = "Test summary"
        mock_author = Mock()
        mock_author.name = "Test Author"
        mock_paper.authors = [mock_author]
        mock_paper.get_short_id.return_value = "1234.5678v1"
        mock_paper.pdf_url = "http://example.com/paper.pdf"
        mock_paper.published = "2024-01-01"

        with (
            patch("alithia.core.arxiv_client.feedparser") as mock_feedparser,
            patch("alithia.core.arxiv_client.arxiv") as mock_arxiv,
        ):
            mock_feedparser.parse.return_value = mock_feed

            # Mock the client and search
            mock_client = Mock()
            mock_search = Mock()
            mock_arxiv.Client.return_value = mock_client
            mock_arxiv.Search.return_value = mock_search
            mock_client.results.return_value = [mock_paper]

            # Call the function
            papers = get_arxiv_papers("cs.AI")

            # Verify the results
            assert len(papers) == 1
            assert papers[0].title == "Test Paper"
            assert papers[0].arxiv_id == "1234.5678"
