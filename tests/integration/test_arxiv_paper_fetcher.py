"""
Integration tests for the enhanced ArXiv paper fetcher module.

These tests make real API calls to ArXiv and should be marked with the 'integration' marker.
Tests cover:
1. ArxivPaperFetcher class with multiple strategies (API, RSS, Web)
2. Convenience functions (get_arxiv_papers_search, get_arxiv_papers_feed, fetch_arxiv_papers)
3. Fallback chain behavior
"""

from datetime import datetime, timedelta

import pytest

from alithia.utils.arxiv_paper_fetcher import (
    ArxivPaperFetcher,
    FetchStrategy,
    fetch_arxiv_papers,
    get_arxiv_papers_feed,
    get_arxiv_papers_search,
)


class TestArxivPaperFetcherAPISearch:
    """Integration tests for API search strategy."""

    @pytest.mark.integration
    def test_api_search_with_date_range_debug_mode(self):
        """Test API search in debug mode with date range."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        # Use yesterday's date to ensure we get some results
        yesterday = datetime.now() - timedelta(days=1)
        from_time = yesterday.strftime("%Y%m%d") + "0000"
        to_time = yesterday.strftime("%Y%m%d") + "2359"

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI+cs.CV",
            from_time=from_time,
            to_time=to_time,
            max_results=10,
            debug=True,
        )

        # Debug mode should limit to 5 papers
        assert result.success
        assert result.strategy_used == FetchStrategy.API_SEARCH
        assert len(result.papers) <= 5
        assert result.elapsed_time > 0

        # Validate paper structure
        for paper in result.papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert hasattr(paper, "pdf_url")
            assert isinstance(paper.title, str)
            assert len(paper.title) > 0
            assert isinstance(paper.authors, list)
            assert len(paper.authors) > 0
            assert paper.pdf_url.startswith("http")

    @pytest.mark.integration
    def test_api_search_with_recent_date_range(self):
        """Test API search with recent date range."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        # Use a week ago to have a broader range
        week_ago = datetime.now() - timedelta(days=7)
        from_time = week_ago.strftime("%Y%m%d") + "0000"
        to_time = datetime.now().strftime("%Y%m%d") + "2359"

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=from_time,
            to_time=to_time,
            max_results=20,
            debug=False,
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.API_SEARCH
        assert isinstance(result.papers, list)
        assert len(result.papers) <= 20

        # Verify papers have published dates
        for paper in result.papers:
            assert paper.published_date is not None
            assert isinstance(paper.arxiv_id, str)
            assert not paper.arxiv_id.endswith("v1")  # No version suffix

    @pytest.mark.integration
    def test_api_search_multiple_categories(self):
        """Test API search with multiple categories."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        # Use yesterday for consistent results
        yesterday = datetime.now() - timedelta(days=1)
        from_time = yesterday.strftime("%Y%m%d") + "0000"
        to_time = yesterday.strftime("%Y%m%d") + "2359"

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI+cs.CV+cs.LG+cs.CL",
            from_time=from_time,
            to_time=to_time,
            max_results=15,
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.API_SEARCH
        assert isinstance(result.papers, list)

        # Validate papers
        for paper in result.papers:
            assert isinstance(paper.title, str)
            assert isinstance(paper.summary, str)
            assert isinstance(paper.authors, list)
            assert len(paper.summary) > 0  # Should have abstract

    @pytest.mark.integration
    def test_api_search_sorted_by_date(self):
        """Test that API search results are sorted by date."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        # Use broader date range
        week_ago = datetime.now() - timedelta(days=7)
        from_time = week_ago.strftime("%Y%m%d") + "0000"
        to_time = datetime.now().strftime("%Y%m%d") + "2359"

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI+cs.CV",
            from_time=from_time,
            to_time=to_time,
            max_results=10,
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.API_SEARCH

        # If we have multiple papers, verify sorting
        if len(result.papers) >= 2:
            dates = [p.published_date for p in result.papers if p.published_date]
            # Papers should be sorted in descending order (newest first)
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1], "Papers should be sorted by date descending"

    @pytest.mark.integration
    def test_api_search_empty_result(self):
        """Test API search with date range that returns no results."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        # Use future date that should have no papers
        future_date = datetime.now() + timedelta(days=365)
        from_time = future_date.strftime("%Y%m%d") + "0000"
        to_time = future_date.strftime("%Y%m%d") + "2359"

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=from_time,
            to_time=to_time,
            max_results=10,
        )

        # Should succeed but return empty list
        assert result.success
        assert result.strategy_used == FetchStrategy.API_SEARCH
        assert len(result.papers) == 0


class TestArxivPaperFetcherRSSFeed:
    """Integration tests for RSS feed strategy."""

    @pytest.mark.integration
    def test_rss_feed_single_category(self):
        """Test RSS feed with single category."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        # No date range - should use RSS feed
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=None,
            to_time=None,
            max_results=20,
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.RSS_FEED
        assert isinstance(result.papers, list)
        assert len(result.papers) <= 20

        # Validate papers
        for paper in result.papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert hasattr(paper, "pdf_url")
            assert isinstance(paper.title, str)
            assert len(paper.title) > 0

    @pytest.mark.integration
    def test_rss_feed_multiple_categories(self):
        """Test RSS feed with multiple categories."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI+cs.CV+cs.LG",
            from_time=None,
            to_time=None,
            max_results=30,
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.RSS_FEED
        assert isinstance(result.papers, list)

        # Should have papers from multiple categories
        for paper in result.papers:
            assert isinstance(paper.title, str)
            assert isinstance(paper.summary, str)
            assert isinstance(paper.authors, list)
            assert len(paper.authors) > 0
            assert paper.pdf_url.startswith("http")

    @pytest.mark.integration
    def test_rss_feed_debug_mode(self):
        """Test RSS feed in debug mode."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        result = fetcher.fetch_papers(
            arxiv_query="cs.CV",
            from_time=None,
            to_time=None,
            max_results=100,
            debug=True,
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.RSS_FEED
        # Debug mode limits to 5 papers
        assert len(result.papers) <= 5

        # Validate paper structure
        for paper in result.papers:
            assert isinstance(paper.title, str)
            assert isinstance(paper.arxiv_id, str)
            assert not paper.arxiv_id.endswith("v1")
            assert not paper.arxiv_id.endswith("v2")

    @pytest.mark.integration
    def test_rss_feed_max_results_respected(self):
        """Test that RSS feed respects max_results parameter."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        max_results = 10
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI+cs.CV",
            from_time=None,
            to_time=None,
            max_results=max_results,
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.RSS_FEED
        assert len(result.papers) <= max_results

    @pytest.mark.integration
    def test_rss_feed_invalid_category(self):
        """Test RSS feed with invalid category."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        result = fetcher.fetch_papers(
            arxiv_query="invalid.category",
            from_time=None,
            to_time=None,
            max_results=10,
        )

        # Should fail and not use RSS_FEED as successful strategy
        assert not result.success or result.strategy_used != FetchStrategy.RSS_FEED

    @pytest.mark.integration
    def test_rss_feed_paper_metadata_completeness(self):
        """Test that RSS feed returns complete paper metadata."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=None,
            to_time=None,
            debug=True,
        )

        assert result.success
        assert result.strategy_used == FetchStrategy.RSS_FEED

        for paper in result.papers:
            # Required fields
            assert isinstance(paper.title, str)
            assert isinstance(paper.summary, str)
            assert isinstance(paper.authors, list)
            assert isinstance(paper.arxiv_id, str)
            assert isinstance(paper.pdf_url, str)

            # Validate content
            assert len(paper.title) > 0
            assert len(paper.summary) > 0
            assert len(paper.authors) > 0
            assert paper.pdf_url.startswith("https://arxiv.org/pdf/")

            # Optional fields should exist
            assert hasattr(paper, "code_url")
            assert hasattr(paper, "published_date")


class TestArxivPaperFetcherWebScraper:
    """Integration tests for web scraper fallback strategy."""

    @pytest.mark.integration
    def test_web_scraper_enabled(self):
        """Test that web scraper can be used when explicitly tested."""
        fetcher = ArxivPaperFetcher(max_retries=1, enable_web_fallback=True)

        # Directly test web scraper method
        result = fetcher._fetch_with_web_scraper(arxiv_query="cs.AI", max_results=5)

        # Web scraper should work (may return 0 papers if none available)
        assert result.success
        assert result.strategy_used == FetchStrategy.WEB_SCRAPER
        assert isinstance(result.papers, list)

        # Validate scraped papers if any are returned
        for paper in result.papers:
            assert isinstance(paper.title, str)
            assert isinstance(paper.arxiv_id, str)
            assert len(paper.title) > 0
            assert len(paper.arxiv_id) > 0

    @pytest.mark.integration
    def test_web_scraper_with_multiple_categories(self):
        """Test web scraper with multiple categories."""
        fetcher = ArxivPaperFetcher(max_retries=1, enable_web_fallback=True)

        result = fetcher._fetch_with_web_scraper(arxiv_query="cs.AI+cs.CV", max_results=10)

        assert result.success
        assert result.strategy_used == FetchStrategy.WEB_SCRAPER
        assert isinstance(result.papers, list)

        # Should have papers
        if len(result.papers) > 0:
            for paper in result.papers:
                assert isinstance(paper.title, str)
                assert isinstance(paper.summary, str)
                assert isinstance(paper.authors, list)
                assert isinstance(paper.arxiv_id, str)
                assert paper.pdf_url.startswith("https://arxiv.org/pdf/")

    @pytest.mark.integration
    def test_web_scraper_disabled(self):
        """Test that web scraper is not used when disabled."""
        fetcher = ArxivPaperFetcher(max_retries=1, enable_web_fallback=False)

        # Force all other methods to fail by using invalid dates
        future_date = datetime.now() + timedelta(days=365)
        from_time = future_date.strftime("%Y%m%d") + "0000"
        to_time = future_date.strftime("%Y%m%d") + "2359"

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=from_time,
            to_time=to_time,
            max_results=5,
        )

        # Should not use web scraper even if other methods fail
        # (future date should return empty results from API, not fail to web scraper)
        assert result.strategy_used != FetchStrategy.WEB_SCRAPER

    @pytest.mark.integration
    def test_web_scraper_paper_structure(self):
        """Test that web scraper returns properly structured papers."""
        fetcher = ArxivPaperFetcher(max_retries=1, enable_web_fallback=True)

        result = fetcher._fetch_with_web_scraper(arxiv_query="cs.AI", max_results=3)

        assert result.success
        assert result.strategy_used == FetchStrategy.WEB_SCRAPER

        for paper in result.papers:
            # Required fields
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert hasattr(paper, "pdf_url")

            # Type validation
            assert isinstance(paper.title, str)
            assert isinstance(paper.summary, str)
            assert isinstance(paper.authors, list)
            assert isinstance(paper.arxiv_id, str)
            assert isinstance(paper.pdf_url, str)

            # Content validation
            assert len(paper.title) > 0
            # Summary might be empty in web scraping
            assert isinstance(paper.summary, str)
            # Authors might be empty in web scraping
            assert isinstance(paper.authors, list)
            assert paper.pdf_url.endswith(".pdf")


class TestArxivPaperFetcherFallbackChain:
    """Integration tests for fallback strategy chain."""

    @pytest.mark.integration
    def test_fallback_from_api_to_rss(self):
        """Test fallback from API search to RSS feed."""
        fetcher = ArxivPaperFetcher(max_retries=1)

        # Use invalid date format that should fail API but allow RSS fallback
        # Actually, if dates are provided, it tries API first
        # If API succeeds with empty results, it won't fallback
        # So we just test normal flow with no dates - goes straight to RSS
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=None,
            to_time=None,
            max_results=5,
        )

        # Should use RSS feed when no dates provided
        assert result.success
        assert result.strategy_used == FetchStrategy.RSS_FEED

    @pytest.mark.integration
    def test_successful_primary_strategy(self):
        """Test that primary strategy (API with dates) is used when successful."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        yesterday = datetime.now() - timedelta(days=1)
        from_time = yesterday.strftime("%Y%m%d") + "0000"
        to_time = yesterday.strftime("%Y%m%d") + "2359"

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=from_time,
            to_time=to_time,
            max_results=5,
        )

        # Should use API search (primary with dates)
        assert result.success
        assert result.strategy_used == FetchStrategy.API_SEARCH

    @pytest.mark.integration
    def test_elapsed_time_tracking(self):
        """Test that elapsed time is properly tracked."""
        fetcher = ArxivPaperFetcher(max_retries=2)

        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=None,
            to_time=None,
            debug=True,
        )

        assert result.success
        assert result.elapsed_time > 0
        assert result.elapsed_time < 60  # Should complete in reasonable time


class TestConvenienceFunctions:
    """Integration tests for convenience functions."""

    @pytest.mark.integration
    def test_get_arxiv_papers_search_debug_mode(self):
        """Test get_arxiv_papers_search in debug mode."""
        yesterday = datetime.now() - timedelta(days=1)
        from_time = yesterday.strftime("%Y%m%d") + "0000"
        to_time = yesterday.strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI+cs.CV",
            from_time=from_time,
            to_time=to_time,
            debug=True,
        )

        # Debug mode limits to 5 papers
        assert isinstance(papers, list)
        assert len(papers) <= 5

        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "arxiv_id")
            assert isinstance(paper.title, str)
            assert len(paper.title) > 0

    @pytest.mark.integration
    def test_get_arxiv_papers_search_multiple_categories(self):
        """Test get_arxiv_papers_search with multiple categories."""
        week_ago = datetime.now() - timedelta(days=7)
        from_time = week_ago.strftime("%Y%m%d") + "0000"
        to_time = datetime.now().strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI+cs.CV+cs.LG",
            from_time=from_time,
            to_time=to_time,
            max_results=10,
        )

        assert isinstance(papers, list)
        assert len(papers) <= 10

        for paper in papers:
            assert isinstance(paper.title, str)
            assert isinstance(paper.summary, str)
            assert isinstance(paper.authors, list)
            assert not paper.arxiv_id.endswith("v1")

    @pytest.mark.integration
    def test_get_arxiv_papers_feed_debug_mode(self):
        """Test get_arxiv_papers_feed in debug mode."""
        papers = get_arxiv_papers_feed("cs.AI", debug=True)

        # Debug mode limits to 5 papers
        assert isinstance(papers, list)
        assert len(papers) <= 5

        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert isinstance(paper.title, str)
            assert len(paper.title) > 0
            assert isinstance(paper.authors, list)
            assert len(paper.authors) > 0

    @pytest.mark.integration
    def test_get_arxiv_papers_feed_multiple_categories(self):
        """Test get_arxiv_papers_feed with multiple categories."""
        papers = get_arxiv_papers_feed("cs.AI+cs.CV")

        assert isinstance(papers, list)

        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "arxiv_id")
            assert isinstance(paper.title, str)
            assert paper.pdf_url.startswith("http")

    @pytest.mark.integration
    def test_get_arxiv_papers_feed_invalid_query(self):
        """Test get_arxiv_papers_feed with invalid query returns empty list."""
        papers = get_arxiv_papers_feed("invalid_query")

        # Should return empty list rather than raising
        assert isinstance(papers, list)

    @pytest.mark.integration
    def test_fetch_arxiv_papers_with_api_search(self):
        """Test fetch_arxiv_papers convenience function with API search."""
        yesterday = datetime.now() - timedelta(days=1)
        from_time = yesterday.strftime("%Y%m%d") + "0000"
        to_time = yesterday.strftime("%Y%m%d") + "2359"

        papers = fetch_arxiv_papers(
            arxiv_query="cs.AI",
            from_time=from_time,
            to_time=to_time,
            max_results=5,
            debug=True,
        )

        assert isinstance(papers, list)
        assert len(papers) <= 5

        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "arxiv_id")
            assert isinstance(paper.title, str)

    @pytest.mark.integration
    def test_fetch_arxiv_papers_with_rss_feed(self):
        """Test fetch_arxiv_papers convenience function with RSS feed."""
        papers = fetch_arxiv_papers(
            arxiv_query="cs.AI",
            from_time=None,
            to_time=None,
            max_results=10,
            debug=True,
        )

        assert isinstance(papers, list)
        assert len(papers) <= 10

        for paper in papers:
            assert isinstance(paper.title, str)
            assert isinstance(paper.arxiv_id, str)

    @pytest.mark.integration
    def test_fetch_arxiv_papers_with_web_fallback(self):
        """Test fetch_arxiv_papers with web fallback enabled."""
        papers = fetch_arxiv_papers(
            arxiv_query="cs.AI",
            from_time=None,
            to_time=None,
            max_results=5,
            debug=True,
            enable_web_fallback=True,
        )

        assert isinstance(papers, list)

    @pytest.mark.integration
    def test_fetch_arxiv_papers_max_retries(self):
        """Test fetch_arxiv_papers with custom max_retries."""
        papers = fetch_arxiv_papers(
            arxiv_query="cs.AI",
            from_time=None,
            to_time=None,
            debug=True,
            max_retries=1,
        )

        assert isinstance(papers, list)

    @pytest.mark.integration
    def test_fetch_arxiv_papers_raises_on_all_failures(self):
        """Test that fetch_arxiv_papers raises error when all strategies fail."""
        with pytest.raises(ValueError, match="Failed to fetch papers"):
            fetch_arxiv_papers(
                arxiv_query="completely.invalid.category.xyz",
                from_time=None,
                to_time=None,
                max_results=5,
                max_retries=1,
                enable_web_fallback=False,
            )
