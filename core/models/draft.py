from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class Draft(BaseModel):
    draft_id: str
    project_id: str
    version: int
    outline: Optional[Any] = None
    latex_source: Optional[str] = None
    compiled_pdf_path: Optional[str] = None
    status: Optional[str] = None
