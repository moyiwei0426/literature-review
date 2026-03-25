from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.llm.adapter import LLMAdapter
from .gap_normalizers import normalize_gap_list


_DEF_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "gap" / "verifier_system.txt"


def verify_gaps(candidate_gaps: list[dict[str, Any]], coverage: dict[str, Any], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Verify gaps conservatively with deterministic evidence checks."""
    return _verify_gaps_rule_based(candidate_gaps, coverage, matrix)


def _verify_gaps_llm(llm: LLMAdapter, candidate_gaps: list[dict[str, Any]], coverage: dict[str, Any], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    system_prompt = _DEF_PROMPT_PATH.read_text(encoding="utf-8") + "\nReturn JSON with key verified_gaps as a list of structured gaps."
    user_prompt = (
        "Verify the following candidate literature-review gaps. Add counter evidence where needed and calibrate status.\n\n"
        f"Candidate gaps:\n{json.dumps(candidate_gaps, ensure_ascii=False)}\n\n"
        f"Coverage:\n{json.dumps(coverage, ensure_ascii=False)}\n\n"
        f"Matrix:\n{json.dumps(matrix, ensure_ascii=False)}"
    )
    response = llm.generate_json(system_prompt, user_prompt)
    payload = response.content
    items = payload.get("verified_gaps") if isinstance(payload, dict) else []
    normalized = normalize_gap_list(items, default_status="verified")
    return normalized or _verify_gaps_rule_based(candidate_gaps, coverage, matrix)


def _verify_gaps_rule_based(candidate_gaps: list[dict[str, Any]], coverage: dict[str, Any], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    has_chinese = coverage.get("language_distribution", {}).get("chinese", 0) > 0 or coverage.get("chinese_coverage_count", 0) > 0

    for gap in candidate_gaps:
        item = dict(gap)
        counter_evidence = list(item.get("counter_evidence", []))

        if item.get("gap_type") == "language" and has_chinese:
            counter_evidence.append("Chinese-language or Chinese-context coverage exists in the current profile set.")

        if item.get("gap_type") == "evaluation":
            metric_rows = sum(1 for row in matrix if row.get("metrics"))
            if metric_rows > 0:
                counter_evidence.append(f"Found {metric_rows} matrix rows with metric information.")

        if item.get("gap_type") == "comparison":
            supporting = " ".join(str(x) for x in item.get("supporting_evidence", []))
            if "cross_paper_task_groups=0" in supporting or "contradiction_count=0" in supporting:
                counter_evidence.append("No cross-paper contradiction signal remained after normalization.")

        item["counter_evidence"] = counter_evidence
        item["status"] = "verified" if not counter_evidence else "rejected"
        item.update(_structured_gap_fields(item, coverage, matrix))
        verified.append(item)

    return verified


def _structured_gap_fields(gap: dict[str, Any], coverage: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, Any]:
    gap_type = str(gap.get("gap_type") or "coverage").lower()
    paper_ids = _select_partial_evidence_paper_ids(gap_type, matrix)
    paper_count = coverage.get("paper_count", len({row.get("paper_id") for row in matrix if row.get("paper_id")}))
    chinese_count = coverage.get("chinese_coverage_count", 0)
    metric_rows = sum(1 for row in matrix if row.get("metrics"))
    contradiction_rows = sum(1 for row in matrix if row.get("claim_text"))

    partial_summary = ""
    why_insufficient = ""
    practical_consequence = ""
    research_need = ""

    if gap_type == "language":
        partial_summary = (
            f"The current corpus covers {paper_count} papers, but only {chinese_count} Chinese-language or Chinese-context studies are explicitly represented."
        )
        why_insufficient = (
            "the available evidence is drawn from a narrow language and context distribution, so transferability to underrepresented settings cannot be checked"
        )
        practical_consequence = (
            "review conclusions may overfit the dominant publication languages and miss region-specific behavioral or deployment conditions"
        )
        research_need = (
            "targeted inclusion and comparative analysis of Chinese-language or Chinese-context studies with compatible reporting fields"
        )
    elif gap_type == "comparison":
        partial_summary = (
            f"The matrix retains {contradiction_rows} claim-bearing rows, indicating partially overlapping evidence but unresolved cross-paper differences."
        )
        why_insufficient = (
            "studies that appear comparable still use different task definitions, context windows, or comparison criteria, which weakens direct alignment"
        )
        practical_consequence = (
            "reviewers cannot distinguish true substantive disagreement from artifacts introduced by inconsistent comparison setup"
        )
        research_need = (
            "head-to-head study designs or review matrices that standardize task grouping, claim framing, and contradiction checks across papers"
        )
    elif gap_type == "evaluation":
        partial_summary = (
            f"The corpus contains {len(matrix)} matrix rows, but only {metric_rows} rows expose reusable metric information for cross-paper evaluation."
        )
        why_insufficient = (
            "too few studies report metrics in a consistent, reusable form for rigorous comparison or downstream benchmarking"
        )
        practical_consequence = (
            "section-level synthesis must stay narrative because cross-paper performance claims cannot be normalized with confidence"
        )
        research_need = (
            "common evaluation protocols and explicit metric reporting conventions that let future reviews compare outcomes on the same scale"
        )
    else:
        partial_summary = (
            f"The current evidence base includes {paper_count} papers and {len(matrix)} matrix rows that partially touch this topic, but the support remains fragmented."
        )
        why_insufficient = (
            "the available studies do not yet cover the gap with enough breadth, alignment, or reporting detail to support a strong synthesis"
        )
        practical_consequence = (
            "the review can identify the direction of the problem, but it cannot yet generalize a stable field-level conclusion"
        )
        research_need = (
            "additional studies that extend coverage while using directly comparable task, method, and reporting definitions"
        )

    return {
        "partial_evidence_paper_ids": paper_ids,
        "partial_evidence_summary": partial_summary,
        "why_insufficient": why_insufficient,
        "practical_consequence": practical_consequence,
        "research_need": research_need,
        "resolution_needed": research_need,
        "partial_evidence": gap.get("partial_evidence") or partial_summary,
        "insufficiency_reason": gap.get("insufficiency_reason") or why_insufficient,
        "consequence": gap.get("consequence") or practical_consequence,
    }


def _select_partial_evidence_paper_ids(gap_type: str, matrix: list[dict[str, Any]]) -> list[str]:
    if not matrix:
        return []

    def row_score(row: dict[str, Any]) -> int:
        score = 0
        if row.get("paper_id"):
            score += 1
        if gap_type == "evaluation" and row.get("metrics"):
            score += 3
        if gap_type == "comparison" and row.get("claim_text"):
            score += 3
        if gap_type == "language" and (row.get("title") or row.get("research_problem") or row.get("datasets")):
            score += 2
        if row.get("limitations"):
            score += 1
        if row.get("notes"):
            score += 1
        return score

    ranked = sorted(matrix, key=row_score, reverse=True)
    picked: list[str] = []
    for row in ranked:
        paper_id = row.get("paper_id")
        if paper_id and paper_id not in picked:
            picked.append(paper_id)
        if len(picked) >= 3:
            break
    return picked
