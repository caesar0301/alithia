"""
Example usage of get_arxiv_papers_search function.

This example demonstrates how to search arXiv papers with specific categories
and date ranges, similar to using the arXiv API query endpoint.
"""

from alithia.arxrec.arxiv_paper_utils import build_arxiv_search_query, get_arxiv_papers_search


def example_basic_search():
    """
    Basic example: Search for papers in AI, CV, LG, and CL categories
    submitted on October 25, 2025.

    This achieves functionality similar to:
    https://export.arxiv.org/api/query?search_query=(cat:cs.AI+OR+cat:cs.CV+OR+cat:cs.LG+OR+cat:cs.CL)+AND+submittedDate:[202510250000+TO+202510252359]&sortBy=submittedDate&sortOrder=ascending&max_results=200
    """
    papers = get_arxiv_papers_search(
        arxiv_query="cs.AI+cs.CV+cs.LG+cs.CL",
        from_time="202510250000",
        to_time="202510252359",
        max_results=200,
    )

    print(f"Found {len(papers)} papers")
    for paper in papers[:5]:  # Show first 5
        print(f"- {paper.title}")
        print(f"  Authors: {', '.join(paper.authors[:3])}")
        print(f"  arXiv ID: {paper.arxiv_id}")
        print()


def example_debug_mode():
    """
    Example: Use debug mode to get just 5 papers for testing.
    """
    papers = get_arxiv_papers_search(
        arxiv_query="cs.AI+cs.CV",
        from_time="202510250000",
        to_time="202510252359",
        debug=True,
    )

    print(f"Debug mode: Found {len(papers)} papers (max 5)")


def example_build_query():
    """
    Example: Build a query string without executing the search.
    """
    query = build_arxiv_search_query(
        arxiv_query="cs.AI+cs.CV+cs.LG+cs.CL",
        from_time="202510250000",
        to_time="202510252359",
    )

    print(f"Generated query: {query}")
    # Output: (cat:cs.AI OR cat:cs.CV OR cat:cs.LG OR cat:cs.CL) AND submittedDate:[202510250000 TO 202510252359]


def example_single_category():
    """
    Example: Search for papers in a single category.
    """
    papers = get_arxiv_papers_search(
        arxiv_query="cs.AI",
        from_time="202510250000",
        to_time="202510252359",
        max_results=50,
    )

    print(f"Found {len(papers)} papers in cs.AI")


if __name__ == "__main__":
    print("=" * 60)
    print("ArXiv Search Examples")
    print("=" * 60)
    print()

    # Uncomment to run examples (they make real API calls):
    # example_basic_search()
    # example_debug_mode()
    example_build_query()
    # example_single_category()
