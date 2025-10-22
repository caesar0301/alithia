"""
ArXiv client utilities for discovering new papers.
"""

from typing import List

import arxiv
import feedparser

from .paper import ArxivPaper


def get_arxiv_papers(arxiv_query: str, debug: bool = False) -> List[ArxivPaper]:
    """
    Retrieve papers from ArXiv based on query.

    Args:
        arxiv_query: ArXiv query string (e.g., "cs.AI+cs.CV")
        debug: If True, return 5 recent papers regardless of date

    Returns:
        List of ArxivPaper objects
    """
    client = arxiv.Client(num_retries=10, delay_seconds=10)

    if debug:
        # Return 5 recent papers for debugging
        search = arxiv.Search(query="cat:cs.AI", sort_by=arxiv.SortCriterion.SubmittedDate, max_results=5)
        papers = [ArxivPaper.from_arxiv_result(p) for p in client.results(search)]
        return papers

    # Fetch papers from RSS feed
    feed = feedparser.parse(f"https://rss.arxiv.org/atom/{arxiv_query}")

    if "Feed error for query" in feed.feed.get("title", ""):
        raise ValueError(f"Invalid ARXIV_QUERY: {arxiv_query}")

    # Extract paper IDs from feed
    paper_ids = [
        entry.id.removeprefix("oai:arXiv.org:")
        for entry in feed.entries
        if hasattr(entry, "arxiv_announce_type") and entry.arxiv_announce_type == "new"
    ]

    if not paper_ids:
        return []

    # Fetch paper details in batches
    papers = []
    batch_size = 50

    for i in range(0, len(paper_ids), batch_size):
        batch_ids = paper_ids[i : i + batch_size]
        search = arxiv.Search(id_list=batch_ids)
        batch_papers = [ArxivPaper.from_arxiv_result(p) for p in client.results(search)]
        papers.extend(batch_papers)

    return papers
