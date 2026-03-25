from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from core.models import PaperMaster
from services.parsing.chunker import chunk_sections
from services.parsing.pdf_fetcher import PDFFetcher
from services.parsing.pymupdf_fallback import FallbackTextExtractor
from services.parsing.quality_scorer import score_parse_quality
from services.parsing.section_splitter import split_sections
from services.parsing.storage import ParsingStorage
from storage.repositories import FileRepository
from storage.repositories.entities import ChunksRepository, PapersRepository

router = APIRouter(prefix="/parsing", tags=["parsing"])


class ParsingRequest(BaseModel):
    paper_id: str
    pdf_url: str
    title: Optional[str] = None


@router.post("/run")
def run_parsing(request: ParsingRequest) -> dict:
    paper = PaperMaster(
        paper_id=request.paper_id,
        canonical_title=request.title or request.paper_id,
        normalized_title=(request.title or request.paper_id).lower(),
        authors=[],
        sources=["api"],
        pdf_candidates=[request.pdf_url],
    )
    fetch_result = PDFFetcher().fetch(paper)
    if fetch_result.get("status") != "downloaded":
        return fetch_result

    parsed = FallbackTextExtractor().extract(fetch_result["path"])
    pseudo_parsed = {
        "abstract": None,
        "sections": [{"title": "Body", "text": parsed.get("full_text", ""), "page_start": 1, "page_end": parsed.get("page_count")}],
    }
    sections = split_sections(pseudo_parsed)
    chunks = chunk_sections(paper.paper_id, sections)
    report = score_parse_quality({**pseudo_parsed, "sections": sections}, chunks)

    storage = ParsingStorage()
    storage.save_parsed(paper.paper_id, parsed)
    storage.save_chunks(paper.paper_id, chunks)
    storage.save_quality_report(paper.paper_id, report)

    repo = FileRepository()
    repo.save_json("parsing", request.paper_id, {"parsed": parsed, "chunks": chunks, "report": report})

    papers_repo = PapersRepository()
    chunks_repo = ChunksRepository()
    papers_repo.save(paper.paper_id, paper.model_dump(mode="json"))
    chunks_repo.save(paper.paper_id, chunks)

    return {"paper_id": paper.paper_id, "chunk_count": len(chunks), "quality": report}
