import os

import pytest

try:
    import pyzotero  # noqa: F401
except Exception:  # pragma: no cover
    pyzotero = None

from alithia.core.zotero_client import filter_corpus, get_zotero_corpus


@pytest.mark.integration
def test_get_zotero_corpus_real_env_or_skip():
    if pyzotero is None:
        pytest.skip("pyzotero not installed")

    zid = os.getenv("ZOTERO_ID")
    zkey = os.getenv("ZOTERO_KEY")
    if not (zid and zkey):
        pytest.skip("Zotero credentials not provided in environment")

    corpus = get_zotero_corpus(zid, zkey)
    assert isinstance(corpus, list)
    if corpus:
        assert "data" in corpus[0]
        assert "abstractNote" in corpus[0]["data"]
        assert isinstance(corpus[0].get("paths"), list)


@pytest.mark.integration
def test_filter_corpus_with_ignore_patterns():
    corpus = [
        {"data": {"abstractNote": "a"}, "paths": ["AI/LLM", "ML/NLP"]},
        {"data": {"abstractNote": "b"}, "paths": ["Physics/Quantum"]},
    ]
    ignore = "AI/*\n!AI/Important\nPhysics/*\n"
    filtered = filter_corpus(corpus, ignore)
    # Physics entry should be filtered out, AI/LLM filtered, but no AI/Important here
    assert len(filtered) == 0
