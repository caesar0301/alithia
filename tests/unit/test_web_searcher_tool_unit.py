import types

from alithia.core.tools.web_searcher import FindPaperInfoInput, WebSearcherTool


class DummyAuthor:
    def __init__(self, name):
        self.name = name


class DummyArxivResult:
    def __init__(self, title, summary, pdf_url, authors):
        self.title = title
        self.summary = summary
        self.pdf_url = pdf_url
        self.authors = [DummyAuthor(a) for a in authors]

    def get_short_id(self):
        return "1234.56789"


class DummyClient:
    def __init__(self, results):
        self._results = results

    def results(self, search):
        return iter(self._results)


def test_web_searcher_exact_match(monkeypatch):
    tool = WebSearcherTool()
    dummy = DummyArxivResult(
        title="Exact Title",
        summary="An abstract",
        pdf_url="http://example.com/x.pdf",
        authors=["Alice", "Bob"],
    )
    # Monkeypatch arxiv.Client and arxiv.Search
    monkeypatch.setattr("alithia.core.tools.web_searcher.arxiv.Client", lambda num_retries=5: DummyClient([dummy]))
    monkeypatch.setattr(
        "alithia.core.tools.web_searcher.arxiv.Search",
        lambda query, max_results=5: types.SimpleNamespace(query=query, max_results=max_results),
    )

    out = tool.execute(FindPaperInfoInput(title="Exact Title"))
    assert out.pdf_url == "http://example.com/x.pdf"
    assert out.metadata["title"] == "Exact Title"
    assert out.metadata["authors"] == ["Alice", "Bob"]


def test_web_searcher_no_match(monkeypatch):
    tool = WebSearcherTool()
    monkeypatch.setattr("alithia.core.tools.web_searcher.arxiv.Client", lambda num_retries=5: DummyClient([]))
    monkeypatch.setattr(
        "alithia.core.tools.web_searcher.arxiv.Search",
        lambda query, max_results=5: types.SimpleNamespace(query=query, max_results=max_results),
    )

    out = tool.execute(FindPaperInfoInput(title="Unknown Title"))
    assert out.pdf_url is None
    assert out.metadata["title"] == "Unknown Title"
