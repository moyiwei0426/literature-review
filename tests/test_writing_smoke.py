from services.analysis.synthesis_mapper import build_synthesis_map
from services.writing.outline_planner import build_outline
from services.writing.section_planner import build_section_plans
from services.writing.paragraph_planner import build_paragraph_plan
from services.writing.section_writer import write_sections
from services.writing.gap_section_builder import build_gap_section
from services.writing.conclusion_builder import build_conclusion_artifact
from services.writing.appendix_builder import build_appendix_artifact
from services.writing.abstract_builder import build_review_abstract
from services.writing.keywords_builder import build_review_keywords
from services.writing.markdown_composer import compose_review_markdown
from services.writing.review_validator import validate_review_writing
from services.writing.citation_grounder import ground_citations
from services.writing.style_rewriter import rewrite_style
import services.writing.style_rewriter as style_rewriter_module
from services.bib.bib_manager import build_bib_entries, prune_bib_entries
from services.latex.latex_composer import compose_latex
from services.latex.compiler import LatexCompiler
from services.llm.adapter import LLMResponse


def test_writing_smoke() -> None:
    verified_gaps = [{"gap_id": "g1", "gap_statement": "Chinese coverage is underrepresented."}]
    matrix = [{"paper_id": "p1", "claim_text": "Claim", "metrics": "coverage"}]
    outline = build_outline(verified_gaps, matrix)
    sections = write_sections(outline, matrix, verified_gaps)
    grounded = ground_citations(sections, matrix)
    rewritten = rewrite_style(grounded)
    bib = build_bib_entries(matrix)
    pruned = prune_bib_entries(bib, ["p1"])
    tex = compose_latex("Demo Review", rewritten, pruned)
    result = LatexCompiler().compile("demo.tex")
    assert len(outline) >= 2
    assert len(sections) >= 2
    assert len(pruned) == 1
    assert "\\section" in tex
    assert result["status"] in {"stub_compiled", "missing_tex"}


def test_write_sections_smoke_with_task_taxonomy_structure() -> None:
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

    taxonomy = next(section for section in sections if section["title"] == "Task Taxonomy and Evaluation Scope")
    focus = next(section for section in sections if section["title"] == "Task Focus: Gap Acceptance")
    comparison = next(section for section in sections if section["title"] == "Comparative Task Evidence and Evaluation Tradeoffs")
    paragraphs = focus.get("paragraphs", [])

    assert "gap acceptance" in taxonomy["text"].lower()
    assert len(paragraphs) >= 3
    assert [paragraph["move_type"] for paragraph in paragraphs[:4]] == ["framing", "evidence", "synthesis", "gap"]
    assert not any(paragraph["text"].startswith(("This ", "These ")) for paragraph in paragraphs[:4])
    assert any(marker in paragraphs[0]["text"].lower() for marker in ("analytic entry point", "comparison set", "shared problem space"))
    assert any(marker in paragraphs[1]["text"].lower() for marker in ("recurring pattern", "collectively", "descriptive inventory"))
    assert any(marker in paragraphs[2]["text"].lower() for marker in ("taken together", "field-level pattern", "boundary conditions"))
    assert any(marker in paragraphs[3]["text"].lower() for marker in ("unresolved problem", "conditional", "generalizable"))
    assert "sets up the evidence" not in paragraphs[0]["text"].lower()
    assert "transition-ready takeaway" not in paragraphs[2]["text"].lower()
    assert "minor aside" not in paragraphs[3]["text"].lower()
    assert "core claim in this section" not in paragraphs[1]["text"].lower()

    grounded = ground_citations(sections, matrix)
    grounded_focus = next(section for section in grounded if section["title"] == "Task Focus: Gap Acceptance")
    rewritten = rewrite_style(grounded)
    rewritten_focus = next(section for section in rewritten if section["title"] == "Task Focus: Gap Acceptance")

    assert grounded_focus["paragraphs"][0]["citation_keys"] == paragraphs[0]["citation_targets"]
    assert grounded_focus["paragraphs"][1]["citation_keys"] == paragraphs[1]["citation_targets"]
    assert rewritten_focus["paragraphs"][0]["move_type"] == "framing"
    assert rewritten_focus["paragraphs"][1]["move_type"] == "evidence"
    assert rewritten_focus["paragraphs"][2]["move_type"] == "synthesis"
    assert rewritten_focus["paragraphs"][0]["citation_keys"] == grounded_focus["paragraphs"][0]["citation_keys"]
    assert rewritten_focus["paragraphs"][1]["citation_keys"] == grounded_focus["paragraphs"][1]["citation_keys"]
    comparison_paragraphs = comparison.get("paragraphs", [])
    assert [paragraph["move_type"] for paragraph in comparison_paragraphs[:2]] == ["framing", "comparison"]
    assert "comparison" in comparison_paragraphs[1]["text"].lower()


def test_paragraph_planner_prefers_frame_evidence_synthesis_progression_and_preserves_metadata() -> None:
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
    section_plans = build_section_plans(
        outline,
        matrix,
        verified_gaps,
        synthesis_map=synthesis_map,
        organization=organization,
    )
    paragraph_plan = build_paragraph_plan(
        next(plan for plan in section_plans if plan["title"] == "Task Focus: Gap Acceptance"),
        matrix,
        verified_gaps,
        synthesis_map=synthesis_map,
        organization=organization,
    )

    blocks = paragraph_plan["blocks"]

    assert paragraph_plan["section_id"].startswith("sec-task")
    assert [block["move_type"] for block in blocks[:3]] == ["framing", "evidence", "synthesis"]
    assert blocks[-1]["move_type"] == "gap"
    assert blocks[0]["move_id"].startswith("sec-task-")
    assert blocks[0]["block_id"].startswith("sec-task-")
    assert blocks[0]["citation_targets"] == blocks[0]["supporting_citations"]
    assert blocks[0]["required_evidence_count"] == 0
    assert blocks[1]["required_evidence_count"] == 1
    assert blocks[1]["coverage_policy"] == "grounded_only"
    assert blocks[1]["allowed_citation_keys"] == blocks[1]["citation_targets"]
    assert blocks[-1]["must_include_gap_statement"] is True
    assert blocks[-1]["polish_eligible"] is True
    assert blocks[0]["theme_refs"]
    assert blocks[0]["gap_refs"]
    assert [sentence["role"] for sentence in blocks[0]["sentence_plan"]] == ["topic", "evidence", "closing"]
    assert "Introduce the subsection focus" in blocks[0]["sentence_plan"][0]["directive"]
    assert blocks[1]["supporting_points"]
    assert "Gap acceptance remains sensitive to traffic volume." in blocks[1]["supporting_points"]
    assert "Gap acceptance reporting remains inconsistent across studies." in blocks[-1]["supporting_points"]


def test_write_sections_smoke_with_factor_taxonomy_structure() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "method_family": "discrete choice",
            "tasks": "crossing_violation",
            "datasets": "signalized_intersection",
            "claim_text": "Older pedestrians show longer waiting time under heavy traffic.",
            "research_problem": "Behavioral factors at signalized crossings",
            "limitations": "Age-specific reporting is incomplete.",
            "notes": "",
            "metrics": "waiting_time",
        },
        {
            "paper_id": "p2",
            "method_family": "simulation",
            "tasks": "crossing_violation",
            "datasets": "signalized_intersection",
            "claim_text": "Female pedestrians show lower violation rates at signalized crossings.",
            "research_problem": "Demographic factors in crossing behavior",
            "limitations": "",
            "notes": "Gender effects depend on traffic density.",
            "metrics": "violation_rate",
        },
    ]
    verified_gaps = [
        {
            "gap_id": "g2",
            "gap_statement": "Demographic factor reporting remains inconsistent across pedestrian studies.",
            "status": "verified",
        }
    ]
    synthesis_map = build_synthesis_map(
        matrix,
        {"paper_count": 2, "themes": ["demographic_factors"]},
        {"contradiction_count": 0, "contradictions": []},
        verified_gaps=verified_gaps,
        scored_gaps=[{"gap_statement": "Demographic factor reporting remains inconsistent across pedestrian studies.", "review_worthiness": 0.8}],
    )
    organization = {"recommended_structure": "factor_taxonomy"}

    outline = build_outline(verified_gaps, matrix, synthesis_map=synthesis_map, organization=organization)
    sections = write_sections(
        outline,
        matrix,
        verified_gaps,
        synthesis_map=synthesis_map,
        organization=organization,
    )

    focus = next(section for section in sections if section["title"] == "Factor Focus: Demographic Factors")
    assert "demographic factors" in focus["text"].lower()
    assert "inconsistent across pedestrian studies" in focus["text"].lower()


def test_build_gap_section_prefers_structured_gap_fields() -> None:
    text = build_gap_section(
        [
            {
                "gap_id": "g-structured",
                "gap_statement": "validated cross-context transfer remains untested",
                "partial_evidence_paper_ids": ["p1", "p2"],
                "partial_evidence_summary": "Two simulation studies report promising transfer within a single urban dataset family",
                "why_insufficient": "both studies share the same city-scale context and omit external validation",
                "practical_consequence": "deployed systems may appear robust in review tables while failing in new cities",
                "research_need": "multi-city evaluation with aligned outcome definitions and external validation",
            }
        ],
        paper_count=2,
    )

    lowered = text.lower()
    assert "partial evidence:" in lowered
    assert "this evidence remains insufficient because" in lowered
    assert "as a result," in lowered
    assert "resolving this gap requires" in lowered
    assert "p1, p2" in text


def test_conclusion_builder_smoke_uses_synthesis_and_gaps() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "title": "Task Study",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "claim_text": "Gap acceptance remains sensitive to traffic volume.",
            "research_problem": "Task-level pedestrian behavior",
            "metrics": "waiting_time",
        },
        {
            "paper_id": "p2",
            "title": "Task Study Two",
            "method_family": "discrete choice",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "claim_text": "Waiting time varies with context.",
            "research_problem": "Task-level pedestrian behavior",
            "metrics": "waiting_time",
        },
    ]
    verified_gaps = [
        {
            "gap_id": "g1",
            "gap_statement": "Cross-context transfer remains under-tested.",
            "research_need": "multi-city evaluation with aligned outcome definitions",
        }
    ]
    synthesis_map = build_synthesis_map(
        matrix,
        {"paper_count": 2, "themes": ["simulation"]},
        {"contradiction_count": 1, "contradictions": []},
        verified_gaps=verified_gaps,
        scored_gaps=[{"gap_statement": "Cross-context transfer remains under-tested.", "review_worthiness": 0.9}],
    )
    organization = {"recommended_structure": "task_taxonomy"}

    artifact = build_conclusion_artifact(matrix, verified_gaps, synthesis_map=synthesis_map, organization=organization)

    lowered = artifact["text"].lower()
    assert artifact["stable_conclusions"]
    assert artifact["unresolved_tensions"]
    assert artifact["research_priorities"]
    assert "field-level picture" in lowered
    assert "stable conclusions" in lowered
    assert "research priorities" in lowered


def test_write_sections_uses_dedicated_conclusion_builder_when_synthesis_is_available() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "title": "Task Study",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "claim_text": "Gap acceptance remains sensitive to traffic volume.",
            "research_problem": "Task-level pedestrian behavior",
            "metrics": "waiting_time",
        },
        {
            "paper_id": "p2",
            "title": "Task Study Two",
            "method_family": "discrete choice",
            "tasks": "safety_assessment",
            "datasets": "urban_video",
            "claim_text": "Safety assessment varies with signal phase.",
            "research_problem": "Task-level pedestrian behavior",
            "metrics": "violation_rate",
        },
    ]
    verified_gaps = [
        {
            "gap_id": "g1",
            "gap_statement": "Cross-context transfer remains under-tested.",
            "research_need": "multi-city evaluation with aligned outcome definitions",
        }
    ]
    synthesis_map = build_synthesis_map(
        matrix,
        {"paper_count": 2, "themes": ["simulation"]},
        {"contradiction_count": 1, "contradictions": []},
        verified_gaps=verified_gaps,
        scored_gaps=[{"gap_statement": "Cross-context transfer remains under-tested.", "review_worthiness": 0.9}],
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

    conclusion = next(section for section in sections if section["section_id"] == "sec-conclusion")
    lowered = conclusion["text"].lower()

    assert "stable conclusions:" in lowered
    assert "unresolved tensions:" in lowered
    assert "research priorities:" in lowered
    assert "task structure" in lowered
    assert "cross-context transfer remains under-tested" in lowered


def test_write_sections_uses_dedicated_gap_builder_when_structured_gaps_available() -> None:
    verified_gaps = [
        {
            "gap_id": "g1",
            "gap_statement": "metric reporting remains inconsistent across studies",
            "status": "verified",
            "partial_evidence_paper_ids": ["p1"],
            "partial_evidence_summary": "One study reports waiting time while another reports violation rate",
            "why_insufficient": "the metrics are not commensurate enough for direct comparison",
            "practical_consequence": "the review cannot support a defensible cross-paper performance ranking",
            "research_need": "shared reporting standards for evaluation metrics",
        }
    ]
    matrix = [
        {
            "paper_id": "p1",
            "claim_text": "Waiting time is the dominant reported metric.",
            "metrics": "waiting_time",
        }
    ]
    outline = build_outline(verified_gaps, matrix)

    sections = write_sections(outline, matrix, verified_gaps)
    gap_section = next(section for section in sections if section["section_id"] == "sec-gaps")
    lowered = gap_section["text"].lower()

    assert "partial evidence:" in lowered
    assert "this evidence remains insufficient because" in lowered
    assert "as a result," in lowered
    assert "resolving this gap requires" in lowered


def test_ground_citations_adds_paragraph_level_keys() -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Methods and Evaluation",
            "objective": "Compare methods and evaluation evidence.",
            "text": (
                "Transformer-based summarization systems improve accuracy on benchmark tasks.\n\n"
                "ROUGE reporting remains inconsistent across evaluation studies."
            ),
        }
    ]
    matrix = [
        {
            "paper_id": "p1",
            "title": "Transformer Summarization",
            "claim_text": "Transformer-based summarization systems improve accuracy on benchmark tasks.",
            "method_summary": "A transformer encoder-decoder for summarization.",
            "method_family": "transformer",
            "tasks": "summarization",
            "research_problem": "summarization accuracy",
            "metrics": "accuracy",
            "limitations": "",
        },
        {
            "paper_id": "p2",
            "title": "Evaluation Metrics Study",
            "claim_text": "ROUGE reporting remains inconsistent across evaluation studies.",
            "method_summary": "An analysis of metric reporting quality.",
            "method_family": "evaluation",
            "tasks": "evaluation",
            "research_problem": "metric reporting consistency",
            "metrics": "rouge",
            "limitations": "",
        },
    ]

    grounded = ground_citations(sections, matrix)

    assert grounded[0]["citation_keys"] == ["p1", "p2"]
    assert grounded[0]["paragraphs"][0]["citation_keys"] == ["p1"]
    assert grounded[0]["paragraphs"][1]["citation_keys"] == ["p2"]


def test_compose_latex_renders_paragraph_level_citations_and_fallback() -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Methods and Evaluation",
            "text": "unused fallback text",
            "citation_keys": ["p1", "p2"],
            "paragraphs": [
                {"text": "Transformer evidence is strong.", "citation_keys": ["p1"]},
                {"text": "Metric reporting remains inconsistent.", "citation_keys": ["p2"]},
            ],
        },
        {
            "section_id": "sec-2",
            "title": "Conclusion",
            "text": "This claim is grounded by prior work [p1].",
            "citation_keys": ["p1"],
        },
    ]
    bib_entries = [
        {"key": "p1", "entry": "@article{p1, title={One}}"},
        {"key": "p2", "entry": "@article{p2, title={Two}}"},
    ]

    tex = compose_latex("Demo Review", sections, bib_entries)

    assert "Transformer evidence is strong. \\cite{p1}" in tex
    assert "Metric reporting remains inconsistent. \\cite{p2}" in tex
    assert "This claim is grounded by prior work \\cite{p1}." in tex


def test_ground_citations_prefers_planner_targets_over_lexical_overlap() -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Evaluation Details",
            "objective": "Ground the evaluation discussion.",
            "text": "Transformer baseline wording appears repeatedly in the draft.",
            "paragraphs": [
                {
                    "text": "Transformer baseline wording appears repeatedly in the draft.",
                    "citation_targets": ["p1"],
                    "supporting_citations": ["p1"],
                }
            ],
        }
    ]
    matrix = [
        {
            "paper_id": "p1",
            "title": "Sparse Evaluation Study",
            "claim_text": "Sparse evaluation reporting remains inconsistent across studies.",
            "method_family": "evaluation",
            "tasks": "reporting",
            "research_problem": "metric reporting",
            "metrics": "rouge",
            "limitations": "",
        },
        {
            "paper_id": "p2",
            "title": "Transformer Baseline",
            "claim_text": "Transformer baseline improves accuracy on benchmark tasks.",
            "method_family": "transformer",
            "tasks": "summarization",
            "research_problem": "benchmark accuracy",
            "metrics": "accuracy",
            "limitations": "",
        },
    ]

    grounded = ground_citations(sections, matrix)

    assert grounded[0]["citation_keys"][0] == "p1"
    assert grounded[0]["paragraphs"][0]["citation_keys"] == ["p1"]
    assert grounded[0]["paragraphs"][0]["_citation_rationale"]["strategy"] == "planner_targets"


def test_ground_citations_uses_theme_and_gap_refs_when_targets_missing() -> None:
    sections = [
        {
            "section_id": "sec-2",
            "title": "Task Focus: Gap Acceptance",
            "objective": "Discuss evidence and remaining gaps.",
            "text": "Transformer baseline wording appears in the section, but the planning signal points elsewhere.",
            "paragraphs": [
                {
                    "text": "Transformer baseline wording appears in the section, but the planning signal points elsewhere.",
                    "theme_refs": [
                        {
                            "theme_id": "task:gap_acceptance",
                            "label": "Gap Acceptance",
                            "synthesis_note": "gap acceptance evidence",
                        }
                    ],
                    "gap_refs": [
                        {
                            "gap_id": "g1",
                            "gap_statement": "Gap acceptance evidence remains underdeveloped.",
                            "research_need": "aligned outcome definitions",
                        }
                    ],
                }
            ],
        }
    ]
    matrix = [
        {
            "paper_id": "p1",
            "title": "Gap Acceptance Study",
            "claim_text": "Gap acceptance evidence remains underdeveloped.",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "research_problem": "gap acceptance",
            "metrics": "acceptance_rate",
            "limitations": "",
        },
        {
            "paper_id": "p2",
            "title": "Transformer Baseline",
            "claim_text": "Transformer baseline improves accuracy on benchmark tasks.",
            "method_family": "transformer",
            "tasks": "summarization",
            "research_problem": "benchmark accuracy",
            "metrics": "accuracy",
            "limitations": "",
        },
    ]

    grounded = ground_citations(sections, matrix)

    assert grounded[0]["paragraphs"][0]["citation_keys"] == ["p1"]
    assert grounded[0]["citation_keys"][0] == "p1"


def test_compose_latex_renders_appendix_evidence_table() -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Methods and Evaluation",
            "text": "Body text.",
        }
    ]
    matrix = [
        {
            "paper_id": "p1",
            "title": "Demo Paper",
            "year": 2023,
            "venue": "Demo Venue",
            "authors": "A. Author",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "metrics": "waiting_time",
            "claim_text": "Gap acceptance remains sensitive to traffic volume.",
            "research_problem": "Task-level pedestrian behavior",
            "evidence_chunk_ids": "c1",
        }
    ]
    appendix = build_appendix_artifact(
        matrix,
        profiles=[{"paper_id": "p1", "title": "Demo Paper", "year": 2023, "venue": "Demo Venue", "authors": ["A. Author"]}],
        verified_gaps=[{"gap_id": "g1", "gap_statement": "Cross-context transfer remains under-tested.", "research_need": "multi-city evaluation"}],
    )

    tex = compose_latex("Demo Review", sections, [{"key": "p1", "entry": "@article{p1, title={One}}"}], appendix=appendix)

    assert "\\appendix" in tex
    assert "\\section{Appendix}" in tex
    assert "\\subsection{Evidence Table}" in tex
    assert "Demo Paper" in tex


def test_build_review_abstract_uses_conclusion_and_appendix_signals() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "title": "Demo Paper",
            "year": 2023,
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "claim_text": "Gap acceptance remains sensitive to traffic volume.",
            "metrics": "waiting_time",
        },
        {
            "paper_id": "p2",
            "title": "Field Study",
            "year": 2022,
            "method_family": "field_study",
            "tasks": "gap_acceptance; safety_assessment",
            "claim_text": "Safety assessment varies with context.",
            "metrics": "violation_rate",
        },
    ]
    verified_gaps = [
        {
            "gap_id": "g1",
            "gap_statement": "Cross-context transfer remains under-tested.",
            "research_need": "multi-city evaluation with aligned outcome definitions",
        }
    ]
    synthesis_map = build_synthesis_map(
        matrix,
        {"paper_count": 2, "themes": ["gap_acceptance"]},
        {"contradiction_count": 0, "contradictions": []},
        verified_gaps=verified_gaps,
        scored_gaps=[{"gap_statement": "Cross-context transfer remains under-tested.", "review_worthiness": 0.9}],
    )
    organization = {"recommended_structure": "task_taxonomy"}
    conclusion = build_conclusion_artifact(matrix, verified_gaps, synthesis_map=synthesis_map, organization=organization)
    appendix = build_appendix_artifact(matrix, verified_gaps=verified_gaps, synthesis_map=synthesis_map, organization=organization)

    abstract = build_review_abstract(
        "Demo Review",
        matrix,
        synthesis_map=synthesis_map,
        organization=organization,
        verified_gaps=verified_gaps,
        conclusion=conclusion,
        appendix=appendix,
    )

    lowered = abstract["text"].lower()
    assert abstract["paper_count"] == 2
    assert abstract["dominant_axis"] == "task structure"
    assert "synthesizes 2 papers" in lowered
    assert "task structure" in lowered
    assert "cross-context transfer remains under-tested" in lowered


def test_compose_latex_renders_abstract_and_structured_gap_index() -> None:
    sections = [{"section_id": "sec-1", "title": "Methods", "text": "Body text."}]
    appendix = {
        "summary": {
            "paper_count": 2,
            "row_count": 4,
            "verified_gap_count": 1,
            "dominant_axis": "task",
            "top_methods": ["simulation"],
            "top_tasks": ["gap acceptance"],
            "top_datasets": ["urban video"],
            "narrative": ["The appendix records the main evidence map."],
        },
        "evidence_table": [
            {
                "paper_id": "p1",
                "title": "Demo Paper",
                "year": 2023,
                "methods": ["simulation"],
                "tasks": ["gap acceptance"],
                "gap_matches": ["g1"],
            }
        ],
        "gap_index": [
            {
                "gap_id": "g1",
                "gap_statement": "Cross-context transfer remains under-tested.",
                "severity": "high",
                "research_need": "multi-city evaluation",
            }
        ],
    }

    tex = compose_latex(
        "Demo Review",
        sections,
        [{"key": "p1", "entry": "@article{p1, title={One}}"}],
        appendix=appendix,
        abstract={"text": "This review synthesizes evidence around task structure."},
    )

    assert "\\begin{abstract}" in tex
    assert "\\subsection{Appendix Summary}" in tex
    assert "\\textbf{Papers}: 2" in tex
    assert "Gap & Statement & Severity & Research need" in tex
    assert "Cross-context transfer remains under-tested." in tex


def test_compose_latex_renders_keywords_under_abstract() -> None:
    sections = [{"section_id": "sec-1", "title": "Methods", "text": "Body text."}]
    tex = compose_latex(
        "Demo Review",
        sections,
        [{"key": "p1", "entry": "@article{p1, title={One}}"}],
        abstract={"text": "This review synthesizes evidence around task structure."},
        keywords={"keywords": ["task structure", "gap acceptance"]},
    )

    assert "\\begin{abstract}" in tex
    assert "\\noindent\\textbf{Keywords:} task structure, gap acceptance" in tex


def test_keywords_builder_smoke_prefers_structured_review_signals() -> None:
    matrix = [
        {
            "paper_id": "p1",
            "method_family": "simulation",
            "tasks": "gap_acceptance",
            "datasets": "urban_video",
            "metrics": "waiting_time",
            "research_problem": "gap acceptance under traffic pressure",
        },
        {
            "paper_id": "p2",
            "method_family": "field study",
            "tasks": "safety_assessment",
            "datasets": "urban_video",
            "metrics": "violation_rate",
            "research_problem": "cross-context transfer and metric reporting",
        },
    ]
    synthesis_map = {
        "overview": {"dominant_axis": "task"},
        "top_themes": [{"label": "gap_acceptance"}, {"label": "cross_context_transfer"}],
    }
    organization = {"recommended_structure": "task_taxonomy"}
    appendix = {
        "summary": {
            "dominant_axis": "task",
            "top_methods": ["simulation"],
            "top_tasks": ["gap acceptance"],
            "top_datasets": ["urban video"],
        },
        "gap_index": [
            {
                "gap_id": "g1",
                "gap_statement": "Cross-context transfer remains under-tested.",
                "research_need": "multi-city evaluation",
            }
        ],
    }
    abstract = {
        "dominant_axis": "task structure",
        "top_methods": ["simulation"],
        "top_tasks": ["gap acceptance"],
        "top_themes": ["gap acceptance"],
    }

    keywords = build_review_keywords(matrix, synthesis_map=synthesis_map, organization=organization, appendix=appendix, abstract=abstract)

    lowered = [item.lower() for item in keywords["keywords"]]
    assert keywords["keyword_count"] == len(keywords["keywords"])
    assert len(keywords["keywords"]) <= 8
    assert "task structure" in lowered or "task taxonomy" in lowered
    assert "gap acceptance" in lowered
    assert any(item in lowered for item in {"simulation", "urban video", "cross context transfer"})


def test_compose_review_markdown_renders_keywords_and_appendix() -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Introduction",
            "paragraphs": [{"text": "Opening paragraph.", "citation_keys": ["p1"]}],
        }
    ]
    appendix = {
        "summary": {
            "paper_count": 2,
            "row_count": 4,
            "verified_gap_count": 1,
            "dominant_axis": "task structure",
            "top_methods": ["simulation"],
            "top_tasks": ["gap acceptance"],
            "top_datasets": ["urban video"],
            "narrative": ["The appendix records the main evidence map."],
        },
        "evidence_table": [
            {
                "paper_id": "p1",
                "title": "Demo Paper",
                "year": 2023,
                "methods": ["simulation"],
                "tasks": ["gap acceptance"],
                "claim_count": 1,
                "gap_matches": ["g1"],
            }
        ],
        "gap_index": [
            {
                "gap_id": "g1",
                "gap_statement": "Cross-context transfer remains under-tested.",
                "severity": "high",
                "research_need": "multi-city evaluation",
            }
        ],
    }

    markdown = compose_review_markdown(
        "Demo Review",
        sections,
        abstract={"text": "This review synthesizes evidence around task structure."},
        keywords={"keywords": ["task structure", "gap acceptance"]},
        appendix=appendix,
        citation_metadata=[{"paper_id": "p1", "authors": ["Alice Smith", "Bob Jones"], "year": 2023, "title": "Demo Paper"}],
        citation_style="apa",
    )

    assert "# Demo Review" in markdown
    assert "## Abstract" in markdown
    assert "**Keywords:** task structure, gap acceptance" in markdown
    assert "## Introduction" in markdown
    assert "Opening paragraph (Smith & Jones, 2023)." in markdown
    assert "## Appendix" in markdown
    assert "### Evidence Highlights" in markdown
    assert "Demo Paper" in markdown
    assert "### Gap Index" in markdown
    assert "Cross-context transfer remains under-tested." in markdown
    assert "## References" in markdown
    assert "- Smith, A., & Jones, B. (2023). Demo Paper." in markdown


def test_compose_review_markdown_renders_apa_reference_fallbacks() -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Findings",
            "paragraphs": [{"text": "Key result.", "citation_keys": ["p2_2024_chen_demo"]}],
        }
    ]

    markdown = compose_review_markdown(
        "Demo Review",
        sections,
        citation_metadata=[{"paper_id": "p2_2024_chen_demo", "authors": ["Liang Chen", "Mina Park"], "year": 2024, "title": "Structured Review Systems", "venue": "Journal of Review Engineering", "doi": "10.1000/demo"}],
        citation_style="apa",
    )

    assert "Key result (Chen & Park, 2024)." in markdown
    assert "## References" in markdown
    assert "- Chen, L., & Park, M. (2024). Structured Review Systems. Journal of Review Engineering. https://doi.org/10.1000/demo" in markdown


def test_rewrite_style_preserves_paragraph_structure_and_metadata() -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Introduction",
            "text": "It is worth noting that this paragraph utilize evidence [p1].\n\nIt should be noted that a pivotal result remains [p2].",
            "citation_keys": ["p1", "p2"],
            "theme_refs": [{"theme_id": "t1", "label": "Theme One"}],
            "gap_refs": [{"gap_id": "g1", "gap_statement": "Gap statement"}],
            "paragraphs": [
                {
                    "text": "It is worth noting that this paragraph utilize evidence [p1].",
                    "move_type": "framing",
                    "purpose": "Set up the section.",
                    "citation_keys": ["p1"],
                    "citation_targets": ["p1"],
                    "supporting_citations": ["p1"],
                    "theme_refs": [{"theme_id": "t1", "label": "Theme One"}],
                    "gap_refs": [{"gap_id": "g1", "gap_statement": "Gap statement"}],
                },
                {
                    "text": "It should be noted that a pivotal result remains [p2].",
                    "move_type": "evidence",
                    "purpose": "Present supporting evidence.",
                    "citation_keys": ["p2"],
                    "citation_targets": ["p2"],
                    "supporting_citations": ["p2"],
                    "theme_refs": [{"theme_id": "t1", "label": "Theme One"}],
                    "gap_refs": [{"gap_id": "g1", "gap_statement": "Gap statement"}],
                },
            ],
        }
    ]

    rewritten = rewrite_style(sections)

    assert len(rewritten) == 1
    assert rewritten[0]["section_id"] == "sec-1"
    assert rewritten[0]["citation_keys"] == ["p1", "p2"]
    assert len(rewritten[0]["paragraphs"]) == 2
    assert [paragraph["move_type"] for paragraph in rewritten[0]["paragraphs"]] == ["framing", "evidence"]
    assert [paragraph["purpose"] for paragraph in rewritten[0]["paragraphs"]] == ["Set up the section.", "Present supporting evidence."]
    assert rewritten[0]["paragraphs"][0]["citation_targets"] == ["p1"]
    assert rewritten[0]["paragraphs"][0]["supporting_citations"] == ["p1"]
    assert rewritten[0]["paragraphs"][0]["theme_refs"] == [{"theme_id": "t1", "label": "Theme One"}]
    assert rewritten[0]["paragraphs"][0]["gap_refs"] == [{"gap_id": "g1", "gap_statement": "Gap statement"}]
    assert rewritten[0]["paragraphs"][0]["citation_keys"] == ["p1"]
    assert rewritten[0]["paragraphs"][1]["citation_keys"] == ["p2"]
    assert rewritten[0]["paragraphs"][0]["text"] == "This paragraph use evidence [p1]."
    assert rewritten[0]["paragraphs"][1]["text"] == "An important result remains [p2]."
    assert rewritten[0]["text"] == "This paragraph use evidence [p1].\n\nAn important result remains [p2]."


def test_rewrite_style_falls_back_when_llm_reorders_or_collapses_paragraphs(monkeypatch) -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Results",
            "text": "It is worth noting that the first paragraph uses [p1].\n\nIt should be noted that the second paragraph remains pivotal [p2].",
            "paragraphs": [
                {
                    "text": "It is worth noting that the first paragraph uses [p1].",
                    "move_type": "framing",
                    "purpose": "Open.",
                    "citation_keys": ["p1"],
                    "citation_targets": ["p1"],
                    "supporting_citations": ["p1"],
                    "theme_refs": [{"theme_id": "t1"}],
                    "gap_refs": [{"gap_id": "g1"}],
                },
                {
                    "text": "It should be noted that the second paragraph remains pivotal [p2].",
                    "move_type": "evidence",
                    "purpose": "Support.",
                    "citation_keys": ["p2"],
                    "citation_targets": ["p2"],
                    "supporting_citations": ["p2"],
                    "theme_refs": [{"theme_id": "t2"}],
                    "gap_refs": [{"gap_id": "g2"}],
                },
            ],
        }
    ]

    class FakeLLMAdapter:
        def __init__(self) -> None:
            self.provider = "openai-compatible"
            self.base_url = "http://example.test"

        def _has_auth(self) -> bool:
            return True

        def generate_json(self, system_prompt: str, user_prompt: str, *, metadata=None) -> LLMResponse:
            return LLMResponse(
                content={
                    "sections": [
                        {
                            "section_id": "sec-1",
                            "title": "Results",
                            "paragraphs": [{"text": "Collapsed output [p1][p2]."}],
                        }
                    ]
                },
                raw_text="",
                model="fake",
                provider="fake",
                latency_ms=0,
                usage={},
            )

    monkeypatch.setattr(style_rewriter_module, "LLMAdapter", FakeLLMAdapter)

    rewritten = rewrite_style(sections)

    assert len(rewritten[0]["paragraphs"]) == 2
    assert [paragraph["move_type"] for paragraph in rewritten[0]["paragraphs"]] == ["framing", "evidence"]
    assert rewritten[0]["paragraphs"][0]["citation_keys"] == ["p1"]
    assert rewritten[0]["paragraphs"][1]["citation_keys"] == ["p2"]
    assert rewritten[0]["paragraphs"][0]["text"] == "The first paragraph uses [p1]."
    assert rewritten[0]["paragraphs"][1]["text"] == "The second paragraph remains important [p2]."


def test_rewrite_style_llm_path_preserves_paragraph_order_and_metadata(monkeypatch) -> None:
    sections = [
        {
            "section_id": "sec-1",
            "title": "Discussion",
            "text": "Original one [p1].\n\nOriginal two [p2].",
            "citation_keys": ["p1", "p2"],
            "paragraphs": [
                {
                    "text": "Original one [p1].",
                    "move_type": "framing",
                    "purpose": "Frame.",
                    "citation_keys": ["p1"],
                    "citation_targets": ["p1"],
                    "supporting_citations": ["p1"],
                    "theme_refs": [{"theme_id": "t1"}],
                    "gap_refs": [{"gap_id": "g1"}],
                },
                {
                    "text": "Original two [p2].",
                    "move_type": "synthesis",
                    "purpose": "Synthesize.",
                    "citation_keys": ["p2"],
                    "citation_targets": ["p2"],
                    "supporting_citations": ["p2"],
                    "theme_refs": [{"theme_id": "t2"}],
                    "gap_refs": [{"gap_id": "g2"}],
                },
            ],
        }
    ]

    class FakeLLMAdapter:
        def __init__(self) -> None:
            self.provider = "openai-compatible"
            self.base_url = "http://example.test"

        def _has_auth(self) -> bool:
            return True

        def generate_json(self, system_prompt: str, user_prompt: str, *, metadata=None) -> LLMResponse:
            return LLMResponse(
                content={
                    "sections": [
                        {
                            "section_id": "sec-1",
                            "title": "Discussion",
                            "paragraphs": [
                                {"text": "Refined first paragraph [p1]."},
                                {"text": "Refined second paragraph [p2]."},
                            ],
                        }
                    ]
                },
                raw_text="",
                model="fake",
                provider="fake",
                latency_ms=0,
                usage={},
            )

    monkeypatch.setattr(style_rewriter_module, "LLMAdapter", FakeLLMAdapter)

    rewritten = rewrite_style(sections)

    assert rewritten[0]["text"] == "Refined first paragraph [p1].\n\nRefined second paragraph [p2]."
    assert [paragraph["text"] for paragraph in rewritten[0]["paragraphs"]] == [
        "Refined first paragraph [p1].",
        "Refined second paragraph [p2].",
    ]
    assert [paragraph["move_type"] for paragraph in rewritten[0]["paragraphs"]] == ["framing", "synthesis"]
    assert [paragraph["purpose"] for paragraph in rewritten[0]["paragraphs"]] == ["Frame.", "Synthesize."]
    assert rewritten[0]["paragraphs"][0]["citation_keys"] == ["p1"]
    assert rewritten[0]["paragraphs"][1]["citation_keys"] == ["p2"]


def test_review_validator_passes_on_balanced_section() -> None:
    outline = [
        {
            "section_id": "sec-task",
            "title": "Task Focus: Evaluation Scope",
            "objective": "Synthesize evaluation evidence across studies.",
        }
    ]
    section_plans = [
        {
            "section_id": "sec-task",
            "title": "Task Focus: Evaluation Scope",
            "objective": "Synthesize evaluation evidence across studies.",
            "section_goal": "Use the strongest task evidence across the corpus.",
            "argument_moves": [
                {"move_id": "m1", "move_type": "framing"},
                {"move_id": "m2", "move_type": "evidence"},
                {"move_id": "m3", "move_type": "synthesis"},
            ],
        }
    ]
    paragraph_plans = [
        {
            "section_id": "sec-task",
            "blocks": [
                {"block_id": "b1", "move_type": "framing"},
                {"block_id": "b2", "move_type": "evidence"},
                {"block_id": "b3", "move_type": "synthesis"},
            ],
        }
    ]
    drafted_sections = [
        {
            "section_id": "sec-task",
            "title": "Task Focus: Evaluation Scope",
            "paragraphs": [
                {"text": "This section frames the task evidence [p1].", "move_type": "framing", "citation_keys": ["p1"]},
                {"text": "This section presents the strongest findings [p1].", "move_type": "evidence", "citation_keys": ["p1"]},
                {"text": "This section closes with a synthesis of the task evidence [p2].", "move_type": "synthesis", "citation_keys": ["p2"]},
            ],
            "citation_keys": ["p1", "p2"],
        }
    ]

    report = validate_review_writing(
        outline=outline,
        section_plans=section_plans,
        paragraph_plans=paragraph_plans,
        drafted_sections=drafted_sections,
        grounded_sections=drafted_sections,
        rewritten_sections=drafted_sections,
        verified_gaps=[],
    )

    assert report["status"] == "pass"
    assert report["counts"]["findings"] == 0
    assert report["sections"][0]["status"] == "pass"


def test_review_validator_flags_weak_gap_section() -> None:
    outline = [
        {
            "section_id": "sec-gaps",
            "title": "Research Gaps and Opportunities",
            "objective": "Surface unresolved issues and future opportunities.",
        }
    ]
    section_plans = [
        {
            "section_id": "sec-gaps",
            "title": "Research Gaps and Opportunities",
            "objective": "Surface unresolved issues and future opportunities.",
            "section_goal": "Keep the linked unresolved issue visible.",
            "argument_moves": [
                {"move_id": "m1", "move_type": "framing"},
                {"move_id": "m2", "move_type": "gap"},
                {"move_id": "m3", "move_type": "synthesis"},
            ],
        }
    ]
    paragraph_plans = [
        {
            "section_id": "sec-gaps",
            "blocks": [
                {"block_id": "b1", "move_type": "framing"},
                {"block_id": "b2", "move_type": "gap"},
                {"block_id": "b3", "move_type": "synthesis"},
            ],
        }
    ]
    weak_sections = [
        {
            "section_id": "sec-gaps",
            "title": "Research Gaps and Opportunities",
            "paragraphs": [
                {"text": "This section briefly introduces the topic.", "move_type": "framing", "citation_keys": []},
            ],
            "citation_keys": [],
        }
    ]

    report = validate_review_writing(
        outline=outline,
        section_plans=section_plans,
        paragraph_plans=paragraph_plans,
        drafted_sections=weak_sections,
        grounded_sections=weak_sections,
        rewritten_sections=weak_sections,
        verified_gaps=[{"gap_id": "g1", "gap_statement": "Linked gap remains unresolved."}],
    )

    section_report = report["sections"][0]
    finding_codes = {finding["code"] for finding in section_report["findings"]}

    assert report["status"] == "fail"
    assert "missing_paragraph_citations" in finding_codes
    assert "missing_linked_gap_handling" in finding_codes
    assert "missing_expected_moves" in finding_codes
    assert section_report["status"] == "fail"


from services.writing.evidence_bundle import build_evidence_bundle
from services.writing.version_selector import select_best_version


def test_build_evidence_bundle_collects_allowed_rows_and_gap_refs() -> None:
    section_plan = {"section_id": "sec-1"}
    block = {
        "block_id": "sec-1-block-1",
        "move_type": "comparison",
        "citation_targets": ["p1"],
        "supporting_citations": ["p1", "p2"],
        "required_evidence_count": 1,
        "supporting_points": ["shared benchmark", "reporting mismatch"],
        "gap_refs": [{"gap_id": "g1", "gap_statement": "Need aligned reporting."}],
    }
    matrix = [{"paper_id": "p1", "claim_text": "A"}, {"paper_id": "p2", "claim_text": "B"}, {"paper_id": "p3", "claim_text": "C"}]
    verified = [{"gap_id": "g1", "gap_statement": "Need aligned reporting.", "research_need": "shared metrics"}]

    bundle = build_evidence_bundle(section_plan, block, matrix, verified)

    assert bundle["bundle_id"] == "sec-1-block-1-evidence"
    assert bundle["allowed_citation_keys"] == ["p1", "p2"]
    assert [row["paper_id"] for row in bundle["evidence_rows"]] == ["p1", "p2"]
    assert bundle["gap_refs"][0]["gap_id"] == "g1"


def test_version_selector_prefers_polished_when_not_worse() -> None:
    choice = select_best_version(
        {"sections": [{"section_id": "sec-1"}], "paragraph_validation": {"summary": {"finding_count": 1}}, "section_validation": {"status": "pass", "summary": {"finding_count": 1}}},
        {"sections": [{"section_id": "sec-1", "track": "polished", "paragraphs": [{"move_type": "synthesis", "track": "polished", "quality_notes": ["polished_synthesis_flow", "citation_retained"]}]}], "paragraph_validation": {"summary": {"finding_count": 0}}, "section_validation": {"status": "pass", "summary": {"finding_count": 0}}},
    )

    assert choice["selected_track"] == "polished"
    assert choice["selected_sections"][0]["track"] == "polished"
    assert choice["selection_report"]["reason"] == "polished_quality_gain_within_risk_budget"


def test_rewrite_style_strengthens_high_value_polished_moves_without_dropping_citations() -> None:
    sections = [
        {
            "section_id": "sec-comp",
            "title": "Comparative Task Evidence and Evaluation Tradeoffs",
            "paragraphs": [
                {
                    "text": "Studies show similar trends across datasets [p1][p2].",
                    "move_type": "synthesis",
                    "citation_keys": ["p1", "p2"],
                    "citation_targets": ["p1", "p2"],
                    "supporting_citations": ["p1", "p2"],
                    "polish_eligible": True,
                },
                {
                    "text": "The results differ across metrics [p1][p2].",
                    "move_type": "comparison",
                    "citation_keys": ["p1", "p2"],
                    "citation_targets": ["p1", "p2"],
                    "supporting_citations": ["p1", "p2"],
                    "polish_eligible": True,
                },
                {
                    "text": "No studies resolve the reporting issue [p2].",
                    "move_type": "gap",
                    "citation_keys": ["p2"],
                    "citation_targets": ["p2"],
                    "supporting_citations": ["p2"],
                    "polish_eligible": True,
                },
            ],
        }
    ]

    rewritten = rewrite_style(sections, track="polished")
    paragraphs = rewritten[0]["paragraphs"]

    assert paragraphs[0]["text"] != sections[0]["paragraphs"][0]["text"]
    assert any(marker in paragraphs[0]["text"].lower() for marker in ("taken together", "across these studies", "viewed jointly"))
    assert any(marker in paragraphs[1]["text"].lower() for marker in ("comparison", "compared with", "tradeoff", "contrast"))
    assert "no studies" not in paragraphs[2]["text"].lower()
    assert "limited evidence" in paragraphs[2]["text"].lower() or "remains unresolved" in paragraphs[2]["text"].lower()
    assert paragraphs[0]["citation_keys"] == ["p1", "p2"]
    assert paragraphs[0]["text"].count("[p1]") == 1
    assert paragraphs[0]["text"].count("[p2]") == 1
    assert "citation_retained" in paragraphs[0]["quality_notes"]
    assert "risk_checked" in paragraphs[2]["quality_notes"]


def test_version_selector_rejects_polished_when_risk_constraints_fail() -> None:
    choice = select_best_version(
        {
            "sections": [{"section_id": "sec-1", "track": "safe"}],
            "paragraph_validation": {"status": "pass", "summary": {"finding_count": 0}, "findings": []},
            "section_validation": {"status": "pass", "summary": {"finding_count": 0}, "extended_findings": []},
        },
        {
            "sections": [{"section_id": "sec-1", "track": "polished", "paragraphs": [{"move_type": "synthesis", "track": "polished", "quality_notes": ["polished_synthesis_flow"]}]}],
            "paragraph_validation": {"status": "fail", "summary": {"finding_count": 1}, "findings": [{"code": "citation_outside_bundle"}]},
            "section_validation": {"status": "pass", "summary": {"finding_count": 0}, "extended_findings": []},
            "metrics": {"citation_retention_penalty": 1, "unsupported_assertion_penalty": 0, "role_drift_penalty": 0, "overstatement_penalty": 1},
        },
    )

    assert choice["selected_track"] == "safe"
    assert choice["selection_report"]["reason"] == "safe_due_to_hard_risk"
    assert choice["selection_report"]["polished"]["hard_risk"] >= 1
