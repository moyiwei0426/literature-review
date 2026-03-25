from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PaperCandidate(BaseModel):
    source: str
    source_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    citation_count: Optional[int] = None
    references: list[str] = Field(default_factory=list)
    related_urls: list[str] = Field(default_factory=list)
    pdf_url: Optional[str] = None
    is_open_access: Optional[bool] = None
    retrieval_query: str
    retrieval_score: Optional[float] = None


class PaperMaster(BaseModel):
    paper_id: str
    canonical_title: str
    normalized_title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    sources: list[str] = Field(default_factory=list)
    pdf_candidates: list[str] = Field(default_factory=list)
    citation_count: Optional[int] = None


class PaperFile(BaseModel):
    paper_id: str
    file_type: str
    file_path: str
    source_url: Optional[str] = None
    parse_status: Optional[str] = None
