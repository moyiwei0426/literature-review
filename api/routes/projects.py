from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from storage.repositories.entities import ProjectsRepository

router = APIRouter(prefix="/projects", tags=["projects"])

# ── Request models ────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    project_id: str = Field(..., description="Unique project identifier (e.g. 'proj-2024-nlp-review')")
    name: str = Field(..., description="Human-readable project name")
    description: Optional[str] = ""
    owner: str = Field(default="default_user")
    status: str = Field(default="active")
    research_question: Optional[str] = ""
    target_venues: list[str] = Field(default_factory=list)
    max_papers: int = Field(default=100)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    research_question: Optional[str] = None
    target_venues: Optional[list[str]] = None
    max_papers: Optional[int] = None
    stage: Optional[str] = None
    notes: Optional[str] = None


class FieldUpdate(BaseModel):
    field: str = Field(..., description="Field name to update")
    value: object = Field(..., description="New value for the field")


# ── CRUD ─────────────────────────────────────────────────────────────────────


@router.post("")
def create_project(req: ProjectCreate) -> dict:
    repo = ProjectsRepository()
    if repo.exists(req.project_id):
        raise HTTPException(status_code=409, detail=f"Project '{req.project_id}' already exists")
    payload = req.model_dump()
    payload["created_at"] = datetime.utcnow().isoformat()
    payload["updated_at"] = datetime.utcnow().isoformat()
    payload["stage"] = "retrieval"
    payload["paper_count"] = 0
    repo.save(req.project_id, payload)
    return {"message": "created", "project_id": req.project_id}


@router.get("")
def list_projects(
    status: Optional[str] = None,
    owner: Optional[str] = None,
    limit: int = 50,
) -> dict:
    repo = ProjectsRepository()
    records = repo.list_records()
    if status:
        records = [r for r in records if r["payload"].get("status") == status]
    if owner:
        records = [r for r in records if r["payload"].get("owner") == owner]
    items = [{"project_id": r["name"], **r["payload"]} for r in records[:limit]]
    return {"count": len(items), "items": items}


@router.get("/{project_id}")
def get_project(project_id: str) -> dict:
    repo = ProjectsRepository()
    try:
        payload = repo.get(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return {"project_id": project_id, **payload}


@router.patch("/{project_id}")
def update_project(project_id: str, req: ProjectUpdate) -> dict:
    repo = ProjectsRepository()
    try:
        payload = repo.get(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.utcnow().isoformat()
    payload.update(updates)
    repo.save(project_id, payload)
    return {"message": "updated", "project_id": project_id, "updated_fields": list(updates.keys())}


@router.patch("/{project_id}/field")
def update_project_field(project_id: str, req: FieldUpdate) -> dict:
    repo = ProjectsRepository()
    repo.update_field(project_id, req.field, req.value)
    return {"message": "field_updated", "project_id": project_id, "field": req.field}


@router.delete("/{project_id}")
def delete_project(project_id: str) -> dict:
    repo = ProjectsRepository()
    if not repo.exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    repo.delete(project_id)
    return {"message": "deleted", "project_id": project_id}


@router.get("/{project_id}/stage")
def get_project_stage(project_id: str) -> dict:
    repo = ProjectsRepository()
    try:
        payload = repo.get(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return {"project_id": project_id, "stage": payload.get("stage", "unknown")}
