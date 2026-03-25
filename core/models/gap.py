from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GapType(str, Enum):
    COVERAGE = "coverage"
    COMPARISON = "comparison"
    METHODOLOGY = "methodology"
    EVALUATION = "evaluation"
    LANGUAGE = "language"
    APPLICATION = "application"
    TAXONOMY = "taxonomy"


class Gap(BaseModel):
    gap_id: str
    gap_statement: str
    gap_type: GapType
    supporting_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    partial_evidence_paper_ids: list[str] = Field(default_factory=list)
    partial_evidence_summary: Optional[str] = None
    why_insufficient: Optional[str] = None
    practical_consequence: Optional[str] = None
    research_need: Optional[str] = None
    resolution_needed: Optional[str] = None
    partial_evidence: Optional[str] = None
    insufficiency_reason: Optional[str] = None
    consequence: Optional[str] = None
    confidence: Optional[float] = None
    novelty_value: Optional[float] = None
    review_worthiness: Optional[float] = None
    status: Optional[str] = None
