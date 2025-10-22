import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Wrapper around MinerU to parse PDFs into structured text chunks.
    """

    def __init__(self) -> None:
        try:
            import mineru  # type: ignore  # noqa: F401
        except Exception as e:
            raise RuntimeError("MinerU is required for PDF parsing. Please install and ensure it is importable.") from e

    def process(self, pdf_path: str, max_chunk_chars: int = 1200, overlap: int = 150) -> List[Dict[str, Any]]:
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        try:
            from mineru import pipeline  # type: ignore
        except Exception as e:
            raise RuntimeError("Unable to import MinerU pipeline. Verify mineru installation.") from e

        try:
            logger.info(f"Running MinerU on {pdf_path}")
            parsed = pipeline(pdf_path)
        except Exception as e:
            raise RuntimeError(f"MinerU failed to parse PDF: {e}") from e

        pages: List[Dict[str, Any]] = []
        if isinstance(parsed, dict) and "pages" in parsed:
            pages = parsed["pages"]
        elif isinstance(parsed, list):
            pages = parsed
        else:
            pages = [{"page": 1, "text": str(parsed)}]

        chunks: List[Dict[str, Any]] = []
        chunk_id_counter = 0
        for page_entry in pages:
            page_num = int(page_entry.get("page", 0) or page_entry.get("page_num", 0) or 0)
            page_text_items = page_entry.get("texts") or page_entry.get("content") or page_entry.get("text")
            if isinstance(page_text_items, list):
                page_text = "\n".join([str(t.get("text", t)) for t in page_text_items])
            else:
                page_text = str(page_text_items) if page_text_items is not None else ""
            page_text = page_text.strip()
            if not page_text:
                continue
            start = 0
            while start < len(page_text):
                end = min(len(page_text), start + max_chunk_chars)
                chunk_text = page_text[start:end]
                if end < len(page_text):
                    while end < len(page_text) and page_text[end] not in (" ", "\n", "\t"):
                        end += 1
                    chunk_text = page_text[start:end]
                chunk = {
                    "id": f"chunk-{chunk_id_counter}",
                    "text": chunk_text.strip(),
                    "page": page_num,
                    "offset": start,
                }
                if chunk["text"]:
                    chunks.append(chunk)
                    chunk_id_counter += 1
                start = max(end - overlap, end)
        logger.info(f"MinerU produced {len(chunks)} chunks from {pdf_path}")
        return chunks
