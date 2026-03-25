from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def _tokenize(text: str) -> set[str]:
    """Extract meaningful n-gram tokens from text."""
    tokens = set()
    text = text.lower()
    words = re.findall(r"[a-z][a-z0-9]{2,}", text)
    for w in words:
        tokens.add(w)
    for i in range(len(words) - 1):
        tokens.add(f"{words[i]} {words[i+1]}")
    for i in range(len(words) - 2):
        tokens.add(f"{words[i]} {words[i+1]} {words[i+2]}")
    return tokens


_TOPIC_STOPWORDS = {
    "automated", "literature", "review", "system", "systems", "approach",
    "approaches", "paper", "papers", "study", "studies", "research",
    "section", "result", "results", "show", "shows", "finding", "findings",
    "using", "used", "based", "propose", "proposed", "demonstrate",
    "demonstrates", "nlp", "llm", "generation", "knowledge", "synthesis",
    "task", "tasks", "method", "methods",
}


def _count_paper_mentions(section_text: str, paper_id: str, paper_row: dict) -> int:
    """Count how many times a paper is directly referenced in the section text."""
    pid = paper_id.lower()
    # Direct ID mentions
    count = section_text.lower().count(pid)
    # Also check claim text snippets as indirect mentions
    claim = (paper_row.get("claim_text") or "").lower()
    if len(claim) > 15:
        # Check if a meaningful substring of claim appears in section text
        short_claim = " ".join(claim.split()[:6])
        if len(short_claim) > 10:
            count += section_text.lower().count(short_claim[:20])
    return count


def _score_paper_for_section(
    section_topic_tokens: set[str],
    section_claim_types: set[str],
    paper_row: dict[str, Any],
    section_text: str,
    planner_tokens: set[str] | None = None,
) -> float:
    """Score paper relevance to a section.

    Positive signals:
    - Topic keyword overlap (heavily weighted)
    - Claim-type alignment with section focus
    - Direct paper/claim mention in section text
    - Specific match in method_family, tasks, metrics fields

    Negative signals:
    - Paper's limitations conflict with section focus
    """
    score = 0.0
    pid = paper_row.get("paper_id", "")

    # Tokenize paper fields
    paper_fields_text = " ".join([
        paper_row.get("claim_text", ""),
        paper_row.get("method_summary", ""),
        paper_row.get("method_family", ""),
        paper_row.get("tasks", ""),
        paper_row.get("research_problem", ""),
        paper_row.get("title", ""),
        paper_row.get("metrics", ""),
        paper_row.get("limitations", ""),
    ])
    paper_tokens = _tokenize(paper_fields_text)

    # Core topic overlap (without stopwords)
    relevant_section = section_topic_tokens - _TOPIC_STOPWORDS
    relevant_paper = paper_tokens - _TOPIC_STOPWORDS
    overlap = relevant_section & relevant_paper
    score += 4.0 * len(overlap)

    if planner_tokens:
        planner_overlap = (planner_tokens - _TOPIC_STOPWORDS) & relevant_paper
        score += 6.0 * len(planner_overlap)

    # Claim-type alignment
    paper_ct = (paper_row.get("claim_type") or "").lower()
    if paper_ct in section_claim_types:
        score += 3.0
    elif section_claim_types:
        # Partial credit if section is about a related type
        if "performance" in section_claim_types and paper_ct == "methodological":
            score += 0.5
        if "methodological" in section_claim_types and paper_ct == "performance":
            score += 0.5

    # Method family specificity
    mf = paper_row.get("method_family", "")
    if mf:
        mf_tokens = _tokenize(mf)
        mf_overlap = mf_tokens & relevant_section
        score += 2.0 * len(mf_overlap)

    # Tasks specificity
    tasks = paper_row.get("tasks", "")
    if tasks:
        task_tokens = _tokenize(tasks)
        task_overlap = task_tokens & relevant_section
        score += 1.5 * len(task_overlap)

    # Metrics specificity (important for evaluation sections)
    metrics = paper_row.get("metrics", "") or ""
    metrics_tokens = _tokenize(metrics)
    metrics_overlap = metrics_tokens & relevant_section
    score += 2.0 * len(metrics_overlap)

    # Limitations as negative signal
    limitations = paper_row.get("limitations", "") or ""
    lim_tokens = _tokenize(limitations)
    lim_overlap = lim_tokens & relevant_section
    score += 1.0 * len(lim_overlap)

    # Direct mention count in section text
    mention_count = _count_paper_mentions(section_text, pid, paper_row)
    score += 1.5 * mention_count

    # Explicit paper-id mention in text
    if pid.lower() in section_text.lower():
        score += 2.0

    return score


def _infer_section_focus(title: str, objective: str) -> tuple[set[str], set[str]]:
    """Infer topic tokens and claim-type focus from section title + objective."""
    combined = f"{title} {objective}".lower()
    tokens = _tokenize(combined)
    title_words = set(re.findall(r"\w+", combined))

    # Claim-type focus
    claim_types: set[str] = set()
    if any(w in title_words for w in ["method", "approach", "technical", "architecture", "model"]):
        claim_types.add("methodological")
    if any(w in title_words for w in ["performance", "metric", "evalu", "accuracy", "f1", "rouge", "precision", "recall", "auc"]):
        claim_types.add("performance")
    if any(w in title_words for w in ["language", "multilingual", "chinese", "cross-lingual", "coverage", "corpus", "english"]):
        claim_types.add("coverage")
    if any(w in title_words for w in ["evidence", "ground", "verif", "claim", "cite", "citation"]):
        claim_types.add("evidence")
    if any(w in title_words for w in ["gap", "future", "opportun", "open", "problem", "challeng"]):
        claim_types.add("gap")
    if any(w in title_words for w in ["intro", "background", "context", "motiv", "scope"]):
        claim_types.add("intro")

    topic_tokens = tokens - _TOPIC_STOPWORDS
    return topic_tokens, claim_types


def _normalize_paragraphs(section: dict[str, Any]) -> list[dict[str, Any]]:
    """Return paragraph objects while preserving existing paragraph metadata when present."""
    raw_paragraphs = section.get("paragraphs")
    normalized: list[dict[str, Any]] = []

    if isinstance(raw_paragraphs, list):
        for item in raw_paragraphs:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if text:
                    normalized.append({**item, "text": text})
            elif isinstance(item, str):
                text = item.strip()
                if text:
                    normalized.append({"text": text})

    if normalized:
        return normalized

    section_text = str(section.get("text") or "").strip()
    if not section_text:
        return []

    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n+", section_text) if chunk.strip()]
    if not chunks:
        chunks = [section_text]
    return [{"text": chunk} for chunk in chunks]


def _coerce_string_list(value: Any) -> list[str]:
    """Flatten planner metadata into a stable list of strings."""
    items: list[str] = []
    if value is None:
        return items
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        for key in ("paper_id", "citation_key", "citation_target", "id", "key", "theme_id", "gap_id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return [candidate.strip()]
        return []
    if isinstance(value, (list, tuple, set)):
        for item in value:
            items.extend(_coerce_string_list(item))
        return items
    text = str(value).strip()
    return [text] if text else []


def _planner_signal_text(paragraph: dict[str, Any], section: dict[str, Any]) -> str:
    """Collect planner context that can bias grounding without hard-coding paper ids."""
    pieces: list[str] = []
    for source in (section, paragraph):
        if not isinstance(source, dict):
            continue
        theme_refs = source.get("theme_refs")
        if isinstance(theme_refs, list):
            for item in theme_refs:
                if isinstance(item, dict):
                    for key in ("label", "theme_id", "synthesis_note"):
                        text = str(item.get(key) or "").strip()
                        if text:
                            pieces.append(text)
        gap_refs = source.get("gap_refs")
        if isinstance(gap_refs, list):
            for item in gap_refs:
                if isinstance(item, dict):
                    for key in ("gap_statement", "research_need", "practical_consequence", "why_insufficient"):
                        text = str(item.get(key) or "").strip()
                        if text:
                            pieces.append(text)
        supporting_points = source.get("supporting_points")
        if isinstance(supporting_points, list):
            for item in supporting_points:
                text = str(item).strip()
                if text:
                    pieces.append(text)
    return " ".join(pieces)


def _planner_targets(
    paragraph: dict[str, Any],
    section: dict[str, Any],
    valid_pids: set[str],
) -> list[str]:
    """Extract explicit planner targets and keep only ids that exist in the matrix."""
    raw_targets: list[str] = []
    for source in (section, paragraph):
        if not isinstance(source, dict):
            continue
        raw_targets.extend(_coerce_string_list(source.get("citation_targets")))
        raw_targets.extend(_coerce_string_list(source.get("supporting_citations")))
    return _dedupe_preserve([pid for pid in raw_targets if pid in valid_pids])


def _merge_citation_keys(
    explicit_targets: list[str],
    paper_scores: list[tuple[str, float]],
    top_k: int,
) -> list[str]:
    """Keep planner targets first, then fill with scored fallback citations."""
    ordered = _dedupe_preserve(explicit_targets)
    seen = set(ordered)
    for pid, _ in paper_scores:
        if pid in seen:
            continue
        ordered.append(pid)
        seen.add(pid)
        if len(ordered) >= top_k:
            break
    return ordered[: max(top_k, len(_dedupe_preserve(explicit_targets)))]


def _select_top_keys(
    paper_scores: list[tuple[str, float]],
    unique_pids: list[str],
    top_k: int,
) -> tuple[list[str], list[tuple[str, float]]]:
    positive = [(pid, sc) for pid, sc in paper_scores if sc > 0]
    if positive:
        return [pid for pid, _ in positive[:top_k]], positive
    if unique_pids:
        return unique_pids[: min(top_k, len(unique_pids))], []
    return [], []


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def ground_citations(sections: list[dict], matrix: list[dict]) -> list[dict]:
    """Score and assign the most relevant citations to each section and paragraph."""
    if not sections or not matrix:
        return sections

    unique_pids = []
    seen = set()
    rows_by_pid: dict[str, list[dict]] = defaultdict(list)
    for row in matrix:
        pid = row.get("paper_id")
        if not pid:
            continue
        rows_by_pid[pid].append(row)
        if pid not in seen:
            seen.add(pid)
            unique_pids.append(pid)

    grounded = []
    for section in sections:
        title = section.get("title", "")
        objective = section.get("objective", "")
        section_text = section.get("text", "")
        topic_tokens, section_claim_types = _infer_section_focus(title, objective)
        title_lower = title.lower()
        valid_pids = set(unique_pids)

        paper_scores: list[tuple[str, float]] = []
        for pid, rows in rows_by_pid.items():
            score = max(_score_paper_for_section(topic_tokens, section_claim_types, row, section_text) for row in rows)
            paper_scores.append((pid, score))

        paper_scores.sort(key=lambda x: x[1], reverse=True)

        if "intro" in section_claim_types or "background" in title_lower:
            section_top_k = 3
            paragraph_top_k = 2
        else:
            section_top_k = 2
            paragraph_top_k = 1

        section_explicit_targets = _planner_targets(section, section, valid_pids)

        paragraphs = []
        paragraph_keys: list[str] = []
        for paragraph in _normalize_paragraphs(section):
            paragraph_text = paragraph.get("text", "")
            paragraph_topic_tokens = (topic_tokens | (_tokenize(paragraph_text) - _TOPIC_STOPWORDS)) - _TOPIC_STOPWORDS
            planner_tokens = _tokenize(_planner_signal_text(paragraph, section))
            paragraph_targets = _planner_targets(paragraph, section, valid_pids)
            paragraph_scores: list[tuple[str, float]] = []
            for pid, rows in rows_by_pid.items():
                score = max(
                    _score_paper_for_section(
                        paragraph_topic_tokens,
                        section_claim_types,
                        row,
                        paragraph_text,
                        planner_tokens=planner_tokens,
                    )
                    for row in rows
                )
                paragraph_scores.append((pid, score))
            paragraph_scores.sort(key=lambda x: x[1], reverse=True)
            para_keys = _merge_citation_keys(paragraph_targets, paragraph_scores, paragraph_top_k)
            paragraph_keys.extend(para_keys)
            paragraph_payload = {**paragraph, "citation_keys": para_keys}
            positive_paragraph_scores = [(pid, sc) for pid, sc in paragraph_scores if sc > 0]
            if positive_paragraph_scores:
                paragraph_payload["_citation_scores"] = {pid: round(sc, 1) for pid, sc in positive_paragraph_scores[:4]}
            if paragraph_targets:
                paragraph_payload["_citation_rationale"] = {
                    "strategy": "planner_targets",
                    "targets": paragraph_targets,
                }
            paragraphs.append(paragraph_payload)

        section_keys = _dedupe_preserve(section_explicit_targets + paragraph_keys)
        if not section_keys:
            section_keys, positive = _select_top_keys(paper_scores, unique_pids, section_top_k)
        else:
            positive = [(pid, sc) for pid, sc in paper_scores if sc > 0]

        grounded_section = {**section, "citation_keys": section_keys, "paragraphs": paragraphs}
        if positive:
            grounded_section["_citation_scores"] = {pid: round(sc, 1) for pid, sc in positive[:4]}
        if section_explicit_targets:
            grounded_section["_citation_rationale"] = {
                "strategy": "planner_targets",
                "targets": section_explicit_targets,
            }
        grounded.append(grounded_section)

    return grounded
