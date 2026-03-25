from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from services.analysis.gap_generator import generate_candidate_gaps
from services.analysis.gap_scorer import score_gaps
from services.analysis.gap_verifier import verify_gaps
from storage.repositories import FileRepository
from storage.repositories.entities import GapsRepository

router = APIRouter(prefix="/gap", tags=["gap"])


class GapRequest(BaseModel):
    coverage: dict
    matrix: list[dict]
    contradiction: dict


@router.post("/run")
def run_gap(request: GapRequest) -> dict:
    candidates = generate_candidate_gaps(request.matrix, request.coverage, request.contradiction)
    verified = verify_gaps(candidates, request.coverage, request.matrix)
    scored = score_gaps(verified)

    repo = FileRepository()
    repo.save_json("gap", "latest", {"candidate_gaps": candidates, "verified_gaps": verified, "scored_gaps": scored})

    gaps_repo = GapsRepository()
    gaps_repo.save("latest", {"candidate_gaps": candidates, "verified_gaps": verified, "scored_gaps": scored})

    return {"candidate_count": len(candidates), "verified_count": len(verified), "scored_count": len(scored)}
