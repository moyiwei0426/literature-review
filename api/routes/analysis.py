from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.models import PaperProfile
from services.analysis.coverage_analyzer import build_coverage_report
from services.analysis.contradiction_analyzer import detect_contradictions
from services.analysis.matrix_builder import build_claims_evidence_matrix
from storage.repositories import FileRepository
from storage.repositories.entities import ProfilesRepository

router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisRequest(BaseModel):
    profiles: list[dict]


# ── Field-level query models ──────────────────────────────────────────────────


class ProfileFieldQuery(BaseModel):
    field: str
    value: str
    limit: int = 50


class CoverageQuery(BaseModel):
    min_papers: Optional[int] = None
    language: Optional[str] = None
    domain: Optional[str] = None


# ── CRUD + Field queries ──────────────────────────────────────────────────────


@router.post("/run")
def run_analysis(request: AnalysisRequest) -> dict:
    profiles = [PaperProfile.model_validate(item) for item in request.profiles]
    coverage = build_coverage_report(profiles)
    matrix = build_claims_evidence_matrix(profiles)
    contradiction = detect_contradictions(profiles)

    repo = FileRepository()
    repo.save_json("analysis", "latest", {"coverage": coverage, "matrix": matrix, "contradiction": contradiction})

    profiles_repo = ProfilesRepository()
    for profile in profiles:
        profiles_repo.save(profile.paper_id, profile.model_dump(mode="json"))

    return {
        "paper_count": coverage["paper_count"],
        "matrix_rows": len(matrix),
        "contradiction_count": contradiction["contradiction_count"],
    }


@router.get("/profiles")
def list_profiles(
    domain: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 50,
) -> dict:
    repo = ProfilesRepository()
    records = repo.list_records()[:limit]
    items = [{"paper_id": r["name"], **r["payload"]} for r in records]
    if domain:
        items = [i for i in items if i.get("domain") == domain]
    if language:
        items = [i for i in items if language in (i.get("language_scope") or "")]
    return {"count": len(items), "items": items}


@router.get("/profiles/{paper_id}")
def get_profile(paper_id: str) -> dict:
    repo = ProfilesRepository()
    try:
        return repo.get(paper_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{paper_id}' not found")


@router.get("/profiles/field/{field}")
def query_profiles_by_field(field: str, value: str, limit: int = 50) -> dict:
    repo = ProfilesRepository()
    records = repo.list_records()[:limit]
    items = [r["payload"] for r in records if r["payload"].get(field) == value]
    return {"count": len(items), "field": field, "value": value, "items": items}


@router.get("/coverage")
def get_coverage(
    min_papers: Optional[int] = None,
    language: Optional[str] = None,
) -> dict:
    repo = FileRepository()
    try:
        data = repo.read_json("analysis", "latest")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No analysis results found. Run /analysis/run first.")
    coverage = data.get("coverage", {})
    if min_papers is not None and coverage.get("paper_count", 0) < min_papers:
        raise HTTPException(status_code=400, detail=f"Coverage has only {coverage.get('paper_count')} papers, minimum {min_papers} required")
    if language:
        lang_dist = coverage.get("language_distribution", {})
        if lang_dist and lang_dist.get(language, 0) == 0:
            raise HTTPException(status_code=404, detail=f"No papers found for language '{language}'")
    return coverage


@router.get("/matrix")
def get_matrix(limit: int = 100) -> dict:
    repo = FileRepository()
    try:
        data = repo.read_json("analysis", "latest")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No analysis results found. Run /analysis/run first.")
    matrix = data.get("matrix", [])
    return {"count": len(matrix), "rows": matrix[:limit]}


@router.get("/contradictions")
def get_contradictions() -> dict:
    repo = FileRepository()
    try:
        data = repo.read_json("analysis", "latest")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No analysis results found. Run /analysis/run first.")
    return data.get("contradiction", {})


@router.delete("/profiles/{paper_id}")
def delete_profile(paper_id: str) -> dict:
    repo = ProfilesRepository()
    if not repo.exists(paper_id):
        raise HTTPException(status_code=404, detail=f"Profile '{paper_id}' not found")
    repo.delete(paper_id)
    return {"message": "deleted", "paper_id": paper_id}
