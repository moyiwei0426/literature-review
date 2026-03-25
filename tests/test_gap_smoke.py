from services.analysis.gap_generator import generate_candidate_gaps
from services.analysis.gap_scorer import score_gaps
from services.analysis.gap_verifier import verify_gaps


def test_gap_smoke() -> None:
    matrix = [
        {"paper_id": "p1", "metrics": "", "tasks": "literature_review"},
        {"paper_id": "p2", "metrics": "", "tasks": "literature_review"},
    ]
    coverage = {
        "paper_count": 2,
        "language_distribution": {"english": 2},
    }
    contradiction = {
        "contradiction_count": 1,
    }
    candidates = generate_candidate_gaps(matrix, coverage, contradiction)
    verified = verify_gaps(candidates, coverage, matrix)
    scored = score_gaps(verified)
    assert len(candidates) >= 1
    assert len(verified) == len(candidates)
    assert all(item["confidence"] is not None for item in scored)
    assert all("partial_evidence_paper_ids" in item for item in verified)
    assert all("partial_evidence_summary" in item for item in verified)
    assert all("why_insufficient" in item for item in verified)
    assert all("practical_consequence" in item for item in verified)
    assert all("research_need" in item for item in verified)
