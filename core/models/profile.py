from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClaimEvidenceLink(BaseModel):
    claim_id: str
    chunk_id: str
    support_type: Optional[str] = None
    confidence: Optional[float] = None


class ClaimType(str, Enum):
    PERFORMANCE = "performance"
    METHODOLOGICAL = "methodological"
    APPLICATION = "application"
    THEORETICAL = "theoretical"


class LimitationSource(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class PaperClaim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: ClaimType
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None


class PaperLimitation(BaseModel):
    text: str
    source: LimitationSource
    evidence_chunk_ids: list[str] = Field(default_factory=list)


class PaperProfile(BaseModel):
    paper_id: str
    title: str = "Untitled"
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    venue: Optional[str] = None
    research_problem: str
    problem_type: Optional[str] = None
    domain: Optional[str] = None
    language_scope: Optional[str] = None
    method_summary: str
    method_family: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    main_claims: list[PaperClaim] = Field(default_factory=list)
    limitations: list[PaperLimitation] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
