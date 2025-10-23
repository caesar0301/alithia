"""
Main entry point for the Alithia research agent.
Replicates zotero-arxiv-daily functionality using agentic architecture.
"""

import argparse
import logging
import sys
from typing import Any, Dict

from alithia.arxrec.agent import ArxrecAgent
from alithia.core.config_loader import load_config
from alithia.core.researcher.profile import ResearcherProfile

from .state import ArxrecConfig

logger = logging.getLogger(__name__)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser with all necessary arguments."""
    parser = argparse.ArgumentParser(
        description="A personalized arXiv recommendation agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with environment variables
  python -m alithia.arxrec
  
  # Run with configuration file
  python -m alithia.arxrec --config config.json
        """,
    )
    # Optional arguments
    parser.add_argument("-c", "--config", type=str, help="Configuration file path (JSON)")

    return parser


def create_arxrec_config(config_dict: Dict[str, Any]) -> ArxrecConfig:
    """
    Create ArxrecConfig from configuration dictionary.

    Args:
        config_dict: Configuration dictionary

    Returns:
        ArxrecConfig object
    """
    # Extract arxrec-specific settings
    arxrec_settings = config_dict.get("arxrec", {})

    # Create ArxrecConfig
    arxrec_config = ArxrecConfig(
        user_profile=ResearcherProfile.from_config(config_dict),
        query=arxrec_settings.get("query", "cs.AI+cs.CV+cs.LG+cs.CL"),
        max_papers=arxrec_settings.get("max_papers", 50),
        send_empty=arxrec_settings.get("send_empty", False),
        ignore_patterns=arxrec_settings.get("ignore_patterns", []),
        debug=config_dict.get("debug", False),
    )

    return arxrec_config


def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Build configuration
    config_dict = load_config(args.config)

    # Create ArxrecConfig
    try:
        config = create_arxrec_config(config_dict)
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


if __name__ == "__main__":
    main()
