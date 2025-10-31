from unittest.mock import Mock, patch

import pytest

from alithia.arxrec.arxiv_paper_utils import (
    _build_category_query,
    build_arxiv_search_query,
    extract_affiliations,
    extract_tex_content,
    generate_tldr,
)
from alithia.arxrec.models import ArxivPaper


@pytest.mark.unit
def test_extract_tex_content_no_arxiv_result_returns_none():
    p = ArxivPaper(title="t", summary="s", authors=["a"], arxiv_id="x", pdf_url="http://x")
    assert extract_tex_content(p) is None


@pytest.mark.unit
def test_generate_tldr_uses_llm_and_truncates_prompt():
    p = ArxivPaper(title="t" * 1000, summary="s" * 5000, authors=["a"], arxiv_id="x", pdf_url="http://x")
    fake_llm = Mock()
    fake_llm.completion.return_value = "TLDR"

    with (patch("alithia.arxrec.arxiv_paper_utils.tiktoken") as mock_tiktoken,):
        mock_enc = Mock()
        mock_enc.encode.side_effect = lambda s: list(range(min(len(s), 8000)))
        mock_enc.decode.side_effect = lambda toks: "x" * len(toks)
        mock_tiktoken.encoding_for_model.return_value = mock_enc

        res = generate_tldr(p, fake_llm)
        assert res == "TLDR"
        fake_llm.completion.assert_called()


@pytest.mark.unit
def test_extract_affiliations_parses_list():
    p = ArxivPaper(title="t", summary="s", authors=["a"], arxiv_id="x", pdf_url="http://x")

    # Provide fake tex with author information
    fake_tex = {
        "all": r"""\\author{Alice \\and Bob} \\maketitle""",
    }
    fake_llm = Mock()
    fake_llm.completion.return_value = "['Inst A', 'Inst B']"

    with (patch("alithia.arxrec.arxiv_paper_utils.tiktoken") as mock_tiktoken,):
        mock_enc = Mock()
        mock_enc.encode.side_effect = lambda s: list(range(min(len(s), 8000)))
        mock_enc.decode.side_effect = lambda toks: "x" * len(toks)
        mock_tiktoken.encoding_for_model.return_value = mock_enc

        # Set the tex content
        p.tex = fake_tex
        affs = extract_affiliations(p, fake_llm)
        assert set(affs) == {"Inst A", "Inst B"}


@pytest.mark.unit
def test_build_category_query_single_category():
    """Test building category query with a single category."""
    query = _build_category_query("cs.AI")
    assert query == "cat:cs.AI"


@pytest.mark.unit
def test_build_category_query_multiple_categories():
    """Test building category query with multiple categories."""
    query = _build_category_query("cs.AI+cs.CV+cs.LG")
    assert query == "cat:cs.AI OR cat:cs.CV OR cat:cs.LG"


@pytest.mark.unit
def test_build_category_query_with_spaces():
    """Test building category query handles spaces around categories."""
    query = _build_category_query("cs.AI + cs.CV + cs.LG")
    assert query == "cat:cs.AI OR cat:cs.CV OR cat:cs.LG"


@pytest.mark.unit
def test_build_arxiv_search_query_single_category():
    """Test building search query with a single category."""
    query = build_arxiv_search_query("cs.AI", "202510250000", "202510252359")
    assert query == "(cat:cs.AI) AND submittedDate:[202510250000 TO 202510252359]"


@pytest.mark.unit
def test_build_arxiv_search_query_multiple_categories():
    """Test building search query with multiple categories."""
    query = build_arxiv_search_query("cs.AI+cs.CV+cs.LG+cs.CL", "202510250000", "202510252359")
    expected = "(cat:cs.AI OR cat:cs.CV OR cat:cs.LG OR cat:cs.CL) AND submittedDate:[202510250000 TO 202510252359]"
    assert query == expected


@pytest.mark.unit
def test_build_arxiv_search_query_with_spaces():
    """Test building search query handles spaces in category list."""
    query = build_arxiv_search_query("cs.AI + cs.CV + cs.LG", "202510250000", "202510252359")
    expected = "(cat:cs.AI OR cat:cs.CV OR cat:cs.LG) AND submittedDate:[202510250000 TO 202510252359]"
    assert query == expected


@pytest.mark.unit
def test_build_arxiv_search_query_different_date_formats():
    """Test building search query with different date/time values."""
    query = build_arxiv_search_query("cs.AI", "202501010000", "202512312359")
    assert query == "(cat:cs.AI) AND submittedDate:[202501010000 TO 202512312359]"
