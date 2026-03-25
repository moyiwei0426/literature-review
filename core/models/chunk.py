from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PaperChunk(BaseModel):
    chunk_id: str
    paper_id: str
    section: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    text: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    order_index: int
