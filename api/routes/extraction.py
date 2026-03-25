from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from core.models import PaperChunk
from services.extraction.claim_linker import build_claim_evidence_links
from services.extraction.extractor import PaperExtractor
from services.extraction.storage import ExtractionStorage
from storage.repositories import FileRepository
from storage.repositories.entities import ProfilesRepository

router = APIRouter(prefix="/extraction", tags=["extraction"])


class ExtractionRequest(BaseModel):
    paper_id: str
    chunks: list[dict]


@router.post("/run")
def run_extraction(request: ExtractionRequest) -> dict:
    chunks = [PaperChunk.model_validate(item) for item in request.chunks]
    profile, report = PaperExtractor().extract(request.paper_id, chunks)
    links = build_claim_evidence_links(profile)

    storage = ExtractionStorage()
    storage.save_profile(request.paper_id, profile.model_dump(mode="json"))
    storage.save_claims(request.paper_id, [claim.model_dump(mode="json") for claim in profile.main_claims])
    storage.save_links(request.paper_id, [link.model_dump(mode="json") for link in links])
    storage.save_report(request.paper_id, report)

    repo = FileRepository()
    repo.save_json("extraction", request.paper_id, {
        "profile": profile.model_dump(mode="json"),
        "links": [link.model_dump(mode="json") for link in links],
        "report": report,
    })

    profiles_repo = ProfilesRepository()
    profiles_repo.save(request.paper_id, profile.model_dump(mode="json"))

    return {"paper_id": request.paper_id, "claim_count": len(profile.main_claims), "link_count": len(links)}
