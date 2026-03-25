from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _parse_filename_metadata(paper_id: str) -> dict[str, str]:
    """Parse year and author surname from paper_id (filename without extension).
    
    Filename format: {序号}_{年份}_{第一作者姓氏}_{期刊缩写}.pdf
    e.g. "01_2001_hamed_safety_science" → year=2001, author_surname="Hamed"
    """
    parts = paper_id.split("_")
    year = parts[1] if len(parts) > 1 and parts[1].isdigit() else ""
    author_surname = parts[2].capitalize() if len(parts) > 2 else "Unknown"
    return {"year": year, "author_surname": author_surname}


def build_bib_entries(matrix: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen = set()
    entries = []
    for row in matrix:
        paper_id = row.get("paper_id")
        if not paper_id or paper_id in seen:
            continue
        seen.add(paper_id)

        # Title: use matrix value, fallback to "Untitled" or paper_id
        title = row.get("title")
        if not title or title == "Untitled":
            title = row.get("claim_text", "")[:80] or f"Paper {paper_id}"

        # Year & author: parse from filename (format: {序号}_{年份}_{作者}_{期刊})
        meta = _parse_filename_metadata(paper_id)
        year = row.get("year") or meta["year"]
        author_surname = meta["author_surname"]
        # Use "Unknown" if we don't have real author data; mark surname-only clearly
        authors = row.get("authors") or f"{author_surname}, [surname only]"
        venue = row.get("venue") or row.get("source") or "preprint"

        entries.append(
            {
                "key": paper_id,
                "year": year,
                "title": title,
                "authors": authors,
                "venue": venue,
                "entry": f"@article{{{paper_id},\n  author={{{authors}}},\n  title={{{title}}},\n  year={{{year}}},\n  journal={{{venue}}}\n}}",
            }
        )
    return entries


def prune_bib_entries(entries: list[dict[str, str]], used_keys: list[str]) -> list[dict[str, str]]:
    used = {key for key in used_keys if key}
    if not used:
        return entries
    pruned = [entry for entry in entries if entry["key"] in used]
    return pruned or entries
