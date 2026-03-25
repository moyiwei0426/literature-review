from __future__ import annotations

from typing import Any


def _convert_citations(text: str, citation_keys: list[str]) -> tuple[str, list[str]]:
    """Replace [p1], [p2] style markers with \\cite{} commands and track consumed keys."""
    import re

    keys_in_text = [key for key in re.findall(r"\[([\w\d]+)\]", text) if key in citation_keys]
    for key in keys_in_text:
        text = re.sub(rf"\[{re.escape(key)}\]", rf"\\cite{{{key}}}", text)
    return text, keys_in_text


def _render_block(text: str, citation_keys: list[str]) -> str:
    rendered, explicit_keys = _convert_citations(text, citation_keys)
    remaining = [key for key in citation_keys if key not in explicit_keys]
    if remaining:
        rendered = f"{rendered.rstrip()} \\cite{{{','.join(remaining)}}}"
    return rendered


def _escape_latex(text: Any) -> str:
    rendered = str(text or "")
    placeholders = {
        "\\": "__LATEX_BACKSLASH__",
        "&": "__LATEX_AMP__",
        "%": "__LATEX_PERCENT__",
        "$": "__LATEX_DOLLAR__",
        "#": "__LATEX_HASH__",
        "_": "__LATEX_UNDERSCORE__",
        "{": "__LATEX_LBRACE__",
        "}": "__LATEX_RBRACE__",
        "~": "__LATEX_TILDE__",
        "^": "__LATEX_CARET__",
    }
    replacements = {
        "__LATEX_BACKSLASH__": r"\textbackslash{}",
        "__LATEX_AMP__": r"\&",
        "__LATEX_PERCENT__": r"\%",
        "__LATEX_DOLLAR__": r"\$",
        "__LATEX_HASH__": r"\#",
        "__LATEX_UNDERSCORE__": r"\_",
        "__LATEX_LBRACE__": r"\{",
        "__LATEX_RBRACE__": r"\}",
        "__LATEX_TILDE__": r"\textasciitilde{}",
        "__LATEX_CARET__": r"\textasciicircum{}",
    }
    for old, placeholder in placeholders.items():
        rendered = rendered.replace(old, placeholder)
    for placeholder, replacement in replacements.items():
        rendered = rendered.replace(placeholder, replacement)
    return rendered


def _render_appendix(appendix: dict[str, Any]) -> str:
    summary = appendix.get("summary", {}) if isinstance(appendix, dict) else {}
    evidence_table = appendix.get("evidence_table", []) if isinstance(appendix, dict) else []
    gap_index = appendix.get("gap_index", []) if isinstance(appendix, dict) else []

    lines = ["\\appendix", "\\section{Appendix}"]
    if isinstance(summary, dict):
        narrative = summary.get("narrative", [])
        narrative_text = " ".join(_escape_latex(item) for item in narrative if str(item).strip())
        if narrative_text:
            lines.append("\\subsection{Appendix Summary}")
            lines.append("\\noindent " + narrative_text)
        summary_items = [
            ("Papers", summary.get("paper_count")),
            ("Matrix rows", summary.get("row_count")),
            ("Verified gaps", summary.get("verified_gap_count")),
            ("Dominant axis", summary.get("dominant_axis")),
            ("Top methods", ", ".join(_escape_latex(item) for item in summary.get("top_methods", [])[:3]) if summary.get("top_methods") else None),
            ("Top tasks", ", ".join(_escape_latex(item) for item in summary.get("top_tasks", [])[:3]) if summary.get("top_tasks") else None),
            ("Top datasets", ", ".join(_escape_latex(item) for item in summary.get("top_datasets", [])[:3]) if summary.get("top_datasets") else None),
        ]
        valid_items = [(label, value) for label, value in summary_items if value not in (None, "", [])]
        if valid_items:
            lines.append("")
            lines.append("\\begin{itemize}")
            for label, value in valid_items:
                lines.append(f"\\item \\textbf{{{_escape_latex(label)}}}: {_escape_latex(value)}")
            lines.append("\\end{itemize}")
        lines.append("")
        lines.append("\\subsection{Evidence Table}")
        if evidence_table:
            lines.append("\\begin{longtable}{p{0.14\\textwidth}p{0.21\\textwidth}p{0.10\\textwidth}p{0.17\\textwidth}p{0.17\\textwidth}p{0.17\\textwidth}}")
            lines.append("\\toprule")
            lines.append("Paper & Title & Year & Methods & Tasks & Gap matches \\\\")
            lines.append("\\midrule")
            lines.append("\\endfirsthead")
            lines.append("\\toprule")
            lines.append("Paper & Title & Year & Methods & Tasks & Gap matches \\\\")
            lines.append("\\midrule")
            lines.append("\\endhead")
            for row in evidence_table:
                gap_matches = ", ".join(_escape_latex(item) for item in row.get("gap_matches", [])[:3]) or "--"
                methods = ", ".join(_escape_latex(item) for item in row.get("methods", [])[:2]) or "--"
                tasks = ", ".join(_escape_latex(item) for item in row.get("tasks", [])[:2]) or "--"
                title = _escape_latex(row.get("title"))
                paper_id = _escape_latex(row.get("paper_id"))
                year = _escape_latex(row.get("year") or "--")
                lines.append(f"{paper_id} & {title} & {year} & {methods} & {tasks} & {gap_matches} \\\\")
            lines.append("\\bottomrule")
            lines.append("\\end{longtable}")
        else:
            lines.append("\\noindent No evidence table rows were available.")
        if gap_index:
            lines.append("")
            lines.append("\\subsection{Gap Index}")
            lines.append("\\begin{longtable}{p{0.12\\textwidth}p{0.44\\textwidth}p{0.14\\textwidth}p{0.22\\textwidth}}")
            lines.append("\\toprule")
            lines.append("Gap & Statement & Severity & Research need \\\\")
            lines.append("\\midrule")
            lines.append("\\endfirsthead")
            lines.append("\\toprule")
            lines.append("Gap & Statement & Severity & Research need \\\\")
            lines.append("\\midrule")
            lines.append("\\endhead")
            for gap in gap_index[:8]:
                gap_id = _escape_latex(gap.get("gap_id") or "--")
                statement = _escape_latex(gap.get("gap_statement"))
                severity = _escape_latex(gap.get("severity") or "--")
                research_need = _escape_latex(gap.get("research_need"))
                lines.append(f"{gap_id} & {statement or '--'} & {severity} & {research_need or '--'} \\\\")
            lines.append("\\bottomrule")
            lines.append("\\end{longtable}")
    return "\n".join(lines)


def _render_abstract(abstract: str | dict[str, Any] | None) -> str:
    if not abstract:
        return ""
    if isinstance(abstract, dict):
        text = abstract.get("text", "")
    else:
        text = abstract
    text = str(text or "").strip()
    if not text:
        return ""
    return "\\begin{abstract}\n" + _escape_latex(text) + "\n\\end{abstract}\n"


def _render_keywords(keywords: list[str] | dict[str, Any] | str | None) -> str:
    if not keywords:
        return ""
    if isinstance(keywords, dict):
        values = keywords.get("keywords", [])
    elif isinstance(keywords, str):
        values = [item.strip() for item in keywords.split(",")]
    else:
        values = keywords
    rendered_keywords = [str(item).strip() for item in values if str(item).strip()]
    if not rendered_keywords:
        return ""
    return "\\noindent\\textbf{Keywords:} " + ", ".join(_escape_latex(item) for item in rendered_keywords) + "\n"


def compose_latex(
    title: str,
    sections: list[dict[str, Any]],
    bib_entries: list[dict[str, str]],
    appendix: dict[str, Any] | None = None,
    abstract: str | dict[str, Any] | None = None,
    keywords: list[str] | dict[str, Any] | str | None = None,
) -> str:
    body = []
    for section in sections:
        paragraphs = section.get("paragraphs") or []
        if paragraphs:
            rendered_paragraphs = [
                _render_block(paragraph.get("text", ""), paragraph.get("citation_keys", []))
                for paragraph in paragraphs
                if paragraph.get("text", "").strip()
            ]
            text = "\n\n".join(rendered_paragraphs)
        else:
            citation_keys = section.get("citation_keys", [])
            text = _render_block(section.get("text", ""), citation_keys)
        body.append(f"\\section{{{section['title']}}}\n{text}\n")

    bib_content = "\n\n".join(entry["entry"] for entry in bib_entries)
    appendix_content = _render_appendix(appendix) if appendix else ""
    abstract_content = _render_abstract(abstract)
    keywords_content = _render_keywords(keywords)
    tex = (
        "\\documentclass{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{longtable}\n"
        "\\title{" + title + "}\n"
        "\\begin{document}\n"
        "\\maketitle\n"
        + abstract_content
        + keywords_content
        + "\n".join(body)
        + ("\n" + appendix_content + "\n" if appendix_content else "\n")
        + "\\end{document}\n"
        + "% BIB START\n"
        + bib_content
    )
    return tex
