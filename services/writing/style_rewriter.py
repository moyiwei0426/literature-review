from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from services.llm.adapter import LLMAdapter

_POLISH_MOVES = {"synthesis", "comparison", "contradiction", "gap", "conclusion"}
_RISKY_MARKERS = {
    "prove",
    "proves",
    "definitive",
    "definitively",
    "always",
    "never",
    "clearly",
    "obviously",
    "undeniably",
    "transformative",
    "breakthrough",
}
_MOVE_OPENERS = {
    "synthesis": [
        "Taken together, ",
        "Across these studies, ",
        "Viewed jointly, ",
    ],
    "comparison": [
        "In comparison, ",
        "Across the comparison set, ",
        "Set side by side, ",
    ],
    "contradiction": [
        "At the same time, ",
        "The record is not fully aligned, ",
        "Across studies, the evidence does not point in a single direction, ",
    ],
    "gap": [
        "Even so, ",
        "Despite that progress, ",
        "What remains unresolved is that ",
    ],
    "conclusion": [
        "Overall, ",
        "In sum, ",
        "At the review level, ",
    ],
}
_MOVE_CLOSERS = {
    "synthesis": [
        "This pattern clarifies the main field-level takeaway.",
        "This synthesis defines the most stable cross-study signal.",
        "This convergence anchors the section's main takeaway.",
    ],
    "comparison": [
        "The comparison mainly sharpens where results remain context-dependent.",
        "The contrast is most useful for locating the practical tradeoffs across studies.",
        "That side-by-side view makes the main tradeoff explicit without overstating consensus.",
    ],
    "contradiction": [
        "The disagreement therefore looks more like a boundary-condition problem than a settled reversal.",
        "This tension suggests a scoped disagreement rather than a clean consensus.",
        "The contradiction is best read as conditional rather than definitive.",
    ],
    "gap": [
        "That limitation keeps the review's strongest conclusion provisional rather than complete.",
        "This unresolved point narrows how far the current evidence can be generalized.",
        "The gap therefore constrains synthesis more than it blocks it entirely.",
    ],
    "conclusion": [
        "This balance between consistency and uncertainty defines the review's bottom line.",
        "That combined view provides a bounded conclusion rather than an inflated one.",
        "The closing claim is therefore strongest when read with these constraints in view.",
    ],
}


def rewrite_style(sections: list[dict], track: str = "polished") -> list[dict]:
    llm = LLMAdapter()
    if llm.provider != "stub" and llm.base_url and llm._has_auth():
        try:
            rewritten = _rewrite_style_llm(llm, sections, track=track)
            if rewritten:
                return rewritten
        except Exception:
            pass
    return _rewrite_style_rule_based(sections, track=track)


def _rewrite_style_llm(llm: LLMAdapter, sections: list[dict], *, track: str) -> list[dict]:
    rewrite_plan = [_section_rewrite_plan(section, track=track) for section in sections if isinstance(section, dict)]
    system_prompt = (
        "You are an academic editing engine. Constrained polish only eligible paragraphs, preserve structure and citations exactly, "
        "avoid unsupported assertions or exaggerated certainty, and return JSON with sections/paragraphs."
    )
    user_prompt = json.dumps({"track": track, "sections": rewrite_plan}, ensure_ascii=False)
    response = llm.generate_json(system_prompt, user_prompt)
    return _merge_llm_rewrite(sections, _extract_llm_sections(response.content), track=track) or _rewrite_style_rule_based(sections, track=track)


def _rewrite_style_rule_based(sections: list[dict], *, track: str) -> list[dict]:
    return [_rewrite_section_rule_based(section, track=track) for section in sections]


def _rewrite_section_rule_based(section: dict[str, Any], *, track: str) -> dict[str, Any]:
    paragraphs = _section_paragraphs(section)
    if not paragraphs:
        text = _rewrite_paragraph_text(
            str(section.get("text") or ""),
            move_type="conclusion" if _section_is_high_value(section) else "synthesis",
            section=section,
            paragraph={"move_type": "synthesis"},
        ) if _should_polish_paragraph({"move_type": "synthesis"}, track=track, section=section) else str(section.get("text") or "")
        return {**section, "text": text, "track": track}
    rewritten = []
    for paragraph in paragraphs:
        should_polish = _should_polish_paragraph(paragraph, track=track, section=section)
        text = (
            _rewrite_paragraph_text(paragraph.get("text", ""), move_type=str(paragraph.get("move_type") or ""), section=section, paragraph=paragraph)
            if should_polish
            else str(paragraph.get("text", "")).strip()
        )
        rewritten.append({
            **paragraph,
            "text": text,
            "track": "polished" if should_polish else paragraph.get("track", "safe"),
            "polish_pass": should_polish,
            "quality_notes": _paragraph_quality_notes(paragraph, text) if should_polish else paragraph.get("quality_notes", []),
        })
    return {
        **section,
        "text": "\n\n".join(p["text"] for p in rewritten if p.get("text", "").strip()),
        "paragraphs": rewritten,
        "track": track,
    }


def _should_polish_paragraph(paragraph: dict[str, Any], *, track: str, section: dict[str, Any]) -> bool:
    if track != "polished":
        return False
    title = str(section.get("title") or "").lower()
    move = str(paragraph.get("move_type") or "").lower()
    prioritized = bool(paragraph.get("polish_eligible")) or move in _POLISH_MOVES or any(key in title for key in ("conclusion", "discussion"))
    return prioritized or move in {"framing", "evidence"}


def _extract_llm_sections(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, dict):
        items = content.get("sections") or content.get("data") or []
    elif isinstance(content, list):
        items = content
    else:
        items = []
    return [item for item in items if isinstance(item, dict)]


def _merge_llm_rewrite(sections: list[dict], items: list[dict[str, Any]], *, track: str) -> list[dict] | None:
    if len(items) != len(sections):
        return None
    merged = []
    for original, candidate in zip(sections, items):
        original_paragraphs = _section_paragraphs(original)
        candidate_paragraphs = candidate.get("paragraphs")
        if not isinstance(candidate_paragraphs, list) or len(candidate_paragraphs) != len(original_paragraphs):
            return None
        rewritten = []
        for source, cand in zip(original_paragraphs, candidate_paragraphs):
            should_polish = _should_polish_paragraph(source, track=track, section=original)
            text = _clean_rewritten_text(cand.get("text")) if should_polish else source.get("text", "")
            if should_polish:
                text = _enforce_citation_retention(source.get("text", ""), text)
                text = _remove_risky_exaggeration(text)
            rewritten.append({
                **source,
                "text": text,
                "track": "polished" if should_polish else source.get("track", "safe"),
                "polish_pass": should_polish,
                "quality_notes": _paragraph_quality_notes(source, text) if should_polish else source.get("quality_notes", []),
            })
        merged.append({**original, "text": "\n\n".join(p["text"] for p in rewritten), "paragraphs": rewritten, "track": track})
    return merged


def _section_rewrite_plan(section: dict[str, Any], *, track: str) -> dict[str, Any]:
    return {
        "section_id": section.get("section_id") or "",
        "title": section.get("title") or "",
        "track": track,
        "paragraphs": [
            {
                "text": p.get("text", ""),
                "move_type": p.get("move_type", ""),
                "polish": _should_polish_paragraph(p, track=track, section=section),
                "citation_keys": p.get("citation_keys", []),
            }
            for p in _section_paragraphs(section)
        ],
    }


def _section_paragraphs(section: dict[str, Any]) -> list[dict[str, Any]]:
    return [{**item, "text": str(item.get("text") or "").strip()} for item in section.get("paragraphs", []) if isinstance(item, dict) and str(item.get("text") or "").strip()] if isinstance(section.get("paragraphs"), list) else []


def _rewrite_paragraph_text(text: Any, *, move_type: str, section: dict[str, Any], paragraph: dict[str, Any]) -> str:
    rewritten = str(text or "").strip()
    if not rewritten:
        return ""
    rewritten = _normalize_baseline_text(rewritten)
    rewritten = _remove_risky_exaggeration(rewritten)
    rewritten = _move_specific_rewrite(rewritten, move_type=move_type, section=section, paragraph=paragraph)
    rewritten = _enforce_citation_retention(str(text or ""), rewritten)
    rewritten = re.sub(r"\s+", " ", rewritten)
    rewritten = re.sub(r"\s+([,.;:])", r"\1", rewritten)
    return _capitalize_leading_text(rewritten.strip())


def _normalize_baseline_text(text: str) -> str:
    replacements = {
        "It is worth noting that ": "",
        "It should be noted that ": "",
        "it should be noted that ": "",
        "It is important to note that ": "",
        "pivotal": "important",
        "utilize": "use",
        "utilizes": "uses",
        "utilized": "used",
        "This paragraph": "This analysis",
    }
    rewritten = text
    for source, target in replacements.items():
        rewritten = rewritten.replace(source, target)
    rewritten = re.sub(r"\bIn conclusion,\s*", "", rewritten)
    rewritten = re.sub(r"\ba ([aeiouAEIOU])", r"an \1", rewritten)
    return rewritten.strip()


def _move_specific_rewrite(text: str, *, move_type: str, section: dict[str, Any], paragraph: dict[str, Any]) -> str:
    move = str(move_type or "").lower()
    if move not in _POLISH_MOVES:
        return text
    base, citations = _split_trailing_citations(text)
    base = base.strip()
    if not base:
        return text

    if move == "synthesis":
        base = _ensure_intro(base, _pick_phrase(_MOVE_OPENERS[move], base))
        base = _replace_sentence_start(base, ("studies show", "the studies show"), "the evidence converges on")
        if len(re.findall(r"\b(and|while|whereas|however)\b", base.lower())) < 1:
            base = _soft_insert_connector(base, "while the reported effects still depend on study setup")
        base = _ensure_closing(base, _pick_phrase(_MOVE_CLOSERS[move], base))
    elif move == "comparison":
        base = _ensure_intro(base, _pick_phrase(_MOVE_OPENERS[move], base))
        base = _replace_sentence_start(base, ("this comparison",), "the comparison")
        if not re.search(r"\b(compared with|relative to|whereas|while|in contrast)\b", base.lower()):
            base = _soft_insert_connector(base, "with the main differences appearing in how each study frames the outcome")
        base = _ensure_closing(base, _pick_phrase(_MOVE_CLOSERS[move], base))
    elif move == "contradiction":
        base = _ensure_intro(base, _pick_phrase(_MOVE_OPENERS[move], base))
        if not re.search(r"\b(conflict|contradict|disagree|tension|mixed)\b", base.lower()):
            base = _soft_insert_connector(base, "which leaves the evidence mixed rather than fully settled")
        base = _ensure_closing(base, _pick_phrase(_MOVE_CLOSERS[move], base))
    elif move == "gap":
        base = _ensure_intro(base, _pick_phrase(_MOVE_OPENERS[move], base))
        base = re.sub(r"\b(no studies?)\b", "limited evidence", base, flags=re.I)
        if not re.search(r"\b(remains|still|limited|unclear|under-|under tested|inconsistent|unresolved)\b", base.lower()):
            base = _soft_insert_connector(base, "so the outstanding limitation remains visible")
        base = _ensure_closing(base, _pick_phrase(_MOVE_CLOSERS[move], base))
    elif move == "conclusion" or _section_is_high_value(section):
        base = _ensure_intro(base, _pick_phrase(_MOVE_OPENERS["conclusion"], base))
        base = _ensure_closing(base, _pick_phrase(_MOVE_CLOSERS["conclusion"], base))

    return _rejoin_text_and_citations(base, citations)


def _clean_rewritten_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return _capitalize_leading_text(text)


def _capitalize_leading_text(text: str) -> str:
    match = re.search(r"[A-Za-z]", text)
    if not match:
        return text
    idx = match.start()
    return text[:idx] + text[idx].upper() + text[idx + 1 :]


def _split_trailing_citations(text: str) -> tuple[str, str]:
    match = re.search(r"((?:\s*\[[^\]]+\])+)([.?!:]*)\s*$", text)
    if not match:
        return text.strip(), ""
    base = text[: match.start()].rstrip()
    citations = f"{match.group(1).strip()}{match.group(2) or ''}"
    return base, citations


def _rejoin_text_and_citations(base: str, citations: str) -> str:
    if not citations:
        return base.strip()
    end_punct = ""
    if citations[-1] in ".?!":
        end_punct = citations[-1]
        citations = citations[:-1]
    base = base.rstrip(" .;:")
    return f"{base} {citations.strip()}{end_punct}".strip()


def _ensure_intro(text: str, prefix: str) -> str:
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered.startswith(prefix.strip().lower()):
        return stripped
    return f"{prefix}{stripped[0].lower() + stripped[1:] if stripped[:1].isupper() else stripped}"


def _ensure_closing(text: str, closing: str) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not sentences:
        return text
    if closing.lower() in text.lower():
        return text
    if len(sentences) >= 2:
        return text
    return f"{text.rstrip('. ')}. {closing}"


def _pick_phrase(options: list[str], seed_text: str) -> str:
    if not options:
        return ""
    digest = hashlib.md5(seed_text.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(options)
    return options[index]


def _replace_sentence_start(text: str, starters: tuple[str, ...], replacement: str) -> str:
    for starter in starters:
        pattern = re.compile(rf"^{re.escape(starter)}\b", re.I)
        if pattern.search(text):
            return pattern.sub(replacement, text, count=1)
    return text


def _soft_insert_connector(text: str, clause: str) -> str:
    if ";" in text or "," in text:
        return text
    return f"{text.rstrip('. ')}; {clause}."


def _enforce_citation_retention(original: str, candidate: str) -> str:
    original_citations = re.findall(r"\[[^\]]+\]", str(original or ""))
    if not original_citations:
        return candidate
    candidate_citations = re.findall(r"\[[^\]]+\]", str(candidate or ""))
    if candidate_citations == original_citations:
        return candidate
    stripped = re.sub(r"(?:\s*\[[^\]]+\])+[.?!:]*\s*$", "", str(candidate or "")).strip()
    suffix = " ".join(original_citations)
    if stripped.endswith((".", "!", "?")):
        punct = stripped[-1]
        stripped = stripped[:-1].rstrip()
        return f"{stripped} {suffix}{punct}".strip()
    return f"{stripped} {suffix}".strip()


def _remove_risky_exaggeration(text: str) -> str:
    cleaned = text
    for marker in _RISKY_MARKERS:
        cleaned = re.sub(rf"\b{re.escape(marker)}\b", _safer_marker(marker), cleaned, flags=re.I)
    cleaned = re.sub(r"\bno studies\b", "limited evidence", cleaned, flags=re.I)
    cleaned = re.sub(r"\bno evidence\b", "limited evidence", cleaned, flags=re.I)
    return cleaned


def _safer_marker(marker: str) -> str:
    mapping = {
        "prove": "support",
        "proves": "supports",
        "definitive": "stronger",
        "definitively": "more clearly",
        "always": "often",
        "never": "rarely",
        "clearly": "consistently",
        "obviously": "notably",
        "undeniably": "credibly",
        "transformative": "important",
        "breakthrough": "substantive",
    }
    return mapping.get(marker.lower(), marker)


def _section_is_high_value(section: dict[str, Any]) -> bool:
    title = str(section.get("title") or section.get("section_id") or "").lower()
    return any(token in title for token in ("comparison", "contradiction", "gap", "conclusion", "discussion", "synthesis"))


def _paragraph_quality_notes(paragraph: dict[str, Any], rewritten_text: str) -> list[str]:
    notes: list[str] = []
    move = str(paragraph.get("move_type") or "").lower()
    if move in _POLISH_MOVES:
        notes.append(f"polished_{move}_flow")
    if re.findall(r"\[[^\]]+\]", rewritten_text) == re.findall(r"\[[^\]]+\]", str(paragraph.get("text") or "")):
        notes.append("citation_retained")
    if not any(marker in rewritten_text.lower() for marker in _RISKY_MARKERS):
        notes.append("risk_checked")
    return notes
