from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


StrategyType = Literal["keyword", "seed_expansion", "survey_backtracking"]


class QueryInput(BaseModel):
    query: str
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    max_results: int = Field(default=50, ge=1, le=500)
    language: Optional[str] = None
    include_sources: list[str] = Field(default_factory=lambda: ["openalex", "arxiv"])
    seed_papers: list[str] = Field(default_factory=list)
    strategy: StrategyType = "keyword"


class QueryPlan(BaseModel):
    query: str
    strategy: StrategyType
    max_results: int
    include_sources: list[str]
    filters: dict[str, object] = Field(default_factory=dict)
    seed_papers: list[str] = Field(default_factory=list)


def build_query_plan(query_input: QueryInput) -> QueryPlan:
    filters: dict[str, object] = {}
    if query_input.year_from is not None:
        filters["year_from"] = query_input.year_from
    if query_input.year_to is not None:
        filters["year_to"] = query_input.year_to
    if query_input.language:
        filters["language"] = query_input.language

    return QueryPlan(
        query=query_input.query,
        strategy=query_input.strategy,
        max_results=query_input.max_results,
        include_sources=query_input.include_sources,
        filters=filters,
        seed_papers=query_input.seed_papers,
    )
