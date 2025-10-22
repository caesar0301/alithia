from alithia.core.tools.reference_linker import ReferenceLinkerTool


def test_extract_citation_keys_bracket_style():
    tool = ReferenceLinkerTool(embedding_service=None)
    text = "Our method [1] builds upon [2, 3]."
    keys = tool._extract_citation_keys(text)
    assert keys == ["[1]", "[2]", "[3]"]


def test_extract_citation_keys_parenthetical_ignored():
    tool = ReferenceLinkerTool(embedding_service=None)
    text = "As shown by Smith et al. (2021), performance improves."
    keys = tool._extract_citation_keys(text)
    assert keys == []
