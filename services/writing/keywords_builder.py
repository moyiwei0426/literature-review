from __future__ import annotations

import re
from collections import Counter
from typing import Any


_TOKEN_RE = re.compile(r"[a-z][a-z0-9+/-]{2,}")
_STOPWORDS = {
    "abstract",
    "analysis",
    "and",
    "appendix",
    "approach",
    "based",
    "comparison",
    "context",
    "contexts",
    "data",
    "evidence",
    "focus",
    "for",
    "framework",
    "from",
    "gap",
    "gaps",
    "literature",
    "main",
    "method",
    "methods",
    "paper",
    "papers",
    "review",
    "section",
    "sections",
    "signal",
    "signals",
    "study",
    "studies",
    "synthesis",
    "task",
    "tasks",
    "the",
    "theme",
    "themes",
    "using",
    "with",
}
_AXIS_LABELS = {
    "method_taxonomy": "method taxonomy",
    "task_taxonomy": "task taxonomy",
    "factor_taxonomy": "factor taxonomy",
    "application_scenario": "application scenario",
}


def build_keywords_artifact(
    matrix: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
    appendix: dict[str, Any] | None = None,
    abstract: dict[str, Any] | str | None = None,
    max_keywords: int = 8,
) -> dict[str, Any]:
    synthesis_map = synthesis_map or {}
    organization = organization or {}
    appendix = appendix or {}

    counter: Counter[str] = Counter()
    _add_axis_signal(counter, organization, synthesis_map)
    _add_top_theme_signal(counter, synthesis_map)
    _add_matrix_signal(counter, matrix, "method_family", weight=1.2, limit=3)
    _add_matrix_signal(counter, matrix, "tasks", weight=1.35, limit=4)
    _add_matrix_signal(counter, matrix, "datasets", weight=1.0, limit=2)
    _add_matrix_signal(counter, matrix, "metrics", weight=0.9, limit=3)
    _add_matrix_signal(counter, matrix, "research_problem", weight=1.0, limit=3)
    _add_appendix_signal(counter, appendix)
    _add_abstract_signal(counter, abstract)

    keywords = [label for label, _ in counter.most_common() if label][:max_keywords]
    return {
        "keywords": keywords,
        "keyword_count": len(keywords),
        "dominant_axis": _dominant_axis(organization, synthesis_map),
        "signals": {label: round(score, 3) for label, score in counter.most_common(max_keywords + 4)},
    }


def build_review_keywords(
    matrix: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
    appendix: dict[str, Any] | None = None,
    abstract: dict[str, Any] | str | None = None,
    *,
    max_keywords: int = 8,
) -> dict[str, Any]:
    return build_keywords_artifact(
        matrix,
        synthesis_map=synthesis_map,
        organization=organization,
        appendix=appendix,
        abstract=abstract,
        max_keywords=max_keywords,
    )


def _add_axis_signal(counter: Counter[str], organization: dict[str, Any], synthesis_map: dict[str, Any]) -> None:
    axis = _dominant_axis(organization, synthesis_map)
    if axis:
        counter[axis] += 1.8


def _dominant_axis(organization: dict[str, Any], synthesis_map: dict[str, Any]) -> str:
    structure = str(organization.get("recommended_structure") or "").strip()
    if structure in _AXIS_LABELS:
        return _AXIS_LABELS[structure]
    overview = synthesis_map.get("overview", {}) if isinstance(synthesis_map, dict) else {}
    axis = str(overview.get("dominant_axis") or "").strip()
    return axis.replace("_", " ").strip()


def _add_top_theme_signal(counter: Counter[str], synthesis_map: dict[str, Any]) -> None:
    top_themes = synthesis_map.get("top_themes", []) if isinstance(synthesis_map, dict) else []
    for theme in top_themes[:4]:
        if not isinstance(theme, dict):
            continue
        label = _normalize_phrase(theme.get("label") or theme.get("theme_id"))
        if label:
            counter[label] += 1.5


def _add_matrix_signal(
    counter: Counter[str],
    matrix: list[dict[str, Any]],
    field: str,
    weight: float,
    limit: int,
) -> None:
    field_counter: Counter[str] = Counter()
    for row in matrix:
        for value in _split_values(row.get(field)):
            field_counter[value] += 1
    for label, count in field_counter.most_common(limit):
        counter[label] += count * weight


def _add_appendix_signal(counter: Counter[str], appendix: dict[str, Any]) -> None:
    summary = appendix.get("summary", {}) if isinstance(appendix, dict) else {}
    for field in ("top_methods", "top_tasks", "top_datasets"):
        for value in summary.get(field, [])[:3] if isinstance(summary, dict) else []:
            label = _normalize_phrase(value)
            if label:
                counter[label] += 1.1
    for gap in appendix.get("gap_index", [])[:4] if isinstance(appendix, dict) else []:
        if not isinstance(gap, dict):
            continue
        for field in ("gap_statement", "research_need"):
            for phrase in _candidate_phrases(str(gap.get(field) or "")):
                counter[phrase] += 0.8


def _add_abstract_signal(counter: Counter[str], abstract: dict[str, Any] | str | None) -> None:
    if isinstance(abstract, dict):
        raw = " ".join(
            [
                str(abstract.get("text") or ""),
                " ".join(str(item) for item in abstract.get("top_themes", [])[:3]),
                " ".join(str(item) for item in abstract.get("top_methods", [])[:3]),
                " ".join(str(item) for item in abstract.get("top_tasks", [])[:3]),
            ]
        )
    else:
        raw = str(abstract or "")

    phrase_counter: Counter[str] = Counter()
    for phrase in _candidate_phrases(raw):
        phrase_counter[phrase] += 1
    for label, count in phrase_counter.most_common(6):
        counter[label] += count * 0.6


def _candidate_phrases(text: str) -> list[str]:
    normalized = " ".join(str(text or "").replace("_", " ").split()).lower()
    phrases: list[str] = []
    for segment in re.split(r"[.;:,()]", normalized):
        words = [token for token in _TOKEN_RE.findall(segment) if token not in _STOPWORDS]
        if len(words) >= 2:
            phrases.append(" ".join(words[:2]))
            if len(words) >= 3:
                phrases.append(" ".join(words[:3]))
    return [_normalize_phrase(item) for item in phrases if _normalize_phrase(item)]


def _split_values(value: Any) -> list[str]:
    if value is None:
        return []
    raw = value if isinstance(value, list) else str(value).split(";")
    values: list[str] = []
    for item in raw:
        normalized = _normalize_phrase(item)
        if normalized:
            values.append(normalized)
    return values


def _normalize_phrase(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"none", "n/a"}:
        return ""
    text = " ".join(text.replace("e_hmi", "eHMI").replace("ehmi", "eHMI").replace("_", " ").split())
    lowered = text.lower()
    if lowered in _STOPWORDS:
        return ""
    if len(lowered) <= 2:
        return ""
    return lowered
