from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from services.llm.adapter import LLMAdapter
from .normalizers import normalize_outline


PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "writing" / "outline_system.txt"

_STRUCTURE_TEMPLATES: dict[str, dict[str, str]] = {
    "method_taxonomy": {
        "axis": "method",
        "taxonomy_title": "Method Taxonomy and Representational Families",
        "taxonomy_objective": "Organize the review around methodological families and clarify how the dominant approaches differ in assumptions, strengths, and limitations.",
        "theme_prefix": "Method Focus",
        "comparison_title": "Comparative Method Evidence and Tradeoffs",
        "comparison_objective": "Compare the strongest method themes, emphasizing where methodological choices shape claims, coverage, and interpretability.",
    },
    "factor_taxonomy": {
        "axis": "factor",
        "taxonomy_title": "Factor Taxonomy and Contextual Drivers",
        "taxonomy_objective": "Organize the review around variable-centered factors and explain how the strongest contextual drivers shape the evidence base.",
        "theme_prefix": "Factor Focus",
        "comparison_title": "Comparative Factor Evidence and Interactions",
        "comparison_objective": "Compare the strongest factor themes, emphasizing interaction patterns, shared covariates, and variable-level gaps.",
    },
    "task_taxonomy": {
        "axis": "task",
        "taxonomy_title": "Task Taxonomy and Evaluation Scope",
        "taxonomy_objective": "Organize the review around task families and clarify how task definitions, metrics, and evaluation settings vary across the corpus.",
        "theme_prefix": "Task Focus",
        "comparison_title": "Comparative Task Evidence and Evaluation Tradeoffs",
        "comparison_objective": "Compare the strongest task themes, emphasizing metric heterogeneity, capability differences, and comparability limits.",
    },
    "application_scenario": {
        "axis": "application",
        "taxonomy_title": "Application Scenario Taxonomy and Transferability",
        "taxonomy_objective": "Organize the review around application contexts and explain how scenario, dataset, or deployment setting changes the interpretation of results.",
        "theme_prefix": "Scenario Focus",
        "comparison_title": "Comparative Scenario Evidence and Transferability",
        "comparison_objective": "Compare the strongest application themes, emphasizing scenario-specific assumptions and transfer limitations.",
    },
}


def build_outline(
    verified_gaps: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    llm = LLMAdapter()
    if llm.provider != "stub" and llm.base_url and llm._has_auth():
        try:
            return _build_outline_llm(llm, verified_gaps, matrix, synthesis_map=synthesis_map, organization=organization)
        except Exception:
            pass
    return _build_outline_rule_based(verified_gaps, matrix, synthesis_map=synthesis_map, organization=organization)


def _build_outline_llm(
    llm: LLMAdapter,
    verified_gaps: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    system_prompt = (
        PROMPT_PATH.read_text(encoding="utf-8")
        + "\nReturn ONLY JSON with key outline as a list of sections. Each section item must contain: section_id, title, objective, gap_inputs, matrix_row_count. Do not use section/subsections format."
        + "\nIf a recommended structure is provided, follow it and prefer the supplied synthesis themes when composing sections."
    )
    user_prompt = (
        "Create a literature review outline from the verified gaps and comparison matrix.\n\n"
        f"Verified gaps:\n{json.dumps(verified_gaps, ensure_ascii=False)}\n\n"
        f"Matrix:\n{json.dumps(matrix, ensure_ascii=False)}"
    )
    if organization:
        user_prompt += f"\n\nOrganization:\n{json.dumps(organization, ensure_ascii=False)}"
    if synthesis_map:
        user_prompt += f"\n\nSynthesis map:\n{json.dumps(synthesis_map, ensure_ascii=False)}"
    response = llm.generate_json(system_prompt, user_prompt)
    outline = normalize_outline(response.content.get("outline") if isinstance(response.content, dict) else [], verified_gaps, matrix)
    return outline or _build_outline_rule_based(verified_gaps, matrix, synthesis_map=synthesis_map, organization=organization)


def _build_outline_rule_based(
    verified_gaps: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    structure = organization.get("recommended_structure") if isinstance(organization, dict) else None
    if structure in _STRUCTURE_TEMPLATES:
        return _build_structured_outline(verified_gaps, matrix, synthesis_map or {}, structure)

    return _build_legacy_outline(verified_gaps, matrix)


def _build_legacy_outline(verified_gaps: list[dict[str, Any]], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections = []

    # Analyze matrix for structural hints
    method_families = list({row.get("method_family") for row in matrix if row.get("method_family") and row.get("method_family") != "None"})
    tasks = list({t for row in matrix if row.get("tasks") for t in row["tasks"].split("; ") if t and t != "None"})
    has_conflicts = any(
        row.get("claim_text") and row.get("claim_text") != "N/A"
        for row in matrix
    )
    n_gaps = len(verified_gaps)
    gap_severities = [g.get("severity", "medium") for g in verified_gaps]
    has_high_severity = "high" in gap_severities

    sections.append({
        "section_id": "sec-intro",
        "title": "Introduction and Research Context",
        "objective": "Establish the review's motivation, scope, and the specific problem space of automated literature review systems.",
        "gap_inputs": [],
        "matrix_row_count": 0,
    })

    if method_families:
        mf_short = "; ".join(method_families[:3])
        sections.append({
            "section_id": "sec-methods",
            "title": "Methodological Approaches",
            "objective": f"Categorize and analyze technical approaches, focusing on {mf_short}.",
            "gap_inputs": [],
            "matrix_row_count": len([r for r in matrix if r.get("method_family") in method_families]),
        })

    if tasks:
        task_short = "; ".join(tasks[:3])
        sections.append({
            "section_id": "sec-tasks",
            "title": "Task Scope and System Capabilities",
            "objective": f"Examine the range of tasks addressed, including {task_short}, and how system capabilities vary across them.",
            "gap_inputs": [],
            "matrix_row_count": len([r for r in matrix if any(t in r.get("tasks","") for t in tasks)]),
        })

    sections.append({
        "section_id": "sec-claims",
        "title": "Claim Synthesis and Cross-Paper Comparability",
        "objective": "Synthesize specific claims from the evidence matrix, assess where papers converge or conflict, and evaluate metric standardization.",
        "gap_inputs": [g.get("gap_id","") for g in verified_gaps if "metric" in g.get("gap_statement","").lower() or "compar" in g.get("gap_statement","").lower()],
        "matrix_row_count": len(matrix),
    })

    if n_gaps > 0:
        sections.append({
            "section_id": "sec-gaps",
            "title": "Research Gaps and Opportunities",
            "objective": f"Present {n_gaps} verified gap{'s' if n_gaps > 1 else ''} and explain what evidence substantiates each.",
            "gap_inputs": [g.get("gap_id","") for g in verified_gaps],
            "matrix_row_count": 0,
        })

    gap_keywords = {
        "high": "urgent research priorities",
        "medium": "important open problems",
        "low": "notable gaps",
    }
    severity_bucket = "high" if has_high_severity else "medium"
    synthesis_desc = gap_keywords.get(severity_bucket, "open problems")

    sections.append({
        "section_id": "sec-discussion",
        "title": "Discussion: Synthesis and Future Directions",
        "objective": f"Synthesize findings and prioritize {synthesis_desc} for future research.",
        "gap_inputs": [g.get("gap_id","") for g in verified_gaps if g.get("severity") == "high"],
        "matrix_row_count": 0,
    })

    sections.append({
        "section_id": "sec-conclusion",
        "title": "Conclusion",
        "objective": "Summarize key comparative findings, gap priorities, and the contribution of this review to the field.",
        "gap_inputs": [],
        "matrix_row_count": 0,
    })

    return sections


def _build_structured_outline(
    verified_gaps: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    synthesis_map: dict[str, Any],
    structure: str,
) -> list[dict[str, Any]]:
    template = _STRUCTURE_TEMPLATES[structure]
    preferred_axis = template["axis"]
    theme_pool = _resolve_theme_pool(synthesis_map, preferred_axis)
    highlighted_themes = theme_pool[:2] or _fallback_theme_pool(synthesis_map)
    theme_sections = [_theme_section(theme, template, verified_gaps) for theme in highlighted_themes[:2]]

    sections: list[dict[str, Any]] = [
        {
            "section_id": "sec-intro",
            "title": "Introduction and Review Scope",
            "objective": "Establish the review motivation, scope, and the evidence base that the selected structure will organize.",
            "gap_inputs": [],
            "matrix_row_count": 0,
        },
        {
            "section_id": f"sec-{structure.replace('_', '-')}",
            "title": template["taxonomy_title"],
            "objective": template["taxonomy_objective"],
            "gap_inputs": _theme_gap_inputs(theme_pool[:3], verified_gaps),
            "matrix_row_count": _theme_evidence_count(theme_pool[:3]),
        },
    ]

    sections.extend(theme_sections)
    sections.append(
        {
            "section_id": f"sec-{structure.replace('_', '-')}-comparison",
            "title": template["comparison_title"],
            "objective": template["comparison_objective"],
            "gap_inputs": _theme_gap_inputs(theme_pool[:3], verified_gaps),
            "matrix_row_count": _theme_evidence_count(theme_pool[:3]) or len(matrix),
        }
    )

    if verified_gaps:
        sections.append(
            {
                "section_id": "sec-gaps",
                "title": "Research Gaps and Opportunities",
                "objective": f"Present {len(verified_gaps)} verified gap{'s' if len(verified_gaps) != 1 else ''} and explain how they shape the next research agenda.",
                "gap_inputs": [gap.get("gap_id", "") for gap in verified_gaps if gap.get("gap_id")],
                "matrix_row_count": 0,
            }
        )

    sections.append(
        {
            "section_id": "sec-conclusion",
            "title": "Conclusion",
            "objective": "Summarize the selected taxonomy, the strongest synthesis themes, and the main future directions implied by the evidence base.",
            "gap_inputs": [],
            "matrix_row_count": 0,
        }
    )

    return sections


def _resolve_theme_pool(synthesis_map: dict[str, Any], preferred_axis: str) -> list[dict[str, Any]]:
    if not isinstance(synthesis_map, dict):
        return []
    theme_axes = synthesis_map.get("theme_axes", {})
    if isinstance(theme_axes, dict):
        preferred = [item for item in theme_axes.get(preferred_axis, []) if isinstance(item, dict)]
        if preferred:
            return preferred
    top_themes = synthesis_map.get("top_themes", [])
    if isinstance(top_themes, list):
        preferred = [item for item in top_themes if isinstance(item, dict) and item.get("theme_type") == preferred_axis]
        if preferred:
            return preferred
        return [item for item in top_themes if isinstance(item, dict)]
    return []


def _fallback_theme_pool(synthesis_map: dict[str, Any]) -> list[dict[str, Any]]:
    top_themes = synthesis_map.get("top_themes", [])
    return [item for item in top_themes if isinstance(item, dict)] if isinstance(top_themes, list) else []


def _theme_label(theme: dict[str, Any]) -> str:
    raw = str(theme.get("label") or theme.get("theme_id") or "Theme").strip()
    raw = raw.replace("_", " ").replace("-", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return "Theme"
    raw = raw.title()
    raw = raw.replace("Ehmi", "eHMI").replace("Av", "AV")
    return raw


def _theme_section(theme: dict[str, Any], template: dict[str, str], verified_gaps: list[dict[str, Any]]) -> dict[str, Any]:
    label = _theme_label(theme)
    evidence_count = int(theme.get("evidence_count", 0) or 0)
    gap_count = int(theme.get("gap_count", 0) or 0)
    contradiction_count = int(theme.get("contradiction_count", 0) or 0)
    section_id = _safe_section_id(str(theme.get("theme_id") or label))
    gap_inputs = _match_gap_inputs(theme, verified_gaps)
    if not gap_inputs and verified_gaps:
        gap_inputs = [gap.get("gap_id", "") for gap in verified_gaps[:2] if gap.get("gap_id")]

    return {
        "section_id": f"sec-{section_id}",
        "title": f"{template['theme_prefix']}: {label}",
        "objective": (
            f"Synthesize the {label.lower()} evidence cluster across {evidence_count} stud{'ies' if evidence_count != 1 else 'y'}, "
            f"highlighting {gap_count} gap signal{'s' if gap_count != 1 else ''} and {contradiction_count} contradiction signal{'s' if contradiction_count != 1 else ''}."
        ),
        "gap_inputs": gap_inputs,
        "matrix_row_count": evidence_count,
    }


def _match_gap_inputs(theme: dict[str, Any], verified_gaps: list[dict[str, Any]]) -> list[str]:
    label_tokens = _token_set(str(theme.get("label") or theme.get("theme_id") or ""))
    if not label_tokens:
        return []
    matched: list[str] = []
    for gap in verified_gaps:
        gap_id = gap.get("gap_id")
        if not gap_id:
            continue
        gap_text = " ".join(
            [
                str(gap.get("gap_statement", "")),
                str(gap.get("partial_evidence", "")),
                str(gap.get("insufficiency_reason", "")),
                str(gap.get("consequence", "")),
                " ".join(str(item) for item in gap.get("supporting_evidence", []) or []),
                " ".join(str(item) for item in gap.get("counter_evidence", []) or []),
            ]
        )
        if label_tokens & _token_set(gap_text):
            matched.append(gap_id)
    return matched[:3]


def _theme_gap_inputs(themes: list[dict[str, Any]], verified_gaps: list[dict[str, Any]]) -> list[str]:
    gap_ids: list[str] = []
    for theme in themes:
        gap_ids.extend(_match_gap_inputs(theme, verified_gaps))
    return _dedupe_ids(gap_ids)


def _theme_evidence_count(themes: list[dict[str, Any]]) -> int:
    return sum(int(theme.get("evidence_count", 0) or 0) for theme in themes if isinstance(theme, dict))


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z0-9]{1,}", text.lower().replace("e_hmi", "ehmi")))


def _safe_section_id(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return cleaned.strip("-") or "theme"


def _dedupe_ids(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _section_objective(title: str) -> str:
    mapping = {
        "Introduction": "Introduce the topic, motivation, and scope of the review.",
        "Methodological Landscape": "Summarize method families, task distributions, and key study categories.",
        "Comparative Evidence Matrix": "Compare representative claims, evidence, datasets, and limitations.",
        "Research Gaps and Opportunities": "Highlight verified gaps and explain why they matter for future reviews or studies.",
        "Conclusion": "Summarize the main comparative findings and open directions.",
    }
    return mapping.get(title, "Summarize this section.")
