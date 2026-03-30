from __future__ import annotations

from typing import Any


def build_evidence_bundle(
    section_plan: dict[str, Any] | None,
    block: dict[str, Any] | None,
    matrix: list[dict[str, Any]],
    verified_gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    section_plan = section_plan or {}
    block = block or {}
    verified_gaps = verified_gaps or []
    citation_targets = _string_list(block.get("citation_targets"))
    supporting_citations = _string_list(block.get("supporting_citations")) or citation_targets
    allowed = _dedupe(citation_targets + supporting_citations)
    evidence_rows = [row for row in matrix if str(row.get("paper_id") or "") in set(allowed)]
    gap_ids = {str(item.get("gap_id") or "") for item in _dict_list(block.get("gap_refs")) if str(item.get("gap_id") or "").strip()}
    linked_gaps = [gap for gap in verified_gaps if str(gap.get("gap_id") or "") in gap_ids] or _dict_list(block.get("gap_refs"))
    return {
        "bundle_id": f"{block.get('block_id', 'block')}-evidence",
        "section_id": str(section_plan.get("section_id") or ""),
        "block_id": str(block.get("block_id") or ""),
        "move_type": str(block.get("move_type") or "synthesis"),
        "allowed_citation_keys": allowed,
        "required_citation_count": max(1, min(len(allowed), int(block.get("required_evidence_count") or 1))) if allowed else 0,
        "evidence_rows": evidence_rows,
        "supporting_points": [str(x).strip() for x in block.get("supporting_points", []) if str(x).strip()],
        "gap_refs": linked_gaps,
        "theme_refs": _dict_list(block.get("theme_refs")),
    }


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _dedupe(items: list[str]) -> list[str]:
    seen=set(); out=[]
    for item in items:
        if item not in seen:
            seen.add(item); out.append(item)
    return out
