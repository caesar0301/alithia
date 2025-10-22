from alithia.core.tools.models import ParagraphElement
from alithia.core.tools.pdf_parser import PDFParserInput, PDFParserTool


class DummyPDFProcessor:
    def process(self, path: str):
        return [
            {"page": 1, "text": "This is a test [1]."},
            {"page": 2, "text": "Another paragraph without citation."},
            {"page": 3, "text": "Related to prior work [2, 3]."},
        ]


def test_pdf_parser_tool_monkeypatch(monkeypatch):
    tool = PDFParserTool()
    # Monkeypatch the internal processor
    monkeypatch.setattr(tool, "processor", DummyPDFProcessor())

    out = tool.execute(PDFParserInput(file_path="/tmp/does_not_matter.pdf"))
    paper = out.structured_paper
    assert paper.paper_id
    assert len(paper.sections) == 1
    elements = paper.sections[0].content
    assert any(isinstance(e, ParagraphElement) for e in elements)
    texts = [getattr(e, "text", "") for e in elements]
    assert any("test" in t for t in texts)
    # Verify citations extracted
    para_with_cites = [e for e in elements if isinstance(e, ParagraphElement) and e.citations]
    assert any(c.key == "[1]" for e in para_with_cites for c in e.citations)
    assert any(c.key == "[2]" for e in para_with_cites for c in e.citations)
    assert any(c.key == "[3]" for e in para_with_cites for c in e.citations)
