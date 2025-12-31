"""
Enhanced ArXiv paper fetcher with API and web scraping fallback.

This module provides a robust ArXiv paper fetching system that:
1. Tries ArXiv API first (primary source)
2. Falls back to RSS feed if API fails
3. Uses web scraping as last resort
4. Includes comprehensive error handling and retry logic
"""

import logging
import time
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

import arxiv
import feedparser
import requests
from requests.adapters import HTTPAdapter, Retry

from alithia.models import ArxivPaper
from alithia.utils.arxiv_paper_utils import build_arxiv_search_query, _build_category_query

logger = logging.getLogger(__name__)


class FetchStrategy(Enum):
    """Available ArXiv paper fetching strategies."""
    API_SEARCH = "api_search"
    RSS_FEED = "rss_feed"
    WEB_SCRAPER = "web_scraper"


@dataclass
class FetchResult:
    """Result of an ArXiv paper fetch operation."""
    papers: List[ArxivPaper] = field(default_factory=list)
    strategy_used: Optional[FetchStrategy] = None
    success: bool = False
    error_message: Optional[str] = None
    retry_count: int = 0
    elapsed_time: float = 0.0


class ArxivPaperFetcher:
    """
    Enhanced ArXiv paper fetcher with multiple fallback strategies.
    
    Features:
    - Automatic retry with exponential backoff
    - Multiple fetch strategies (API, RSS, web scraping)
    - Comprehensive error handling
    - Performance metrics
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30,
        enable_web_fallback: bool = True,
    ):
        """
        Initialize the enhanced ArXiv paper fetcher.
        
        Args:
            max_retries: Maximum number of retries per strategy
            retry_delay: Initial delay between retries (seconds)
            timeout: Request timeout (seconds)
            enable_web_fallback: Enable web scraping fallback
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.enable_web_fallback = enable_web_fallback
        
        # Configure requests session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configure arxiv client with retry logic
        self.arxiv_client = arxiv.Client(
            num_retries=max_retries,
            delay_seconds=retry_delay
        )
    
    def fetch_papers(
        self,
        arxiv_query: str,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        max_results: int = 200,
        debug: bool = False,
    ) -> FetchResult:
        """
        Fetch papers with automatic fallback strategies.
        
        Args:
            arxiv_query: ArXiv query string (e.g., "cs.AI+cs.CV+cs.LG")
            from_time: Start time in format YYYYMMDDHHMM
            to_time: End time in format YYYYMMDDHHMM
            max_results: Maximum number of results
            debug: Debug mode (limits results to 5)
            
        Returns:
            FetchResult with papers and metadata
        """
        start_time = time.time()
        
        if debug:
            logger.info(f"Debug mode: limiting results to 5 papers")
            max_results = 5
        
        # Strategy 1: Try API search with date range (if dates provided)
        if from_time and to_time:
            result = self._fetch_with_api_search(
                arxiv_query, from_time, to_time, max_results
            )
            if result.success:
                result.elapsed_time = time.time() - start_time
                return result
            logger.warning(f"API search failed: {result.error_message}")
        
        # Strategy 2: Try RSS feed
        result = self._fetch_with_rss_feed(arxiv_query, max_results)
        if result.success:
            result.elapsed_time = time.time() - start_time
            return result
        logger.warning(f"RSS feed failed: {result.error_message}")
        
        # Strategy 3: Try web scraping (if enabled)
        if self.enable_web_fallback:
            result = self._fetch_with_web_scraper(arxiv_query, max_results)
            if result.success:
                result.elapsed_time = time.time() - start_time
                return result
            logger.error(f"Web scraper failed: {result.error_message}")
        
        # All strategies failed
        elapsed_time = time.time() - start_time
        return FetchResult(
            papers=[],
            strategy_used=None,
            success=False,
            error_message="All fetch strategies failed",
            elapsed_time=elapsed_time
        )
    
    def _fetch_with_api_search(
        self,
        arxiv_query: str,
        from_time: str,
        to_time: str,
        max_results: int,
    ) -> FetchResult:
        """
        Fetch papers using ArXiv API search with date filtering.
        
        Args:
            arxiv_query: ArXiv query string
            from_time: Start time in format YYYYMMDDHHMM
            to_time: End time in format YYYYMMDDHHMM
            max_results: Maximum number of results
            
        Returns:
            FetchResult with papers from API search
        """
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                logger.info(f"Attempting API search (attempt {retry_count + 1}/{self.max_retries})")
                
                # Build search query
                full_query = build_arxiv_search_query(arxiv_query, from_time, to_time)
                logger.info(f"API search query: {full_query}")
                
                # Create search
                search = arxiv.Search(
                    query=full_query,
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                    sort_order=arxiv.SortOrder.Descending,
                    max_results=max_results,
                )
                
                # Fetch results
                papers = []
                for result in self.arxiv_client.results(search):
                    paper = ArxivPaper.from_arxiv_result(result)
                    if paper is not None:
                        papers.append(paper)
                
                logger.info(f"API search successful: found {len(papers)} papers")
                return FetchResult(
                    papers=papers,
                    strategy_used=FetchStrategy.API_SEARCH,
                    success=True,
                    retry_count=retry_count
                )
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                logger.warning(f"API search attempt {retry_count} failed: {e}")
                
                if retry_count < self.max_retries:
                    delay = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        return FetchResult(
            papers=[],
            strategy_used=FetchStrategy.API_SEARCH,
            success=False,
            error_message=last_error,
            retry_count=retry_count
        )
    
    def _fetch_with_rss_feed(
        self,
        arxiv_query: str,
        max_results: int,
    ) -> FetchResult:
        """
        Fetch papers using ArXiv RSS feed.
        
        Args:
            arxiv_query: ArXiv query string
            max_results: Maximum number of results
            
        Returns:
            FetchResult with papers from RSS feed
        """
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                logger.info(f"Attempting RSS feed (attempt {retry_count + 1}/{self.max_retries})")
                
                # Fetch RSS feed
                feed_url = f"https://rss.arxiv.org/atom/{arxiv_query}"
                logger.info(f"RSS feed URL: {feed_url}")
                
                feed = feedparser.parse(feed_url)
                
                # Check for feed errors
                if "Feed error for query" in feed.feed.get("title", ""):
                    raise ValueError(f"Invalid ArXiv query: {arxiv_query}")
                
                # Extract paper IDs from feed (only new papers)
                paper_ids = []
                for entry in feed.entries:
                    if hasattr(entry, "arxiv_announce_type") and entry.arxiv_announce_type == "new":
                        paper_id = entry.id.removeprefix("oai:arXiv.org:")
                        paper_ids.append(paper_id)
                        if len(paper_ids) >= max_results:
                            break
                
                if not paper_ids:
                    logger.warning("No new papers found in RSS feed")
                    return FetchResult(
                        papers=[],
                        strategy_used=FetchStrategy.RSS_FEED,
                        success=True,  # Success, but no papers
                        retry_count=retry_count
                    )
                
                # Fetch paper details in batches
                papers = []
                batch_size = 50
                
                for i in range(0, len(paper_ids), batch_size):
                    batch_ids = paper_ids[i:i + batch_size]
                    search = arxiv.Search(id_list=batch_ids)
                    
                    for result in self.arxiv_client.results(search):
                        paper = ArxivPaper.from_arxiv_result(result)
                        if paper is not None:
                            papers.append(paper)
                
                logger.info(f"RSS feed successful: found {len(papers)} papers")
                return FetchResult(
                    papers=papers,
                    strategy_used=FetchStrategy.RSS_FEED,
                    success=True,
                    retry_count=retry_count
                )
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                logger.warning(f"RSS feed attempt {retry_count} failed: {e}")
                
                if retry_count < self.max_retries:
                    delay = self.retry_delay * (2 ** retry_count)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        return FetchResult(
            papers=[],
            strategy_used=FetchStrategy.RSS_FEED,
            success=False,
            error_message=last_error,
            retry_count=retry_count
        )
    
    def _fetch_with_web_scraper(
        self,
        arxiv_query: str,
        max_results: int,
    ) -> FetchResult:
        """
        Fetch papers using web scraping as last resort.
        
        Args:
            arxiv_query: ArXiv query string
            max_results: Maximum number of results
            
        Returns:
            FetchResult with papers from web scraping
        """
        try:
            logger.info("Attempting web scraping fallback")
            
            # Import web scraper module
            from alithia.utils.web_scraper import ArxivWebScraper
            
            scraper = ArxivWebScraper(
                session=self.session,
                timeout=self.timeout
            )
            
            papers = scraper.scrape_arxiv_search(
                arxiv_query=arxiv_query,
                max_results=max_results
            )
            
            logger.info(f"Web scraping successful: found {len(papers)} papers")
            return FetchResult(
                papers=papers,
                strategy_used=FetchStrategy.WEB_SCRAPER,
                success=True
            )
            
        except ImportError:
            logger.error("Web scraper module not available")
            return FetchResult(
                papers=[],
                strategy_used=FetchStrategy.WEB_SCRAPER,
                success=False,
                error_message="Web scraper module not available"
            )
        except Exception as e:
            logger.error(f"Web scraping failed: {e}")
            return FetchResult(
                papers=[],
                strategy_used=FetchStrategy.WEB_SCRAPER,
                success=False,
                error_message=str(e)
            )


def fetch_arxiv_papers(
    arxiv_query: str,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    max_results: int = 200,
    debug: bool = False,
    max_retries: int = 3,
    enable_web_fallback: bool = True,
) -> List[ArxivPaper]:
    """
    Convenience function to fetch ArXiv papers with automatic fallback.
    
    Args:
        arxiv_query: ArXiv query string (e.g., "cs.AI+cs.CV+cs.LG")
        from_time: Start time in format YYYYMMDDHHMM
        to_time: End time in format YYYYMMDDHHMM
        max_results: Maximum number of results
        debug: Debug mode (limits results to 5)
        max_retries: Maximum retries per strategy
        enable_web_fallback: Enable web scraping fallback
        
    Returns:
        List of ArxivPaper objects
        
    Raises:
        ValueError: If no papers could be fetched
    """
    fetcher = ArxivPaperFetcher(
        max_retries=max_retries,
        enable_web_fallback=enable_web_fallback
    )
    
    result = fetcher.fetch_papers(
        arxiv_query=arxiv_query,
        from_time=from_time,
        to_time=to_time,
        max_results=max_results,
        debug=debug
    )
    
    if not result.success and not result.papers:
        raise ValueError(
            f"Failed to fetch papers: {result.error_message}. "
            f"All strategies exhausted after {result.retry_count} retries."
        )
    
    logger.info(
        f"Fetched {len(result.papers)} papers using {result.strategy_used.value} "
        f"in {result.elapsed_time:.2f}s"
    )
    
    return result.papers
