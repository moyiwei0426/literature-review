from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.llm.adapter import LLMAdapter
from .gap_normalizers import normalize_gap_list


_DEF_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "gap" / "critic_system.txt"


def generate_candidate_gaps(matrix: list[dict[str, Any]], coverage: dict[str, Any], contradiction: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate conservative, evidence-grounded candidate gaps.

    Rule-based logic is primary on purpose: gap generation is high-risk for hallucinated
    research claims, so we prefer deterministic evidence checks over LLM creativity.
    """
    return _generate_candidate_gaps_rule_based(matrix, coverage, contradiction)


def _generate_candidate_gaps_llm(llm: LLMAdapter, matrix: list[dict[str, Any]], coverage: dict[str, Any], contradiction: dict[str, Any]) -> list[dict[str, Any]]:
    system_prompt = _DEF_PROMPT_PATH.read_text(encoding="utf-8") + "\nReturn JSON with key candidate_gaps as a list of structured gaps."
    user_prompt = (
        "Generate evidence-grounded candidate literature-review gaps from the following signals. "
        "Avoid generic claims and only use supported observations.\n\n"
        f"Coverage:\n{json.dumps(coverage, ensure_ascii=False)}\n\n"
        f"Matrix:\n{json.dumps(matrix, ensure_ascii=False)}\n\n"
        f"Contradiction:\n{json.dumps(contradiction, ensure_ascii=False)}"
    )
    response = llm.generate_json(system_prompt, user_prompt)
    payload = response.content
    items = payload.get("candidate_gaps") if isinstance(payload, dict) else []
    normalized = normalize_gap_list(items, default_status="candidate")
    return normalized or _generate_candidate_gaps_rule_based(matrix, coverage, contradiction)


def _generate_candidate_gaps_rule_based(matrix: list[dict[str, Any]], coverage: dict[str, Any], contradiction: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []

    language_distribution = coverage.get("language_distribution", {})
    chinese_context_count = coverage.get("chinese_coverage_count", 0)
    paper_count = coverage.get("paper_count", 0)
    if paper_count >= 5 and chinese_context_count == 0:
        gaps.append(
            {
                "gap_id": str(uuid4()),
                "gap_statement": "Current coverage appears to underrepresent Chinese-language or Chinese-context studies.",
                "gap_type": "language",
                "supporting_evidence": [
                    f"paper_count={paper_count}",
                    f"language_distribution={language_distribution}",
                    f"chinese_coverage_count={chinese_context_count}",
                ],
                "counter_evidence": [],
                "confidence": None,
                "novelty_value": None,
                "review_worthiness": None,
                "status": "candidate",
            }
        )

    contradiction_count = contradiction.get("contradiction_count", 0) if isinstance(contradiction, dict) else 0
    contradictions_list = contradiction.get("contradictions", []) if isinstance(contradiction, dict) else []
    if not contradictions_list:
        contradiction_count = 0
    normalized_groups = contradiction.get("normalized_task_groups", []) if isinstance(contradiction, dict) else []
    cross_paper_groups = [g for g in normalized_groups if g.get("paper_count", 0) >= 2 and g.get("has_conflict", False)]
    if contradiction_count > 0 and cross_paper_groups:
        gaps.append(
            {
                "gap_id": str(uuid4()),
                "gap_statement": "There are unresolved claim differences across papers under related tasks, suggesting a need for clearer comparison criteria.",
                "gap_type": "comparison",
                "supporting_evidence": [
                    f"contradiction_count={contradiction_count}",
                    f"cross_paper_task_groups={len(cross_paper_groups)}",
                ],
                "counter_evidence": [],
                "confidence": None,
                "novelty_value": None,
                "review_worthiness": None,
                "status": "candidate",
            }
        )

    metric_rows = sum(1 for row in matrix if row.get("metrics"))
    if matrix and metric_rows == 0:
        gaps.append(
            {
                "gap_id": str(uuid4()),
                "gap_statement": "The current literature set shows weak metric reporting, limiting rigorous cross-paper evaluation.",
                "gap_type": "evaluation",
                "supporting_evidence": [f"metric_rows={metric_rows}"],
                "counter_evidence": [],
                "confidence": None,
                "novelty_value": None,
                "review_worthiness": None,
                "status": "candidate",
            }
        )

    return gaps
