import pytest

from alithia.core.paper import ArxivPaper, EmailContent, ScoredPaper


@pytest.mark.unit
def test_arxiv_paper_from_arxiv_result_strips_version():
    class DummyAuthor:
        def __init__(self, name: str):
            self.name = name

    class DummyResult:
        title = "Title"
        summary = "Summary"
        authors = [DummyAuthor("Alice"), DummyAuthor("Bob")]
        pdf_url = "http://example.com/paper.pdf"
        published = "2024-01-01"

        def get_short_id(self):
            return "1234.5678v2"

    p = ArxivPaper.from_arxiv_result(DummyResult())
    assert p.arxiv_id == "1234.5678"
    assert p.title == "Title"
    assert p.authors == ["Alice", "Bob"]


@pytest.mark.unit
def test_scored_paper_sets_paper_score():
    p = ArxivPaper(title="t", summary="s", authors=["a"], arxiv_id="x", pdf_url="http://x")
    sp = ScoredPaper(paper=p, score=8.1)
    assert sp.paper.score == 8.1


@pytest.mark.unit
def test_email_content_is_empty():
    e = EmailContent(subject="sub", html_content="html", papers=[])
    assert e.is_empty() is True
