"""
PaperLens - Research Paper Discovery Tool

Given a research topic and a directory of PDF papers, finds the most relevant papers
using semantic similarity matching.
"""

import argparse
import sys
from pathlib import Path
from typing import List

from cogents_core.utils import get_logger

from .engine import PaperLensEngine

logger = get_logger(__name__)

try:
    pass
except ImportError:
    logger.error("docling is not installed. Install with: pip install 'alithia[paperlens]'")
    sys.exit(1)

try:
    pass
except ImportError:
    logger.error("sentence-transformers is not installed. Install with: pip install 'alithia[extra]'")
    sys.exit(1)

from alithia.paperlens.models import (
    AcademicPaper,
)


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

    parser.add_argument(
        "--force-gpu",
        action="store_true",
        help="Force GPU usage even if CUDA compatibility issues are detected",
    )

    args = parser.parse_args()

    # Load research topic
    research_topic = load_research_topic(args.input)

    # Initialize engine
    engine = PaperLensEngine(sbert_model=args.model, force_gpu=args.force_gpu)

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
