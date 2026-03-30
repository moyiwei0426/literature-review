from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class DraftTrack(BaseModel):
    name: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    paragraph_validation: Optional[dict[str, Any]] = None
    section_validation: Optional[dict[str, Any]] = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class Draft(BaseModel):
    draft_id: str
    project_id: str
    version: int
    outline: Optional[Any] = None
    latex_source: Optional[str] = None
    compiled_pdf_path: Optional[str] = None
    status: Optional[str] = None
    tracks: list[DraftTrack] = Field(default_factory=list)
    selected_track: Optional[str] = None
    selected_sections: list[dict[str, Any]] = Field(default_factory=list)
    selection_report: Optional[dict[str, Any]] = None
    dual_track_metrics: dict[str, Any] = Field(default_factory=dict)
