from __future__ import annotations

from typing import Any


def compose_markdown_review(
    title: str,
    sections: list[dict[str, Any]],
    abstract: dict[str, Any] | str | None = None,
    keywords: dict[str, Any] | list[str] | None = None,
    appendix: dict[str, Any] | None = None,
) -> str:
    parts = [f"# {title}".rstrip(), ""]

    abstract_text = _abstract_text(abstract)
    if abstract_text:
        parts.extend(["## Abstract", "", abstract_text, ""])

    keyword_items = _keyword_items(keywords)
    if keyword_items:
        parts.extend(["**Keywords:** " + ", ".join(keyword_items), ""])

    if sections:
        parts.extend(["## Sections", ""])
        parts.extend(_render_sections(sections))

    appendix_lines = _render_appendix(appendix or {})
    if appendix_lines:
        parts.extend(appendix_lines)

    return "\n".join(parts).rstrip() + "\n"


def compose_review_markdown(
    title: str,
    sections: list[dict[str, Any]],
    abstract: dict[str, Any] | str | None = None,
    keywords: dict[str, Any] | list[str] | None = None,
    appendix: dict[str, Any] | None = None,
) -> str:
    return compose_markdown_review(
        title,
        sections,
        abstract=abstract,
        keywords=keywords,
        appendix=appendix,
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


def _render_sections(sections: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
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
                    lines.extend([text, ""])
        else:
            text = str(section.get("text") or "").strip()
            if text:
                lines.extend([text, ""])
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
