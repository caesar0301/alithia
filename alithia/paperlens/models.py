"""Data models for paperlens."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FileMetadata:
    """Metadata about the PDF file itself."""

    file_path: Path
    file_name: str
    file_size: int  # in bytes
    last_modified: datetime
    md5_hash: Optional[str] = None


@dataclass
class PaperMetadata:
    """Metadata extracted from the paper content."""

    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    venue: Optional[str] = None  # Journal or conference
    field_topic: Optional[str] = None


@dataclass
class PaperContent:
    """Structured content from the paper."""

    full_text: str
    sections: Dict[str, str] = field(default_factory=dict)  # section_name: content
    references: List[str] = field(default_factory=list)
    figures: List[str] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)


@dataclass
class AcademicPaper:
    """Complete data model for an academic paper."""

    file_metadata: FileMetadata
    paper_metadata: PaperMetadata
    content: PaperContent
    similarity_score: float = 0.0  # Similarity to research topic
    parse_timestamp: datetime = field(default_factory=datetime.now)
    parsing_errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Ensure all required fields are properly initialized."""
        if not isinstance(self.file_metadata, FileMetadata):
            raise ValueError("file_metadata must be a FileMetadata instance")
        if not isinstance(self.paper_metadata, PaperMetadata):
            raise ValueError("paper_metadata must be a PaperMetadata instance")
        if not isinstance(self.content, PaperContent):
            raise ValueError("content must be a PaperContent instance")

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
        """Convert to dictionary for serialization."""
        return {
            "file_path": str(self.file_metadata.file_path),
            "file_name": self.file_metadata.file_name,
            "title": self.paper_metadata.title,
            "authors": self.paper_metadata.authors,
            "year": self.paper_metadata.year,
            "abstract": self.paper_metadata.abstract,
            "keywords": self.paper_metadata.keywords,
            "doi": self.paper_metadata.doi,
            "venue": self.paper_metadata.venue,
            "field_topic": self.paper_metadata.field_topic,
            "similarity_score": self.similarity_score,
            "parse_timestamp": self.parse_timestamp.isoformat(),
            "parsing_errors": self.parsing_errors,
        }
