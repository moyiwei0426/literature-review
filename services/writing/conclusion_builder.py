from __future__ import annotations

import re
from typing import Any


_WORD_RE = re.compile(r"[a-z][a-z0-9_+-]{1,}")


def build_conclusion_artifact(
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paper_count = len({str(row.get("paper_id") or "").strip() for row in matrix if row.get("paper_id")})
    signals = _collect_signals(matrix, verified_gaps, synthesis_map, organization)
    stable_conclusions = _stable_conclusions(signals, paper_count)
    unresolved_tensions = _unresolved_tensions(signals, verified_gaps)
    research_priorities = _research_priorities(signals, verified_gaps)

    text = _render_text(signals, stable_conclusions, unresolved_tensions, research_priorities, paper_count)
    return {
        "section_id": "sec-conclusion",
        "title": "Conclusion",
        "paper_count": paper_count,
        "signals": signals,
        "stable_conclusions": stable_conclusions,
        "unresolved_tensions": unresolved_tensions,
        "research_priorities": research_priorities,
        "text": text,
    }


def build_conclusion_text(
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> str:
    return build_conclusion_artifact(
        matrix,
        verified_gaps,
        synthesis_map=synthesis_map,
        organization=organization,
    )["text"]


def _collect_signals(
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
) -> dict[str, Any]:
    theme_axes = synthesis_map.get("theme_axes", {}) if isinstance(synthesis_map, dict) else {}
    top_themes = synthesis_map.get("top_themes", []) if isinstance(synthesis_map, dict) else []
    overview = synthesis_map.get("overview", {}) if isinstance(synthesis_map, dict) else {}

    dominant_axis = _dominant_axis(organization, overview)
    top_theme_labels = _top_theme_labels(top_themes, dominant_axis)
    method_families, tasks, datasets, metrics = _matrix_axes(matrix)
    gap_statements = [str(gap.get("gap_statement") or "").strip() for gap in verified_gaps if str(gap.get("gap_statement") or "").strip()]
    research_needs = [
        str(gap.get("research_need") or gap.get("resolution_needed") or "").strip()
        for gap in verified_gaps
        if str(gap.get("research_need") or gap.get("resolution_needed") or "").strip()
    ]
    return {
        "paper_count": len({str(row.get("paper_id") or "").strip() for row in matrix if row.get("paper_id")}),
        "dominant_axis": dominant_axis,
        "top_themes": top_theme_labels,
        "method_families": method_families,
        "tasks": tasks,
        "datasets": datasets,
        "metrics": metrics,
        "gap_statements": gap_statements,
        "research_needs": research_needs,
        "theme_axes": theme_axes if isinstance(theme_axes, dict) else {},
        "top_theme_count": len(top_theme_labels),
        "verified_gap_count": len(verified_gaps),
    }


def _stable_conclusions(signals: dict[str, Any], paper_count: int) -> list[str]:
    axis = signals.get("dominant_axis") or "evidence clusters"
    themes = signals.get("top_themes") or []
    methods = signals.get("method_families") or []
    metrics = signals.get("metrics") or []
    tasks = signals.get("tasks") or []
    task_tail = f" such as {', '.join(tasks[:2])}" if tasks else ""
    metric_tail = f" and {', '.join(metrics[:2])}" if metrics else ""

    conclusion_1 = (
        f"Across {paper_count} papers, the evidence is most coherently organized around {axis} "
        f"rather than any single method, and the strongest clusters are {', '.join(themes[:3]) or 'still concentrated in a few recurring themes'}."
    )
    conclusion_2 = (
        f"Methodological diversity is real, but the review still shows recurring families such as {', '.join(methods[:3]) or 'multiple methodological families'}, "
        f"which suggests the field is comparing similar problems with different operational choices."
    )
    conclusion_3 = (
        f"Reporting remains uneven across tasks and metrics{task_tail}{metric_tail}, which limits direct comparison across studies."
    )
    return [conclusion_1, conclusion_2, conclusion_3]


def _unresolved_tensions(signals: dict[str, Any], verified_gaps: list[dict[str, Any]]) -> list[str]:
    gaps = signals.get("gap_statements") or []
    needs = signals.get("research_needs") or []
    tensions: list[str] = []

    if gaps:
        tensions.append(f"One unresolved tension is that {gaps[0]}.")
    if len(gaps) > 1:
        tensions.append(f"A second tension is that {gaps[1]}.")
    elif needs:
        tensions.append(f"A second tension is that current studies still need {needs[0]}.")
    else:
        tensions.append("A second tension is that cross-study comparison still depends on inconsistent reporting conventions.")

    if len(gaps) > 2:
        tensions.append(f"A further tension is that {gaps[2]}.")
    elif len(verified_gaps) > 2:
        tensions.append("A further tension is that the remaining verified gaps are not yet resolved by the available evidence base.")

    return tensions[:3]


def _research_priorities(signals: dict[str, Any], verified_gaps: list[dict[str, Any]]) -> list[str]:
    priorities: list[str] = []
    needs = signals.get("research_needs") or []
    gaps = signals.get("gap_statements") or []

    for item in needs[:3]:
        priorities.append(f"Priority should be given to {item}.")
    for item in gaps[:3]:
        if len(priorities) >= 3:
            break
        priorities.append(f"Future work should directly target {item}.")
    if not priorities:
        priorities.append("Future work should prioritize standardized reporting and more explicit cross-study comparison.")
    if len(priorities) < 2 and verified_gaps:
        priorities.append("A second priority is to close the strongest verified gaps before drawing broader generalizations.")
    if len(priorities) < 3:
        priorities.append("A third priority is to align methods, metrics, and context descriptors so the literature can be synthesized more defensibly.")
    return priorities[:3]


def _render_text(
    signals: dict[str, Any],
    stable_conclusions: list[str],
    unresolved_tensions: list[str],
    research_priorities: list[str],
    paper_count: int,
) -> str:
    axis = signals.get("dominant_axis") or "the main evidence clusters"
    lead = (
        f"The field-level picture across {paper_count} papers is that {axis} provide the clearest organizing lens, "
        f"with the strongest signals concentrated in {', '.join(signals.get('top_themes') or []) or 'a small number of recurring clusters'}."
    )
    return " ".join(
        [
            lead,
            "Stable conclusions: " + " ".join(stable_conclusions[:3]),
            "Unresolved tensions: " + " ".join(unresolved_tensions[:3]),
            "Research priorities: " + " ".join(research_priorities[:3]),
        ]
    )


def _dominant_axis(organization: dict[str, Any] | None, overview: dict[str, Any] | None) -> str:
    if isinstance(organization, dict):
        structure = str(organization.get("recommended_structure") or "").strip()
        mapping = {
            "method_taxonomy": "methodological variation",
            "task_taxonomy": "task structure",
            "factor_taxonomy": "factor structure",
            "application_scenario": "application context",
        }
        if structure in mapping:
            return mapping[structure]
    if isinstance(overview, dict):
        axis = str(overview.get("dominant_axis") or "").strip()
        if axis:
            return axis.replace("_", " ")
    return "the dominant evidence clusters"


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
    return labels[:3]


def _matrix_axes(matrix: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str], list[str]]:
    methods = _dedupe(_split_values(row.get("method_family")) for row in matrix)
    tasks = _dedupe(_split_values(row.get("tasks")) for row in matrix)
    datasets = _dedupe(_split_values(row.get("datasets")) for row in matrix)
    metrics = _dedupe(_split_values(row.get("metrics")) for row in matrix)
    return methods, tasks, datasets, metrics


def _split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value).split(";")
    values = []
    for item in raw:
        cleaned = _normalize(str(item).strip())
        if cleaned:
            values.append(cleaned)
    return values


def _dedupe(seqs: list[list[str]]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for seq in seqs:
        for item in seq:
            key = item.lower()
            if key and key not in seen:
                seen.add(key)
                out.append(item)
    return out


def _normalize(text: str) -> str:
    if not text or text.lower() in {"none", "n/a"}:
        return ""
    text = text.replace("e_hmi", "eHMI").replace("ehmi", "eHMI")
    text = " ".join(text.split("_"))
    text = re.sub(r"\s+", " ", text)
    return text.strip()
