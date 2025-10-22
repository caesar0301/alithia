from alithia.core.tools.code_generator import CodeGeneratorInput, CodeGeneratorTool
from alithia.core.tools.models import ParagraphElement, Section, StructuredPaper


class DummyLLM:
    def generate(self, messages):
        return "def foo():\n    return 42\n"


def test_code_generator_with_dummy_llm(monkeypatch):
    # Monkeypatch get_llm to return DummyLLM
    monkeypatch.setattr("alithia.core.tools.code_generator.get_llm", lambda profile: DummyLLM())

    paper = StructuredPaper(
        paper_id="p1",
        sections=[
            Section(section_number="1", title="Intro", content=[ParagraphElement(element_id="p", text="context")])
        ],
    )
    tool = CodeGeneratorTool()
    out = tool.execute(
        CodeGeneratorInput(
            pseudocode_element={"label": "Alg 1", "caption": "cap", "pseudocode": "return 42"},
            source_paper=paper,
        )
    )
    assert "def" in out.generated_code
