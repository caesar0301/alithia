"""
Web scraping fallback for ArXiv paper retrieval.

This module provides web scraping capabilities as a last resort
when API and RSS feed methods fail.
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from alithia.constants import ARXIV_PAGE_SIZE, DEFAULT_ARXIV_MAX_RESULTS, DEFAULT_REQUEST_TIMEOUT
from alithia.models import ArxivPaper

logger = logging.getLogger(__name__)


class ArxivWebScraper:
    """
    Web scraper for ArXiv papers.

    This is a fallback mechanism when API and RSS feed fail.
    Uses BeautifulSoup to parse ArXiv search results pages.
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
        user_agent: str = "AlithiaResearchAssistant/1.0",
    ):
        """
        Initialize the web scraper.

        Args:
            session: Requests session (or creates new one)
            timeout: Request timeout (seconds)
            user_agent: User agent string for requests
        """
        self.session = session or requests.Session()
        self.timeout = timeout
        self.base_url = "https://arxiv.org"

        # Set user agent
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def scrape_arxiv_search(
        self,
        arxiv_query: str,
        max_results: int = DEFAULT_ARXIV_MAX_RESULTS,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[ArxivPaper]:
        """
        Scrape ArXiv search results.

        Args:
            arxiv_query: ArXiv category query (e.g., "cs.AI+cs.CV")
            max_results: Maximum number of papers to retrieve
            from_date: Filter papers from this date
            to_date: Filter papers until this date

        Returns:
            List of ArxivPaper objects scraped from search results
        """
        papers = []
        start = 0
        page_size = ARXIV_PAGE_SIZE  # ArXiv default page size

        try:
            # Note: /list endpoint doesn't support pagination, so we only fetch once
            list_url = self._build_search_url(arxiv_query, start)

            logger.info(f"Scraping URL: {list_url}")

            # Fetch page
            response = self.session.get(list_url, timeout=self.timeout)
            response.raise_for_status()

            # Parse results
            papers = self._parse_search_results(response.text)

            if not papers:
                logger.info("No papers found")
                return []

            # Filter by date if specified
            if from_date or to_date:
                papers = self._filter_by_date(papers, from_date, to_date)

            # Limit to max_results
            if len(papers) > max_results:
                papers = papers[:max_results]

            logger.info(f"Scraped {len(papers)} papers from ArXiv")
            return papers

        except Exception as e:
            logger.error(f"Error scraping ArXiv: {e}")
            return []  # Return empty list on error

    def _build_search_url(self, arxiv_query: str, start: int = 0) -> str:
        """
        Build ArXiv search URL.

        Args:
            arxiv_query: Category query (e.g., "cs.AI" or "cs.AI+cs.CV")
            start: Starting index for pagination (Note: ArXiv search no longer supports pagination)

        Returns:
            Complete search URL
        """
        # ArXiv search accepts category queries directly (e.g., "cs.AI")
        # Note: ArXiv search no longer accepts 'start' or 'size' parameters
        # It returns a default page of results (typically 50)

        # For multi-category queries, use "+" to join them
        # ArXiv interprets "cs.AI+cs.CV" as papers in either category

        if start > 0:
            logger.warning(
                f"ArXiv /search endpoint doesn't support pagination (start={start} ignored). "
                f"Only the first page of results will be returned (~50 papers)."
            )

        # Construct search URL (no encoding needed for simple category queries)
        url = f"{self.base_url}/search/?query={arxiv_query}&searchtype=all"
        return url

    def _parse_search_results(self, html: str) -> List[ArxivPaper]:
        """
        Parse ArXiv search results page.

        Args:
            html: HTML content of search results page

        Returns:
            List of ArxivPaper objects
        """
        papers = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # ArXiv search results use <li class="arxiv-result"> for each paper
            result_items = soup.find_all("li", class_="arxiv-result")

            for item in result_items:
                try:
                    paper = self._parse_paper_entry_search(item)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing paper entry: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing search results: {e}")

        return papers

    def _parse_paper_entry_search(self, item) -> Optional[ArxivPaper]:
        """
        Parse a paper from ArXiv search results (li.arxiv-result structure).

        Args:
            item: BeautifulSoup element for <li class="arxiv-result"> tag

        Returns:
            ArxivPaper object or None if parsing fails
        """
        try:
            # Extract ArXiv ID from the list-title link
            list_title = item.find("p", class_="list-title")
            if not list_title:
                return None

            arxiv_link = list_title.find("a")
            if not arxiv_link:
                return None

            href = arxiv_link.get("href", "")
            arxiv_id_match = re.search(r"/abs/(\d+\.\d+)", href)
            if not arxiv_id_match:
                return None

            arxiv_id = arxiv_id_match.group(1)

            # Extract title (has multiple classes: "title is-5 mathjax")
            # Use lambda to match any element with "title" in its class list
            title_elem = item.find("p", class_=lambda x: x and "title" in x.split())
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)

            # Extract authors
            authors_elem = item.find("p", class_="authors")
            authors = []
            if authors_elem:
                author_links = authors_elem.find_all("a")
                authors = [a.get_text(strip=True) for a in author_links]

            # Extract abstract (search results don't show abstracts, only list view does)
            # We'll leave summary empty for search results
            summary = ""

            # Try to extract submission date from the list-comments section if present
            comments_elem = item.find("p", class_="is-size-7")
            published_date = None
            if comments_elem:
                date_text = comments_elem.get_text()
                # Try to find date in format "Submitted DD MMM YYYY"
                date_match = re.search(r"Submitted\s+(\d+\s+\w+\s+\d{4})", date_text)
                if date_match:
                    try:
                        published_date = datetime.strptime(date_match.group(1), "%d %b %Y")
                    except ValueError:
                        pass

            # Construct PDF URL
            pdf_url = f"{self.base_url}/pdf/{arxiv_id}.pdf"

            paper = ArxivPaper(
                title=title,
                summary=summary,
                authors=authors,
                arxiv_id=arxiv_id,
                pdf_url=pdf_url,
                published_date=published_date,
            )

            return paper

        except Exception as e:
            logger.warning(f"Error parsing search result entry: {e}")
            return None

    def _parse_paper_entry_list(self, dt, dd) -> Optional[ArxivPaper]:
        """
        Parse a paper from ArXiv /list/ endpoint (dt/dd structure).

        Args:
            dt: BeautifulSoup element for <dt> tag
            dd: BeautifulSoup element for <dd> tag

        Returns:
            ArxivPaper object or None if parsing fails
        """
        try:
            # Extract ArXiv ID from dt
            abs_link = dt.find("a", href=re.compile(r"/abs/"))
            if not abs_link:
                return None

            href = abs_link.get("href", "")
            arxiv_id_match = re.search(r"/abs/(\d+\.\d+)", href)
            if not arxiv_id_match:
                return None

            arxiv_id = arxiv_id_match.group(1)

            # Extract title from dd
            title_div = dd.find("div", class_="list-title")
            if not title_div:
                return None

            title = title_div.get_text(strip=True)
            # Remove "Title:" prefix if present
            title = re.sub(r"^Title:\s*", "", title)

            # Extract authors from dd
            authors_div = dd.find("div", class_="list-authors")
            authors = []
            if authors_div:
                # Authors are in <a> tags
                author_links = authors_div.find_all("a")
                authors = [a.get_text(strip=True) for a in author_links]

            # Try to extract submission date from comments
            comments_div = dd.find("div", class_="list-comments")
            published_date = None
            if comments_div:
                comment_text = comments_div.get_text()
                # Try to find date in format "DD MMM YYYY"
                date_match = re.search(r"(\d+\s+\w+\s+\d{4})", comment_text)
                if date_match:
                    try:
                        published_date = datetime.strptime(date_match.group(1), "%d %b %Y")
                    except ValueError:
                        pass

            # Construct PDF URL
            pdf_url = f"{self.base_url}/pdf/{arxiv_id}.pdf"

            # Note: The /list/ endpoint doesn't show full abstracts
            # Abstract is empty here - use individual paper scraping for that
            summary = ""

            paper = ArxivPaper(
                title=title,
                summary=summary,
                authors=authors,
                arxiv_id=arxiv_id,
                pdf_url=pdf_url,
                published_date=published_date,
            )

            return paper

        except Exception as e:
            logger.warning(f"Error parsing list paper entry: {e}")
            return None

    def _parse_paper_entry(self, entry) -> Optional[ArxivPaper]:
        """
        Parse a single paper entry from search results.

        Args:
            entry: BeautifulSoup element for paper entry

        Returns:
            ArxivPaper object or None if parsing fails
        """
        try:
            # Extract paper ID
            link_elem = entry.find("p", class_="list-title")
            if not link_elem:
                return None

            link = link_elem.find("a")
            if not link:
                return None

            href = link.get("href", "")
            # Extract ID from URL like /abs/2312.12345
            arxiv_id_match = re.search(r"/abs/(\d+\.\d+)", href)
            if not arxiv_id_match:
                return None

            arxiv_id = arxiv_id_match.group(1)

            # Extract title
            title_elem = entry.find("p", class_="title")
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)

            # Extract authors
            authors_elem = entry.find("p", class_="authors")
            authors = []
            if authors_elem:
                author_links = authors_elem.find_all("a")
                authors = [a.get_text(strip=True) for a in author_links]

            # Extract abstract/summary
            abstract_elem = entry.find("span", class_="abstract-full")
            if not abstract_elem:
                abstract_elem = entry.find("span", class_="abstract-short")

            summary = ""
            if abstract_elem:
                summary = abstract_elem.get_text(strip=True)

            # Extract submission date
            submitted_elem = entry.find("p", class_="is-size-7")
            published_date = None
            if submitted_elem:
                date_text = submitted_elem.get_text()
                # Try to extract date like "Submitted 23 Dec 2023"
                date_match = re.search(r"Submitted\s+(\d+\s+\w+\s+\d{4})", date_text)
                if date_match:
                    try:
                        published_date = datetime.strptime(date_match.group(1), "%d %b %Y")
                    except ValueError:
                        pass

            # Construct PDF URL
            pdf_url = f"{self.base_url}/pdf/{arxiv_id}.pdf"

            # Create ArxivPaper object
            paper = ArxivPaper(
                title=title,
                summary=summary,
                authors=authors,
                arxiv_id=arxiv_id,
                pdf_url=pdf_url,
                published_date=published_date,
            )

            return paper

        except Exception as e:
            logger.warning(f"Error parsing paper entry: {e}")
            return None

    def _filter_by_date(
        self, papers: List[ArxivPaper], from_date: Optional[datetime], to_date: Optional[datetime]
    ) -> List[ArxivPaper]:
        """
        Filter papers by date range.

        Args:
            papers: List of papers to filter
            from_date: Filter papers from this date
            to_date: Filter papers until this date

        Returns:
            Filtered list of papers
        """
        filtered = []

        for paper in papers:
            if paper.published_date is None:
                # Include papers without date
                filtered.append(paper)
                continue

            # Check date range
            if from_date and paper.published_date < from_date:
                continue
            if to_date and paper.published_date > to_date:
                continue

            filtered.append(paper)

        return filtered

    def scrape_paper_details(self, arxiv_id: str) -> Optional[ArxivPaper]:
        """
        Scrape detailed information for a specific paper.

        Args:
            arxiv_id: ArXiv ID (e.g., "2312.12345")

        Returns:
            ArxivPaper object with detailed information
        """
        try:
            # Fetch abstract page
            url = f"{self.base_url}/abs/{arxiv_id}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title_elem = soup.find("h1", class_="title")
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True).replace("Title:", "").strip()

            # Extract authors
            authors_elem = soup.find("div", class_="authors")
            authors = []
            if authors_elem:
                author_links = authors_elem.find_all("a")
                authors = [a.get_text(strip=True) for a in author_links]

            # Extract abstract
            abstract_elem = soup.find("blockquote", class_="abstract")
            summary = ""
            if abstract_elem:
                summary = abstract_elem.get_text(strip=True).replace("Abstract:", "").strip()

            # Extract submission date
            dateline_elem = soup.find("div", class_="dateline")
            published_date = None
            if dateline_elem:
                date_text = dateline_elem.get_text()
                date_match = re.search(r"\[Submitted.*?(\d+\s+\w+\s+\d{4})", date_text)
                if date_match:
                    try:
                        published_date = datetime.strptime(date_match.group(1), "%d %b %Y")
                    except ValueError:
                        pass

            # Construct PDF URL
            pdf_url = f"{self.base_url}/pdf/{arxiv_id}.pdf"

            # Create ArxivPaper object
            paper = ArxivPaper(
                title=title,
                summary=summary,
                authors=authors,
                arxiv_id=arxiv_id,
                pdf_url=pdf_url,
                published_date=published_date,
            )

            return paper

        except Exception as e:
            logger.error(f"Error scraping paper details for {arxiv_id}: {e}")
            return None
