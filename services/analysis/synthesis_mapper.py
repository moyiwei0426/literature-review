from __future__ import annotations

import re
from collections import Counter
from typing import Any


_WORD_RE = re.compile(r"[a-z][a-z0-9_+-]{1,}")

_FACTOR_GROUPS = {
    "demographic_factors": {"gender", "female", "male", "age", "elderly", "older", "young", "child", "adult"},
    "temporal_factors": {"time", "timing", "delay", "waiting", "duration", "green", "red", "phase"},
    "traffic_factors": {"traffic", "vehicle", "vehicles", "volume", "speed", "flow", "lane", "lanes"},
    "behavioral_factors": {"risk", "violation", "violations", "hurry", "attention", "distraction", "group", "companion"},
    "design_factors": {"signal", "signals", "crosswalk", "facility", "infrastructure", "median", "marking", "ehmi", "av"},
    "environmental_factors": {"weather", "lighting", "night", "day", "visibility", "environment"},
}


def _tokenize(value: Any) -> set[str]:
    text = str(value or "").lower().replace("e_hmi", "ehmi")
    return set(_WORD_RE.findall(text))


def _split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value).split(";")
    values = []
    for item in raw:
        cleaned = str(item).strip()
        if cleaned and cleaned.lower() not in {"none", "n/a"}:
            values.append(cleaned)
    return values


def _count_axis(matrix: list[dict[str, Any]], field: str) -> Counter:
    counter: Counter[str] = Counter()
    for row in matrix:
        counter.update(_split_values(row.get(field)))
    return counter


def _count_factor_signals(matrix: list[dict[str, Any]]) -> Counter:
    counter: Counter[str] = Counter()
    for row in matrix:
        tokens = _tokenize(" ".join([
            str(row.get("claim_text", "")),
            str(row.get("research_problem", "")),
            str(row.get("limitations", "")),
            str(row.get("notes", "")),
        ]))
        for label, keywords in _FACTOR_GROUPS.items():
            if tokens & keywords:
                counter[label] += 1
    return counter


def _theme_gap_count(label: str, gap_pool: list[dict[str, Any]]) -> int:
    label_tokens = _tokenize(label)
    if not label_tokens:
        return 0
    matches = 0
    for gap in gap_pool:
        gap_text = " ".join(
            [str(gap.get("gap_statement", ""))]
            + [str(item) for item in gap.get("supporting_evidence", [])]
            + [str(item) for item in gap.get("counter_evidence", [])]
        )
        if label_tokens & _tokenize(gap_text):
            matches += 1
    return matches


def _theme_contradiction_count(theme_type: str, label: str, contradiction: dict[str, Any]) -> int:
    contradictions = contradiction.get("contradictions", []) if isinstance(contradiction, dict) else []
    if theme_type != "task":
        return contradiction.get("contradiction_count", 0) if contradictions else 0
    label_tokens = _tokenize(label)
    count = 0
    for item in contradictions:
        tokens = _tokenize(" ".join([str(item.get("task", ""))] + [str(x) for x in item.get("related_tasks", [])]))
        if label_tokens & tokens:
            count += 1
    return count


def _build_theme_entries(
    theme_type: str,
    counts: Counter,
    contradiction: dict[str, Any],
    gap_pool: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for label, count in counts.items():
        gap_count = _theme_gap_count(label, gap_pool)
        contradiction_count = _theme_contradiction_count(theme_type, label, contradiction)
        priority = round(count + gap_count * 1.5 + contradiction_count * 1.2, 3)
        entries.append(
            {
                "theme_id": f"{theme_type}:{label.lower().replace(' ', '_')}",
                "theme_type": theme_type,
                "label": label,
                "evidence_count": count,
                "gap_count": gap_count,
                "contradiction_count": contradiction_count,
                "priority_score": priority,
                "synthesis_note": (
                    f"{label} appears in {count} evidence unit(s), with {gap_count} gap signal(s) "
                    f"and {contradiction_count} contradiction signal(s)."
                ),
            }
        )
    entries.sort(key=lambda item: (-item["priority_score"], -item["evidence_count"], item["label"].lower()))
    return entries


def build_synthesis_map(
    matrix: list[dict[str, Any]],
    coverage: dict[str, Any],
    contradiction: dict[str, Any],
    verified_gaps: list[dict[str, Any]] | None = None,
    scored_gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    verified_gaps = verified_gaps or []
    scored_gaps = scored_gaps or []
    gap_pool = list(verified_gaps) + list(scored_gaps)

    method_counts = _count_axis(matrix, "method_family")
    task_counts = _count_axis(matrix, "tasks")
    factor_counts = _count_factor_signals(matrix)
    dataset_counts = _count_axis(matrix, "datasets")

    method_themes = _build_theme_entries("method", method_counts, contradiction, gap_pool)
    task_themes = _build_theme_entries("task", task_counts, contradiction, gap_pool)
    factor_themes = _build_theme_entries("factor", factor_counts, contradiction, gap_pool)
    application_themes = _build_theme_entries("application", dataset_counts, contradiction, gap_pool)

    axis_sizes = {
        "method": len(method_themes),
        "task": len(task_themes),
        "factor": len(factor_themes),
        "application": len(application_themes),
    }
    dominant_axis = max(axis_sizes, key=lambda key: (axis_sizes[key], sum(t["evidence_count"] for t in {
        "method": method_themes,
        "task": task_themes,
        "factor": factor_themes,
        "application": application_themes,
    }[key])))

    contradiction_count = contradiction.get("contradiction_count", 0) if isinstance(contradiction, dict) else 0
    average_gap_score = 0.0
    if scored_gaps:
        average_gap_score = round(
            sum(float(gap.get("review_worthiness", 0.0) or 0.0) for gap in scored_gaps) / len(scored_gaps),
            3,
        )

    top_themes = sorted(
        method_themes[:3] + task_themes[:3] + factor_themes[:3] + application_themes[:3],
        key=lambda item: (-item["priority_score"], item["theme_type"], item["label"].lower()),
    )[:8]

    return {
        "overview": {
            "paper_count": coverage.get("paper_count", 0),
            "matrix_row_count": len(matrix),
            "verified_gap_count": len(verified_gaps),
            "scored_gap_count": len(scored_gaps),
            "rejected_gap_count": sum(1 for gap in verified_gaps if gap.get("status") == "rejected"),
            "contradiction_count": contradiction_count,
            "dominant_axis": dominant_axis,
            "average_gap_score": average_gap_score,
            "theme_counts": axis_sizes,
            "coverage_themes": list(coverage.get("themes", [])),
        },
        "theme_axes": {
            "method": method_themes,
            "task": task_themes,
            "factor": factor_themes,
            "application": application_themes,
        },
        "top_themes": top_themes,
    }
