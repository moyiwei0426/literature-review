from __future__ import annotations

import re
from typing import Any


_STRUCTURE_AXIS = {
    "method_taxonomy": "method",
    "task_taxonomy": "task",
    "factor_taxonomy": "factor",
    "application_scenario": "application",
}

_THEME_PREFIXES = (
    "Method Focus:",
    "Task Focus:",
    "Factor Focus:",
    "Scenario Focus:",
)


def build_section_plans(
    outline: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any] | None = None,
    organization: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    synthesis_map = synthesis_map or {}
    organization = organization or {}

    plans: list[dict[str, Any]] = []
    for item in outline:
        if not isinstance(item, dict):
            continue
        plans.append(
            _build_section_plan(
                item,
                matrix,
                verified_gaps,
                synthesis_map=synthesis_map,
                organization=organization,
            )
        )
    return plans


def _build_section_plan(
    item: dict[str, Any],
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]],
    synthesis_map: dict[str, Any],
    organization: dict[str, Any],
) -> dict[str, Any]:
    structure = _recommended_structure(organization)
    axis = _STRUCTURE_AXIS.get(structure or "")
    theme_refs = _theme_refs_for_section(item, synthesis_map, axis)
    gap_refs = _gap_refs_for_section(item, verified_gaps, theme_refs)
    matched_rows = _rows_for_section(item, matrix, theme_refs)
    matrix_signals = _matrix_signals(matched_rows)

    return {
        "section_id": item.get("section_id", ""),
        "title": item.get("title", ""),
        "objective": item.get("objective", ""),
        "section_goal": _section_goal(item, theme_refs, gap_refs, matrix_signals),
        "structure": structure,
        "dominant_axis": axis or str((synthesis_map.get("overview") or {}).get("dominant_axis") or ""),
        "theme_refs": theme_refs,
        "gap_refs": gap_refs,
        "matrix_signals": matrix_signals,
        "argument_moves": _argument_moves(item, theme_refs, gap_refs, matched_rows, matrix_signals),
    }


def _recommended_structure(organization: dict[str, Any] | None) -> str | None:
    if isinstance(organization, dict):
        value = organization.get("recommended_structure")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _token_set(value: Any) -> set[str]:
    return set(re.findall(r"[a-z][a-z0-9_+-]{1,}", str(value or "").lower().replace("e_hmi", "ehmi")))


def _humanize(value: str) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.title()
    return text.replace("Ehmi", "eHMI").replace("Av", "AV")


def _dedupe_dicts(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        value = str(item.get(key) or "")
        if value and value not in seen:
            seen.add(value)
            out.append(item)
    return out


def _theme_refs_for_section(
    item: dict[str, Any],
    synthesis_map: dict[str, Any],
    axis: str | None,
) -> list[dict[str, Any]]:
    if not isinstance(synthesis_map, dict):
        return []

    title = str(item.get("title", ""))
    title_tokens = _token_set(f"{title} {item.get('objective', '')}")
    theme_axes = synthesis_map.get("theme_axes", {})
    top_themes = synthesis_map.get("top_themes", [])
    pool: list[dict[str, Any]] = []
    if isinstance(theme_axes, dict) and axis and isinstance(theme_axes.get(axis), list):
        pool.extend(theme for theme in theme_axes[axis] if isinstance(theme, dict))
    if isinstance(top_themes, list):
        pool.extend(theme for theme in top_themes if isinstance(theme, dict))

    label = title.split(":", 1)[1].strip() if any(title.startswith(prefix) for prefix in _THEME_PREFIXES) else ""
    if label:
        exact = [theme for theme in pool if str(theme.get("label") or "").lower() == label.lower()]
        if exact:
            return [_theme_ref(theme) for theme in exact[:2]]

    scored: list[tuple[float, dict[str, Any]]] = []
    for theme in pool:
        theme_tokens = _token_set(theme.get("label") or theme.get("theme_id") or "")
        if not theme_tokens:
            continue
        overlap = len(title_tokens & theme_tokens)
        priority = float(theme.get("priority_score", 0.0) or 0.0)
        score = overlap * 10 + priority
        if score > 0:
            scored.append((score, theme))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    theme_refs = [_theme_ref(theme) for _, theme in scored[:3]]
    if theme_refs:
        return _dedupe_dicts(theme_refs, "theme_id")

    fallback = []
    if isinstance(top_themes, list):
        fallback = [_theme_ref(theme) for theme in top_themes[:2] if isinstance(theme, dict)]
    return _dedupe_dicts(fallback, "theme_id")


def _theme_ref(theme: dict[str, Any]) -> dict[str, Any]:
    return {
        "theme_id": str(theme.get("theme_id") or ""),
        "label": _humanize(str(theme.get("label") or theme.get("theme_id") or "Theme")),
        "theme_type": str(theme.get("theme_type") or ""),
        "evidence_count": int(theme.get("evidence_count", 0) or 0),
        "gap_count": int(theme.get("gap_count", 0) or 0),
        "contradiction_count": int(theme.get("contradiction_count", 0) or 0),
        "priority_score": float(theme.get("priority_score", 0.0) or 0.0),
        "synthesis_note": str(theme.get("synthesis_note") or "").strip(),
    }


def _gap_refs_for_section(
    item: dict[str, Any],
    verified_gaps: list[dict[str, Any]],
    theme_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {str(gap.get("gap_id") or ""): gap for gap in verified_gaps if gap.get("gap_id")}
    gap_refs: list[dict[str, Any]] = []

    for gap_id in item.get("gap_inputs", []) or []:
        gap = by_id.get(str(gap_id))
        if gap:
            gap_refs.append(_gap_ref(gap))

    section_tokens = _token_set(f"{item.get('title', '')} {item.get('objective', '')}")
    theme_tokens = set().union(*(_token_set(theme.get("label", "")) for theme in theme_refs)) if theme_refs else set()
    target_tokens = section_tokens | theme_tokens
    for gap in verified_gaps:
        gap_id = str(gap.get("gap_id") or "")
        if not gap_id or gap_id in {ref["gap_id"] for ref in gap_refs}:
            continue
        gap_text = " ".join(
            [
                str(gap.get("gap_statement", "")),
                str(gap.get("why_insufficient", "")),
                str(gap.get("research_need", "")),
                str(gap.get("practical_consequence", "")),
            ]
        )
        if target_tokens and target_tokens & _token_set(gap_text):
            gap_refs.append(_gap_ref(gap))

    return _dedupe_dicts(gap_refs[:3], "gap_id")


def _gap_ref(gap: dict[str, Any]) -> dict[str, Any]:
    return {
        "gap_id": str(gap.get("gap_id") or ""),
        "gap_statement": str(gap.get("gap_statement") or "").strip(),
        "severity": str(gap.get("severity") or gap.get("status") or "medium"),
        "research_need": str(gap.get("research_need") or "").strip(),
    }


def _rows_for_section(
    item: dict[str, Any],
    matrix: list[dict[str, Any]],
    theme_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cues = _token_set(f"{item.get('title', '')} {item.get('objective', '')}")
    for theme in theme_refs:
        cues |= _token_set(theme.get("label"))

    scored: list[tuple[int, dict[str, Any]]] = []
    for row in matrix:
        hay = " ".join(
            [
                str(row.get("title", "")),
                str(row.get("claim_text", "")),
                str(row.get("research_problem", "")),
                str(row.get("method_family", "")),
                str(row.get("tasks", "")),
                str(row.get("datasets", "")),
                str(row.get("metrics", "")),
                str(row.get("limitations", "")),
                str(row.get("notes", "")),
            ]
        )
        row_tokens = _token_set(hay)
        overlap = len(cues & row_tokens)
        if overlap > 0:
            scored.append((overlap, row))
    if not scored:
        return matrix[: min(6, len(matrix))]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in scored[: min(6, len(scored))]]


def _matrix_signals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    paper_ids = _dedupe([str(row.get("paper_id") or "") for row in rows if row.get("paper_id")])
    method_families = _dedupe([_humanize(str(row.get("method_family") or "")) for row in rows if row.get("method_family")])
    tasks = _split_field(rows, "tasks")
    datasets = _split_field(rows, "datasets")
    metrics = _split_field(rows, "metrics")
    return {
        "row_count": len(rows),
        "paper_count": len(paper_ids),
        "paper_ids": paper_ids,
        "method_families": method_families[:4],
        "tasks": tasks[:4],
        "datasets": datasets[:4],
        "metrics": metrics[:4],
        "claim_count": sum(1 for row in rows if row.get("claim_text")),
    }


def _split_field(rows: list[dict[str, Any]], field: str) -> list[str]:
    values: list[str] = []
    for row in rows:
        for part in str(row.get(field, "")).split(";"):
            cleaned = part.strip()
            if cleaned and cleaned.lower() not in {"none", "n/a"}:
                values.append(_humanize(cleaned))
    return _dedupe(values)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _section_goal(
    item: dict[str, Any],
    theme_refs: list[dict[str, Any]],
    gap_refs: list[dict[str, Any]],
    matrix_signals: dict[str, Any],
) -> str:
    theme_phrase = ", ".join(theme["label"] for theme in theme_refs[:2]) or "the dominant evidence clusters"
    gap_phrase = f" while keeping {len(gap_refs)} linked gap signal{'s' if len(gap_refs) != 1 else ''} visible" if gap_refs else ""
    return (
        f"{str(item.get('objective') or '').strip() or 'Structure the section around the strongest available evidence.'} "
        f"Use {theme_phrase} as the organizing lens across {matrix_signals['row_count']} matrix row{'s' if matrix_signals['row_count'] != 1 else ''}{gap_phrase}."
    ).strip()


def _argument_moves(
    item: dict[str, Any],
    theme_refs: list[dict[str, Any]],
    gap_refs: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    matrix_signals: dict[str, Any],
) -> list[dict[str, Any]]:
    lowered = str(item.get("title", "")).lower()
    move_types = ["framing", "evidence", "synthesis"]
    if "comparative" in lowered or "comparison" in lowered:
        move_types = ["framing", "comparison", "evidence", "synthesis"]
    elif any(prefix.lower() in lowered for prefix in ("method focus", "task focus", "factor focus", "scenario focus")):
        move_types = ["framing", "evidence", "synthesis"]
    elif "taxonomy" in lowered:
        move_types = ["framing", "evidence", "comparison", "synthesis"]
    elif any(token in lowered for token in ("gap", "opportun", "limitation")):
        move_types = ["framing", "gap", "synthesis"]
    elif any(token in lowered for token in ("conclusion", "discussion", "future")):
        move_types = ["synthesis", "comparison"]

    if gap_refs and "gap" not in move_types:
        move_types.append("gap")

    paper_ids = matrix_signals.get("paper_ids", [])
    moves: list[dict[str, Any]] = []
    for idx, move_type in enumerate(move_types, start=1):
        moves.append(
            {
                "move_id": f"{item.get('section_id', 'sec')}-{move_type}-{idx}",
                "move_type": move_type,
                "purpose": _move_purpose(move_type, item, theme_refs, gap_refs, matrix_signals),
                "theme_refs": theme_refs[:2],
                "gap_refs": gap_refs[:2],
                "citation_targets": paper_ids[: (3 if move_type in {"comparison", "evidence"} else 2)],
                "supporting_points": _supporting_points(move_type, rows, theme_refs, gap_refs),
            }
        )
    return moves


def _move_purpose(
    move_type: str,
    item: dict[str, Any],
    theme_refs: list[dict[str, Any]],
    gap_refs: list[dict[str, Any]],
    matrix_signals: dict[str, Any],
) -> str:
    theme_phrase = ", ".join(theme["label"] for theme in theme_refs[:2]) or "the dominant themes"
    if move_type == "framing":
        return f"Frame {item.get('title', 'this section')} around {theme_phrase} and clarify why this evidence cluster matters."
    if move_type == "evidence":
        return f"Anchor the section in {matrix_signals.get('claim_count', 0)} extracted claim signal(s) and the strongest matrix evidence."
    if move_type == "comparison":
        return f"Compare how {theme_phrase} diverge in evidence density, contradictions, or reporting conventions."
    if move_type == "synthesis":
        return "Close the section by stating the field-level takeaway rather than repeating paper-by-paper details."
    if move_type == "gap":
        return f"Surface {len(gap_refs)} linked gap signal(s) and explain what remains unresolved."
    return "Advance the section argument."


def _supporting_points(
    move_type: str,
    rows: list[dict[str, Any]],
    theme_refs: list[dict[str, Any]],
    gap_refs: list[dict[str, Any]],
) -> list[str]:
    if move_type == "gap":
        points = [gap.get("gap_statement", "") for gap in gap_refs if gap.get("gap_statement")]
        return points[:2]
    if move_type == "comparison":
        points = [theme.get("synthesis_note", "") for theme in theme_refs if theme.get("synthesis_note")]
        return points[:2]
    if move_type == "evidence":
        points = [str(row.get("claim_text") or "").strip() for row in rows if row.get("claim_text")]
        return points[:2]
    if move_type == "synthesis":
        labels = [theme.get("label", "") for theme in theme_refs if theme.get("label")]
        if labels:
            return [f"The evidence clusters most clearly around {', '.join(labels[:2])}."]
    return [str(rows[0].get("research_problem") or rows[0].get("claim_text") or "").strip()] if rows else []
