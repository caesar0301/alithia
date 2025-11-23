"""Data models for paperlens."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    """Metadata about the PDF file itself."""

    file_path: Path
    file_name: str
    file_size: int = Field(..., description="File size in bytes")
    last_modified: datetime
    md5_hash: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class PaperMetadata(BaseModel):
    """Metadata extracted from the paper content."""

    title: Optional[str] = Field(None, description="The title of the paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    year: Optional[int] = Field(None, description="Publication year (4-digit integer)")
    abstract: Optional[str] = Field(None, description="Abstract or summary of the paper")
    keywords: List[str] = Field(default_factory=list, description="List of keywords or topics")
    doi: Optional[str] = Field(None, description="Digital Object Identifier (DOI)")
    venue: Optional[str] = Field(None, description="Journal or conference name")

    class Config:
        arbitrary_types_allowed = True


class PaperContent(BaseModel):
    """Structured content from the paper."""

    full_text: str
    sections: Dict[str, str] = Field(default_factory=dict, description="Section name to content mapping")
    references: List[str] = Field(default_factory=list, description="List of references")
    figures: List[str] = Field(default_factory=list, description="List of figures")
    tables: List[str] = Field(default_factory=list, description="List of tables")

    class Config:
        arbitrary_types_allowed = True


class AcademicPaper(BaseModel):
    """Complete data model for an academic paper."""

    file_metadata: FileMetadata
    paper_metadata: PaperMetadata
    content: PaperContent
    similarity_score: float = Field(default=0.0, description="Similarity to research topic")
    parse_timestamp: datetime = Field(default_factory=datetime.now, description="When the paper was parsed")
    parsing_errors: List[str] = Field(default_factory=list, description="List of parsing errors")

    class Config:
        arbitrary_types_allowed = True

    @property
    def display_title(self) -> str:
        """Get a display title for the paper."""
        if self.paper_metadata.title:
            return self.paper_metadata.title
        return self.file_metadata.file_name

    @property
    def display_authors(self) -> str:
        """Get a formatted string of authors."""
        if not self.paper_metadata.authors:
            return "Unknown"
        if len(self.paper_metadata.authors) <= 3:
            return ", ".join(self.paper_metadata.authors)
        return f"{self.paper_metadata.authors[0]} et al."

    def get_searchable_text(self) -> str:
        """
        Get all searchable text from the paper for similarity matching.
        Combines title, abstract, keywords, and full text.
        """
        parts = []

        # Title (weighted more by including it multiple times)
        if self.paper_metadata.title:
            parts.extend([self.paper_metadata.title] * 3)

        # Abstract (weighted more)
        if self.paper_metadata.abstract:
            parts.extend([self.paper_metadata.abstract] * 2)

        # Keywords
        if self.paper_metadata.keywords:
            parts.append(" ".join(self.paper_metadata.keywords))

        # Full text
        if self.content.full_text:
            parts.append(self.content.full_text)

        return " ".join(parts)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization with custom formatting."""
        # Use Pydantic's model_dump() method but customize Path and datetime serialization
        result = self.model_dump()

        # Convert Path to string
        result["file_metadata"]["file_path"] = str(result["file_metadata"]["file_path"])

        # Convert datetime to ISO format
        if result["file_metadata"]["last_modified"]:
            result["file_metadata"]["last_modified"] = result["file_metadata"]["last_modified"].isoformat()
        if result["parse_timestamp"]:
            result["parse_timestamp"] = result["parse_timestamp"].isoformat()

        return result
