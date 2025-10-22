"""
Agent state management for the Alithia research agent.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from alithia.core.researcher import ResearcherProfile

from .arxiv_paper import ArxivPaper
from .models import EmailContent, ScoredPaper


class ArxrecConfig(BaseModel):
    """Arxrec configuration."""

    # User Profile
    user_profile: ResearcherProfile

    # Agent Config
    query: str = "cs.AI+cs.CV+cs.LG+cs.CL"
    max_papers: int = 50
    send_empty: bool = False
    ignore_patterns: List[str] = Field(default_factory=list)

    debug: bool = False


class AgentState(BaseModel):
    """Centralized state for the research agent workflow."""

    # Agent Config
    config: ArxrecConfig

    # Discovery State
    discovered_papers: List[ArxivPaper] = Field(default_factory=list)
    zotero_corpus: List[Dict[str, Any]] = Field(default_factory=list)

    # Assessment State
    scored_papers: List[ScoredPaper] = Field(default_factory=list)

    # Content State
    email_content: Optional[EmailContent] = None

    # System State
    current_step: str = "initializing"
    error_log: List[str] = Field(default_factory=list)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)

    # Debug State
    debug_mode: bool = False

    def add_error(self, error: str) -> None:
        """Add an error to the error log."""
        self.error_log.append(f"{datetime.now().isoformat()}: {error}")

    def update_metric(self, key: str, value: float) -> None:
        """Update a performance metric."""
        self.performance_metrics[key] = value

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state."""
        return {
            "current_step": self.current_step,
            "papers_discovered": len(self.discovered_papers),
            "papers_scored": len(self.scored_papers),
            "errors": len(self.error_log),
            "metrics": self.performance_metrics,
        }
