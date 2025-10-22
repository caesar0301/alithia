import pytest

from alithia.core.email_utils import create_empty_email_html, create_paper_html, get_stars_html
from alithia.core.paper import ArxivPaper, ScoredPaper


@pytest.mark.unit
def test_get_stars_html_boundaries():
    assert get_stars_html(0) == ""
    assert get_stars_html(6) == ""
    assert "⭐" in get_stars_html(7)
    assert get_stars_html(8).count("⭐") == 5
    assert get_stars_html(10).count("⭐") == 5


@pytest.mark.unit
def test_create_empty_email_html_contains_message():
    html = create_empty_email_html()
    assert "No Papers Today" in html


@pytest.mark.unit
def test_create_paper_html_includes_fields():
    paper = ArxivPaper(
        title="An Interesting Paper",
        summary="Summary",
        authors=["Alice", "Bob", "Carol", "Dave", "Eve", "Frank"],
        arxiv_id="1234.5678",
        pdf_url="http://example.com/paper.pdf",
        code_url="http://example.com/code",
        affiliations=["Inst A", "Inst B", "Inst C", "Inst D", "Inst E", "Inst F"],
    )
    sp = ScoredPaper(paper=paper, score=9.0)
    html = create_paper_html(sp)

    assert "An Interesting Paper" in html
    assert "Alice, Bob, Carol, Dave, Eve, ..." in html
    assert "Inst A, Inst B, Inst C, Inst D, Inst E, ..." in html
    assert "arXiv ID" in html
    assert "Relevance" in html
    assert "Code" in html
