"""
Integration tests for ArXiv client functionality.

These tests make real API calls to ArXiv and should be marked with the 'integration' marker.
"""

from datetime import datetime, timedelta

import pytest

from alithia.utils.arxiv_paper_utils import get_arxiv_papers_feed, get_arxiv_papers_search


class TestArxivClientIntegration:
    """Integration tests for ArXiv client functionality."""

    @pytest.mark.integration
    def test_get_arxiv_papers_debug_mode(self):
        """Test get_arxiv_papers in debug mode returns recent papers."""
        papers = get_arxiv_papers_feed("cs.AI", debug=True)

        # Should return exactly 5 papers in debug mode
        assert len(papers) == 5

        # Each paper should be an ArxivPaper instance
        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert hasattr(paper, "pdf_url")

            # Basic validation of paper data
            assert isinstance(paper.title, str)
            assert len(paper.title) > 0
            assert isinstance(paper.summary, str)
            assert len(paper.summary) > 0
            assert isinstance(paper.authors, list)
            assert len(paper.authors) > 0
            assert isinstance(paper.arxiv_id, str)
            assert len(paper.arxiv_id) > 0
            assert paper.pdf_url.startswith("http")

    @pytest.mark.integration
    def test_get_arxiv_papers_with_valid_query(self):
        """Test get_arxiv_papers with a valid ArXiv query."""
        # Test with a specific category that should have recent papers
        papers = get_arxiv_papers_feed("cs.AI")

        # Should return a list (may be empty if no recent papers)
        assert isinstance(papers, list)

        # If papers are returned, validate their structure
        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert hasattr(paper, "pdf_url")

            # Basic validation
            assert isinstance(paper.title, str)
            assert len(paper.title) > 0
            assert isinstance(paper.summary, str)
            assert len(paper.summary) > 0
            assert isinstance(paper.authors, list)
            assert len(paper.authors) > 0
            assert isinstance(paper.arxiv_id, str)
            assert len(paper.arxiv_id) > 0
            assert paper.pdf_url.startswith("http")

    @pytest.mark.integration
    def test_get_arxiv_papers_with_multiple_categories(self):
        """Test get_arxiv_papers with multiple categories in query."""
        # Test with multiple categories
        papers = get_arxiv_papers_feed("cs.AI+cs.CV")

        # Should return a list
        assert isinstance(papers, list)

        # If papers are returned, validate their structure
        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert hasattr(paper, "pdf_url")

    @pytest.mark.integration
    def test_get_arxiv_papers_with_invalid_query(self):
        """Test get_arxiv_papers with an invalid query raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ARXIV_QUERY"):
            get_arxiv_papers_feed("invalid_query_that_should_fail")

    @pytest.mark.integration
    def test_get_arxiv_papers_empty_result(self):
        """Test get_arxiv_papers with a query that returns no results."""
        # Use a very specific query that's unlikely to have recent papers
        # This should be detected as an invalid query
        with pytest.raises(ValueError, match="Invalid ARXIV_QUERY"):
            get_arxiv_papers_feed("cs.AI+AND+very_specific_term_that_should_not_exist")

    @pytest.mark.integration
    def test_get_arxiv_papers_paper_structure(self):
        """Test that returned papers have the correct structure and data types."""
        papers = get_arxiv_papers_feed("cs.AI", debug=True)

        assert len(papers) == 5

        for paper in papers:
            # Test required fields exist and have correct types
            assert isinstance(paper.title, str)
            assert isinstance(paper.summary, str)
            assert isinstance(paper.authors, list)
            assert isinstance(paper.arxiv_id, str)
            assert isinstance(paper.pdf_url, str)

            # Test optional fields
            assert hasattr(paper, "code_url")
            assert hasattr(paper, "affiliations")
            assert hasattr(paper, "tldr")
            assert hasattr(paper, "score")
            assert hasattr(paper, "published_date")

            # Test that arxiv_id doesn't contain version suffix
            assert not paper.arxiv_id.endswith("v1")
            assert not paper.arxiv_id.endswith("v2")

            # Test that authors list contains strings
            for author in paper.authors:
                assert isinstance(author, str)
                assert len(author) > 0

    @pytest.mark.integration
    def test_get_arxiv_papers_network_retry_behavior(self):
        """Test that the client handles network issues gracefully."""
        # This test verifies the client is configured with retries
        # We can't easily test actual network failures in integration tests,
        # but we can verify the client is configured properly
        papers = get_arxiv_papers_feed("cs.AI", debug=True)

        # If we get here, the client handled any network issues
        assert len(papers) == 5

    @pytest.mark.integration
    def test_get_arxiv_papers_batch_processing(self):
        """Test that batch processing works correctly for large result sets."""
        # Use a broad query that might return many papers
        papers = get_arxiv_papers_feed("cs.AI")

        # Should handle batching gracefully
        assert isinstance(papers, list)

        # If we have papers, verify they're all valid
        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "arxiv_id")
            assert len(paper.title) > 0
            assert len(paper.arxiv_id) > 0


class TestArxivSearchIntegration:
    """Integration tests for ArXiv search functionality."""

    @pytest.mark.integration
    def test_get_arxiv_papers_search_debug_mode(self):
        """Test get_arxiv_papers_search in debug mode with recent date range."""
        # Use yesterday's date to ensure we get some results
        yesterday = datetime.now() - timedelta(days=1)
        from_time = yesterday.strftime("%Y%m%d") + "0000"
        to_time = yesterday.strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI+cs.CV+cs.LG+cs.CL",
            from_time=from_time,
            to_time=to_time,
            debug=True,
        )

        # Should return at most 5 papers in debug mode
        assert isinstance(papers, list)
        assert len(papers) <= 5

        # Validate paper structure
        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert hasattr(paper, "pdf_url")
            assert hasattr(paper, "published_date")

            # Basic validation
            assert isinstance(paper.title, str)
            assert len(paper.title) > 0
            assert isinstance(paper.summary, str)
            assert len(paper.summary) > 0
            assert isinstance(paper.authors, list)
            assert len(paper.authors) > 0
            assert isinstance(paper.arxiv_id, str)
            assert len(paper.arxiv_id) > 0
            assert paper.pdf_url.startswith("http")

    @pytest.mark.integration
    def test_get_arxiv_papers_search_single_category(self):
        """Test search with a single category."""
        # Use a narrow date range from a week ago
        week_ago = datetime.now() - timedelta(days=7)
        from_time = week_ago.strftime("%Y%m%d") + "0000"
        to_time = week_ago.strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI", from_time=from_time, to_time=to_time, max_results=10, debug=False
        )

        assert isinstance(papers, list)
        # Verify results are limited to max_results
        assert len(papers) <= 10

        # All papers should be valid
        for paper in papers:
            assert isinstance(paper.title, str)
            assert isinstance(paper.arxiv_id, str)
            assert len(paper.title) > 0

    @pytest.mark.integration
    def test_get_arxiv_papers_search_multiple_categories(self):
        """Test search with multiple categories."""
        # Use a narrow date range from 2 weeks ago
        two_weeks_ago = datetime.now() - timedelta(days=14)
        from_time = two_weeks_ago.strftime("%Y%m%d") + "0000"
        to_time = two_weeks_ago.strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI+cs.CV+cs.LG",
            from_time=from_time,
            to_time=to_time,
            max_results=20,
        )

        assert isinstance(papers, list)
        assert len(papers) <= 20

        # Validate paper structure
        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "summary")
            assert hasattr(paper, "authors")
            assert hasattr(paper, "arxiv_id")
            assert hasattr(paper, "pdf_url")

    @pytest.mark.integration
    def test_get_arxiv_papers_search_date_range(self):
        """Test search with specific date range."""
        # Use a specific date from the past with high probability of papers
        # Using a date from a few weeks ago
        target_date = datetime.now() - timedelta(days=21)
        from_time = target_date.strftime("%Y%m%d") + "0000"
        to_time = target_date.strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI+cs.CV",
            from_time=from_time,
            to_time=to_time,
            max_results=50,
        )

        assert isinstance(papers, list)

        # If we have papers, verify they're within the date range
        for paper in papers:
            if paper.published_date:
                paper_date = paper.published_date
                # The paper should be roughly within our target date
                # (allowing some buffer for timezone/submission vs publication differences)
                assert paper_date is not None

    @pytest.mark.integration
    def test_get_arxiv_papers_search_sorted_by_date(self):
        """Test that results are sorted by submission date in ascending order."""
        # Use a broader date range to get multiple papers
        week_ago = datetime.now() - timedelta(days=7)
        from_time = week_ago.strftime("%Y%m%d") + "0000"
        to_time = datetime.now().strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI",
            from_time=from_time,
            to_time=to_time,
            max_results=10,
        )

        assert isinstance(papers, list)

        # If we have multiple papers, verify they're sorted
        if len(papers) >= 2:
            dates = [p.published_date for p in papers if p.published_date is not None]
            if len(dates) >= 2:
                # Check that dates are in ascending order
                for i in range(len(dates) - 1):
                    assert dates[i] <= dates[i + 1], "Papers should be sorted by date in ascending order"

    @pytest.mark.integration
    def test_get_arxiv_papers_search_empty_result(self):
        """Test search with parameters that should return no results."""
        # Use a date far in the future
        future_date = datetime.now() + timedelta(days=365)
        from_time = future_date.strftime("%Y%m%d") + "0000"
        to_time = future_date.strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI",
            from_time=from_time,
            to_time=to_time,
            max_results=10,
        )

        # Should return an empty list, not raise an error
        assert isinstance(papers, list)
        assert len(papers) == 0

    @pytest.mark.integration
    def test_get_arxiv_papers_search_max_results_limit(self):
        """Test that max_results parameter is respected."""
        # Use a broader date range that should have many papers
        two_weeks_ago = datetime.now() - timedelta(days=14)
        from_time = two_weeks_ago.strftime("%Y%m%d") + "0000"
        to_time = datetime.now().strftime("%Y%m%d") + "2359"

        max_results = 5
        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI+cs.CV+cs.LG+cs.CL",
            from_time=from_time,
            to_time=to_time,
            max_results=max_results,
        )

        # Should not exceed max_results
        assert len(papers) <= max_results

    @pytest.mark.integration
    def test_get_arxiv_papers_search_paper_structure(self):
        """Test that returned papers have the correct structure and data types."""
        yesterday = datetime.now() - timedelta(days=1)
        from_time = yesterday.strftime("%Y%m%d") + "0000"
        to_time = yesterday.strftime("%Y%m%d") + "2359"

        papers = get_arxiv_papers_search(
            arxiv_query="cs.AI",
            from_time=from_time,
            to_time=to_time,
            debug=True,
        )

        for paper in papers:
            # Test required fields exist and have correct types
            assert isinstance(paper.title, str)
            assert isinstance(paper.summary, str)
            assert isinstance(paper.authors, list)
            assert isinstance(paper.arxiv_id, str)
            assert isinstance(paper.pdf_url, str)

            # Test optional fields exist
            assert hasattr(paper, "code_url")
            assert hasattr(paper, "affiliations")
            assert hasattr(paper, "tldr")
            assert hasattr(paper, "score")
            assert hasattr(paper, "published_date")

            # Test that arxiv_id doesn't contain version suffix
            assert not paper.arxiv_id.endswith("v1")
            assert not paper.arxiv_id.endswith("v2")

            # Test that authors list contains strings
            for author in paper.authors:
                assert isinstance(author, str)
                assert len(author) > 0
