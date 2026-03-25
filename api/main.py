from __future__ import annotations

from fastapi import FastAPI

from api.routes.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.projects import router as projects_router
from api.routes.retrieval import router as retrieval_router
from api.routes.parsing import router as parsing_router
from api.routes.extraction import router as extraction_router
from api.routes.analysis import router as analysis_router
from api.routes.gap import router as gap_router
from api.routes.writing import router as writing_router
from infra.settings import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(retrieval_router)
app.include_router(parsing_router)
app.include_router(extraction_router)
app.include_router(analysis_router)
app.include_router(gap_router)
app.include_router(writing_router)


@app.get("/")
def root() -> dict:
    return {
        "app": settings.app_name,
        "status": "ok",
        "docs": "/docs",
    }
