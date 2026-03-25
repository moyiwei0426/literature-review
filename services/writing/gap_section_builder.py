from __future__ import annotations

from typing import Any


def has_structured_gap_data(gap: dict[str, Any]) -> bool:
    if not isinstance(gap, dict):
        return False
    return any(
        str(gap.get(field) or "").strip()
        for field in (
            "partial_evidence_summary",
            "why_insufficient",
            "practical_consequence",
            "research_need",
            "resolution_needed",
        )
    )


def build_gap_section(
    gaps: list[dict[str, Any]],
    *,
    paper_count: int = 0,
    max_gaps: int = 5,
) -> str:
    if not gaps:
        return ""

    chosen = [gap for gap in gaps if isinstance(gap, dict)][:max_gaps]
    opening = (
        f"The comparative analysis of {paper_count} papers highlights {len(chosen)} structured gap"
        f"{'s' if len(chosen) != 1 else ''} that remain unresolved despite partial evidence in the current corpus."
    )
    entries = [_render_gap_entry(idx, gap) for idx, gap in enumerate(chosen, start=1)]
    closing = (
        "Taken together, these gaps show that the evidence base is only partially cumulative: the field can point to promising signals, "
        "but stronger study designs and reporting discipline are still needed before those signals can support robust generalization."
    )
    return " ".join(part for part in [opening, *entries, closing] if part)


def _render_gap_entry(index: int, gap: dict[str, Any]) -> str:
    gap_id = str(gap.get("gap_id") or f"gap-{index}")
    statement = str(gap.get("gap_statement") or "An unresolved gap remains in the current literature.").strip()
    evidence = _value(gap, "partial_evidence_summary", "partial_evidence")
    why = _value(gap, "why_insufficient", "insufficiency_reason")
    consequence = _value(gap, "practical_consequence", "consequence")
    needed = _value(gap, "research_need", "resolution_needed")
    paper_ids = [str(item).strip() for item in gap.get("partial_evidence_paper_ids", []) or [] if str(item).strip()]
    paper_anchor = f" Evidence currently comes from {', '.join(paper_ids)}." if paper_ids else ""

    parts = [f"Gap [{gap_id}] concerns {statement}."]
    if evidence:
        parts.append(f"Partial evidence: {evidence}.{paper_anchor}".rstrip())
    if why:
        parts.append(f"This evidence remains insufficient because {why}.")
    if consequence:
        parts.append(f"As a result, {consequence}.")
    if needed:
        parts.append(f"Resolving this gap requires {needed}.")
    return " ".join(_trim_periods(part) for part in parts if part)


def _value(gap: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(gap.get(key) or "").strip()
        if value:
            return value
    return ""


def _trim_periods(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    return text[:-1] if text.endswith("..") else text
