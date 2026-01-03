"""ArXiv search examples: category and date range queries."""

from alithia.utils.arxiv_paper_fetcher import build_arxiv_search_query
from alithia.utils.arxiv_paper_utils import get_arxiv_papers_search


def example_basic_search():
    """Search AI/CV/LG/CL papers from Oct 25, 2025."""
    papers = get_arxiv_papers_search(
        arxiv_query="cs.AI+cs.CV+cs.LG+cs.CL",
        from_time="202510250000",
        to_time="202510252359",
        max_results=200,
    )

    print(f"Found {len(papers)} papers")
    for paper in papers[:5]:
        print(f"- {paper.title}")
        print(f"  Authors: {', '.join(paper.authors[:3])}")
        print(f"  arXiv ID: {paper.arxiv_id}")
        print()


def example_debug_mode():
    """Debug mode: limit to 5 papers for testing."""
    papers = get_arxiv_papers_search(
        arxiv_query="cs.AI+cs.CV",
        from_time="202510250000",
        to_time="202510252359",
        debug=True,
    )

    print(f"Debug: {len(papers)} papers (max 5)")


def example_build_query():
    """Build query string without executing search."""
    query = build_arxiv_search_query(
        arxiv_query="cs.AI+cs.CV+cs.LG+cs.CL",
        from_time="202510250000",
        to_time="202510252359",
    )

    print(f"Generated query: {query}")


def example_single_category():
    """Search single category (cs.AI only)."""
    papers = get_arxiv_papers_search(
        arxiv_query="cs.AI",
        from_time="202510250000",
        to_time="202510252359",
        max_results=50,
    )

    print(f"Found {len(papers)} cs.AI papers")


if __name__ == "__main__":
    print("=" * 60)
    print("ArXiv Search Examples")
    print("=" * 60)
    print()

    example_build_query()
    # Uncomment to run (makes real API calls):
    # example_basic_search()
    # example_debug_mode()
    # example_single_category()
