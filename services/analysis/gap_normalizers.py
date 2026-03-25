from __future__ import annotations

from typing import Any
from uuid import uuid4

VALID_GAP_TYPES = {"coverage", "comparison", "methodology", "evaluation", "language", "application", "taxonomy"}


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def normalize_gap_list(items: list[dict[str, Any]] | None, *, default_status: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        gap_type = (item.get("gap_type") or item.get("type") or "coverage").lower()
        if gap_type not in VALID_GAP_TYPES:
            gap_type = "coverage"
        supporting = item.get("supporting_evidence") or item.get("support") or item.get("supporting_signals") or []
        counter = item.get("counter_evidence") or item.get("counter") or []
        if isinstance(supporting, dict):
            supporting = [f"{k}={v}" for k, v in supporting.items()]
        elif isinstance(supporting, str):
            supporting = [supporting]
        if isinstance(counter, str):
            counter = [counter]
        partial_evidence_summary = (
            item.get("partial_evidence_summary")
            or item.get("partial_evidence")
            or item.get("evidence_summary")
        )
        why_insufficient = (
            item.get("why_insufficient")
            or item.get("insufficiency_reason")
            or item.get("insufficiency")
        )
        practical_consequence = (
            item.get("practical_consequence")
            or item.get("consequence")
            or item.get("impact")
        )
        research_need = item.get("research_need") or item.get("study_needed")
        resolution_needed = item.get("resolution_needed") or research_need
        partial_evidence_paper_ids = _as_string_list(
            item.get("partial_evidence_paper_ids")
            or item.get("evidence_paper_ids")
            or item.get("paper_ids")
        )
        normalized.append(
            {
                "gap_id": item.get("gap_id") or f"gap-{idx}-{uuid4().hex[:8]}",
                "gap_statement": item.get("gap_statement") or item.get("statement") or item.get("gap") or item.get("inference") or item.get("observation") or "",
                "gap_type": gap_type,
                "supporting_evidence": supporting,
                "counter_evidence": counter,
                "partial_evidence_paper_ids": partial_evidence_paper_ids,
                "partial_evidence_summary": partial_evidence_summary,
                "why_insufficient": why_insufficient,
                "practical_consequence": practical_consequence,
                "research_need": research_need,
                "resolution_needed": resolution_needed,
                "partial_evidence": item.get("partial_evidence") or partial_evidence_summary,
                "insufficiency_reason": item.get("insufficiency_reason") or why_insufficient,
                "consequence": item.get("consequence") or practical_consequence,
                "confidence": item.get("confidence"),
                "novelty_value": item.get("novelty_value"),
                "review_worthiness": item.get("review_worthiness"),
                "status": item.get("status") or default_status,
            }
        )
    return normalized
