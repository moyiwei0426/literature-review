from __future__ import annotations

import json
import re
from typing import Any

from services.llm.adapter import LLMAdapter


def rewrite_style(sections: list[dict]) -> list[dict]:
    llm = LLMAdapter()
    if llm.provider != "stub" and llm.base_url and llm._has_auth():
        try:
            rewritten = _rewrite_style_llm(llm, sections)
            if rewritten:
                return rewritten
        except Exception:
            pass
    return _rewrite_style_rule_based(sections)


def _rewrite_style_llm(llm: LLMAdapter, sections: list[dict]) -> list[dict]:
    rewrite_plan = [_section_rewrite_plan(section) for section in sections if isinstance(section, dict)]
    system_prompt = (
        "You are an academic editing engine. Rewrite text for clarity, concise academic tone, and coherence. "
        "Preserve structure exactly. Return ONLY JSON with key 'sections'. "
        "Each section must keep the same section_id, title, and paragraph count. "
        "Do not merge, split, delete, reorder, or add paragraphs. "
        "For each section, return {section_id, title, paragraphs:[{text}]}. "
        "Preserve citation markers such as [p1] exactly when present."
    )
    user_prompt = (
        "Rewrite each paragraph independently while preserving paragraph order.\n\n"
        f"{json.dumps({'sections': rewrite_plan}, ensure_ascii=False)}"
    )
    response = llm.generate_json(system_prompt, user_prompt)
    items = _extract_llm_sections(response.content)
    merged = _merge_llm_rewrite(sections, items)
    return merged or _rewrite_style_rule_based(sections)


def _rewrite_style_rule_based(sections: list[dict]) -> list[dict]:
    rewritten = []
    for section in sections:
        rewritten.append(_rewrite_section_rule_based(section))
    return rewritten


def _rewrite_section_rule_based(section: dict[str, Any]) -> dict[str, Any]:
    paragraphs = _section_paragraphs(section)
    if not paragraphs:
        text = _rewrite_paragraph_text(str(section.get("text") or ""))
        return {**section, "text": text}

    rewritten_paragraphs = [{**paragraph, "text": _rewrite_paragraph_text(paragraph.get("text", ""))} for paragraph in paragraphs]
    return {
        **section,
        "text": "\n\n".join(paragraph["text"] for paragraph in rewritten_paragraphs if paragraph.get("text", "").strip()),
        "paragraphs": rewritten_paragraphs,
    }


def _extract_llm_sections(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, dict):
        items = content.get("sections") or content.get("data") or []
    elif isinstance(content, list):
        items = content
    else:
        items = []
    return [item for item in items if isinstance(item, dict)]


def _merge_llm_rewrite(sections: list[dict], items: list[dict[str, Any]]) -> list[dict] | None:
    if len(items) != len(sections):
        return None

    merged: list[dict[str, Any]] = []
    for original, candidate in zip(sections, items):
        expected_id = str(original.get("section_id") or "").strip()
        candidate_id = str(candidate.get("section_id") or "").strip()
        if expected_id and candidate_id != expected_id:
            return None

        original_paragraphs = _section_paragraphs(original)
        if original_paragraphs:
            candidate_paragraphs = candidate.get("paragraphs")
            if not isinstance(candidate_paragraphs, list) or len(candidate_paragraphs) != len(original_paragraphs):
                return None

            rewritten_paragraphs: list[dict[str, Any]] = []
            for source_paragraph, rewritten_paragraph in zip(original_paragraphs, candidate_paragraphs):
                if not isinstance(rewritten_paragraph, dict):
                    return None
                text = _clean_rewritten_text(rewritten_paragraph.get("text"))
                if not text:
                    return None
                rewritten_paragraphs.append({**source_paragraph, "text": text})

            merged.append(
                {
                    **original,
                    "title": candidate.get("title") or original.get("title") or "",
                    "text": "\n\n".join(paragraph["text"] for paragraph in rewritten_paragraphs),
                    "paragraphs": rewritten_paragraphs,
                }
            )
            continue

        candidate_paragraphs = candidate.get("paragraphs")
        if not isinstance(candidate_paragraphs, list) or len(candidate_paragraphs) != 1:
            return None
        if not isinstance(candidate_paragraphs[0], dict):
            return None
        text = _clean_rewritten_text(candidate_paragraphs[0].get("text"))
        if not text:
            return None
        merged.append({**original, "title": candidate.get("title") or original.get("title") or "", "text": text})

    return merged


def _section_rewrite_plan(section: dict[str, Any]) -> dict[str, Any]:
    paragraphs = _section_paragraphs(section)
    if not paragraphs:
        paragraphs = [{"text": str(section.get("text") or "").strip()}]
    return {
        "section_id": section.get("section_id") or "",
        "title": section.get("title") or "",
        "paragraphs": [{"text": paragraph.get("text", "")} for paragraph in paragraphs],
    }


def _section_paragraphs(section: dict[str, Any]) -> list[dict[str, Any]]:
    paragraphs = section.get("paragraphs")
    normalized: list[dict[str, Any]] = []
    if isinstance(paragraphs, list):
        for item in paragraphs:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if text:
                    normalized.append({**item, "text": text})
    return normalized


def _rewrite_paragraph_text(text: Any) -> str:
    rewritten = str(text or "").strip()
    if not rewritten:
        return ""

    replacements = {
        "It is worth noting that ": "",
        "it is worth noting that ": "",
        "It should be noted that ": "",
        "it should be noted that ": "",
        "It is important to note that ": "",
        "it is important to note that ": "",
        "pivotal": "important",
        "utilize": "use",
        "utilizes": "uses",
        "utilized": "used",
    }
    for source, target in replacements.items():
        rewritten = rewritten.replace(source, target)

    rewritten = re.sub(r"\s+", " ", rewritten)
    rewritten = re.sub(r"\s+([,.;:])", r"\1", rewritten)
    rewritten = re.sub(r"\(\s+", "(", rewritten)
    rewritten = re.sub(r"\s+\)", ")", rewritten)
    rewritten = re.sub(r"\bThis paragraph\b", "This analysis", rewritten)
    rewritten = re.sub(r"\bIn conclusion,\s*", "", rewritten)
    rewritten = re.sub(r"\ba ([aeiouAEIOU])", r"an \1", rewritten)
    rewritten = _capitalize_leading_text(rewritten.strip())
    return rewritten


def _clean_rewritten_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"\ba ([aeiouAEIOU])", r"an \1", text)
    return _capitalize_leading_text(text.strip())


def _capitalize_leading_text(text: str) -> str:
    match = re.search(r"[A-Za-z]", text)
    if not match:
        return text
    idx = match.start()
    return text[:idx] + text[idx].upper() + text[idx + 1:]
