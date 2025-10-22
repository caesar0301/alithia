from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from alithia.core.pdf_processor import PDFProcessor

from .base import ToolInput, ToolOutput
from .models import Citation, ParagraphElement, Section, StructuredPaper


class PDFParserInput(ToolInput):
    file_path: str


class PDFParserOutput(ToolOutput):
    structured_paper: StructuredPaper


class PDFParserTool(BaseTool):
    name: str = "core.pdf_parser"
    description: str = "Parse PDF into structured paper elements using MinerU"
    args_schema: type[BaseModel] = PDFParserInput

    processor: Optional[PDFProcessor] = None

    def execute(self, inputs: PDFParserInput, **kwargs: Any) -> PDFParserOutput:
        # Lazy initialize processor if not injected (useful for tests)
        if self.processor is None:
            self.processor = PDFProcessor()
        chunks: List[Dict[str, Any]] = self.processor.process(inputs.file_path)
        paper_id = str(uuid.uuid4())

        # Simple heuristic: build one section with paragraphs from chunks
        section = Section(section_number="1", title="Document Body", content=[])

        citation_pattern = re.compile(r"\[(\d+(?:,\s*\d+)*)\]")
        element_counter = 0
        for chunk in chunks:
            text = str(chunk.get("text", "")).strip()
            if not text:
                continue
            citations: List[Citation] = []
            for match in citation_pattern.finditer(text):
                keys_text = match.group(1)
                for key in re.split(r",\s*", keys_text):
                    citations.append(Citation(key=f"[{key}]"))
            paragraph = ParagraphElement(
                element_id=f"para_{element_counter:04d}",
                text=text,
                citations=citations,
            )
            element_counter += 1
            section.content.append(paragraph)

        structured = StructuredPaper(
            paper_id=paper_id,
            sections=[section],
        )
        return PDFParserOutput(structured_paper=structured)

    # BaseTool sync run implementation (structured)
    def _run(self, file_path: str) -> PDFParserOutput:  # type: ignore[override]
        return self.execute(PDFParserInput(file_path=file_path))
