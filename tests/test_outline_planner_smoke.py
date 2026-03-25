from services.analysis.synthesis_mapper import build_synthesis_map
from services.writing.outline_planner import build_outline


def test_outline_planner_smoke_with_organization_and_synthesis() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "claim_text": "Gap acceptance remains sensitive to traffic volume.",
            "research_problem": "Gap acceptance under traffic pressure",
            "limitations": "Small sample.",
            "notes": "",
        },
        {
            "paper_id": "p2",
            "method_family": "simulation",
            "tasks": "gap_acceptance; safety_assessment",
            "datasets": "urban_video",
            "claim_text": "Safety assessment varies by signal phase.",
            "research_problem": "Task-level pedestrian behavior",
            "limitations": "",
            "notes": "",
        },
    ]
    coverage = {"paper_count": 2, "themes": ["simulation"]}
    contradiction = {"contradiction_count": 0, "contradictions": []}
    verified_gaps = [
        {
            "gap_id": "g1",
            "gap_statement": "Gap acceptance reporting remains inconsistent across studies.",
            "status": "verified",
        }
    ]
    synthesis_map = build_synthesis_map(
        matrix,
        coverage,
        contradiction,
        verified_gaps=verified_gaps,
        scored_gaps=[{"gap_statement": "Gap acceptance reporting remains inconsistent across studies.", "review_worthiness": 0.9}],
    )
    organization = {"recommended_structure": "task_taxonomy"}

    outline = build_outline(
        verified_gaps,
        matrix,
        synthesis_map=synthesis_map,
        organization=organization,
    )

    assert outline[1]["title"] == "Task Taxonomy and Evaluation Scope"
    assert any("Task Focus: Gap Acceptance" in section["title"] for section in outline)
    assert any("g1" in section.get("gap_inputs", []) for section in outline)
