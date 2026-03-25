from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.retrieval.aggregator import RetrievalAggregator
from services.retrieval.query_builder import QueryInput, build_query_plan
from storage.repositories import FileRepository

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class RetrievalRequest(BaseModel):
    query: str
    max_results: int = Field(default=10, ge=1, le=100)


@router.post("/run")
def run_retrieval(request: RetrievalRequest) -> dict:
    plan = build_query_plan(QueryInput(query=request.query, max_results=request.max_results))
    result = RetrievalAggregator().run(plan)
    repo = FileRepository()
    repo.save_json("retrieval", "latest", {
        "count": result["count"],
        "sources": result["sources"],
        "candidates": [item.model_dump(mode="json") for item in result["candidates"]],
    })
    return {
        "count": result["count"],
        "sources": result["sources"],
    }
