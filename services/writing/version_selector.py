from __future__ import annotations

from typing import Any


def select_best_version(safe_track: dict[str, Any], polished_track: dict[str, Any] | None = None) -> dict[str, Any]:
    polished_track = polished_track or {}
    safe_scorecard = _build_scorecard(safe_track, name="safe")
    polished_scorecard = _build_scorecard(polished_track, name="polished")

    polished_available = bool(polished_track.get("sections"))
    polished_guard_failed = polished_scorecard["hard_risk"] > 0
    quality_gain = polished_scorecard["quality_score"] - safe_scorecard["quality_score"]
    risk_delta = polished_scorecard["risk_score"] - safe_scorecard["risk_score"]

    selected = "safe"
    reason = "safe_default"
    if polished_available:
        if polished_guard_failed:
            selected = "safe"
            reason = "safe_due_to_hard_risk"
        elif quality_gain >= 0 and risk_delta <= 1:
            selected = "polished"
            reason = "polished_quality_gain_within_risk_budget"
        elif quality_gain >= 3 and risk_delta <= 3:
            selected = "polished"
            reason = "polished_quality_gain_offsets_minor_risk"
        else:
            selected = "safe"
            reason = "safe_more_reliable_after_quality_risk_tradeoff"

    chosen = polished_track if selected == "polished" else safe_track
    return {
        "selected_track": selected,
        "selected_sections": chosen.get("sections", []),
        "selection_report": {
            "safe_score": safe_scorecard["composite_score"],
            "polished_score": polished_scorecard["composite_score"],
            "quality_gain": quality_gain,
            "risk_delta": risk_delta,
            "reason": reason,
            "safe": safe_scorecard,
            "polished": polished_scorecard,
        },
    }


def _build_scorecard(track: dict[str, Any], *, name: str) -> dict[str, Any]:
    if not track:
        return {
            "name": name,
            "composite_score": -(10**6),
            "quality_score": -(10**6),
            "risk_score": 10**6,
            "hard_risk": 1,
            "signals": {},
        }

    section_report = track.get("section_validation", {}) if isinstance(track.get("section_validation"), dict) else {}
    para_report = track.get("paragraph_validation", {}) if isinstance(track.get("paragraph_validation"), dict) else {}
    metrics = track.get("metrics", {}) if isinstance(track.get("metrics"), dict) else {}
    sections = track.get("sections", []) if isinstance(track.get("sections"), list) else []

    section_findings = int(section_report.get("summary", {}).get("finding_count", 0) or 0)
    paragraph_findings = int(para_report.get("summary", {}).get("finding_count", 0) or 0)
    section_status = str(section_report.get("status") or "")
    paragraph_status = str(para_report.get("status") or "")
    extended_findings = section_report.get("extended_findings", []) if isinstance(section_report.get("extended_findings"), list) else []
    para_findings = para_report.get("findings", []) if isinstance(para_report.get("findings"), list) else []

    signals = {
        "section_status_bonus": {"pass": 24, "warn": 12, "fail": 0}.get(section_status, 0),
        "paragraph_status_bonus": {"pass": 12, "warn": 6, "fail": 0}.get(paragraph_status, 0),
        "quality_notes": _count_quality_notes(sections),
        "high_value_polish": _count_high_value_polish(sections),
        "section_count": len(sections),
        "section_findings": section_findings,
        "paragraph_findings": paragraph_findings,
        "citation_outside_bundle": _count_findings(para_findings, "citation_outside_bundle"),
        "insufficient_citations": _count_findings(para_findings, "insufficient_citations"),
        "polish_guard_failed": _count_findings(para_findings, "polish_guard_failed"),
        "missing_structured_paragraphs": _count_findings(extended_findings, "missing_structured_paragraphs"),
        "citation_retention_penalty": int(metrics.get("citation_retention_penalty", 0) or 0),
        "unsupported_assertion_penalty": int(metrics.get("unsupported_assertion_penalty", 0) or 0),
        "role_drift_penalty": int(metrics.get("role_drift_penalty", 0) or 0),
        "overstatement_penalty": int(metrics.get("overstatement_penalty", 0) or 0),
    }

    quality_score = (
        signals["section_status_bonus"]
        + signals["paragraph_status_bonus"]
        + signals["quality_notes"]
        + signals["high_value_polish"] * 2
        + min(len(sections), 8)
        - section_findings
        - paragraph_findings
    )
    risk_score = (
        signals["citation_outside_bundle"] * 8
        + signals["insufficient_citations"] * 5
        + signals["polish_guard_failed"] * 4
        + signals["missing_structured_paragraphs"] * 6
        + signals["citation_retention_penalty"] * 8
        + signals["unsupported_assertion_penalty"] * 7
        + signals["role_drift_penalty"] * 5
        + signals["overstatement_penalty"] * 4
        + (12 if section_status == "fail" else 0)
        + (8 if paragraph_status == "fail" else 0)
    )
    hard_risk = (
        signals["citation_outside_bundle"]
        + signals["citation_retention_penalty"]
        + signals["unsupported_assertion_penalty"]
        + signals["role_drift_penalty"]
    )
    composite_score = quality_score - risk_score

    return {
        "name": name,
        "composite_score": composite_score,
        "quality_score": quality_score,
        "risk_score": risk_score,
        "hard_risk": hard_risk,
        "signals": signals,
    }


def _count_findings(findings: list[dict[str, Any]], code: str) -> int:
    return len([finding for finding in findings if str(finding.get("code") or "") == code])


def _count_quality_notes(sections: list[dict[str, Any]]) -> int:
    count = 0
    for section in sections:
        paragraphs = section.get("paragraphs", []) if isinstance(section.get("paragraphs"), list) else []
        for paragraph in paragraphs:
            notes = paragraph.get("quality_notes", []) if isinstance(paragraph.get("quality_notes"), list) else []
            count += len(notes)
    return count


def _count_high_value_polish(sections: list[dict[str, Any]]) -> int:
    high_value_moves = {"synthesis", "comparison", "contradiction", "gap", "conclusion"}
    count = 0
    for section in sections:
        paragraphs = section.get("paragraphs", []) if isinstance(section.get("paragraphs"), list) else []
        for paragraph in paragraphs:
            if paragraph.get("track") == "polished" and str(paragraph.get("move_type") or "").lower() in high_value_moves:
                count += 1
    return count
