from services.analysis.synthesis_mapper import build_synthesis_map
from services.writing.outline_planner import build_outline
from services.writing.section_planner import build_section_plans
from services.writing.paragraph_planner import build_paragraph_plan, build_paragraph_plans
from services.writing.section_writer import write_sections


def test_section_planner_smoke_builds_argument_moves() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "claim_text": "Gap acceptance remains sensitive to traffic volume.",
            "research_problem": "Gap acceptance under traffic pressure",
            "limitations": "Metric definitions are inconsistent.",
            "notes": "",
            "metrics": "acceptance_rate",
        },
        {
            "paper_id": "p2",
            "method_family": "discrete choice",
            "tasks": "gap_acceptance; safety_assessment",
            "datasets": "urban_video",
            "claim_text": "Safety assessment varies by signal phase.",
            "research_problem": "Task-level pedestrian behavior",
            "limitations": "",
            "notes": "Gap acceptance thresholds vary across datasets.",
            "metrics": "waiting_time",
        },
    ]
    verified_gaps = [
        {
            "gap_id": "g1",
            "gap_statement": "Gap acceptance reporting remains inconsistent across studies.",
            "research_need": "aligned outcome definitions across datasets",
            "status": "verified",
        }
    ]
    synthesis_map = build_synthesis_map(
        matrix,
        {"paper_count": 2, "themes": ["simulation"]},
        {"contradiction_count": 1, "contradictions": [{"task": "gap_acceptance", "related_tasks": ["gap_acceptance"]}]},
        verified_gaps=verified_gaps,
        scored_gaps=[{"gap_statement": "Gap acceptance reporting remains inconsistent across studies.", "review_worthiness": 0.9}],
    )
    organization = {"recommended_structure": "task_taxonomy"}
    outline = build_outline(verified_gaps, matrix, synthesis_map=synthesis_map, organization=organization)

    section_plans = build_section_plans(
        outline,
        matrix,
        verified_gaps,
        synthesis_map=synthesis_map,
        organization=organization,
    )

    focus_plan = next(plan for plan in section_plans if "Gap Acceptance" in plan["title"])
    move_types = [move["move_type"] for move in focus_plan["argument_moves"]]

    assert focus_plan["theme_refs"]
    assert focus_plan["gap_refs"][0]["gap_id"] == "g1"
    assert "framing" in move_types
    assert "evidence" in move_types
    assert "synthesis" in move_types
    assert "gap" in move_types


def test_paragraph_planner_smoke_builds_blocks_from_section_plan() -> None:
    section_plan = {
        "section_id": "sec-gap-acceptance",
        "title": "Task Focus: Gap Acceptance",
        "section_goal": "Synthesize the strongest task evidence around gap acceptance.",
        "argument_moves": [
            {
                "move_id": "m1",
                "move_type": "framing",
                "purpose": "Frame the section around gap acceptance.",
                "theme_refs": [{"theme_id": "task:gap_acceptance", "label": "Gap Acceptance"}],
                "gap_refs": [],
                "citation_targets": ["p1"],
                "supporting_points": [],
            },
            {
                "move_id": "m2",
                "move_type": "evidence",
                "purpose": "Anchor the section in evidence.",
                "theme_refs": [{"theme_id": "task:gap_acceptance", "label": "Gap Acceptance"}],
                "gap_refs": [{"gap_id": "g1", "gap_statement": "Reporting remains inconsistent."}],
                "citation_targets": ["p1", "p2"],
                "supporting_points": ["Gap acceptance remains sensitive to traffic volume."],
            },
        ],
    }

    paragraph_plan = build_paragraph_plan(section_plan, [], [])

    assert paragraph_plan["section_id"] == "sec-gap-acceptance"
    assert len(paragraph_plan["blocks"]) == 2
    assert paragraph_plan["blocks"][1]["move_type"] == "evidence"
    assert paragraph_plan["blocks"][1]["supporting_citations"] == ["p1", "p2"]


def test_write_sections_uses_planners_when_synthesis_is_available() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "claim_text": "Gap acceptance remains sensitive to traffic volume.",
            "research_problem": "Gap acceptance under traffic pressure",
            "limitations": "Metric definitions are inconsistent.",
            "notes": "",
            "metrics": "acceptance_rate",
        },
        {
            "paper_id": "p2",
            "method_family": "simulation",
            "tasks": "gap_acceptance; safety_assessment",
            "datasets": "urban_video",
            "claim_text": "Safety assessment varies by signal phase.",
            "research_problem": "Task-level pedestrian behavior",
            "limitations": "",
            "notes": "Gap acceptance thresholds vary across datasets.",
            "metrics": "waiting_time",
        },
    ]
    verified_gaps = [
        {
            "gap_id": "g1",
            "gap_statement": "Gap acceptance reporting remains inconsistent across studies.",
            "status": "verified",
        }
    ]
    synthesis_map = build_synthesis_map(
        matrix,
        {"paper_count": 2, "themes": ["simulation"]},
        {"contradiction_count": 1, "contradictions": [{"task": "gap_acceptance", "related_tasks": ["gap_acceptance"]}]},
        verified_gaps=verified_gaps,
        scored_gaps=[{"gap_statement": "Gap acceptance reporting remains inconsistent across studies.", "review_worthiness": 0.9}],
    )
    organization = {"recommended_structure": "task_taxonomy"}
    outline = build_outline(verified_gaps, matrix, synthesis_map=synthesis_map, organization=organization)

    sections = write_sections(
        outline,
        matrix,
        verified_gaps,
        synthesis_map=synthesis_map,
        organization=organization,
    )

    focus = next(section for section in sections if "Gap Acceptance" in section["title"])
    move_types = [paragraph.get("move_type") for paragraph in focus.get("paragraphs", [])]

    assert focus.get("paragraphs")
    assert "framing" in move_types
    assert "evidence" in move_types
    assert "gap" in move_types
    assert "analytic entry point" in focus["text"].lower()
    assert "conditional rather than fully generalizable" in focus["text"].lower()
