import types

import pytest

from alithia.core.tools.code_generator import CodeGeneratorInput, CodeGeneratorTool
from alithia.core.tools.models import BibliographyEntry, ParagraphElement, Section, StructuredPaper
from alithia.core.tools.pdf_parser import PDFParserInput, PDFParserTool
from alithia.core.tools.reference_linker import ReferenceLinkerInput, ReferenceLinkerTool
from alithia.core.tools.web_searcher import FindPaperInfoInput, WebSearcherTool


@pytest.mark.integration
def test_pdf_parser_integration(monkeypatch):
    class DummyPDFProcessor:
        def process(self, path: str):
            return [
                {"page": 1, "text": "Intro [1]"},
                {"page": 2, "text": "Method."},
            ]

    tool = PDFParserTool()
    monkeypatch.setattr(tool, "processor", DummyPDFProcessor())
    out = tool.execute(PDFParserInput(file_path="/tmp/sample.pdf"))
    assert out.structured_paper.sections


@pytest.mark.integration
def test_web_searcher_integration(monkeypatch):
    from alithia.core.tools import web_searcher as ws

    class DummyAuthor:
        def __init__(self, name):
            self.name = name

    class DummyRes:
        def __init__(self):
            self.title = "Foo"
            self.summary = "Bar"
            self.pdf_url = "http://x/y.pdf"
            self.authors = [DummyAuthor("A")]

        def get_short_id(self):
            return "0000.00000"

    monkeypatch.setattr(
        ws.arxiv, "Client", lambda num_retries=5: types.SimpleNamespace(results=lambda s: iter([DummyRes()]))
    )
    monkeypatch.setattr(ws.arxiv, "Search", lambda query, max_results=5: types.SimpleNamespace())

    tool = WebSearcherTool()
    out = tool.execute(FindPaperInfoInput(title="Foo"))
    assert out.pdf_url and out.metadata


@pytest.mark.integration
def test_reference_linker_integration(monkeypatch):
    class DummyEmbeddingService:
        def embed_texts(self, texts):
            import numpy as np

            v = np.ones((len(texts), 2), dtype=float)
            return v / 1.4142

    paper = StructuredPaper(
        paper_id="p",
        sections=[Section(section_number="1", title="t", content=[ParagraphElement(element_id="p", text="x [1]")])],
        bibliography=[BibliographyEntry(ref_id="[1]", full_citation="Ref")],
    )
    tool = ReferenceLinkerTool(embedding_service=DummyEmbeddingService())
    out = tool.execute(ReferenceLinkerInput(source_paper=paper, query="topic"))
    assert out.references


@pytest.mark.integration
def test_code_generator_integration(monkeypatch):
    from alithia.core.tools import code_generator as cg

    class DummyLLM:
        def generate(self, messages):
            return "print('ok')\n"

    monkeypatch.setattr(cg, "get_llm", lambda profile: DummyLLM())

    paper = StructuredPaper(paper_id="p", sections=[Section(section_number="1", title="t", content=[])])
    tool = CodeGeneratorTool()
    out = tool.execute(CodeGeneratorInput(pseudocode_element={"pseudocode": "x"}, source_paper=paper))
    assert "print" in out.generated_code
