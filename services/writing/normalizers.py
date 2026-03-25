from __future__ import annotations

from typing import Any
import re


def _clean_section_title(value: str) -> str:
    return re.sub(r'^\s*\d+(?:\.\d+)*\.??\s*', '', value).strip()


def normalize_outline(items: list[dict[str, Any]] | None, verified_gaps: list[dict[str, Any]], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    fallback_gap_ids = [gap.get("gap_id") for gap in verified_gaps[:3]]
    for idx, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        raw_title = item.get("title") or item.get("section_title") or item.get("section") or f"Section {idx}"
        title = _clean_section_title(raw_title)
        subsections = item.get("subsections") or []
        objective = item.get("objective") or item.get("goal")
        if not objective and subsections:
            objective = "Cover: " + "; ".join(str(x) for x in subsections[:3])
        normalized.append(
            {
                "section_id": item.get("section_id") or f"sec-{idx}",
                "title": title,
                "objective": objective or f"Draft the {title} section.",
                "gap_inputs": item.get("gap_inputs") or fallback_gap_ids,
                "matrix_row_count": item.get("matrix_row_count") or len(matrix),
            }
        )
    return normalized


def normalize_sections(items: list[dict[str, Any]] | None, outline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for idx, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("section_title") or outline[idx - 1]["title"] if idx - 1 < len(outline) else f"Section {idx}"
        paragraphs = item.get("paragraphs")
        normalized.append(
            {
                "section_id": item.get("section_id") or f"sec-{idx}",
                "title": title,
                "text": item.get("text") or item.get("content") or item.get("draft") or "",
                **({"paragraphs": paragraphs} if isinstance(paragraphs, list) else {}),
                **({"citation_keys": item["citation_keys"]} if isinstance(item.get("citation_keys"), list) else {}),
                **({"_citation_scores": item["_citation_scores"]} if isinstance(item.get("_citation_scores"), dict) else {}),
                **({"_citation_rationale": item["_citation_rationale"]} if isinstance(item.get("_citation_rationale"), dict) else {}),
                **({"citation_targets": item["citation_targets"]} if isinstance(item.get("citation_targets"), list) else {}),
                **({"supporting_citations": item["supporting_citations"]} if isinstance(item.get("supporting_citations"), list) else {}),
                **({"theme_refs": item["theme_refs"]} if isinstance(item.get("theme_refs"), list) else {}),
                **({"gap_refs": item["gap_refs"]} if isinstance(item.get("gap_refs"), list) else {}),
            }
        )
    return normalized
