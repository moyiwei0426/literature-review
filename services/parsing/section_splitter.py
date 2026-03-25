from __future__ import annotations

import re
from typing import Any

SECTION_PATTERNS = {
    "abstract": [r"^abstract$"],
    "introduction": [r"^introduction$", r"^1\.?\s+introduction$"],
    "method": [r"^method", r"^approach", r"^methodology"],
    "experiment": [r"^experiment", r"^evaluation", r"^results"],
    "conclusion": [r"^conclusion", r"^discussion"],
    "references": [r"^references$", r"^bibliography$"],
}


def normalize_section_name(title: str) -> str:
    cleaned = title.strip().lower()
    for canonical, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, cleaned):
                return canonical
    return cleaned or "unknown"


def split_sections(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    sections = parsed.get("sections") or []
    normalized = []
    for idx, item in enumerate(sections):
        title = item.get("title") or f"section_{idx}"
        normalized.append(
            {
                "section_name": normalize_section_name(title),
                "title": title,
                "text": item.get("text", ""),
                "page_start": item.get("page_start"),
                "page_end": item.get("page_end"),
                "order_index": idx,
            }
        )
    return normalized
