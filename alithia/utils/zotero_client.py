"""
Zotero client utilities for retrieving research corpus.
"""

import os
from tempfile import mkstemp
from typing import Any, Dict, List

from gitignore_parser import parse_gitignore
from pyzotero import zotero


def get_zotero_corpus(zotero_id: str, zotero_key: str) -> List[Dict[str, Any]]:
    """
    Retrieve research corpus from Zotero library.

    Args:
        zotero_id: Zotero user ID
        zotero_key: Zotero API key

    Returns:
        List of paper dictionaries with abstracts
    """
    zot = zotero.Zotero(zotero_id, "user", zotero_key)

    # Get all collections
    collections = zot.everything(zot.collections())
    collections = {c["key"]: c for c in collections}

    # Get papers with abstracts
    corpus = zot.everything(zot.items(itemType="conferencePaper || journalArticle || preprint"))
    corpus = [c for c in corpus if c["data"]["abstractNote"] != ""]

    def get_collection_path(col_key: str) -> str:
        """Get the full path of a collection."""
        if p := collections[col_key]["data"]["parentCollection"]:
            return get_collection_path(p) + "/" + collections[col_key]["data"]["name"]
        else:
            return collections[col_key]["data"]["name"]

    # Add collection paths to each paper
    for c in corpus:
        paths = [get_collection_path(col) for col in c["data"]["collections"]]
        c["paths"] = paths

    return corpus


def filter_corpus(corpus: List[Dict[str, Any]], ignore_patterns: str) -> List[Dict[str, Any]]:
    """
    Filter corpus using gitignore-style patterns.

    Args:
        corpus: List of papers to filter
        ignore_patterns: Gitignore-style patterns (one per line)

    Returns:
        Filtered list of papers
    """
    if not ignore_patterns.strip():
        return corpus

    # Create temporary gitignore file
    _, filename = mkstemp()
    try:
        with open(filename, "w") as file:
            file.write(ignore_patterns)

        matcher = parse_gitignore(filename, base_dir="./")

        # Filter papers based on collection paths
        filtered_corpus = []
        for paper in corpus:
            match_results = [matcher(p) for p in paper.get("paths", [])]
            if not any(match_results):
                filtered_corpus.append(paper)

        return filtered_corpus
    finally:
        # Clean up temporary file
        if os.path.exists(filename):
            os.remove(filename)
