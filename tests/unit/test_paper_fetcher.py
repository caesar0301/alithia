"""
Unit tests for the enhanced paper fetcher module.
"""

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest

from alithia.models import ArxivPaper
from alithia.utils.paper_fetcher import (
    EnhancedPaperFetcher,
    FetchStrategy,
    FetchResult,
    fetch_arxiv_papers,
)


@pytest.fixture
def mock_paper():
    """Create a mock ArxivPaper for testing."""
    return ArxivPaper(
        title="Test Paper",
        summary="This is a test abstract.",
        authors=["Alice", "Bob"],
        arxiv_id="2312.12345",
        pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
        published_date=datetime(2023, 12, 23)
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
def test_enhanced_paper_fetcher_initialization():
    """Test EnhancedPaperFetcher initialization."""
    fetcher = EnhancedPaperFetcher(
        max_retries=5,
        retry_delay=2.0,
        timeout=60,
        enable_web_fallback=False
    )
    
    assert fetcher.max_retries == 5
    assert fetcher.retry_delay == 2.0
    assert fetcher.timeout == 60
    assert fetcher.enable_web_fallback is False
    assert fetcher.session is not None
    assert fetcher.arxiv_client is not None


@pytest.mark.unit
def test_fetch_papers_debug_mode(mock_paper, mock_arxiv_result):
    """Test fetch_papers in debug mode limits results."""
    fetcher = EnhancedPaperFetcher()
    
    with patch.object(fetcher, '_fetch_with_api_search') as mock_api:
        mock_api.return_value = FetchResult(
            papers=[mock_paper],
            strategy_used=FetchStrategy.API_SEARCH,
            success=True
        )
        
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time="202312230000",
            to_time="202312232359",
            max_results=100,
            debug=True
        )
        
        assert result.success
        assert len(result.papers) == 1
        # Verify debug mode limited max_results to 5
        call_args = mock_api.call_args[0]
        assert call_args[3] == 5  # max_results argument


@pytest.mark.unit
def test_fetch_papers_api_search_success(mock_paper):
    """Test successful API search strategy."""
    fetcher = EnhancedPaperFetcher()
    
    with patch.object(fetcher, '_fetch_with_api_search') as mock_api:
        mock_api.return_value = FetchResult(
            papers=[mock_paper, mock_paper],
            strategy_used=FetchStrategy.API_SEARCH,
            success=True
        )
        
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI+cs.CV",
            from_time="202312230000",
            to_time="202312232359",
            max_results=200
        )
        
        assert result.success
        assert result.strategy_used == FetchStrategy.API_SEARCH
        assert len(result.papers) == 2
        mock_api.assert_called_once()


@pytest.mark.unit
def test_fetch_papers_rss_fallback(mock_paper):
    """Test fallback to RSS feed when API fails."""
    fetcher = EnhancedPaperFetcher()
    
    with patch.object(fetcher, '_fetch_with_api_search') as mock_api, \
         patch.object(fetcher, '_fetch_with_rss_feed') as mock_rss:
        
        # API fails
        mock_api.return_value = FetchResult(
            papers=[],
            strategy_used=FetchStrategy.API_SEARCH,
            success=False,
            error_message="API error"
        )
        
        # RSS succeeds
        mock_rss.return_value = FetchResult(
            papers=[mock_paper],
            strategy_used=FetchStrategy.RSS_FEED,
            success=True
        )
        
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time="202312230000",
            to_time="202312232359"
        )
        
        assert result.success
        assert result.strategy_used == FetchStrategy.RSS_FEED
        assert len(result.papers) == 1
        mock_api.assert_called_once()
        mock_rss.assert_called_once()


@pytest.mark.unit
def test_fetch_papers_web_scraper_fallback(mock_paper):
    """Test fallback to web scraper when API and RSS fail."""
    fetcher = EnhancedPaperFetcher(enable_web_fallback=True)
    
    with patch.object(fetcher, '_fetch_with_api_search') as mock_api, \
         patch.object(fetcher, '_fetch_with_rss_feed') as mock_rss, \
         patch.object(fetcher, '_fetch_with_web_scraper') as mock_web:
        
        # API fails
        mock_api.return_value = FetchResult(
            papers=[],
            strategy_used=FetchStrategy.API_SEARCH,
            success=False,
            error_message="API error"
        )
        
        # RSS fails
        mock_rss.return_value = FetchResult(
            papers=[],
            strategy_used=FetchStrategy.RSS_FEED,
            success=False,
            error_message="RSS error"
        )
        
        # Web scraper succeeds
        mock_web.return_value = FetchResult(
            papers=[mock_paper],
            strategy_used=FetchStrategy.WEB_SCRAPER,
            success=True
        )
        
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time="202312230000",
            to_time="202312232359"
        )
        
        assert result.success
        assert result.strategy_used == FetchStrategy.WEB_SCRAPER
        assert len(result.papers) == 1
        mock_api.assert_called_once()
        mock_rss.assert_called_once()
        mock_web.assert_called_once()


@pytest.mark.unit
def test_fetch_papers_all_strategies_fail():
    """Test when all fetch strategies fail."""
    fetcher = EnhancedPaperFetcher(enable_web_fallback=True)
    
    with patch.object(fetcher, '_fetch_with_api_search') as mock_api, \
         patch.object(fetcher, '_fetch_with_rss_feed') as mock_rss, \
         patch.object(fetcher, '_fetch_with_web_scraper') as mock_web:
        
        # All strategies fail
        for mock in [mock_api, mock_rss, mock_web]:
            mock.return_value = FetchResult(
                papers=[],
                success=False,
                error_message="Failed"
            )
        
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time="202312230000",
            to_time="202312232359"
        )
        
        assert not result.success
        assert result.strategy_used is None
        assert len(result.papers) == 0
        assert result.error_message == "All fetch strategies failed"


@pytest.mark.unit
def test_fetch_with_api_search_retry_logic(mock_paper):
    """Test retry logic in API search."""
    fetcher = EnhancedPaperFetcher(max_retries=3, retry_delay=0.1)
    
    with patch.object(fetcher.arxiv_client, 'results') as mock_results:
        # First two attempts fail, third succeeds
        mock_results.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            [Mock(return_value=mock_paper)]
        ]
        
        with patch('alithia.utils.paper_fetcher.ArxivPaper.from_arxiv_result') as mock_from:
            mock_from.return_value = mock_paper
            
            result = fetcher._fetch_with_api_search(
                arxiv_query="cs.AI",
                from_time="202312230000",
                to_time="202312232359",
                max_results=10
            )
            
            # Should have retried and eventually failed
            assert not result.success
            assert result.retry_count == 3


@pytest.mark.unit
def test_fetch_arxiv_papers_convenience_function(mock_paper):
    """Test the convenience function fetch_arxiv_papers."""
    with patch('alithia.utils.paper_fetcher.EnhancedPaperFetcher') as mock_fetcher_class:
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher
        
        mock_fetcher.fetch_papers.return_value = FetchResult(
            papers=[mock_paper],
            strategy_used=FetchStrategy.API_SEARCH,
            success=True,
            elapsed_time=1.5
        )
        
        papers = fetch_arxiv_papers(
            arxiv_query="cs.AI",
            from_time="202312230000",
            to_time="202312232359",
            max_results=50
        )
        
        assert len(papers) == 1
        assert papers[0] == mock_paper
        mock_fetcher.fetch_papers.assert_called_once()


@pytest.mark.unit
def test_fetch_arxiv_papers_raises_on_failure():
    """Test convenience function raises error when all strategies fail."""
    with patch('alithia.utils.paper_fetcher.EnhancedPaperFetcher') as mock_fetcher_class:
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher
        
        mock_fetcher.fetch_papers.return_value = FetchResult(
            papers=[],
            strategy_used=None,
            success=False,
            error_message="All strategies failed",
            retry_count=3
        )
        
        with pytest.raises(ValueError, match="Failed to fetch papers"):
            fetch_arxiv_papers(
                arxiv_query="cs.AI",
                from_time="202312230000",
                to_time="202312232359"
            )


@pytest.mark.unit
def test_fetch_papers_no_dates_skips_api_search(mock_paper):
    """Test that API search is skipped when no dates are provided."""
    fetcher = EnhancedPaperFetcher()
    
    with patch.object(fetcher, '_fetch_with_api_search') as mock_api, \
         patch.object(fetcher, '_fetch_with_rss_feed') as mock_rss:
        
        mock_rss.return_value = FetchResult(
            papers=[mock_paper],
            strategy_used=FetchStrategy.RSS_FEED,
            success=True
        )
        
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time=None,
            to_time=None
        )
        
        assert result.success
        mock_api.assert_not_called()
        mock_rss.assert_called_once()


@pytest.mark.unit
def test_fetch_papers_web_fallback_disabled():
    """Test that web scraper is not used when disabled."""
    fetcher = EnhancedPaperFetcher(enable_web_fallback=False)
    
    with patch.object(fetcher, '_fetch_with_api_search') as mock_api, \
         patch.object(fetcher, '_fetch_with_rss_feed') as mock_rss, \
         patch.object(fetcher, '_fetch_with_web_scraper') as mock_web:
        
        # Both fail
        mock_api.return_value = FetchResult(success=False, papers=[])
        mock_rss.return_value = FetchResult(success=False, papers=[])
        
        result = fetcher.fetch_papers(
            arxiv_query="cs.AI",
            from_time="202312230000",
            to_time="202312232359"
        )
        
        assert not result.success
        mock_web.assert_not_called()
