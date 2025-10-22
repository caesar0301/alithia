from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from langchain_core.tools import BaseTool

from alithia.core.embedding import EmbeddingService, cosine_similarity_matrix

from .base import ToolInput, ToolOutput
from .models import BibliographyEntry, ParagraphElement, StructuredPaper


class ReferenceLinkerInput(ToolInput):
    source_paper: StructuredPaper
    query: str
    top_k: int = 5


class ReferenceLinkerOutput(ToolOutput):
    references: List[BibliographyEntry]


class ReferenceLinkerTool(BaseTool):
    name: str = "core.reference_linker"
    description: str = "Resolve citations relevant to a query from a parsed paper"
    args_schema: type[ReferenceLinkerInput] = ReferenceLinkerInput

    embedding_service: Optional[EmbeddingService] = None

    def __init__(self, embedding_service: Optional[EmbeddingService] = None, **data: Any) -> None:
        super().__init__(embedding_service=embedding_service, **data)
        self._citation_regex = re.compile(r"\\?\[(\d+(?:,\s*\d+)*)\]|\(([^\)]+?),\s*(\d{4})\)")

    def execute(self, inputs: ReferenceLinkerInput, **kwargs: Any) -> ReferenceLinkerOutput:
        ref_map = {b.ref_id: b for b in inputs.source_paper.bibliography}

        # Mode detection: snippet if direct citation present
        direct_keys = self._extract_citation_keys(inputs.query)
        found: Dict[str, BibliographyEntry] = {}
        if direct_keys:
            for key in direct_keys:
                entry = ref_map.get(key)
                if entry:
                    found[key] = entry
            return ReferenceLinkerOutput(references=list(found.values()))

        # Topic mode: semantic search over paragraphs
        paragraphs: List[Tuple[str, ParagraphElement]] = []
        for section in inputs.source_paper.sections:
            for element in section.content:
                if isinstance(element, ParagraphElement):
                    paragraphs.append((element.text, element))
        if not paragraphs:
            return ReferenceLinkerOutput(references=[])

        texts = [t for t, _ in paragraphs]
        # Lazy init embedding service if needed
        if self.embedding_service is None:
            self.embedding_service = EmbeddingService()
        query_embedding = self.embedding_service.embed_texts([inputs.query])  # shape (1, d)
        para_embeddings = self.embedding_service.embed_texts(texts)  # shape (n, d)
        sims = cosine_similarity_matrix(query_embedding, para_embeddings).flatten()
        top_indices = np.argsort(-sims)[: max(1, inputs.top_k)]

        keys: List[str] = []
        for idx in top_indices:
            _, para = paragraphs[int(idx)]
            keys.extend([c.key for c in para.citations])
        # Deduplicate while preserving order
        seen = set()
        deduped_keys = [k for k in keys if not (k in seen or seen.add(k))]

        for key in deduped_keys:
            entry = ref_map.get(key)
            if entry:
                found[key] = entry
        return ReferenceLinkerOutput(references=list(found.values()))

    # BaseTool sync run implementation (structured)
    def _run(self, source_paper: StructuredPaper, query: str, top_k: int = 5) -> ReferenceLinkerOutput:  # type: ignore[override]
        return self.execute(ReferenceLinkerInput(source_paper=source_paper, query=query, top_k=top_k))

    def _extract_citation_keys(self, text: str) -> List[str]:
        keys: List[str] = []
        for m in self._citation_regex.finditer(text):
            if m.group(1):
                # [1] or [4, 5]
                for k in re.split(r",\s*", m.group(1)):
                    keys.append(f"[{k}]")
            elif m.group(2) and m.group(3):
                # (Author, 2023) -> we cannot reliably map without metadata; skip
                continue
        return keys
