from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any


_WORD_RE = re.compile(r"[a-z][a-z0-9_+-]{1,}")


def build_appendix_artifact(
    matrix: list[dict[str, Any]],
    profiles: list[Any] | None = None,
    verified_gaps: list[dict[str, Any]] | None = None,
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profiles = profiles or []
    verified_gaps = verified_gaps or []
    grouped_rows = _group_matrix_rows(matrix)
    evidence_table = [_build_evidence_row(paper_id, rows, profiles, verified_gaps) for paper_id, rows in grouped_rows.items()]
    evidence_table.sort(key=lambda row: (row.get("year") is None, -(row.get("year") or 0), row.get("paper_id") or ""))

    appendix = {
        "title": "Appendix",
        "summary": _build_summary(matrix, evidence_table, verified_gaps, synthesis_map, organization),
        "evidence_table": evidence_table,
        "gap_index": _build_gap_index(verified_gaps, matrix),
    }
    return appendix


def _build_summary(
    matrix: list[dict[str, Any]],
    evidence_table: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None,
    organization: dict[str, Any] | None,
) -> dict[str, Any]:
    paper_count = len(evidence_table)
    row_count = len(matrix)
    top_methods = _top_values(matrix, "method_family")
    top_tasks = _top_values(matrix, "tasks")
    top_datasets = _top_values(matrix, "datasets")
    return {
        "paper_count": paper_count,
        "row_count": row_count,
        "verified_gap_count": len(verified_gaps),
        "dominant_axis": _dominant_axis(synthesis_map, organization),
        "top_methods": top_methods[:3],
        "top_tasks": top_tasks[:3],
        "top_datasets": top_datasets[:3],
        "narrative": _summary_narrative(paper_count, row_count, top_methods, top_tasks, verified_gaps),
    }


def _summary_narrative(
    paper_count: int,
    row_count: int,
    top_methods: list[str],
    top_tasks: list[str],
    verified_gaps: list[dict[str, Any]],
) -> list[str]:
    narrative = [
        f"The appendix records {paper_count} papers and {row_count} matrix rows used to generate the review synthesis.",
        f"The most visible methodological families are {', '.join(top_methods[:3]) or 'not strongly differentiated'}, while recurring tasks include {', '.join(top_tasks[:3]) or 'not strongly differentiated'}."
    ]
    if verified_gaps:
        narrative.append(
            f"Verified gaps are indexed separately so readers can trace which evidence clusters remain unresolved before moving to the main conclusion."
        )
    return narrative


def _build_gap_index(
    verified_gaps: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matrix_text = _matrix_tokens(matrix)
    gap_index: list[dict[str, Any]] = []
    for gap in verified_gaps:
        statement = str(gap.get("gap_statement") or "").strip()
        if not statement:
            continue
        tokens = _tokenize(statement)
        supporting_rows = [row.get("paper_id") for row in matrix if tokens & matrix_text.get(row.get("paper_id"), set())]
        gap_index.append(
            {
                "gap_id": gap.get("gap_id"),
                "gap_statement": statement,
                "severity": gap.get("severity"),
                "supporting_paper_ids": [paper_id for paper_id in supporting_rows if paper_id],
                "research_need": gap.get("research_need") or gap.get("resolution_needed"),
            }
        )
    return gap_index


def _build_evidence_row(
    paper_id: str,
    rows: list[dict[str, Any]],
    profiles: list[Any],
    verified_gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    profile = _find_profile(paper_id, profiles)
    titles = _unique(str(row.get("title") or _profile_value(profile, "title", "") or "").strip() for row in rows)
    year = _first_non_null(row.get("year") for row in rows) or _profile_value(profile, "year")
    venue = _first_non_null(row.get("venue") for row in rows) or _profile_value(profile, "venue")
    authors = _first_non_empty([
        _split_values(row.get("authors"))
        for row in rows
    ]) or [author for author in (_profile_value(profile, "authors", []) or []) if author]
    claims = _unique(str(row.get("claim_text") or "").strip() for row in rows if row.get("claim_text"))
    methods = _unique(_split_values(row.get("method_family")) for row in rows)
    tasks = _unique(_split_values(row.get("tasks")) for row in rows)
    datasets = _unique(_split_values(row.get("datasets")) for row in rows)
    metrics = _unique(_split_values(row.get("metrics")) for row in rows)
    gap_matches = _matching_gaps(rows, verified_gaps)
    return {
        "paper_id": paper_id,
        "title": titles[0] if titles else paper_id,
        "year": year,
        "venue": venue,
        "authors": authors,
        "methods": methods,
        "tasks": tasks,
        "datasets": datasets,
        "metrics": metrics,
        "claim_count": len(claims),
        "claims": claims[:3],
        "gap_matches": gap_matches,
        "evidence_chunk_ids": _unique(_split_values(row.get("evidence_chunk_ids")) for row in rows if row.get("evidence_chunk_ids")),
    }


def _matching_gaps(rows: list[dict[str, Any]], verified_gaps: list[dict[str, Any]]) -> list[str]:
    row_tokens = _matrix_tokens_from_rows(rows)
    matched: list[str] = []
    for gap in verified_gaps:
        statement = str(gap.get("gap_statement") or "").strip()
        if not statement:
            continue
        if row_tokens & _tokenize(statement):
            matched.append(str(gap.get("gap_id") or statement))
    return matched[:5]


def _group_matrix_rows(matrix: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in matrix:
        paper_id = str(row.get("paper_id") or "").strip()
        if paper_id:
            grouped[paper_id].append(row)
    return dict(grouped)


def _dominant_axis(synthesis_map: dict[str, Any] | None, organization: dict[str, Any] | None) -> str:
    if isinstance(organization, dict):
        structure = str(organization.get("recommended_structure") or "").strip()
        mapping = {
            "method_taxonomy": "method",
            "task_taxonomy": "task",
            "factor_taxonomy": "factor",
            "application_scenario": "application",
        }
        if structure in mapping:
            return mapping[structure]
    if isinstance(synthesis_map, dict):
        overview = synthesis_map.get("overview", {})
        if isinstance(overview, dict):
            axis = str(overview.get("dominant_axis") or "").strip()
            if axis:
                return axis.replace("_", " ")
    return "evidence clusters"


def _top_values(matrix: list[dict[str, Any]], field: str) -> list[str]:
    counter: Counter[str] = Counter()
    for row in matrix:
        for value in _split_values(row.get(field)):
            counter[value] += 1
    return [item for item, _ in counter.most_common()]


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


def _tokenize(value: Any) -> set[str]:
    return set(_WORD_RE.findall(str(value or "").lower().replace("e_hmi", "ehmi")))


def _matrix_tokens(matrix: list[dict[str, Any]]) -> dict[str, set[str]]:
    tokens: dict[str, set[str]] = defaultdict(set)
    for row in matrix:
        paper_id = str(row.get("paper_id") or "").strip()
        if paper_id:
            tokens[paper_id].update(_matrix_tokens_from_rows([row]))
    return dict(tokens)


def _matrix_tokens_from_rows(rows: list[dict[str, Any]]) -> set[str]:
    tokens: set[str] = set()
    for row in rows:
        for field in ("title", "claim_text", "research_problem", "method_family", "tasks", "datasets", "metrics", "limitations", "notes"):
            tokens |= _tokenize(row.get(field))
    return tokens


def _find_profile(paper_id: str, profiles: list[Any]) -> Any | None:
    for profile in profiles:
        if isinstance(profile, dict):
            if str(profile.get("paper_id") or "").strip() == paper_id:
                return profile
        elif getattr(profile, "paper_id", None) == paper_id:
            return profile
    return None


def _profile_value(profile: Any | None, key: str, default: Any = None) -> Any:
    if isinstance(profile, dict):
        return profile.get(key, default)
    if profile is None:
        return default
    return getattr(profile, key, default)


def _first_non_null(values: Any) -> Any:
    for value in values:
        if value not in (None, "", []):
            return value
    return None


def _first_non_empty(values: list[Any]) -> list[str]:
    for value in values:
        if value:
            return value
    return []


def _normalize(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"none", "n/a"}:
        return ""
    text = " ".join(text.replace("e_hmi", "eHMI").replace("ehmi", "eHMI").split("_"))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _unique(values: Any) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if isinstance(value, list):
            items = value
        else:
            items = _split_values(value) if isinstance(value, str) and ";" in value else [value]
        for item in items:
            text = _normalize(item)
            if text and text.lower() not in seen:
                seen.add(text.lower())
                out.append(text)
    return out
