from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


class PaperAuthor(BaseModel):
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None


class PaperMetadata(BaseModel):
    title: Optional[str] = None
    authors: List[PaperAuthor] = Field(default_factory=list)
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    journal_or_conference: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)


class Citation(BaseModel):
    key: str
    text: Optional[str] = None


class BaseElement(BaseModel):
    element_id: str


class ParagraphElement(BaseElement):
    type: Literal["paragraph"] = "paragraph"
    text: str
    citations: List[Citation] = Field(default_factory=list)


class FigureElement(BaseElement):
    type: Literal["figure"] = "figure"
    label: Optional[str] = None
    image_path: Optional[str] = None
    caption: Optional[str] = None
    in_text_reference: Optional[str] = None


class TableElement(BaseElement):
    type: Literal["table"] = "table"
    label: Optional[str] = None
    caption: Optional[str] = None
    data_csv: Optional[str] = None
    data_json: Optional[list] = None


class EquationElement(BaseElement):
    type: Literal["equation"] = "equation"
    label: Optional[str] = None
    latex_code: Optional[str] = None
    image_path: Optional[str] = None


class AlgorithmElement(BaseElement):
    type: Literal["algorithm"] = "algorithm"
    label: Optional[str] = None
    caption: Optional[str] = None
    pseudocode: Optional[str] = None


Element = Union[
    ParagraphElement,
    FigureElement,
    TableElement,
    EquationElement,
    AlgorithmElement,
]


class Section(BaseModel):
    section_number: Optional[str] = None
    title: Optional[str] = None
    content: List[Element] = Field(default_factory=list)


class BibliographyEntry(BaseModel):
    ref_id: str
    full_citation: str


class StructuredPaper(BaseModel):
    paper_id: str
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    sections: List[Section] = Field(default_factory=list)
    bibliography: List[BibliographyEntry] = Field(default_factory=list)
