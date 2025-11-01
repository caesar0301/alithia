"""Unit tests for DoclingOCR class."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from alithia.paperlens.models import PaperMetadata
from alithia.paperlens.paper_ocr.docling_ocr import DoclingOCR


@pytest.fixture
def mock_pdf_path(tmp_path):
    """Create a mock PDF file path."""
    pdf_file = tmp_path / "test_paper.pdf"
    pdf_file.write_bytes(b"Mock PDF content")
    return pdf_file


@pytest.fixture
def mock_docling_document():
    """Create a mock docling document with metadata."""
    doc = Mock()
    doc.title = "Test Paper Title"
    doc.authors = ["Author One", "Author Two"]
    doc.date = "2024-01-15"
    doc.abstract = "This is a test abstract"
    doc.doi = "10.1234/test.2024"
    doc.export_to_markdown.return_value = "# Test Paper\n\nThis is the full text content."
    return doc


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    llm = Mock()
    return llm


@pytest.mark.unit
class TestDoclingOCRInitialization:
    """Test DoclingOCR initialization."""

    @patch("docling.document_converter.DocumentConverter")
    @patch("docling.datamodel.pipeline_options.VlmPipelineOptions")
    def test_init_with_vlm_pipeline(self, mock_vlm_options, mock_converter):
        """Test initialization with VLM pipeline options."""
        ocr = DoclingOCR(llm=None)

        assert ocr.llm is None
        mock_vlm_options.assert_called_once_with(vlm_model="granite_docling")
        mock_converter.assert_called_once()

    @patch("docling.document_converter.DocumentConverter")
    @patch("docling.datamodel.pipeline_options.VlmPipelineOptions", side_effect=ImportError)
    def test_init_without_vlm_pipeline(self, mock_vlm_options, mock_converter):
        """Test initialization fallback when VLM is not available."""
        ocr = DoclingOCR(llm=None)

        assert ocr.llm is None
        # Should fallback to regular DocumentConverter
        assert mock_converter.call_count >= 1

    @patch("docling.document_converter.DocumentConverter")
    def test_init_with_llm(self, mock_converter, mock_llm_client):
        """Test initialization with LLM client."""
        ocr = DoclingOCR(llm=mock_llm_client)

        assert ocr.llm == mock_llm_client


@pytest.mark.unit
class TestDoclingOCRMetadataExtraction:
    """Test metadata extraction methods."""

    @patch("docling.document_converter.DocumentConverter")
    def test_extract_metadata_complete(self, mock_converter, mock_docling_document):
        """Test extracting complete metadata from docling document."""
        ocr = DoclingOCR(llm=None)
        metadata = ocr._extract_metadata(mock_docling_document)

        assert metadata.title == "Test Paper Title"
        assert metadata.authors == ["Author One", "Author Two"]
        assert metadata.year == 2024
        assert metadata.abstract == "This is a test abstract"
        assert metadata.doi == "10.1234/test.2024"

    @patch("docling.document_converter.DocumentConverter")
    def test_extract_metadata_partial(self, mock_converter):
        """Test extracting partial metadata."""
        doc = Mock()
        doc.title = "Partial Title"
        doc.authors = None
        doc.date = None
        doc.abstract = None
        doc.doi = None

        ocr = DoclingOCR(llm=None)
        metadata = ocr._extract_metadata(doc)

        assert metadata.title == "Partial Title"
        assert metadata.authors == []
        assert metadata.year is None
        assert metadata.abstract is None
        assert metadata.doi is None

    @patch("docling.document_converter.DocumentConverter")
    def test_extract_metadata_with_error(self, mock_converter):
        """Test metadata extraction handles errors gracefully."""
        doc = Mock()
        doc.title = Mock(side_effect=Exception("Extraction error"))

        ocr = DoclingOCR(llm=None)
        metadata = ocr._extract_metadata(doc)

        # Should return empty metadata without crashing
        assert isinstance(metadata, PaperMetadata)
        assert metadata.title is None


@pytest.mark.unit
class TestDoclingOCRContentExtraction:
    """Test content extraction methods."""

    @patch("docling.document_converter.DocumentConverter")
    def test_extract_content_markdown(self, mock_converter, mock_docling_document):
        """Test extracting content as markdown."""
        ocr = DoclingOCR(llm=None)
        content = ocr._extract_content(mock_docling_document)

        assert content.full_text == "# Test Paper\n\nThis is the full text content."

    @patch("docling.document_converter.DocumentConverter")
    def test_extract_content_text_fallback(self, mock_converter):
        """Test content extraction falls back to text export."""
        doc = Mock()
        doc.export_to_markdown = None
        doc.export_to_text = Mock(return_value="Plain text content")

        ocr = DoclingOCR(llm=None)
        content = ocr._extract_content(doc)

        assert content.full_text == "Plain text content"

    @patch("docling.document_converter.DocumentConverter")
    def test_extract_content_str_fallback(self, mock_converter):
        """Test content extraction falls back to string representation."""
        doc = Mock()
        doc.export_to_markdown = None
        doc.export_to_text = None
        doc.__str__ = Mock(return_value="String representation")

        ocr = DoclingOCR(llm=None)
        content = ocr._extract_content(doc)

        assert content.full_text == "String representation"


@pytest.mark.unit
class TestDoclingOCRMetadataCompleteness:
    """Test metadata completeness checking."""

    @patch("docling.document_converter.DocumentConverter")
    def test_is_metadata_incomplete_missing_title(self, mock_converter):
        """Test detecting incomplete metadata when title is missing."""
        metadata = PaperMetadata(title=None, abstract="Has abstract")

        ocr = DoclingOCR(llm=None)
        assert ocr._is_metadata_incomplete(metadata) is True

    @patch("docling.document_converter.DocumentConverter")
    def test_is_metadata_incomplete_missing_abstract(self, mock_converter):
        """Test detecting incomplete metadata when abstract is missing."""
        metadata = PaperMetadata(title="Has title", abstract=None)

        ocr = DoclingOCR(llm=None)
        assert ocr._is_metadata_incomplete(metadata) is True

    @patch("docling.document_converter.DocumentConverter")
    def test_is_metadata_complete(self, mock_converter):
        """Test detecting complete metadata."""
        metadata = PaperMetadata(title="Has title", abstract="Has abstract")

        ocr = DoclingOCR(llm=None)
        assert ocr._is_metadata_incomplete(metadata) is False


@pytest.mark.unit
class TestDoclingOCRLLMExtraction:
    """Test LLM-based metadata extraction."""

    @patch("docling.document_converter.DocumentConverter")
    def test_extract_metadata_with_llm(self, mock_converter, mock_llm_client):
        """Test metadata extraction using LLM."""
        # Setup mock LLM response
        llm_metadata = PaperMetadata(
            title="LLM Extracted Title",
            authors=["LLM Author 1", "LLM Author 2"],
            year=2024,
            abstract="LLM extracted abstract",
            keywords=["AI", "ML"],
            doi="10.1234/llm",
            venue="LLM Conference",
            field_topic="Machine Learning",
        )
        mock_llm_client.structured_completion.return_value = llm_metadata

        ocr = DoclingOCR(llm=mock_llm_client)
        full_text = "This is a paper about AI and ML. Title: Test Paper. Authors: Author One, Author Two."

        result = ocr._extract_metadata_with_llm(full_text)

        assert result.title == "LLM Extracted Title"
        assert result.authors == ["LLM Author 1", "LLM Author 2"]
        assert result.keywords == ["AI", "ML"]
        mock_llm_client.structured_completion.assert_called_once()

    @patch("docling.document_converter.DocumentConverter")
    def test_extract_metadata_with_llm_truncates_text(self, mock_converter, mock_llm_client):
        """Test that LLM extraction truncates long text."""
        llm_metadata = PaperMetadata(title="Test")
        mock_llm_client.structured_completion.return_value = llm_metadata

        ocr = DoclingOCR(llm=mock_llm_client)
        long_text = "x" * 10000

        ocr._extract_metadata_with_llm(long_text)

        # Check that the text was truncated in the prompt
        call_args = mock_llm_client.structured_completion.call_args
        messages = call_args[1]["messages"]
        prompt_text = messages[0]["content"]
        # Should contain truncated text (8000 chars max)
        assert len(prompt_text) < 8500  # Some buffer for the prompt text itself


@pytest.mark.unit
class TestDoclingOCRMetadataMerging:
    """Test metadata merging logic."""

    @patch("docling.document_converter.DocumentConverter")
    def test_merge_metadata_docling_takes_precedence(self, mock_converter):
        """Test that docling metadata takes precedence over LLM."""
        docling_meta = PaperMetadata(
            title="Docling Title",
            authors=["Docling Author"],
            year=2024,
            abstract=None,  # Missing in docling
        )

        llm_meta = PaperMetadata(
            title="LLM Title",
            authors=["LLM Author"],
            year=2023,
            abstract="LLM Abstract",  # Has abstract
            keywords=["AI"],
        )

        ocr = DoclingOCR(llm=None)
        merged = ocr._merge_metadata(docling_meta, llm_meta)

        # Docling data should win
        assert merged.title == "Docling Title"
        assert merged.authors == ["Docling Author"]
        assert merged.year == 2024

        # LLM should fill gaps
        assert merged.abstract == "LLM Abstract"
        assert merged.keywords == ["AI"]

    @patch("docling.document_converter.DocumentConverter")
    def test_merge_metadata_empty_lists_use_llm(self, mock_converter):
        """Test that empty lists from docling use LLM data."""
        docling_meta = PaperMetadata(
            title="Docling Title",
            authors=[],  # Empty list
            keywords=[],  # Empty list
        )

        llm_meta = PaperMetadata(
            title="LLM Title",
            authors=["LLM Author"],
            keywords=["AI", "ML"],
        )

        ocr = DoclingOCR(llm=None)
        merged = ocr._merge_metadata(docling_meta, llm_meta)

        # Empty lists should be replaced with LLM data
        assert merged.authors == ["LLM Author"]
        assert merged.keywords == ["AI", "ML"]


@pytest.mark.unit
class TestDoclingOCRParsePDF:
    """Test full PDF parsing workflow."""

    @patch("docling.document_converter.DocumentConverter")
    def test_parse_pdf_success(self, mock_converter, mock_pdf_path, mock_docling_document):
        """Test successful PDF parsing."""
        # Setup mock converter
        mock_result = Mock()
        mock_result.document = mock_docling_document
        mock_converter.return_value.convert.return_value = mock_result

        ocr = DoclingOCR(llm=None)
        paper = ocr.parse_pdf(mock_pdf_path)

        assert paper is not None
        assert paper.file_metadata.file_name == "test_paper.pdf"
        assert paper.file_metadata.file_size > 0
        assert paper.file_metadata.md5_hash is not None
        assert paper.paper_metadata.title == "Test Paper Title"
        assert paper.content.full_text == "# Test Paper\n\nThis is the full text content."
        assert paper.parse_timestamp is not None
        assert len(paper.parsing_errors) == 0

    @patch("docling.document_converter.DocumentConverter")
    def test_parse_pdf_with_llm_enhancement(self, mock_converter, mock_pdf_path, mock_llm_client):
        """Test PDF parsing with LLM metadata enhancement."""
        # Setup docling document with incomplete metadata
        incomplete_doc = Mock()
        incomplete_doc.title = None  # Missing title
        incomplete_doc.authors = []
        incomplete_doc.abstract = None  # Missing abstract
        incomplete_doc.export_to_markdown.return_value = "Content"

        mock_result = Mock()
        mock_result.document = incomplete_doc
        mock_converter.return_value.convert.return_value = mock_result

        # Setup LLM response
        llm_metadata = PaperMetadata(
            title="LLM Title",
            authors=["LLM Author"],
            abstract="LLM Abstract",
        )
        mock_llm_client.structured_completion.return_value = llm_metadata

        ocr = DoclingOCR(llm=mock_llm_client)
        paper = ocr.parse_pdf(mock_pdf_path)

        assert paper is not None
        assert paper.paper_metadata.title == "LLM Title"
        assert paper.paper_metadata.abstract == "LLM Abstract"
        # Should have called LLM
        mock_llm_client.structured_completion.assert_called_once()

    @patch("docling.document_converter.DocumentConverter")
    def test_parse_pdf_docling_failure(self, mock_converter, mock_pdf_path):
        """Test handling of docling conversion failure."""
        mock_converter.return_value.convert.side_effect = Exception("Docling error")

        ocr = DoclingOCR(llm=None)
        paper = ocr.parse_pdf(mock_pdf_path)

        assert paper is None

    @patch("docling.document_converter.DocumentConverter")
    def test_parse_pdf_llm_enhancement_failure(self, mock_converter, mock_pdf_path, mock_llm_client):
        """Test that LLM enhancement failure doesn't break parsing."""
        # Setup docling with incomplete metadata
        incomplete_doc = Mock()
        incomplete_doc.title = None
        incomplete_doc.abstract = None
        incomplete_doc.export_to_markdown.return_value = "Content"

        mock_result = Mock()
        mock_result.document = incomplete_doc
        mock_converter.return_value.convert.return_value = mock_result

        # LLM fails
        mock_llm_client.structured_completion.side_effect = Exception("LLM error")

        ocr = DoclingOCR(llm=mock_llm_client)
        paper = ocr.parse_pdf(mock_pdf_path)

        # Should still return paper with docling data
        assert paper is not None
        assert len(paper.parsing_errors) == 1
        assert "LLM metadata extraction failed" in paper.parsing_errors[0]

    @patch("docling.document_converter.DocumentConverter")
    def test_parse_pdf_creates_file_metadata(self, mock_converter, mock_pdf_path, mock_docling_document):
        """Test that file metadata is properly created."""
        mock_result = Mock()
        mock_result.document = mock_docling_document
        mock_converter.return_value.convert.return_value = mock_result

        ocr = DoclingOCR(llm=None)
        paper = ocr.parse_pdf(mock_pdf_path)

        assert paper.file_metadata.file_path == mock_pdf_path
        assert paper.file_metadata.file_name == mock_pdf_path.name
        assert paper.file_metadata.file_size == mock_pdf_path.stat().st_size
        assert isinstance(paper.file_metadata.last_modified, datetime)
        assert len(paper.file_metadata.md5_hash) == 32  # MD5 hash length

    @patch("docling.document_converter.DocumentConverter")
    def test_parse_pdf_nonexistent_file(self, mock_converter):
        """Test parsing nonexistent file."""
        nonexistent_path = Path("/nonexistent/file.pdf")

        ocr = DoclingOCR(llm=None)
        paper = ocr.parse_pdf(nonexistent_path)

        assert paper is None


@pytest.mark.unit
class TestDoclingOCRIntegration:
    """Integration-style tests for DoclingOCR."""

    @patch("docling.document_converter.DocumentConverter")
    def test_complete_workflow_without_llm(self, mock_converter, mock_pdf_path):
        """Test complete parsing workflow without LLM."""
        # Setup complete mock document
        doc = Mock()
        doc.title = "Complete Title"
        doc.authors = ["Author One", "Author Two"]
        doc.date = "2024"
        doc.abstract = "Complete abstract"
        doc.doi = "10.1234/test"
        doc.export_to_markdown.return_value = "# Full text content"

        mock_result = Mock()
        mock_result.document = doc
        mock_converter.return_value.convert.return_value = mock_result

        ocr = DoclingOCR(llm=None)
        paper = ocr.parse_pdf(mock_pdf_path)

        # Verify complete paper object
        assert paper.file_metadata.file_name == "test_paper.pdf"
        assert paper.paper_metadata.title == "Complete Title"
        assert len(paper.paper_metadata.authors) == 2
        assert paper.content.full_text == "# Full text content"
        assert isinstance(paper.parse_timestamp, datetime)
        assert len(paper.parsing_errors) == 0

    @patch("docling.document_converter.DocumentConverter")
    def test_complete_workflow_with_llm(self, mock_converter, mock_pdf_path, mock_llm_client):
        """Test complete parsing workflow with LLM enhancement."""
        # Incomplete docling extraction
        doc = Mock()
        doc.title = "Partial Title"
        doc.authors = []
        doc.abstract = None  # Missing
        doc.export_to_markdown.return_value = "Content"

        mock_result = Mock()
        mock_result.document = doc
        mock_converter.return_value.convert.return_value = mock_result

        # LLM provides missing data
        llm_metadata = PaperMetadata(
            title="Partial Title",
            authors=["Enhanced Author"],
            abstract="Enhanced abstract from LLM",
            keywords=["keyword1", "keyword2"],
        )
        mock_llm_client.structured_completion.return_value = llm_metadata

        ocr = DoclingOCR(llm=mock_llm_client)
        paper = ocr.parse_pdf(mock_pdf_path)

        # Verify LLM enhancement was applied
        assert paper.paper_metadata.title == "Partial Title"
        assert paper.paper_metadata.authors == ["Enhanced Author"]
        assert paper.paper_metadata.abstract == "Enhanced abstract from LLM"
        assert paper.paper_metadata.keywords == ["keyword1", "keyword2"]
        assert len(paper.parsing_errors) == 0
