"""
User profile and configuration models for the Alithia research agent.
"""

import logging
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .connected import (
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
    github: GithubConnection
    google_scholar: GoogleScholarConnection
    x: XConnection

    # Gems
    gems: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "ResearcherProfile":
        """Create ResearcherProfile from configuration dictionary."""

        if not _validate(config):
            raise ValueError("Invalid configuration")

        return cls(
            research_interests=config.get("research_interests", []),
            expertise_level=config.get("expertise_level", "intermediate"),
            language=config.get("language", "English"),
            email=config.get("email", ""),
            llm=LLMConnection(**config.get("llm", {})),
            zotero=ZoteroConnection(**config.get("zotero", {})),
            email_notification=EmailConnection(**config.get("email_notification", {})),
            github=GithubConnection(**config.get("github", {})),
            google_scholar=GoogleScholarConnection(**config.get("google_scholar", {})),
            x=XConnection(**config.get("x", {})),
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
