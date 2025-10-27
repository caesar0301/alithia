"""
PaperLens - Research Paper Discovery Tool

Given a research topic and a directory of PDF papers, finds the most relevant papers
using semantic similarity matching.
"""

import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger

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

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the PaperLens engine.

        Args:
            model_name: Name of the sentence-transformer model to use.
                       Default is 'all-MiniLM-L6-v2' which is fast and efficient.
        """
        logger.info(f"Loading sentence transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.converter = DocumentConverter()
        logger.info("PaperLens engine initialized")

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

            logger.success(f"Successfully parsed: {pdf_path.name}")
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

        logger.success("Similarity calculation complete")
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


def load_research_topic(input_file: Path) -> str:
    """Load research topic from input file."""
    if not input_file.exists():
        logger.error(f"Input file does not exist: {input_file}")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        topic = f.read().strip()

    if not topic:
        logger.error("Input file is empty")
        sys.exit(1)

    logger.info(f"Loaded research topic ({len(topic)} characters)")
    return topic


def display_results(papers: List[AcademicPaper], research_topic: str):
    """Display the ranked papers in a formatted way."""
    print("\n" + "=" * 80)
    print("PAPERLENS - Research Paper Discovery Results")
    print("=" * 80)
    print(f"\nResearch Topic:\n{research_topic[:200]}{'...' if len(research_topic) > 200 else ''}\n")
    print(f"Found {len(papers)} relevant papers:\n")
    print("=" * 80)

    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}] {paper.display_title}")
        print(f"    Authors: {paper.display_authors}")
        if paper.paper_metadata.year:
            print(f"    Year: {paper.paper_metadata.year}")
        if paper.paper_metadata.venue:
            print(f"    Venue: {paper.paper_metadata.venue}")
        print(f"    Similarity Score: {paper.similarity_score:.4f}")
        print(f"    File: {paper.file_metadata.file_path}")

        if paper.paper_metadata.abstract:
            abstract = paper.paper_metadata.abstract
            if len(abstract) > 300:
                abstract = abstract[:300] + "..."
            print(f"    Abstract: {abstract}")

        if paper.parsing_errors:
            print(f"    ⚠️  Parsing warnings: {len(paper.parsing_errors)}")

    print("\n" + "=" * 80)


def main():
    """Main entry point for paperlens."""
    parser = argparse.ArgumentParser(
        description="PaperLens - Find relevant research papers using semantic similarity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i research_topic.txt -d ./papers
  %(prog)s -i topic.txt -d ./papers -n 20
  %(prog)s -i topic.txt -d ./papers --model all-mpnet-base-v2
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        required=True,
        help="Input file containing research topic (text/paragraph)",
    )

    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        required=True,
        help="Directory containing PDF papers",
    )

    parser.add_argument(
        "-n",
        "--top-n",
        type=int,
        default=10,
        help="Number of top papers to display (default: 10)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Sentence transformer model to use (default: all-MiniLM-L6-v2)",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't search subdirectories for PDFs",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()  # Remove default handler
    log_level = "DEBUG" if args.verbose else "INFO"
    logger.add(sys.stderr, level=log_level)

    # Load research topic
    research_topic = load_research_topic(args.input)

    # Initialize engine
    engine = PaperLensEngine(model_name=args.model)

    # Scan and parse PDFs
    papers = engine.scan_pdf_directory(args.directory, recursive=not args.no_recursive)

    if not papers:
        logger.error("No papers were successfully parsed. Exiting.")
        sys.exit(1)

    # Calculate similarity
    papers = engine.calculate_similarity(research_topic, papers)

    # Rank papers
    top_papers = engine.rank_papers(papers, top_n=args.top_n)

    # Display results
    display_results(top_papers, research_topic)


if __name__ == "__main__":
    main()
