"""
Unit tests for the enhanced ArXiv paper fetcher module.

Tests cover:
- Query building utilities
- ArxivPaperFetcher class with multiple strategies
- Convenience functions
- Retry logic and fallback behavior
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from alithia.models import ArxivPaper
from alithia.utils.arxiv_paper_fetcher import (
    ArxivPaperFetcher,
    FetchResult,
    FetchStrategy,
    _build_category_query,
    build_arxiv_search_query,
    fetch_arxiv_papers,
    get_arxiv_papers_feed,
    get_arxiv_papers_search,
)

# ============================================================================
# Query Building Utilities Tests
# ============================================================================


@pytest.mark.unit
def test_build_category_query_single_category():
    """Test building category query with a single category."""
    query = _build_category_query("cs.AI")
    assert query == "cat:cs.AI"


@pytest.mark.unit
def test_build_category_query_multiple_categories():
    """Test building category query with multiple categories."""
    query = _build_category_query("cs.AI+cs.CV+cs.LG")
    assert query == "cat:cs.AI OR cat:cs.CV OR cat:cs.LG"


@pytest.mark.unit
def test_build_category_query_with_spaces():
    """Test building category query handles spaces around categories."""
    query = _build_category_query("cs.AI + cs.CV + cs.LG")
    assert query == "cat:cs.AI OR cat:cs.CV OR cat:cs.LG"


@pytest.mark.unit
def test_build_arxiv_search_query_single_category():
    """Test building search query with a single category."""
    query = build_arxiv_search_query("cs.AI", "202510250000", "202510252359")
    assert query == "(cat:cs.AI) AND submittedDate:[202510250000 TO 202510252359]"


@pytest.mark.unit
def test_build_arxiv_search_query_multiple_categories():
    """Test building search query with multiple categories."""
    query = build_arxiv_search_query("cs.AI+cs.CV+cs.LG+cs.CL", "202510250000", "202510252359")
    expected = "(cat:cs.AI OR cat:cs.CV OR cat:cs.LG OR cat:cs.CL) AND submittedDate:[202510250000 TO 202510252359]"
    assert query == expected


@pytest.mark.unit
def test_build_arxiv_search_query_with_spaces():
    """Test building search query handles spaces in category list."""
    query = build_arxiv_search_query("cs.AI + cs.CV + cs.LG", "202510250000", "202510252359")
    expected = "(cat:cs.AI OR cat:cs.CV OR cat:cs.LG) AND submittedDate:[202510250000 TO 202510252359]"
    assert query == expected


@pytest.mark.unit
def test_build_arxiv_search_query_different_date_formats():
    """Test building search query with different date/time values."""
    query = build_arxiv_search_query("cs.AI", "202501010000", "202512312359")
    assert query == "(cat:cs.AI) AND submittedDate:[202501010000 TO 202512312359]"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_paper():
    """Create a mock ArxivPaper for testing."""
    return ArxivPaper(
        title="Test Paper",
        summary="This is a test abstract.",
        authors=["Alice", "Bob"],
        arxiv_id="2312.12345",
        pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
        published_date=datetime(2023, 12, 23),
    )


@pytest.fixture
def mock_arxiv_result():
    """Create a mock arxiv.Result object."""
    result = Mock()
    result.title = "Test Paper"
    result.summary = "This is a test abstract."
    result.authors = [Mock(name="Alice"), Mock(name="Bob")]
    result.get_short_id = Mock(return_value="2312.12345v1")
    result.pdf_url = "https://arxiv.org/pdf/2312.12345.pdf"
    result.published = datetime(2023, 12, 23)
    return result


# ============================================================================
# ArxivPaperFetcher Class Tests
# ============================================================================


@pytest.mark.unit
def test_fetch_result_initialization():
    """Test FetchResult initialization."""
    result = FetchResult()
    assert result.papers == []
    assert result.strategy_used is None
    assert result.success is False
    assert result.error_message is None
    assert result.retry_count == 0
    assert result.elapsed_time == 0.0


@pytest.mark.unit
def test_arxiv_paper_fetcher_initialization():
    """Test ArxivPaperFetcher initialization."""
    fetcher = ArxivPaperFetcher(max_retries=5, retry_delay=2.0, timeout=60, enable_web_fallback=False)

    assert fetcher.max_retries == 5
    assert fetcher.retry_delay == 2.0
    assert fetcher.timeout == 60
    assert fetcher.enable_web_fallback is False
    assert fetcher.session is not None
    assert fetcher.arxiv_client is not None


# ============================================================================
# Fetch Strategies Tests
# ============================================================================


@pytest.mark.unit
def test_fetch_papers_debug_mode(mock_paper, mock_arxiv_result):
    """Test fetch_papers in debug mode limits results."""
    fetcher = ArxivPaperFetcher()

    with patch.object(fetcher, "_fetch_with_api_search") as mock_api:
        mock_api.return_value = FetchResult(papers=[mock_paper], strategy_used=FetchStrategy.API_SEARCH, success=True)

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359", max_results=100, debug=True
        )

        assert result.success
        assert len(result.papers) == 1
        # Verify debug mode limited max_results to 5
        call_args = mock_api.call_args[0]
        assert call_args[3] == 5  # max_results argument


@pytest.mark.unit
def test_fetch_papers_api_search_success(mock_paper):
    """Test successful API search strategy."""
    fetcher = ArxivPaperFetcher()

    with patch.object(fetcher, "_fetch_with_api_search") as mock_api:
        mock_api.return_value = FetchResult(
            papers=[mock_paper, mock_paper], strategy_used=FetchStrategy.API_SEARCH, success=True
        )

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI+cs.CV", from_time="202312230000", to_time="202312232359", max_results=200
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.API_SEARCH
        assert len(result.papers) == 2
        mock_api.assert_called_once()


@pytest.mark.unit
def test_fetch_papers_rss_fallback(mock_paper):
    """Test fallback to RSS feed when API fails."""
    fetcher = ArxivPaperFetcher()

    with (
        patch.object(fetcher, "_fetch_with_api_search") as mock_api,
        patch.object(fetcher, "_fetch_with_rss_feed") as mock_rss,
    ):

        # API fails
        mock_api.return_value = FetchResult(
            papers=[], strategy_used=FetchStrategy.API_SEARCH, success=False, error_message="API error"
        )

        # RSS succeeds
        mock_rss.return_value = FetchResult(papers=[mock_paper], strategy_used=FetchStrategy.RSS_FEED, success=True)

        result = fetcher.fetch_papers(arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359")

        assert result.success
        assert result.strategy_used == FetchStrategy.RSS_FEED
        assert len(result.papers) == 1
        mock_api.assert_called_once()
        mock_rss.assert_called_once()


@pytest.mark.unit
def test_fetch_papers_web_scraper_fallback(mock_paper):
    """Test fallback to web scraper when API and RSS fail."""
    fetcher = ArxivPaperFetcher(enable_web_fallback=True)

    with (
        patch.object(fetcher, "_fetch_with_api_search") as mock_api,
        patch.object(fetcher, "_fetch_with_rss_feed") as mock_rss,
        patch.object(fetcher, "_fetch_with_web_scraper") as mock_web,
    ):

        # API fails
        mock_api.return_value = FetchResult(
            papers=[], strategy_used=FetchStrategy.API_SEARCH, success=False, error_message="API error"
        )

        # RSS fails
        mock_rss.return_value = FetchResult(
            papers=[], strategy_used=FetchStrategy.RSS_FEED, success=False, error_message="RSS error"
        )

        # Web scraper succeeds
        mock_web.return_value = FetchResult(papers=[mock_paper], strategy_used=FetchStrategy.WEB_SCRAPER, success=True)

        result = fetcher.fetch_papers(arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359")

        assert result.success
        assert result.strategy_used == FetchStrategy.WEB_SCRAPER
        assert len(result.papers) == 1
        mock_api.assert_called_once()
        mock_rss.assert_called_once()
        mock_web.assert_called_once()


@pytest.mark.unit
def test_fetch_papers_all_strategies_fail():
    """Test when all fetch strategies fail."""
    fetcher = ArxivPaperFetcher(enable_web_fallback=True)

    with (
        patch.object(fetcher, "_fetch_with_api_search") as mock_api,
        patch.object(fetcher, "_fetch_with_rss_feed") as mock_rss,
        patch.object(fetcher, "_fetch_with_web_scraper") as mock_web,
    ):

        # All strategies fail
        for mock in [mock_api, mock_rss, mock_web]:
            mock.return_value = FetchResult(papers=[], success=False, error_message="Failed")

        result = fetcher.fetch_papers(arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359")

        assert not result.success
        assert result.strategy_used is None
        assert len(result.papers) == 0
        assert result.error_message == "All fetch strategies failed"


# ============================================================================
# Retry Logic Tests
# ============================================================================


@pytest.mark.unit
def test_fetch_with_api_search_retry_logic(mock_paper):
    """Test retry logic in API search."""
    fetcher = ArxivPaperFetcher(max_retries=3, retry_delay=0.1)

    with patch.object(fetcher.arxiv_client, "results") as mock_results:
        # All three attempts fail
        mock_results.side_effect = [Exception("Network error"), Exception("Timeout"), Exception("Connection timeout")]

        with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaper.from_arxiv_result") as mock_from:
            mock_from.return_value = mock_paper

            result = fetcher._fetch_with_api_search(
                arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359", max_results=10
            )

            # Should have retried and eventually failed
            assert not result.success
            assert result.retry_count == 3


# ============================================================================
# Convenience Functions Tests
# ============================================================================


@pytest.mark.unit
def test_fetch_arxiv_papers_convenience_function(mock_paper):
    """Test the convenience function fetch_arxiv_papers."""
    with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaperFetcher") as mock_fetcher_class:
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        mock_fetcher.fetch_papers.return_value = FetchResult(
            papers=[mock_paper], strategy_used=FetchStrategy.API_SEARCH, success=True, elapsed_time=1.5
        )

        papers = fetch_arxiv_papers(
            arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359", max_results=50
        )

        assert len(papers) == 1
        assert papers[0] == mock_paper
        mock_fetcher.fetch_papers.assert_called_once()


@pytest.mark.unit
def test_fetch_arxiv_papers_raises_on_failure():
    """Test convenience function raises error when all strategies fail."""
    with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaperFetcher") as mock_fetcher_class:
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        mock_fetcher.fetch_papers.return_value = FetchResult(
            papers=[], strategy_used=None, success=False, error_message="All strategies failed", retry_count=3
        )

        with pytest.raises(ValueError, match="Failed to fetch papers"):
            fetch_arxiv_papers(arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359")


@pytest.mark.unit
def test_fetch_papers_no_dates_skips_api_search(mock_paper):
    """Test that API search is skipped when no dates are provided."""
    fetcher = ArxivPaperFetcher()

    with (
        patch.object(fetcher, "_fetch_with_api_search") as mock_api,
        patch.object(fetcher, "_fetch_with_rss_feed") as mock_rss,
    ):

        mock_rss.return_value = FetchResult(papers=[mock_paper], strategy_used=FetchStrategy.RSS_FEED, success=True)

        result = fetcher.fetch_papers(arxiv_query="cs.AI", from_time=None, to_time=None)

        assert result.success
        mock_api.assert_not_called()
        mock_rss.assert_called_once()


@pytest.mark.unit
def test_fetch_papers_web_fallback_disabled():
    """Test that web scraper is not used when disabled."""
    fetcher = ArxivPaperFetcher(enable_web_fallback=False)

    with (
        patch.object(fetcher, "_fetch_with_api_search") as mock_api,
        patch.object(fetcher, "_fetch_with_rss_feed") as mock_rss,
        patch.object(fetcher, "_fetch_with_web_scraper") as mock_web,
    ):

        # Both fail
        mock_api.return_value = FetchResult(success=False, papers=[])
        mock_rss.return_value = FetchResult(success=False, papers=[])

        result = fetcher.fetch_papers(arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359")

        assert not result.success
        mock_web.assert_not_called()


# ============================================================================
# High-Level Convenience Functions Tests
# ============================================================================


class TestConvenienceFunctionsUnit:
    """Unit tests for convenience functions."""

    @pytest.mark.unit
    def test_get_arxiv_papers_search_success(self, mock_paper):
        """Test get_arxiv_papers_search with successful result."""
        with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaperFetcher") as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            mock_fetcher._fetch_with_api_search.return_value = FetchResult(
                papers=[mock_paper], strategy_used=FetchStrategy.API_SEARCH, success=True
            )

            papers = get_arxiv_papers_search(
                arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359", max_results=10
            )

            assert len(papers) == 1
            assert papers[0] == mock_paper
            mock_fetcher._fetch_with_api_search.assert_called_once()

    @pytest.mark.unit
    def test_get_arxiv_papers_search_debug_mode(self, mock_paper):
        """Test get_arxiv_papers_search in debug mode limits results."""
        with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaperFetcher") as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            mock_fetcher._fetch_with_api_search.return_value = FetchResult(
                papers=[mock_paper], strategy_used=FetchStrategy.API_SEARCH, success=True
            )

            papers = get_arxiv_papers_search(
                arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359", debug=True
            )

            assert len(papers) == 1
            # Verify debug mode set max_results to 5
            call_kwargs = mock_fetcher._fetch_with_api_search.call_args[1]
            assert call_kwargs["max_results"] == 5

    @pytest.mark.unit
    def test_get_arxiv_papers_search_raises_on_failure(self):
        """Test get_arxiv_papers_search raises error on failure."""
        with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaperFetcher") as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            mock_fetcher._fetch_with_api_search.return_value = FetchResult(
                papers=[], success=False, error_message="API error"
            )

            with pytest.raises(ValueError, match="Failed to fetch papers via API search"):
                get_arxiv_papers_search(arxiv_query="cs.AI", from_time="202312230000", to_time="202312232359")

    @pytest.mark.unit
    def test_get_arxiv_papers_feed_success(self, mock_paper):
        """Test get_arxiv_papers_feed with successful result."""
        with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaperFetcher") as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            mock_fetcher._fetch_with_rss_feed.return_value = FetchResult(
                papers=[mock_paper, mock_paper], strategy_used=FetchStrategy.RSS_FEED, success=True
            )

            papers = get_arxiv_papers_feed("cs.AI")

            assert len(papers) == 2
            mock_fetcher._fetch_with_rss_feed.assert_called_once()

    @pytest.mark.unit
    def test_get_arxiv_papers_feed_debug_mode(self, mock_paper):
        """Test get_arxiv_papers_feed in debug mode."""
        with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaperFetcher") as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            mock_fetcher._fetch_with_rss_feed.return_value = FetchResult(
                papers=[mock_paper], strategy_used=FetchStrategy.RSS_FEED, success=True
            )

            papers = get_arxiv_papers_feed("cs.AI", debug=True)

            assert len(papers) == 1
            # Verify debug mode set max_results to 5
            call_kwargs = mock_fetcher._fetch_with_rss_feed.call_args[1]
            assert call_kwargs["max_results"] == 5

    @pytest.mark.unit
    def test_get_arxiv_papers_feed_returns_empty_on_failure(self):
        """Test get_arxiv_papers_feed returns empty list on failure."""
        with patch("alithia.utils.arxiv_paper_fetcher.ArxivPaperFetcher") as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            mock_fetcher._fetch_with_rss_feed.return_value = FetchResult(
                papers=[], success=False, error_message="RSS error"
            )

            papers = get_arxiv_papers_feed("cs.AI")

            # Should return empty list, not raise
            assert papers == []
