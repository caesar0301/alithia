"""
Alithia - AI-Powered Research Companion

Main entry point for all Alithia agents.
"""

import argparse
import sys
from pathlib import Path
from typing import List

from cogents_core.utils import get_logger

logger = get_logger(__name__)


def create_arxrec_parser(subparsers):
    """Create argument parser for arxrec agent."""
    parser = subparsers.add_parser(
        "arxrec_agent",
        help="Personalized arXiv recommendation agent",
        description="A personalized arXiv recommendation agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with environment variables
  python -m alithia.run arxrec_agent
  
  # Run with configuration file
  python -m alithia.run arxrec_agent --config config.json
        """,
    )
    parser.add_argument("-c", "--config", type=str, help="Configuration file path (JSON)")
    return parser


def create_paperlens_parser(subparsers):
    """Create argument parser for paperlens agent."""
    parser = subparsers.add_parser(
        "paperlens_agent",
        help="Deep paper interaction and discovery tool",
        description="PaperLens - Find relevant research papers using semantic similarity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m alithia.run paperlens_agent -i research_topic.txt -d ./papers
  python -m alithia.run paperlens_agent -i topic.txt -d ./papers -n 20
  python -m alithia.run paperlens_agent -i topic.txt -d ./papers --model all-mpnet-base-v2
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

    return parser


def run_arxrec_agent(args):
    """Run the arxrec agent."""
    from alithia.arxrec.agent import ArxrecAgent
    from alithia.arxrec.state import ArxrecConfig
    from alithia.config_loader import load_config
    from alithia.researcher.profile import ResearcherProfile

    # Build configuration
    config_dict = load_config(args.config)

    # Create ArxrecConfig
    try:
        arxrec_settings = config_dict.get("arxrec", {})

        config = ArxrecConfig(
            user_profile=ResearcherProfile.from_config(config_dict),
            query=arxrec_settings.get("query", "cs.AI+cs.CV+cs.LG+cs.CL"),
            max_papers=arxrec_settings.get("max_papers", 50),
            send_empty=arxrec_settings.get("send_empty", False),
            ignore_patterns=arxrec_settings.get("ignore_patterns", []),
            debug=config_dict.get("debug", False),
        )
    except Exception as e:
        logger.error(f"Failed to create ArxrecConfig: {e}")
        sys.exit(1)

    # Create and run agent
    agent = ArxrecAgent()

    try:
        logger.info("Starting Alithia research agent...")
        result = agent.run(config)

        if result["success"]:
            logger.info("✅ Research agent completed successfully")
            logger.info(f"📧 Email sent with {result['summary']['papers_scored']} papers")

            if result["errors"]:
                logger.warning(f"⚠️  {len(result['errors'])} warnings occurred")
                for error in result["errors"]:
                    logger.warning(f"   - {error}")
        else:
            logger.error("❌ Research agent failed")
            logger.error(f"Error: {result['error']}")

            if result["errors"]:
                logger.error("Additional errors:")
                for error in result["errors"]:
                    logger.error(f"   - {error}")

            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("🛑 Research agent interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        sys.exit(1)


def run_paperlens_agent(args):
    """Run the paperlens agent."""
    from alithia.paperlens.engine import PaperLensEngine
    from alithia.paperlens.models import AcademicPaper

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


def main():
    """Main entry point for Alithia."""
    parser = argparse.ArgumentParser(
        prog="alithia",
        description="Alithia - AI-Powered Research Companion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Agents:
  arxrec_agent      Personalized arXiv recommendation agent
  paperlens_agent   Deep paper interaction and discovery tool

Examples:
  python -m alithia.run arxrec_agent --config config.json
  python -m alithia.run paperlens_agent -i topic.txt -d ./papers

For more information on each agent, use:
  python -m alithia.run <agent> --help
        """,
    )

    # Create subparsers for different agents
    subparsers = parser.add_subparsers(dest="agent", help="Agent to run", required=True)

    # Add agent parsers
    create_arxrec_parser(subparsers)
    create_paperlens_parser(subparsers)

    # Parse arguments
    args = parser.parse_args()

    # Route to appropriate agent
    if args.agent == "arxrec_agent":
        run_arxrec_agent(args)
    elif args.agent == "paperlens_agent":
        run_paperlens_agent(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
