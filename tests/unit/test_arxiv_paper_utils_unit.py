from unittest.mock import Mock, patch

import pytest

from alithia.core.arxiv_paper_utils import extract_affiliations, extract_tex_content, generate_tldr
from alithia.core.paper import ArxivPaper


@pytest.mark.unit
def test_extract_tex_content_no_arxiv_result_returns_none():
    p = ArxivPaper(title="t", summary="s", authors=["a"], arxiv_id="x", pdf_url="http://x")
    assert extract_tex_content(p) is None


@pytest.mark.unit
def test_generate_tldr_uses_llm_and_truncates_prompt():
    p = ArxivPaper(title="t" * 1000, summary="s" * 5000, authors=["a"], arxiv_id="x", pdf_url="http://x")
    fake_llm = Mock()
    fake_llm.chat_completion.return_value = "TLDR"

    with (
        patch("alithia.core.arxiv_paper_utils.extract_tex_content", return_value=None),
        patch("alithia.core.arxiv_paper_utils.tiktoken") as mock_tiktoken,
    ):
        mock_enc = Mock()
        mock_enc.encode.side_effect = lambda s: list(range(min(len(s), 8000)))
        mock_enc.decode.side_effect = lambda toks: "x" * len(toks)
        mock_tiktoken.encoding_for_model.return_value = mock_enc

        res = generate_tldr(p, fake_llm)
        assert res == "TLDR"
        fake_llm.chat_completion.assert_called()


@pytest.mark.unit
def test_extract_affiliations_parses_list():
    p = ArxivPaper(title="t", summary="s", authors=["a"], arxiv_id="x", pdf_url="http://x")

    # Provide fake tex with author information
    fake_tex = {
        "all": r"""\\author{Alice \\and Bob} \\maketitle""",
    }
    fake_llm = Mock()
    fake_llm.chat_completion.return_value = "['Inst A', 'Inst B']"

    with (
        patch("alithia.core.arxiv_paper_utils.extract_tex_content", return_value=fake_tex),
        patch("alithia.core.arxiv_paper_utils.tiktoken") as mock_tiktoken,
    ):
        mock_enc = Mock()
        mock_enc.encode.side_effect = lambda s: list(range(min(len(s), 8000)))
        mock_enc.decode.side_effect = lambda toks: "x" * len(toks)
        mock_tiktoken.encoding_for_model.return_value = mock_enc

        affs = extract_affiliations(p, fake_llm)
        assert set(affs) == {"Inst A", "Inst B"}
