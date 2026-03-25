from __future__ import annotations

import re
from collections import Counter
from typing import Any


def build_review_abstract(
    title: str,
    matrix: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
    verified_gaps: list[dict[str, Any]] | None = None,
    conclusion: dict[str, Any] | None = None,
    appendix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verified_gaps = verified_gaps or []
    synthesis_map = synthesis_map or {}
    organization = organization or {}
    conclusion = conclusion or {}
    appendix = appendix or {}

    paper_ids = {str(row.get("paper_id") or "").strip() for row in matrix if row.get("paper_id")}
    paper_count = len(paper_ids)
    row_count = len(matrix)
    dominant_axis = _dominant_axis(synthesis_map, organization)
    top_methods = _top_values(matrix, "method_family")
    top_tasks = _top_values(matrix, "tasks")
    top_themes = _top_theme_labels(synthesis_map.get("top_themes", []), dominant_axis)
    gap_statements = [str(gap.get("gap_statement") or "").strip() for gap in verified_gaps if str(gap.get("gap_statement") or "").strip()]

    stable = conclusion.get("stable_conclusions") if isinstance(conclusion, dict) else []
    tensions = conclusion.get("unresolved_tensions") if isinstance(conclusion, dict) else []
    priorities = conclusion.get("research_priorities") if isinstance(conclusion, dict) else []
    appendix_summary = appendix.get("summary", {}) if isinstance(appendix, dict) else {}
    appendix_papers = appendix_summary.get("paper_count") if isinstance(appendix_summary, dict) else None
    appendix_rows = appendix_summary.get("row_count") if isinstance(appendix_summary, dict) else None

    sentences = [
        (
            f"{title} synthesizes {paper_count or appendix_papers or 0} papers"
            f" across {row_count or appendix_rows or 0} evidence rows"
            f" using {dominant_axis} as the main organizing lens."
        )
    ]
    if top_themes or top_methods or top_tasks:
        themes = ", ".join(top_themes[:2]) or "recurring evidence clusters"
        methods = ", ".join(top_methods[:2]) or "mixed methods"
        tasks = ", ".join(top_tasks[:2]) or "shared review tasks"
        sentences.append(
            f"The synthesis is concentrated in {themes}, with recurring methods such as {methods} and task coverage centered on {tasks}."
        )
    if stable:
        sentences.append(_trim_sentence(str(stable[0])))
    elif tensions:
        sentences.append(_trim_sentence(str(tensions[0])))
    if gap_statements:
        lead_gap = _trim_sentence(gap_statements[0], lower_first=True)
        sentences.append(
            f"The main unresolved gap is that {lead_gap}, which keeps broader comparison and transfer claims provisional."
        )
    elif priorities:
        sentences.append(_trim_sentence(str(priorities[0])))

    text = " ".join(sentence for sentence in sentences if sentence).strip()
    return {
        "title": title,
        "paper_count": paper_count,
        "matrix_row_count": row_count,
        "dominant_axis": dominant_axis,
        "top_themes": top_themes[:3],
        "top_methods": top_methods[:3],
        "top_tasks": top_tasks[:3],
        "verified_gap_count": len(verified_gaps),
        "text": text,
    }


def _dominant_axis(synthesis_map: dict[str, Any], organization: dict[str, Any]) -> str:
    structure = str(organization.get("recommended_structure") or "").strip()
    mapping = {
        "method_taxonomy": "methodological variation",
        "task_taxonomy": "task structure",
        "factor_taxonomy": "factor structure",
        "application_scenario": "application context",
    }
    if structure in mapping:
        return mapping[structure]
    overview = synthesis_map.get("overview", {}) if isinstance(synthesis_map, dict) else {}
    axis = str(overview.get("dominant_axis") or "").strip() if isinstance(overview, dict) else ""
    return axis.replace("_", " ") if axis else "evidence structure"


def _top_theme_labels(top_themes: list[dict[str, Any]], dominant_axis: str) -> list[str]:
    labels: list[str] = []
    for theme in top_themes:
        if not isinstance(theme, dict):
            continue
        label = str(theme.get("label") or theme.get("theme_id") or "").strip()
        if label:
            labels.append(label.replace("_", " "))
    if not labels and dominant_axis:
        labels.append(dominant_axis)
    return labels


def _top_values(matrix: list[dict[str, Any]], field: str) -> list[str]:
    counter: Counter[str] = Counter()
    for row in matrix:
        for value in _split_values(row.get(field)):
            counter[value] += 1
    return [item for item, _ in counter.most_common()]


def _split_values(value: Any) -> list[str]:
    if value is None:
        return []
    raw = value if isinstance(value, list) else str(value).split(";")
    values: list[str] = []
    for item in raw:
        cleaned = _normalize(str(item).strip())
        if cleaned:
            values.append(cleaned)
    return values


def _normalize(text: str) -> str:
    if not text or text.lower() in {"none", "n/a"}:
        return ""
    text = text.replace("e_hmi", "eHMI").replace("ehmi", "eHMI")
    text = " ".join(text.split("_"))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _trim_sentence(text: str, lower_first: bool = False) -> str:
    sentence = " ".join(str(text or "").split()).strip()
    if not sentence:
        return ""
    sentence = sentence[:-1] if sentence.endswith(".") else sentence
    if lower_first and sentence:
        sentence = sentence[0].lower() + sentence[1:]
    return sentence + "."
