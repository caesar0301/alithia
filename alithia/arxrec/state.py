"""
Agent state management for the Alithia research agent.
"""

from datetime import datetime
from operator import add
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field

from alithia.researcher import ResearcherProfile

from .models import ArxivPaper, EmailContent, ScoredPaper


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


def merge_dicts(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, with right overriding left."""
    return {**left, **right}


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
    # Use Annotated with operator.add to accumulate error_log entries across nodes
    error_log: Annotated[List[str], add] = Field(default_factory=list)
    # Use custom merge function to accumulate performance_metrics across nodes
    performance_metrics: Annotated[Dict[str, float], merge_dicts] = Field(default_factory=dict)

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
