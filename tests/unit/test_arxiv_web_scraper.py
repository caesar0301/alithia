"""
Unit tests for the ArXiv web scraper module.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from alithia.utils.arxiv_web_scraper import ArxivWebScraper


@pytest.mark.unit
def test_arxiv_web_scraper_initialization():
    """Test ArxivWebScraper initialization."""
    scraper = ArxivWebScraper(timeout=60, user_agent="TestAgent/1.0")

    assert scraper.timeout == 60
    assert scraper.base_url == "https://arxiv.org"
    assert scraper.session is not None
    assert scraper.session.headers["User-Agent"] == "TestAgent/1.0"


@pytest.mark.unit
def test_arxiv_web_scraper_custom_session():
    """Test ArxivWebScraper with custom session."""
    custom_session = Mock()
    custom_session.headers = {}

    scraper = ArxivWebScraper(session=custom_session)
    assert scraper.session == custom_session


@pytest.mark.unit
def test_build_search_url_single_category():
    """Test building search URL with single category."""
    scraper = ArxivWebScraper()
    url = scraper._build_search_url("cs.AI", start=0)

    assert "arxiv.org/search/" in url
    assert "cat%3Acs.AI" in url  # URL encoded
    assert "start=0" in url
    assert "size=50" in url


@pytest.mark.unit
def test_build_search_url_multiple_categories():
    """Test building search URL with multiple categories."""
    scraper = ArxivWebScraper()
    url = scraper._build_search_url("cs.AI+cs.CV+cs.LG", start=50)

    assert "arxiv.org/search/" in url
    assert "cat%3Acs.AI" in url
    assert "cat%3Acs.CV" in url
    assert "cat%3Acs.LG" in url
    assert "OR" in url
    assert "start=50" in url


@pytest.mark.unit
def test_parse_paper_entry_valid():
    """Test parsing a valid paper entry."""
    scraper = ArxivWebScraper()

    # Create mock HTML structure
    mock_entry = Mock()

    # Mock paper ID link
    mock_link_p = Mock()
    mock_link = Mock()
    mock_link.get.return_value = "/abs/2312.12345"
    mock_link_p.find.return_value = mock_link

    # Mock title
    mock_title = Mock()
    mock_title.get_text.return_value = "Test Paper Title"

    # Mock authors
    mock_authors_p = Mock()
    mock_author1 = Mock()
    mock_author1.get_text.return_value = "Alice"
    mock_author2 = Mock()
    mock_author2.get_text.return_value = "Bob"
    mock_authors_p.find_all.return_value = [mock_author1, mock_author2]

    # Mock abstract
    mock_abstract = Mock()
    mock_abstract.get_text.return_value = "This is a test abstract."

    # Mock date
    mock_date = Mock()
    mock_date.get_text.return_value = "Submitted 23 Dec 2023"

    # Set up mock entry to return these elements
    def mock_find(tag, **kwargs):
        class_name = kwargs.get("class_")
        if class_name == "list-title":
            return mock_link_p
        elif class_name == "title":
            return mock_title
        elif class_name == "authors":
            return mock_authors_p
        elif class_name == "abstract-full":
            return mock_abstract
        elif class_name == "is-size-7":
            return mock_date
        return None

    mock_entry.find = mock_find

    paper = scraper._parse_paper_entry(mock_entry)

    assert paper is not None
    assert paper.title == "Test Paper Title"
    assert paper.arxiv_id == "2312.12345"
    assert paper.authors == ["Alice", "Bob"]
    assert paper.summary == "This is a test abstract."
    assert paper.pdf_url == "https://arxiv.org/pdf/2312.12345.pdf"


@pytest.mark.unit
def test_parse_paper_entry_missing_required_fields():
    """Test parsing fails gracefully when required fields are missing."""
    scraper = ArxivWebScraper()

    # Mock entry without required fields
    mock_entry = Mock()
    mock_entry.find.return_value = None

    paper = scraper._parse_paper_entry(mock_entry)
    assert paper is None


@pytest.mark.unit
def test_filter_by_date():
    """Test date filtering of papers."""
    scraper = ArxivWebScraper()

    from alithia.models import ArxivPaper

    papers = [
        ArxivPaper(
            title="Paper 1",
            summary="Abstract 1",
            authors=["Author 1"],
            arxiv_id="2312.00001",
            pdf_url="url1",
            published_date=datetime(2023, 12, 20),
        ),
        ArxivPaper(
            title="Paper 2",
            summary="Abstract 2",
            authors=["Author 2"],
            arxiv_id="2312.00002",
            pdf_url="url2",
            published_date=datetime(2023, 12, 25),
        ),
        ArxivPaper(
            title="Paper 3",
            summary="Abstract 3",
            authors=["Author 3"],
            arxiv_id="2312.00003",
            pdf_url="url3",
            published_date=datetime(2023, 12, 30),
        ),
        ArxivPaper(
            title="Paper 4",
            summary="Abstract 4",
            authors=["Author 4"],
            arxiv_id="2312.00004",
            pdf_url="url4",
            published_date=None,  # No date
        ),
    ]

    # Filter from Dec 23 to Dec 28
    from_date = datetime(2023, 12, 23)
    to_date = datetime(2023, 12, 28)

    filtered = scraper._filter_by_date(papers, from_date, to_date)

    # Should include Paper 2 (Dec 25) and Paper 4 (no date)
    assert len(filtered) == 2
    assert filtered[0].arxiv_id == "2312.00002"
    assert filtered[1].arxiv_id == "2312.00004"


@pytest.mark.unit
def test_filter_by_date_from_only():
    """Test date filtering with only from_date."""
    scraper = ArxivWebScraper()

    from alithia.models import ArxivPaper

    papers = [
        ArxivPaper(
            title="Paper 1",
            summary="Abstract 1",
            authors=["Author 1"],
            arxiv_id="2312.00001",
            pdf_url="url1",
            published_date=datetime(2023, 12, 20),
        ),
        ArxivPaper(
            title="Paper 2",
            summary="Abstract 2",
            authors=["Author 2"],
            arxiv_id="2312.00002",
            pdf_url="url2",
            published_date=datetime(2023, 12, 25),
        ),
    ]

    from_date = datetime(2023, 12, 23)
    filtered = scraper._filter_by_date(papers, from_date, None)

    # Should only include Paper 2
    assert len(filtered) == 1
    assert filtered[0].arxiv_id == "2312.00002"


@pytest.mark.unit
def test_scrape_arxiv_search_error_handling():
    """Test that scraping handles errors gracefully."""
    scraper = ArxivWebScraper()

    with patch.object(scraper.session, "get") as mock_get:
        mock_get.side_effect = Exception("Network error")

        papers = scraper.scrape_arxiv_search("cs.AI", max_results=10)

        # Should return empty list instead of crashing
        assert papers == []


@pytest.mark.unit
def test_scrape_paper_details_success():
    """Test scraping detailed paper information."""
    scraper = ArxivWebScraper()

    # Mock HTML response
    mock_html = """
    <html>
        <h1 class="title">Title:Test Paper Title</h1>
        <div class="authors">
            <a>Alice Smith</a>
            <a>Bob Jones</a>
        </div>
        <blockquote class="abstract">Abstract:This is the paper abstract.</blockquote>
        <div class="dateline">[Submitted on 23 Dec 2023]</div>
    </html>
    """

    with patch.object(scraper.session, "get") as mock_get:
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        paper = scraper.scrape_paper_details("2312.12345")

        assert paper is not None
        assert paper.title == "Test Paper Title"
        assert paper.arxiv_id == "2312.12345"
        assert "Alice Smith" in paper.authors
        assert "Bob Jones" in paper.authors
        assert paper.summary == "This is the paper abstract."
        assert paper.pdf_url == "https://arxiv.org/pdf/2312.12345.pdf"


@pytest.mark.unit
def test_scrape_paper_details_error():
    """Test scraping paper details handles errors."""
    scraper = ArxivWebScraper()

    with patch.object(scraper.session, "get") as mock_get:
        mock_get.side_effect = Exception("Network error")

        paper = scraper.scrape_paper_details("2312.12345")

        # Should return None on error
        assert paper is None


@pytest.mark.unit
def test_parse_search_results_empty():
    """Test parsing empty search results."""
    scraper = ArxivWebScraper()

    mock_html = """
    <html>
        <div class="results">
            <!-- No results -->
        </div>
    </html>
    """

    papers = scraper._parse_search_results(mock_html)
    assert papers == []


@pytest.mark.unit
def test_scrape_arxiv_search_pagination():
    """Test pagination during scraping."""
    scraper = ArxivWebScraper()

    from alithia.models import ArxivPaper

    mock_paper = ArxivPaper(title="Test", summary="Abstract", authors=["Author"], arxiv_id="2312.00001", pdf_url="url")

    with (
        patch.object(scraper, "_parse_search_results") as mock_parse,
        patch.object(scraper.session, "get") as mock_get,
        patch("time.sleep"),
    ):  # Mock sleep to speed up test

        # First page returns papers, second page returns empty
        mock_parse.side_effect = [[mock_paper], []]

        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        papers = scraper.scrape_arxiv_search("cs.AI", max_results=100)

        # Should have made 2 requests (one successful, one empty)
        assert mock_get.call_count == 2
        assert len(papers) == 1


@pytest.mark.unit
def test_scrape_arxiv_search_respects_max_results():
    """Test that max_results is respected during scraping."""
    scraper = ArxivWebScraper()

    from alithia.models import ArxivPaper

    # Create more papers than max_results
    papers_page1 = [
        ArxivPaper(title=f"Paper {i}", summary="Abstract", authors=["Author"], arxiv_id=f"2312.0000{i}", pdf_url="url")
        for i in range(50)
    ]

    papers_page2 = [
        ArxivPaper(title=f"Paper {i}", summary="Abstract", authors=["Author"], arxiv_id=f"2312.0010{i}", pdf_url="url")
        for i in range(50)
    ]

    with (
        patch.object(scraper, "_parse_search_results") as mock_parse,
        patch.object(scraper.session, "get") as mock_get,
        patch("time.sleep"),
    ):

        mock_parse.side_effect = [papers_page1, papers_page2]

        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        papers = scraper.scrape_arxiv_search("cs.AI", max_results=75)

        # Should stop at 75 papers
        assert len(papers) == 75
