from core.models import PaperClaim, PaperLimitation, PaperProfile, ClaimType, LimitationSource
from services.analysis.coverage_analyzer import build_coverage_report
from services.analysis.matrix_builder import build_claims_evidence_matrix
from services.analysis.contradiction_analyzer import detect_contradictions


def make_profile(paper_id: str, claim_type: ClaimType) -> PaperProfile:
    return PaperProfile(
        paper_id=paper_id,
        research_problem="Test problem",
        method_summary="Test method",
        method_family=["pipeline"],
        tasks=["literature_review"],
        datasets=["demo-dataset"],
        metrics=["coverage"],
        main_claims=[
            PaperClaim(
                claim_id=f"{paper_id}-c1",
                claim_text="A test claim",
                claim_type=claim_type,
                evidence_chunk_ids=[f"{paper_id}-chunk-1"],
                confidence=0.8,
            )
        ],
        limitations=[
            PaperLimitation(
                text="Test limitation",
                source=LimitationSource.INFERRED,
                evidence_chunk_ids=[f"{paper_id}-chunk-1"],
            )
        ],
        language_scope="english",
    )


def test_analysis_smoke() -> None:
    profiles = [
        make_profile("p1", ClaimType.METHODOLOGICAL),
        make_profile("p2", ClaimType.APPLICATION),
    ]
    coverage = build_coverage_report(profiles)
    matrix = build_claims_evidence_matrix(profiles)
    contradiction = detect_contradictions(profiles)

    assert coverage["paper_count"] == 2
    assert len(matrix) == 2
    assert contradiction["contradiction_count"] >= 1
