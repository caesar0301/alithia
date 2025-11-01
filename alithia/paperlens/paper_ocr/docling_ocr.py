import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from cogents_core.llm import BaseLLMClient
from cogents_core.utils import get_logger

from alithia.paperlens.models import AcademicPaper, FileMetadata, PaperContent, PaperMetadata
from alithia.paperlens.paper_ocr.base import PaperOCRBase

logger = get_logger(__name__)


class DoclingOCR(PaperOCRBase):
    """Parse the PDF using Docling."""

    def __init__(self, llm: Optional[BaseLLMClient] = None):
        super().__init__()
        self.llm = llm
        if self.llm is None:
            logger.warning("No LLM provided, using default settings")

        try:
            from docling.datamodel.pipeline_options import VlmPipelineOptions
            from docling.document_converter import DocumentConverter

            pipeline_options = VlmPipelineOptions(vlm_model="granite_docling")
            logger.info("Using docling with IBM Granite VLM model")
            self.converter = DocumentConverter(pipeline_options=pipeline_options)
        except (ImportError, TypeError, AttributeError) as e:
            logger.warning(f"VLM pipeline not available ({e}), falling back to default settings")
            self.converter = DocumentConverter()

    def parse_pdf(self, pdf_path: Path) -> Optional[AcademicPaper]:
        """
        Parse a PDF file and extract structured content.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            AcademicPaper object or None if parsing fails
        """
        logger.info(f"Parsing PDF: {pdf_path}")
        errors = []
        parse_timestamp = datetime.now()

        try:
            # Get file metadata
            stat = pdf_path.stat()
            with open(pdf_path, "rb") as f:
                md5_hash = hashlib.md5(f.read()).hexdigest()

            file_metadata = FileMetadata(
                file_path=pdf_path,
                file_name=pdf_path.name,
                file_size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                md5_hash=md5_hash,
            )

            # Parse PDF with docling
            try:
                result = self.converter.convert(str(pdf_path))
                doc = result.document
            except Exception as e:
                error_msg = f"Failed to parse PDF with docling: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                return None

            # Extract content first (needed for LLM fallback)
            content = self._extract_content(doc)

            # Extract paper metadata from docling
            paper_metadata = self._extract_metadata(doc)

            # If metadata extraction failed and LLM is available, try LLM-based extraction
            if self._is_metadata_incomplete(paper_metadata) and self.llm is not None:
                logger.info("Docling metadata incomplete, attempting LLM-based extraction")
                try:
                    llm_metadata = self._extract_metadata_with_llm(content.full_text)
                    paper_metadata = self._merge_metadata(paper_metadata, llm_metadata)
                    logger.info("Successfully enhanced metadata with LLM extraction")
                except Exception as e:
                    error_msg = f"LLM metadata extraction failed: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

            # Create AcademicPaper object with explicit parse_timestamp
            paper = AcademicPaper(
                file_metadata=file_metadata,
                paper_metadata=paper_metadata,
                content=content,
                parse_timestamp=parse_timestamp,
                parsing_errors=errors,
            )

            logger.info(f"Successfully parsed: {pdf_path.name}")
            return paper

        except Exception as e:
            error_msg = f"Unexpected error parsing {pdf_path}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            return None

    def _extract_metadata(self, doc) -> PaperMetadata:
        """Extract metadata from docling document."""
        metadata = PaperMetadata()

        try:
            # Try to extract title
            if hasattr(doc, "title") and doc.title:
                metadata.title = doc.title.strip()

            # Try to extract authors
            if hasattr(doc, "authors") and doc.authors:
                metadata.authors = [author.strip() for author in doc.authors if author.strip()]

            # Try to extract year
            if hasattr(doc, "date") and doc.date:
                try:
                    metadata.year = int(str(doc.date)[:4])
                except (ValueError, TypeError):
                    pass

            # Try to extract abstract
            if hasattr(doc, "abstract") and doc.abstract:
                metadata.abstract = doc.abstract.strip()

            # Try to extract DOI
            if hasattr(doc, "doi") and doc.doi:
                metadata.doi = doc.doi.strip()

        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")

        return metadata

    def _extract_content(self, doc) -> PaperContent:
        """Extract content from docling document."""
        content = PaperContent(full_text="")

        try:
            # Extract full text
            if hasattr(doc, "export_to_markdown"):
                content.full_text = doc.export_to_markdown()
            elif hasattr(doc, "export_to_text"):
                content.full_text = doc.export_to_text()
            else:
                # Fallback: try to get text from document
                content.full_text = str(doc)

        except Exception as e:
            logger.warning(f"Error extracting content: {e}")

        return content

    def _is_metadata_incomplete(self, metadata: PaperMetadata) -> bool:
        """
        Check if metadata extraction is incomplete and should be enhanced with LLM.

        Args:
            metadata: PaperMetadata object to check

        Returns:
            True if metadata is incomplete, False otherwise
        """
        # Consider metadata incomplete if title or abstract is missing
        return not metadata.title or not metadata.abstract

    def _extract_metadata_with_llm(self, full_text: str) -> PaperMetadata:
        """
        Extract metadata from paper text using LLM structured completion.

        Args:
            full_text: Full text content of the paper

        Returns:
            PaperMetadata object with extracted metadata
        """
        # Truncate text to first ~8000 characters (roughly first few pages)
        # This should include title, authors, abstract, and introduction
        truncated_text = full_text[:8000] if len(full_text) > 8000 else full_text

        # Create prompt for metadata extraction
        prompt = f"""Extract the following metadata from this academic paper:

Paper text:
{truncated_text}

Please extract:
- Title (exact title of the paper)
- Authors (list of all author names)
- Year (publication year as 4-digit integer)
- Abstract (the paper's abstract or summary)
- Keywords (list of key topics or keywords)
- DOI (Digital Object Identifier, if present)
- Venue (journal or conference name, if present)
- Field/Topic (research field or topic area)

If any field is not found or unclear, leave it empty."""

        messages = [{"role": "user", "content": prompt}]

        # Use structured completion to get structured metadata
        # PaperMetadata is now a Pydantic model, so it can be used directly
        llm_response = self.llm.structured_completion(
            messages=messages, response_model=PaperMetadata, temperature=0.1, max_tokens=1000
        )

        return llm_response

    def _merge_metadata(self, docling_metadata: PaperMetadata, llm_metadata: PaperMetadata) -> PaperMetadata:
        """
        Merge metadata from docling and LLM extraction.
        Docling metadata takes precedence if available, LLM fills in the gaps.

        Args:
            docling_metadata: Metadata extracted by docling
            llm_metadata: Metadata extracted by LLM

        Returns:
            Merged PaperMetadata object
        """
        # Use Pydantic's copy and update pattern for merging
        # Start with LLM metadata and override with docling metadata where available
        merged_data = llm_metadata.model_dump()
        docling_data = docling_metadata.model_dump()

        # Override with docling data where it's not None/empty
        for key, value in docling_data.items():
            if value:  # If value is truthy (not None, not empty list, not empty string)
                merged_data[key] = value

        return PaperMetadata(**merged_data)
