"""
Paper data models for the Alithia research agent.
"""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .arxiv_paper import ArxivPaper


class ScoredPaper(BaseModel):
    """Represents a paper with relevance score."""

    paper: ArxivPaper
    score: float
    relevance_factors: Dict[str, float] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Update the paper's score after initialization."""
        self.paper.score = self.score


class EmailContent(BaseModel):
    """Represents the content for email delivery."""

    subject: str
    html_content: str
    papers: List[ScoredPaper]
    generated_at: datetime = Field(default_factory=datetime.now)

    def is_empty(self) -> bool:
        """Check if email has no papers."""
        return len(self.papers) == 0
