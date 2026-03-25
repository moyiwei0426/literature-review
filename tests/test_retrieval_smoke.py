from core.models import PaperCandidate
from services.retrieval.deduper import dedupe_candidates
from services.retrieval.query_builder import QueryInput, build_query_plan


def test_query_plan() -> None:
    plan = build_query_plan(QueryInput(query="test"))
    assert plan.query == "test"
    assert "openalex" in plan.include_sources


def test_dedup_smoke() -> None:
    candidates = [
        PaperCandidate(source="openalex", source_id="1", title="A Test Paper", authors=["Alice"], year=2024, doi="10.1/x", retrieval_query="q"),
        PaperCandidate(source="arxiv", source_id="2", title="A Test Paper", authors=["Alice"], year=2024, doi="10.1/x", retrieval_query="q"),
    ]
    masters, report = dedupe_candidates(candidates)
    assert len(masters) == 1
    assert report["after_count"] == 1
