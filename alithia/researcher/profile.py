"""
User profile and configuration models for the Alithia research agent.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .connection import (
    EmailConnection,
    GithubConnection,
    GoogleScholarConnection,
    LLMConnection,
    XConnection,
    ZoteroConnection,
)

logger = logging.getLogger(__name__)


class ResearcherProfile(BaseModel):
    """Represents a user's research profile and preferences."""

    # Basic profile
    research_interests: List[str] = Field(default_factory=list)
    expertise_level: str = "intermediate"
    language: str = "English"
    email: str

    # Connected services
    llm: LLMConnection
    zotero: ZoteroConnection
    email_notification: EmailConnection
    github: Optional[GithubConnection] = None
    google_scholar: Optional[GoogleScholarConnection] = None
    x: Optional[XConnection] = None

    # Gems
    gems: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "ResearcherProfile":
        """Create ResearcherProfile from configuration dictionary."""

        if not _validate(config):
            raise ValueError("Invalid configuration")

        # Helper function to safely create optional connections
        def safe_create_connection(connection_class, config_key):
            config_data = config.get(connection_class.__name__.lower(), {})
            if config_data:
                try:
                    return connection_class(**config_data)
                except Exception:
                    logger.warning(f"Failed to create {connection_class.__name__}, skipping")
                    return None
            return None

        return cls(
            research_interests=config.get("research_interests", []),
            expertise_level=config.get("expertise_level", "intermediate"),
            language=config.get("language", "English"),
            email=config.get("email", ""),
            llm=LLMConnection(**config.get("llm", {})),
            zotero=ZoteroConnection(**config.get("zotero", {})),
            email_notification=EmailConnection(**config.get("email_notification", {})),
            github=GithubConnection(**config.get("github", {})) if config.get("github") else None,
            google_scholar=(
                GoogleScholarConnection(**config.get("google_scholar", {})) if config.get("google_scholar") else None
            ),
            x=XConnection(**config.get("x", {})) if config.get("x") else None,
            gems=config.get("gems", {}),
        )


def _validate(config: dict) -> bool:
    """
    Validate configuration has all required fields.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "llm",
        "zotero",
        "email_notification",
    ]

    missing = [field for field in required_fields if field not in config or not config[field]]

    if missing:
        logger.error(f"Missing required configuration: {', '.join(missing)}")
        return False

    return True
