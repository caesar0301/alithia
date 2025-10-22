from alithia.core.tools.models import (
    AlgorithmElement,
    BibliographyEntry,
    PaperMetadata,
    ParagraphElement,
    Section,
    StructuredPaper,
)


def test_structured_paper_model():
    meta = PaperMetadata(title="T")
    para = ParagraphElement(element_id="p1", text="hello")
    sec = Section(section_number="1", title="Intro", content=[para])
    bib = [BibliographyEntry(ref_id="[1]", full_citation="Foo")]
    sp = StructuredPaper(paper_id="id", metadata=meta, sections=[sec], bibliography=bib)
    assert sp.metadata.title == "T"
    assert sp.sections[0].content[0].type == "paragraph"


def test_algorithm_element_defaults():
    alg = AlgorithmElement(element_id="a1")
    assert alg.type == "algorithm"
