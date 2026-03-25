from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.bib.bib_manager import build_bib_entries, prune_bib_entries
from services.latex.compiler import LatexCompiler
from services.latex.latex_composer import compose_latex
from services.writing.citation_grounder import ground_citations
from services.writing.outline_planner import build_outline
from services.writing.section_writer import write_sections
from services.writing.style_rewriter import rewrite_style
from storage.repositories import FileRepository
from storage.repositories.entities import DraftsRepository

router = APIRouter(prefix="/writing", tags=["writing"])


class WritingRequest(BaseModel):
    verified_gaps: list[dict]
    matrix: list[dict]
    title: str = "ARIS-Lit Review"
    compile: bool = False  # skip compilation if False


class DraftSaveRequest(BaseModel):
    draft_id: str
    title: str
    outline: list[dict]
    sections: list[dict]
    bib_entries: list[dict]
    tex: str


# ── CRUD + Field queries ──────────────────────────────────────────────────────


@router.post("/run")
def run_writing(request: WritingRequest) -> dict:
    outline = build_outline(request.verified_gaps, request.matrix)
    sections = write_sections(outline, request.matrix, request.verified_gaps)
    grounded = ground_citations(sections, request.matrix)
    rewritten = rewrite_style(grounded)
    bib_entries = build_bib_entries(request.matrix)
    used_keys = []
    for section in grounded:
        used_keys.extend(section.get("citation_keys", []))
    pruned = prune_bib_entries(bib_entries, used_keys)
    tex = compose_latex(request.title, rewritten, pruned)

    compile_result = {}
    if request.compile:
        compile_result = LatexCompiler().compile(tex)

    repo = FileRepository()
    repo.save_json("writing", "latest", {"outline": outline, "sections": rewritten, "bib_entries": pruned, "tex": tex})

    drafts_repo = DraftsRepository()
    drafts_repo.save("latest", {
        "outline": outline,
        "sections": rewritten,
        "bib_entries": pruned,
        "tex": tex,
        "compile_result": compile_result,
    })

    return {
        "outline_sections": len(outline),
        "written_sections": len(rewritten),
        "bib_entries": len(pruned),
        "compile_result": compile_result,
    }


@router.get("/drafts")
def list_drafts(
    compile_status: Optional[str] = None,
    limit: int = 20,
) -> dict:
    repo = DraftsRepository()
    records = repo.list_records()[:limit]
    items = [{"draft_id": r["name"], **r["payload"]} for r in records]
    if compile_status:
        items = [i for i in items if (i.get("compile_result") or {}).get("status") == compile_status]
    return {"count": len(items), "items": items}


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str) -> dict:
    repo = DraftsRepository()
    try:
        return repo.get(draft_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found")


@router.post("/drafts")
def save_draft(req: DraftSaveRequest) -> dict:
    repo = DraftsRepository()
    repo.save(req.draft_id, {
        "title": req.title,
        "outline": req.outline,
        "sections": req.sections,
        "bib_entries": req.bib_entries,
        "tex": req.tex,
        "compile_result": {},
    })
    return {"message": "saved", "draft_id": req.draft_id}


@router.patch("/drafts/{draft_id}/compile")
def recompile_draft(draft_id: str) -> dict:
    repo = DraftsRepository()
    try:
        draft = repo.get(draft_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found")
    tex = draft.get("tex", "")
    if not tex:
        raise HTTPException(status_code=400, detail="No TeX content in draft")
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".tex", delete=False, mode="w") as f:
        f.write(tex)
        tmp_path = f.name
    try:
        result = LatexCompiler().compile(tmp_path)
        draft["compile_result"] = result
        repo.save(draft_id, draft)
        return {"message": "compiled", "draft_id": draft_id, "result": result}
    finally:
        os.unlink(tmp_path)


@router.delete("/drafts/{draft_id}")
def delete_draft(draft_id: str) -> dict:
    repo = DraftsRepository()
    if not repo.exists(draft_id):
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found")
    repo.delete(draft_id)
    return {"message": "deleted", "draft_id": draft_id}
