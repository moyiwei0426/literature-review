from __future__ import annotations

import re
from typing import Any


def compose_markdown_review(
    title: str,
    sections: list[dict[str, Any]],
    abstract: dict[str, Any] | str | None = None,
    keywords: dict[str, Any] | list[str] | None = None,
    appendix: dict[str, Any] | None = None,
    citation_metadata: list[dict[str, Any]] | dict[str, dict[str, Any]] | None = None,
    citation_style: str = "apa",
) -> str:
    parts = [f"# {title}".rstrip(), ""]
    metadata = _build_citation_metadata(citation_metadata)

    abstract_text = _abstract_text(abstract)
    if abstract_text:
        parts.extend(["## Abstract", "", abstract_text, ""])

    keyword_items = _keyword_items(keywords)
    if keyword_items:
        parts.extend(["**Keywords:** " + ", ".join(keyword_items), ""])

    if sections:
        parts.extend(["## Sections", ""])
        parts.extend(_render_sections(sections, citation_metadata=metadata, citation_style=citation_style))

    appendix_lines = _render_appendix(appendix or {})
    if appendix_lines:
        parts.extend(appendix_lines)

    reference_lines = _render_references(_collect_cited_keys(sections), metadata, citation_style)
    if reference_lines:
        parts.extend(reference_lines)

    return "\n".join(parts).rstrip() + "\n"


def compose_review_markdown(
    title: str,
    sections: list[dict[str, Any]],
    abstract: dict[str, Any] | str | None = None,
    keywords: dict[str, Any] | list[str] | None = None,
    appendix: dict[str, Any] | None = None,
    citation_metadata: list[dict[str, Any]] | dict[str, dict[str, Any]] | None = None,
    citation_style: str = "apa",
) -> str:
    return compose_markdown_review(
        title,
        sections,
        abstract=abstract,
        keywords=keywords,
        appendix=appendix,
        citation_metadata=citation_metadata,
        citation_style=citation_style,
    )


def _abstract_text(abstract: dict[str, Any] | str | None) -> str:
    if isinstance(abstract, dict):
        return str(abstract.get("text") or "").strip()
    return str(abstract or "").strip()


def _keyword_items(keywords: dict[str, Any] | list[str] | None) -> list[str]:
    if isinstance(keywords, dict):
        values = keywords.get("keywords", [])
    else:
        values = keywords or []
    return [str(item).strip() for item in values if str(item).strip()]


def _render_sections(
    sections: list[dict[str, Any]],
    citation_metadata: list[dict[str, Any]] | dict[str, dict[str, Any]] | None = None,
    citation_style: str = "apa",
) -> list[str]:
    lines: list[str] = []
    metadata = _build_citation_metadata(citation_metadata)
    for section in sections:
        title = str(section.get("title") or "").strip()
        if not title:
            continue
        lines.extend([f"## {title}", ""])
        paragraphs = section.get("paragraphs") or []
        if paragraphs:
            for paragraph in paragraphs:
                text = str(paragraph.get("text") or "").strip()
                if text:
                    rendered = _render_text_with_citations(
                        text,
                        paragraph.get("citation_keys", []),
                        metadata,
                        citation_style=citation_style,
                    )
                    lines.extend([rendered, ""])
        else:
            text = str(section.get("text") or "").strip()
            if text:
                rendered = _render_text_with_citations(
                    text,
                    section.get("citation_keys", []),
                    metadata,
                    citation_style=citation_style,
                )
                lines.extend([rendered, ""])
    return lines


def _render_appendix(appendix: dict[str, Any]) -> list[str]:
    if not appendix:
        return []
    summary = appendix.get("summary", {}) if isinstance(appendix, dict) else {}
    evidence_table = appendix.get("evidence_table", []) if isinstance(appendix, dict) else []
    gap_index = appendix.get("gap_index", []) if isinstance(appendix, dict) else []

    lines = ["## Appendix", ""]
    if isinstance(summary, dict):
        narrative = [str(item).strip() for item in summary.get("narrative", []) if str(item).strip()]
        if narrative:
            lines.extend(["### Summary", ""])
            for item in narrative:
                lines.append(f"- {item}")
            lines.append("")

        summary_items = [
            ("Papers", summary.get("paper_count")),
            ("Matrix rows", summary.get("row_count")),
            ("Verified gaps", summary.get("verified_gap_count")),
            ("Dominant axis", summary.get("dominant_axis")),
            ("Top methods", ", ".join(summary.get("top_methods", [])[:3])),
            ("Top tasks", ", ".join(summary.get("top_tasks", [])[:3])),
            ("Top datasets", ", ".join(summary.get("top_datasets", [])[:3])),
        ]
        valid_items = [(label, value) for label, value in summary_items if value not in (None, "", [])]
        if valid_items:
            for label, value in valid_items:
                lines.append(f"- **{label}:** {value}")
            lines.append("")

    if evidence_table:
        lines.extend(["### Evidence Highlights", ""])
        for row in evidence_table[:8]:
            title = str(row.get("title") or row.get("paper_id") or "Untitled").strip()
            methods = ", ".join(row.get("methods", [])[:2]) or "n/a"
            tasks = ", ".join(row.get("tasks", [])[:2]) or "n/a"
            gaps = ", ".join(row.get("gap_matches", [])[:3]) or "none"
            year = row.get("year") or "n/a"
            lines.append(f"- **{title}** ({year}) | Methods: {methods} | Tasks: {tasks} | Gap matches: {gaps}")
        lines.append("")

    if gap_index:
        lines.extend(["### Gap Index", ""])
        for gap in gap_index[:8]:
            statement = str(gap.get("gap_statement") or "").strip()
            if not statement:
                continue
            gap_id = str(gap.get("gap_id") or "gap").strip()
            severity = str(gap.get("severity") or "n/a").strip()
            research_need = str(gap.get("research_need") or "n/a").strip()
            lines.append(f"- **{gap_id}** ({severity}): {statement} Research need: {research_need}.")
        lines.append("")

    return lines


def _collect_cited_keys(sections: list[dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def remember(keys: Any) -> None:
        for key in keys or []:
            normalized = str(key).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                ordered.append(normalized)

    for section in sections or []:
        remember(section.get("citation_keys"))
        for paragraph in section.get("paragraphs") or []:
            if isinstance(paragraph, dict):
                remember(paragraph.get("citation_keys"))
    return ordered


def _render_references(cited_keys: list[str], metadata: dict[str, dict[str, Any]], citation_style: str) -> list[str]:
    if not cited_keys:
        return []

    lines = ["## References", ""]
    for key in cited_keys:
        entry = metadata.get(key, {})
        if citation_style.lower() == "apa":
            lines.append(f"- {_format_apa_reference(key, entry)}")
        else:
            lines.append(f"- {key}")
    lines.append("")
    return lines


def _build_citation_metadata(
    citation_metadata: list[dict[str, Any]] | dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if isinstance(citation_metadata, dict):
        normalized: dict[str, dict[str, Any]] = {}
        for key, value in citation_metadata.items():
            if not isinstance(value, dict):
                continue
            normalized[str(key)] = {
                "authors": value.get("authors"),
                "year": value.get("year"),
                "title": value.get("title"),
                "venue": value.get("venue"),
                "doi": value.get("doi"),
            }
        return normalized

    metadata: dict[str, dict[str, Any]] = {}
    for row in citation_metadata or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("paper_id") or row.get("key") or "").strip()
        if not key:
            continue
        current = metadata.get(key, {})
        metadata[key] = {
            "authors": current.get("authors") or row.get("authors"),
            "year": current.get("year") or row.get("year"),
            "title": current.get("title") or row.get("title"),
            "venue": current.get("venue") or row.get("venue"),
            "doi": current.get("doi") or row.get("doi"),
        }
    return metadata


def _render_text_with_citations(
    text: str,
    citation_keys: list[str],
    metadata: dict[str, dict[str, Any]],
    citation_style: str = "apa",
) -> str:
    rendered = str(text or "").strip()
    used_keys: list[str] = []
    for key in citation_keys or []:
        pattern = rf"(?<!\w){re.escape(str(key))}(?!\w)"
        replacement = _format_single_citation(str(key), metadata, citation_style, bare=True)
        rendered, count = re.subn(pattern, replacement, rendered)
        if count:
            used_keys.append(str(key))

    remaining = [str(key) for key in (citation_keys or []) if str(key) not in used_keys]
    suffix = _format_citation_group(remaining, metadata, citation_style)
    if suffix:
        rendered = _append_parenthetical_citation(rendered, suffix)
    return rendered


def _append_parenthetical_citation(text: str, citation: str) -> str:
    if not citation:
        return text
    stripped = text.rstrip()
    if not stripped:
        return citation
    if stripped[-1] in ".?!":
        return f"{stripped[:-1]} {citation}{stripped[-1]}"
    return f"{stripped} {citation}"


def _format_citation_group(keys: list[str], metadata: dict[str, dict[str, Any]], citation_style: str) -> str:
    normalized = [key for key in keys if str(key).strip()]
    if not normalized:
        return ""
    if citation_style.lower() != "apa":
        return "(" + "; ".join(normalized) + ")"
    return "(" + "; ".join(_format_single_citation(key, metadata, citation_style) for key in normalized) + ")"


def _format_single_citation(key: str, metadata: dict[str, dict[str, Any]], citation_style: str, bare: bool = False) -> str:
    if citation_style.lower() != "apa":
        return key if bare else key
    entry = metadata.get(key, {})
    author_part = _format_apa_author(entry.get("authors"), fallback_key=key)
    year = str(entry.get("year") or _infer_year_from_key(key) or "n.d.")
    rendered = f"{author_part}, {year}"
    return rendered if bare else rendered


def _format_apa_reference(key: str, entry: dict[str, Any]) -> str:
    author_part = _format_apa_reference_authors(entry.get("authors"), fallback_key=key)
    year = str(entry.get("year") or _infer_year_from_key(key) or "n.d.")
    title = str(entry.get("title") or key).strip().rstrip(".")
    venue = str(entry.get("venue") or "").strip().rstrip(".")
    doi = str(entry.get("doi") or "").strip()

    reference = f"{author_part} ({year}). {title}."
    if venue:
        reference += f" {venue}."
    if doi:
        reference += f" https://doi.org/{doi.removeprefix('https://doi.org/').removeprefix('http://doi.org/').removeprefix('doi:')}"
    return reference.strip()


def _format_apa_author(authors: Any, fallback_key: str) -> str:
    names = _author_list(authors)
    surnames = [_surname(name) for name in names if _surname(name)]
    if not surnames:
        fallback = _infer_author_from_key(fallback_key)
        return fallback or "Unknown"
    if len(surnames) == 1:
        return surnames[0]
    if len(surnames) == 2:
        return f"{surnames[0]} & {surnames[1]}"
    return f"{surnames[0]} et al."


def _format_apa_reference_authors(authors: Any, fallback_key: str) -> str:
    names = _author_list(authors)
    if not names:
        fallback = _infer_author_from_key(fallback_key)
        return f"{fallback}." if fallback else "Unknown."

    formatted = [_format_reference_author_name(name) for name in names]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def _author_list(authors: Any) -> list[str]:
    if isinstance(authors, str):
        return [part.strip() for part in re.split(r"\band\b", authors) if part.strip()]
    if isinstance(authors, list):
        return [str(item).strip() for item in authors if str(item).strip()]
    return []


def _format_reference_author_name(name: str) -> str:
    text = str(name or "").strip()
    if not text:
        return ""
    if "," in text:
        surname, given = [part.strip() for part in text.split(",", 1)]
    else:
        parts = text.split()
        surname = parts[-1]
        given = " ".join(parts[:-1])
    initials = " ".join(f"{part[0].upper()}." for part in re.split(r"[\s-]+", given) if part)
    return f"{surname}, {initials}".strip().rstrip(",")


def _surname(name: str) -> str:
    text = str(name or "").strip()
    if not text:
        return ""
    if "," in text:
        return text.split(",", 1)[0].strip()
    return text.split()[-1].strip()


def _infer_year_from_key(key: str) -> str:
    match = re.search(r"(?:^|_)(\d{4})(?:_|$)", str(key))
    return match.group(1) if match else ""


def _infer_author_from_key(key: str) -> str:
    parts = [part for part in str(key).split("_") if part]
    for part in parts:
        if not part.isdigit() and len(part) > 2:
            return part.capitalize()
    return str(key)
