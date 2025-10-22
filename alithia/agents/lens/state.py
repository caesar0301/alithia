"""
Agent state management for the Alithia research agent.
"""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from alithia.core.researcher import ResearcherProfile


class LensConfig(BaseModel):
    """Lens configuration."""

    # User Profile
    user_profile: ResearcherProfile

    # Agent Config
    query: str = "cs.AI+cs.CV+cs.LG+cs.CL"
    max_papers: int = 50
    send_empty: bool = False
    ignore_patterns: List[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Centralized state for the lens agent workflow."""

    # Agent Config
    config: LensConfig

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
            "errors": len(self.error_log),
            "metrics": self.performance_metrics,
        }
