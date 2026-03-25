from __future__ import annotations

import re
from collections import defaultdict

from core.models import PaperProfile


_WORD_RE = re.compile(r"[a-z][a-z0-9]{2,}")
_STOP = {
    "pedestrian", "crossing", "behavior", "behaviour", "analysis", "study", "model",
    "task", "tasks", "effect", "factors", "factor", "results", "paper", "traffic",
    "road", "signal", "signals", "intersection", "intersections",
}
_POSITIVE = {"increase", "increases", "higher", "improve", "improves", "more", "greater", "positive"}
_NEGATIVE = {"decrease", "decreases", "lower", "reduce", "reduces", "less", "negative"}
_VARIABLE_MARKERS = {
    "gender", "female", "male", "age", "elderly", "older", "companion", "pedestrians",
    "waiting", "time", "green", "red", "traffic", "volume", "vehicles", "vehicle",
    "lanes", "purpose", "hurry", "facility", "quality", "social", "violations",
}
# Canonical variable short-phrase signatures for strict variable-overlap detection
_VARIABLE_PHRASES = [
    {"female", "male", "gender", "sex"},
    {"age", "older", "elderly", "young"},
    {"companion", "group", "pedestrians", "waiting"},
    {"time", "waiting", "delay", "green", "red"},
    {"traffic", "volume", "vehicles", "vehicle"},
    {"hurry", "purpose", "trip"},
]


def _task_signature(task: str) -> tuple[str, ...]:
    words = [w for w in _WORD_RE.findall((task or "").lower()) if w not in _STOP]
    return tuple(sorted(set(words)))


def _same_task_family(task_a: str, task_b: str) -> bool:
    a = set(_task_signature(task_a))
    b = set(_task_signature(task_b))
    if not a or not b:
        return False
    overlap = len(a & b)
    return overlap >= 2 or (overlap >= 1 and min(len(a), len(b)) <= 2)


def _claim_topic_signature(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOP}


def _claim_variable_signature(text: str) -> set[str]:
    words = set(_WORD_RE.findall((text or "").lower()))
    return words & _VARIABLE_MARKERS


def _shared_phrase_group(a_words: set[str], b_words: set[str]) -> bool:
    for phrase in _VARIABLE_PHRASES:
        overlap = a_words & phrase & b_words
        if len(overlap) >= 1:
            return True
    return False


def _claim_polarity(text: str) -> int:
    words = set(_WORD_RE.findall((text or "").lower()))
    pos = len(words & _POSITIVE)
    neg = len(words & _NEGATIVE)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def _has_real_cross_paper_conflict(claims: list[dict]) -> bool:
    for i, a in enumerate(claims):
        for b in claims[i + 1:]:
            if a["paper_id"] == b["paper_id"]:
                continue
            a_words = set(_WORD_RE.findall((a["claim_text"] or "").lower()))
            b_words = set(_WORD_RE.findall((b["claim_text"] or "").lower()))
            if not _shared_phrase_group(a_words, b_words):
                continue
            topic_overlap = _claim_topic_signature(a["claim_text"]) & _claim_topic_signature(b["claim_text"])
            if len(topic_overlap) < 5:
                continue
            pa = _claim_polarity(a["claim_text"])
            pb = _claim_polarity(b["claim_text"])
            if pa != 0 and pb != 0 and pa != pb:
                return True
    return False


def detect_contradictions(profiles: list[PaperProfile]) -> dict:
    task_to_claims = defaultdict(list)
    normalized_groups: list[dict] = []

    for profile in profiles:
        for task in profile.tasks:
            for claim in profile.main_claims:
                task_to_claims[task].append(
                    {
                        "paper_id": profile.paper_id,
                        "claim_id": claim.claim_id,
                        "claim_text": claim.claim_text,
                        "claim_type": claim.claim_type.value if hasattr(claim.claim_type, 'value') else str(claim.claim_type),
                    }
                )

    contradictions = []
    tasks = list(task_to_claims.keys())
    used = set()
    for i, task in enumerate(tasks):
        if task in used:
            continue
        family_tasks = [task]
        used.add(task)
        for other in tasks[i + 1:]:
            if other not in used and _same_task_family(task, other):
                family_tasks.append(other)
                used.add(other)

        family_claims = []
        family_papers = set()
        for t in family_tasks:
            family_claims.extend(task_to_claims[t])
            family_papers.update(item["paper_id"] for item in task_to_claims[t])

        has_conflict = len(family_papers) >= 2 and _has_real_cross_paper_conflict(family_claims)
        normalized_groups.append({
            "tasks": family_tasks,
            "paper_count": len(family_papers),
            "claims": family_claims,
            "has_conflict": has_conflict,
        })

        if has_conflict:
            contradictions.append(
                {
                    "task": family_tasks[0],
                    "related_tasks": family_tasks,
                    "reason": "Potential cross-paper contradiction detected: overlapping claim topic with opposite directional signal.",
                    "claims": family_claims,
                }
            )

    return {
        "task_groups": dict(task_to_claims),
        "normalized_task_groups": normalized_groups,
        "contradictions": contradictions,
        "contradiction_count": len(contradictions),
    }
