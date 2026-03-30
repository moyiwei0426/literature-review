"""
Smoke tests for ShadowReviewer.
"""
from __future__ import annotations

import pytest
from services.writing.shadow_reviewer import (
    ShadowReviewer,
    ShadowReport,
    CritiqueFinding,
    CritiqueRound,
    _parse_critique,
    _diff_sections,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINIMAL_SECTIONS = [
    {
        "section_id": "sec-1",
        "title": "Introduction",
        "text": "Pedestrian safety at intersections is a critical concern. "
                "Studies show that gap acceptance is the dominant factor in crossing decisions. "
                "This review synthesizes 10 papers.",
        "paragraphs": [
            {
                "text": "Pedestrian safety at intersections is a critical concern.",
                "move_type": "framing",
                "purpose": "Establish stakes",
            },
            {
                "text": "Studies show that gap acceptance is the dominant factor in crossing decisions.",
                "move_type": "evidence",
                "purpose": "Cite primary finding",
            },
            {
                "text": "This review synthesizes 10 papers.",
                "move_type": "synthesis",
                "purpose": "Scope statement",
            },
        ],
    },
    {
        "section_id": "sec-2",
        "title": "Methodological Approaches",
        "text": "Four methodological paradigms appear in this corpus: discrete choice models, "
                "social force models, neural networks, and random forests.",
        "paragraphs": [
            {
                "text": "Four methodological paradigms appear in this corpus: "
                        "discrete choice models, social force models, neural networks, and random forests.",
                "move_type": "framing",
                "purpose": "Announce taxonomy",
            },
        ],
    },
]

_MINIMAL_MATRIX = [
    {
        "paper_id": "Chen2020",
        "claim_text": "Neural network achieves 89% accuracy on gap acceptance prediction",
        "method_family": "neural network",
    },
    {
        "paper_id": "Wang2019",
        "claim_text": "Discrete choice model shows waiting time as strongest predictor",
        "method_family": "discrete choice model",
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_shadow_reviewer_init():
    r = ShadowReviewer(shadow_model="gpt-4o", max_rounds=2, strict=True)
    assert r.shadow_model == "gpt-4o"
    assert r.max_rounds == 2
    assert r.strict is True


def test_shadow_reviewer_stub_mode_returns_report():
    """Stub model should return a ShadowReport without crashing."""
    r = ShadowReviewer(shadow_model="stub-model", max_rounds=1, strict=True)
    report = r.review(_MINIMAL_SECTIONS, _MINIMAL_MATRIX)
    assert isinstance(report, ShadowReport)
    assert report.section_count == len(_MINIMAL_SECTIONS)
    assert isinstance(report.rounds, list)
    assert isinstance(report.final_sections, list)
    assert len(report.final_sections) == len(_MINIMAL_SECTIONS)


def test_shadow_reviewer_respects_max_rounds():
    r = ShadowReviewer(shadow_model="stub-model", max_rounds=2, strict=False)
    report = r.review(_MINIMAL_SECTIONS, _MINIMAL_MATRIX)
    assert len(report.rounds) <= 2


def test_shadow_reviewer_strict_exits_early():
    """strict=True should exit after first round with no critical flaws."""
    r = ShadowReviewer(shadow_model="stub-model", max_rounds=3, strict=True)
    report = r.review(_MINIMAL_SECTIONS, _MINIMAL_MATRIX)
    # Stub always returns empty findings, so strict=True should exit after 1 round
    assert len(report.rounds) == 1


def test_shadow_report_to_dict():
    finding = CritiqueFinding(
        section_id="sec-1",
        section_title="Introduction",
        severity="CRITICAL_FLAW",
        location="paragraph 2",
        claim="dominant factor claim",
        evidence="matrix contradicts this",
        fix_guidance="qualify the claim",
        paper_refs=["Chen2020"],
    )
    round_obj = CritiqueRound(
        round=1,
        findings=[finding],
        critique_text='{"findings": []}',
        has_critical_flaws=True,
    )
    report = ShadowReport(
        section_count=2,
        rounds=[round_obj],
        final_sections=_MINIMAL_SECTIONS,
        adopted_fixes=["fixed sec-1 claim overgeneralization"],
        overall_stable=False,
    )
    d = report.to_dict()
    assert d["section_count"] == 2
    assert d["overall_stable"] is False
    assert len(d["rounds"]) == 1
    assert d["rounds"][0]["findings"][0]["severity"] == "CRITICAL_FLAW"


def test_shadow_report_summary():
    finding = CritiqueFinding(
        section_id="sec-1", section_title="Intro",
        severity="CRITICAL_FLAW", location="para 2",
        claim="claim", evidence="ev", fix_guidance="fix",
    )
    round_obj = CritiqueRound(
        round=1, findings=[finding],
        critique_text="", has_critical_flaws=True,
    )
    report = ShadowReport(
        section_count=2, rounds=[round_obj],
        final_sections=[], adopted_fixes=[], overall_stable=False,
    )
    s = report.summary()
    assert "1 CRITICAL_FLAW" in s
    assert "stable=False" in s


def test_parse_critique_with_flaw():
    # Build valid JSON string using concatenation with regular (non-f) strings
    raw = '{"findings": [{"section_id": "sec-1", "severity": "CRITICAL_FLAW", ' \
          '"location": "paragraph 2", "claim": "gap acceptance is dominant", ' \
          '"evidence": "no matrix support for this claim", ' \
          '"fix_guidance": "qualify the claim", ' \
          '"paper_refs": ["Chen2020"]}]}'
    findings, parsed_ok = _parse_critique(raw, _MINIMAL_SECTIONS)
    assert parsed_ok is True
    assert len(findings) == 1
    assert findings[0].severity == "CRITICAL_FLAW"
    assert findings[0].paper_refs == ["Chen2020"]


def test_parse_critique_empty():
    raw = '{"findings": []}'
    findings, parsed_ok = _parse_critique(raw, _MINIMAL_SECTIONS)
    assert parsed_ok is True
    assert len(findings) == 0


def test_parse_critique_malformed():
    findings, parsed_ok = _parse_critique("not json at all", _MINIMAL_SECTIONS)
    assert parsed_ok is False
    assert len(findings) == 0


def test_parse_critique_strips_markdown():
    raw = '''
    ```json
    {"findings": [{"section_id": "sec-1", "severity": "WARNING",
    "location": "intro", "claim": "vague claim",
    "evidence": "needs specificity", "fix_guidance": "be specific",
    "paper_refs": []}]}
    ```
    '''
    findings, parsed_ok = _parse_critique(raw, _MINIMAL_SECTIONS)
    assert parsed_ok is True
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"


def test_diff_sections_tracks_fixes():
    before = [{"section_id": "sec-1", "text": "original"}]
    after = [{"section_id": "sec-1", "text": "revised", "_shadow_fixes": ["fixed claim"]}]
    diff = _diff_sections(before, after)
    assert "fixed claim" in diff
