"""
PaperLens - Research Paper Discovery Tool

Given a research topic and a directory of PDF papers, finds the most relevant papers
using semantic similarity matching.
"""

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from cogents_core.utils import get_logger

logger = get_logger(__name__)

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    logger.error("docling is not installed. Install with: pip install 'alithia[paperlens]'")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.error("sentence-transformers is not installed. Install with: pip install 'alithia[extra]'")
    sys.exit(1)

from alithia.paperlens.models import (
    AcademicPaper,
    FileMetadata,
    PaperContent,
    PaperMetadata,
)


class PaperLensEngine:
    """Core engine for paper analysis and ranking."""

    def __init__(self, sbert_model: str = "all-MiniLM-L6-v2", force_gpu: bool = False):
        """
        Initialize the PaperLens engine.

        Args:
            sbert_model: Name of the sentence-transformer model to use.
                       Default is 'all-MiniLM-L6-v2' which is fast and efficient.
            force_gpu: Force GPU usage even if CUDA compatibility issues are detected.

        Note:
            This engine uses IBM Granite Docling 258M model for PDF parsing and layout analysis.
        """
        import os

        import torch

        # Handle GPU/CPU device selection
        if force_gpu:
            logger.info("Force GPU mode enabled")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cpu":
                logger.warning("GPU requested but CUDA not available, falling back to CPU")
        else:
            # Default behavior: use CPU to avoid CUDA compatibility issues
            device = "cpu"
            os.environ["CUDA_VISIBLE_DEVICES"] = ""

        logger.info(f"Loading sentence transformer model: {sbert_model} (device: {device})")
        self.model = SentenceTransformer(sbert_model, device=device)

        try:
            from docling.datamodel.pipeline_options import VlmPipelineOptions

            # Configure IBM Granite Docling model using VLM pipeline
            pipeline_options = VlmPipelineOptions(vlm_model="granite_docling")
            logger.info("Using docling with IBM Granite VLM model")
            self.converter = DocumentConverter()
            self.converter.pipeline_options = pipeline_options
        except (ImportError, TypeError, AttributeError) as e:
            # Fallback to default settings if VLM pipeline not available
            logger.warning(f"VLM pipeline not available ({e}), falling back to default settings")
            self.converter = DocumentConverter()
            logger.info("Using docling with default settings")

        logger.info(f"PaperLens engine initialized (device: {device})")

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

            # Extract paper metadata
            paper_metadata = self._extract_metadata(doc)

            # Extract content
            content = self._extract_content(doc)

            # Create AcademicPaper object
            paper = AcademicPaper(
                file_metadata=file_metadata,
                paper_metadata=paper_metadata,
                content=content,
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

    def scan_pdf_directory(self, directory: Path, recursive: bool = True) -> List[AcademicPaper]:
        """
        Scan a directory for PDF files and parse them.

        Args:
            directory: Directory containing PDF files
            recursive: Whether to search subdirectories

        Returns:
            List of successfully parsed AcademicPaper objects
        """
        logger.info(f"Scanning directory: {directory}")

        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return []

        if not directory.is_dir():
            logger.error(f"Path is not a directory: {directory}")
            return []

        # Find all PDF files
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_files = list(directory.glob(pattern))
        logger.info(f"Found {len(pdf_files)} PDF files")

        # Parse each PDF
        papers = []
        for pdf_path in pdf_files:
            paper = self.parse_pdf(pdf_path)
            if paper:
                papers.append(paper)

        logger.info(f"Successfully parsed {len(papers)} out of {len(pdf_files)} PDFs")
        return papers

    def calculate_similarity(self, research_topic: str, papers: List[AcademicPaper]) -> List[AcademicPaper]:
        """
        Calculate similarity scores between research topic and papers.

        Args:
            research_topic: The research topic string
            papers: List of AcademicPaper objects

        Returns:
            List of papers with updated similarity scores
        """
        if not papers:
            logger.warning("No papers to calculate similarity for")
            return papers

        logger.info(f"Calculating similarity for {len(papers)} papers")

        # Encode the research topic
        topic_embedding = self.model.encode(research_topic, convert_to_tensor=True)

        # Encode all paper texts
        paper_texts = [paper.get_searchable_text() for paper in papers]

        # Batch encode for efficiency
        logger.info("Encoding paper contents...")
        paper_embeddings = self.model.encode(paper_texts, convert_to_tensor=True, show_progress_bar=True)

        # Calculate cosine similarity
        from sentence_transformers import util

        similarities = util.cos_sim(topic_embedding, paper_embeddings)[0]

        # Update similarity scores
        for paper, score in zip(papers, similarities):
            paper.similarity_score = float(score)

        return papers

    def rank_papers(self, papers: List[AcademicPaper], top_n: int = 10) -> List[AcademicPaper]:
        """
        Rank papers by similarity score.

        Args:
            papers: List of AcademicPaper objects
            top_n: Number of top papers to return

        Returns:
            Sorted list of top N papers
        """
        sorted_papers = sorted(papers, key=lambda p: p.similarity_score, reverse=True)
        return sorted_papers[:top_n]
