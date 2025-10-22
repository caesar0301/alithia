"""
Paper data models for the Alithia research agent.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ArxivPaper(BaseModel):
    """Represents an ArXiv paper with all relevant metadata."""

    title: str
    summary: str
    authors: List[str]
    arxiv_id: str
    pdf_url: str
    code_url: Optional[str] = None
    affiliations: Optional[List[str]] = None
    tldr: Optional[str] = None
    score: Optional[float] = None
    published_date: Optional[datetime] = None
    tex: Optional[Dict[str, str]] = None  # Store extracted LaTeX content
    arxiv_result: Optional[Any] = Field(
        default=None, exclude=True
    )  # Store original arxiv.Result object for source access

    @classmethod
    def from_arxiv_result(cls, paper_result) -> "ArxivPaper":
        """Create ArxivPaper from arxiv.Result object."""
        arxiv_id = re.sub(r"v\d+$", "", paper_result.get_short_id())

        return cls(
            title=paper_result.title,
            summary=paper_result.summary,
            authors=[author.name for author in paper_result.authors],
            arxiv_id=arxiv_id,
            pdf_url=paper_result.pdf_url,
            published_date=paper_result.published,
            arxiv_result=paper_result,  # Store the original result object
        )

    def download_source(self, dirpath: str) -> str:
        """Download source files for the paper."""
        if self.arxiv_result is None:
            raise AttributeError("Cannot download source: no arxiv_result available")
        return self.arxiv_result.download_source(dirpath=dirpath)


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
