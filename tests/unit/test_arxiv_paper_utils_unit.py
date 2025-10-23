from unittest.mock import Mock, patch

import pytest

from alithia.arxrec.arxiv_paper import ArxivPaper


@pytest.mark.unit
def test_extract_tex_content_no_arxiv_result_returns_none():
    p = ArxivPaper(title="t", summary="s", authors=["a"], arxiv_id="x", pdf_url="http://x")
    assert p._extract_tex_content() is None


@pytest.mark.unit
def test_generate_tldr_uses_llm_and_truncates_prompt():
    p = ArxivPaper(title="t" * 1000, summary="s" * 5000, authors=["a"], arxiv_id="x", pdf_url="http://x")
    fake_llm = Mock()
    fake_llm.chat_completion.return_value = "TLDR"

    with (patch("alithia.arxrec.arxiv_paper.tiktoken") as mock_tiktoken,):
        mock_enc = Mock()
        mock_enc.encode.side_effect = lambda s: list(range(min(len(s), 8000)))
        mock_enc.decode.side_effect = lambda toks: "x" * len(toks)
        mock_tiktoken.encoding_for_model.return_value = mock_enc

        res = p._generate_tldr(fake_llm)
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

    with (patch("alithia.arxrec.arxiv_paper.tiktoken") as mock_tiktoken,):
        mock_enc = Mock()
        mock_enc.encode.side_effect = lambda s: list(range(min(len(s), 8000)))
        mock_enc.decode.side_effect = lambda toks: "x" * len(toks)
        mock_tiktoken.encoding_for_model.return_value = mock_enc

        # Set the tex content
        p.tex = fake_tex
        affs = p._extract_affiliations(fake_llm)
        assert set(affs) == {"Inst A", "Inst B"}
