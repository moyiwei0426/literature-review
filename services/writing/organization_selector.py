from __future__ import annotations

from typing import Any


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def select_organization(synthesis_map: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, Any]:
    overview = synthesis_map.get("overview", {}) if isinstance(synthesis_map, dict) else {}
    theme_axes = synthesis_map.get("theme_axes", {}) if isinstance(synthesis_map, dict) else {}

    method_count = len(theme_axes.get("method", []))
    task_count = len(theme_axes.get("task", []))
    factor_count = len(theme_axes.get("factor", []))
    application_count = len(theme_axes.get("application", []))
    contradiction_count = int(overview.get("contradiction_count", 0) or 0)
    average_gap_score = float(overview.get("average_gap_score", 0.0) or 0.0)
    matrix_rows = max(1, len(matrix))

    scores = {
        "method_taxonomy": round(
            method_count * 1.3
            + _safe_div(contradiction_count, matrix_rows) * 8
            + (0.6 if overview.get("dominant_axis") == "method" else 0.0),
            3,
        ),
        "task_taxonomy": round(
            task_count * 1.3
            + (0.6 if overview.get("dominant_axis") == "task" else 0.0)
            + average_gap_score,
            3,
        ),
        "factor_taxonomy": round(
            factor_count * 1.4
            + _safe_div(sum(item.get("evidence_count", 0) for item in theme_axes.get("factor", [])), matrix_rows) * 2
            + (0.6 if overview.get("dominant_axis") == "factor" else 0.0),
            3,
        ),
        "application_scenario": round(
            application_count * 1.2
            + _safe_div(overview.get("paper_count", 0), max(1, application_count)) * 0.4
            + (0.6 if overview.get("dominant_axis") == "application" else 0.0),
            3,
        ),
    }

    recommended = max(scores, key=lambda key: (scores[key], key))
    rationale_map = {
        "method_taxonomy": "Method diversity or contradiction pressure is strong enough to foreground methodological comparison.",
        "task_taxonomy": "Task coverage is broad enough that organizing by task makes the synthesis easier to follow.",
        "factor_taxonomy": "Cross-paper factor signals are dense enough to support a variable-centered narrative.",
        "application_scenario": "Scenario or dataset clusters are strong enough to anchor the review around application contexts.",
    }

    return {
        "recommended_structure": recommended,
        "scores": scores,
        "rationale": rationale_map[recommended],
        "signals": {
            "method_theme_count": method_count,
            "task_theme_count": task_count,
            "factor_theme_count": factor_count,
            "application_theme_count": application_count,
            "contradiction_count": contradiction_count,
            "average_gap_score": average_gap_score,
        },
    }
