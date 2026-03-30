from core.models import PaperCandidate
from services.retrieval.deduper import dedupe_candidates
from services.retrieval.query_builder import QueryInput, build_query_plan, parse_boolean_query


def test_query_plan() -> None:
    plan = build_query_plan(QueryInput(query="test"))
    assert plan.query == "test"
    assert "openalex" in plan.include_sources


def test_boolean_query_supports_and_not() -> None:
    normalized, positive_terms, negative_terms = parse_boolean_query("pedestrian crossing AND signalized intersections AND NOT autonomous vehicles OR robots")
    assert normalized == "pedestrian crossing signalized intersections"
    assert positive_terms == ["pedestrian crossing", "signalized intersections"]
    assert negative_terms == ["autonomous vehicles", "robots"]


def test_query_plan_persists_negative_terms() -> None:
    plan = build_query_plan(QueryInput(query="pedestrian crossing AND NOT autonomous vehicles"))
    assert plan.query == "pedestrian crossing"
    assert plan.negative_terms == ["autonomous vehicles"]
    assert plan.filters["exclude_terms"] == ["autonomous vehicles"]


def test_dedup_smoke() -> None:
    candidates = [
        PaperCandidate(source="openalex", source_id="1", title="A Test Paper", authors=["Alice"], year=2024, doi="10.1/x", retrieval_query="q"),
        PaperCandidate(source="arxiv", source_id="2", title="A Test Paper", authors=["Alice"], year=2024, doi="10.1/x", retrieval_query="q"),
    ]
    masters, report = dedupe_candidates(candidates)
    assert len(masters) == 1
    assert report["after_count"] == 1
