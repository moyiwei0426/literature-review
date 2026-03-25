from services.analysis.synthesis_mapper import build_synthesis_map
from services.writing.organization_selector import select_organization


def test_synthesis_and_organization_smoke() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "method_family": "simulation; discrete choice",
            "tasks": "gap_acceptance; safety_assessment",
            "datasets": "urban_video",
            "claim_text": "Older pedestrians show longer waiting time under heavy traffic.",
            "research_problem": "Pedestrian gap acceptance at signalized crossings",
            "limitations": "Small sample under one signal configuration.",
            "notes": "",
        },
        {
            "paper_id": "p2",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "claim_text": "Female pedestrians show lower violation rates at signalized crossings.",
            "research_problem": "Behavioral factors at signalized intersections",
            "limitations": "",
            "notes": "",
        },
    ]
    coverage = {
        "paper_count": 2,
        "themes": ["simulation", "discrete choice"],
    }
    contradiction = {
        "contradiction_count": 1,
        "contradictions": [{"task": "gap_acceptance", "related_tasks": ["gap_acceptance"]}],
    }
    verified_gaps = [{"gap_statement": "Metric reporting for gap acceptance remains limited.", "status": "verified"}]
    scored_gaps = [{"gap_statement": "Metric reporting for gap acceptance remains limited.", "review_worthiness": 0.7}]

    synthesis_map = build_synthesis_map(
        matrix,
        coverage,
        contradiction,
        verified_gaps=verified_gaps,
        scored_gaps=scored_gaps,
    )
    organization = select_organization(synthesis_map, matrix)

    assert synthesis_map["overview"]["paper_count"] == 2
    assert synthesis_map["theme_axes"]["method"]
    assert organization["recommended_structure"] in {
        "method_taxonomy",
        "factor_taxonomy",
        "task_taxonomy",
        "application_scenario",
    }
