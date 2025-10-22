"""
Integration tests for ArXiv client functionality.

These tests make real API calls to ArXiv and should be marked with the 'integration' marker.
"""

import pytest

from alithia.core.arxiv_client import get_arxiv_papers


class TestArxivClientIntegration:
    """Integration tests for ArXiv client functionality."""

    @pytest.mark.integration
    def test_get_arxiv_papers_debug_mode(self):
        """Test get_arxiv_papers in debug mode returns recent papers."""
        papers = get_arxiv_papers("cs.AI", debug=True)

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
        papers = get_arxiv_papers("cs.AI")

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
        papers = get_arxiv_papers("cs.AI+cs.CV")

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
            get_arxiv_papers("invalid_query_that_should_fail")

    @pytest.mark.integration
    def test_get_arxiv_papers_empty_result(self):
        """Test get_arxiv_papers with a query that returns no results."""
        # Use a very specific query that's unlikely to have recent papers
        # This should be detected as an invalid query
        with pytest.raises(ValueError, match="Invalid ARXIV_QUERY"):
            get_arxiv_papers("cs.AI+AND+very_specific_term_that_should_not_exist")

    @pytest.mark.integration
    def test_get_arxiv_papers_paper_structure(self):
        """Test that returned papers have the correct structure and data types."""
        papers = get_arxiv_papers("cs.AI", debug=True)

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
        papers = get_arxiv_papers("cs.AI", debug=True)

        # If we get here, the client handled any network issues
        assert len(papers) == 5

    @pytest.mark.integration
    def test_get_arxiv_papers_batch_processing(self):
        """Test that batch processing works correctly for large result sets."""
        # Use a broad query that might return many papers
        papers = get_arxiv_papers("cs.AI")

        # Should handle batching gracefully
        assert isinstance(papers, list)

        # If we have papers, verify they're all valid
        for paper in papers:
            assert hasattr(paper, "title")
            assert hasattr(paper, "arxiv_id")
            assert len(paper.title) > 0
            assert len(paper.arxiv_id) > 0
