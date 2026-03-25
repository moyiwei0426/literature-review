from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import re
from typing import Any


_SECTION_ROLE_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...], int], ...] = (
    ("introduction", ("intro", "background", "scope", "context"), ("framing", "evidence", "synthesis"), 3),
    ("taxonomy", ("taxonomy",), ("framing", "evidence", "comparison", "synthesis"), 4),
    ("comparison", ("comparative", "comparison", "tradeoff", "interaction"), ("framing", "comparison", "evidence", "synthesis"), 4),
    ("gap", ("gap", "opportun", "limitation", "future direction", "future", "open problem"), ("framing", "gap", "synthesis"), 3),
    ("conclusion", ("conclusion", "discussion", "future direction", "future directions"), ("synthesis", "comparison"), 2),
)


def validate_review_artifact(
    outline: list[dict[str, Any]] | None,
    section_plans: list[dict[str, Any]] | None,
    paragraph_plans: list[dict[str, Any]] | None,
    sections: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    outline = outline or []
    section_plans = section_plans or []
    paragraph_plans = paragraph_plans or []
    sections = sections or []

    outline_map = _index_by_id(outline)
    section_plan_map = _index_by_id(section_plans)
    paragraph_plan_map = _index_by_id(paragraph_plans)
    section_map = _index_by_id(sections)

    ordered_ids = _ordered_section_ids(outline, section_plans, sections)
    section_reports = [
        _validate_section(
            section_id,
            outline_map.get(section_id, {}),
            section_plan_map.get(section_id, {}),
            paragraph_plan_map.get(section_id, {}),
            section_map.get(section_id, {}),
        )
        for section_id in ordered_ids
    ]

    severity_counts = Counter()
    recommendation_pool: list[str] = []
    for report in section_reports:
        for finding in report["findings"]:
            severity_counts[str(finding.get("severity") or "info")] += 1
            recommendation = str(finding.get("recommendation") or "").strip()
            if recommendation and recommendation not in recommendation_pool:
                recommendation_pool.append(recommendation)

    weak_sections = [report for report in section_reports if report["status"] != "pass"]
    overall_status = _overall_status(severity_counts, weak_sections, len(section_reports))
    counts = {
        "section_count": len(section_reports),
        "healthy_section_count": sum(1 for report in section_reports if report["status"] == "pass"),
        "weak_section_count": len(weak_sections),
        "finding_count": sum(severity_counts.values()),
        "findings": sum(severity_counts.values()),
        "severity_counts": dict(severity_counts),
    }
    summary = summarize_validation_report(
        {
            "overall_status": overall_status,
            "counts": counts,
            "sections": section_reports,
        }
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validator": "review_validator.rule_based.v1",
        "status": overall_status,
        "overall_status": overall_status,
        "counts": counts,
        "summary": summary,
        "sections": section_reports,
        "recommendations": recommendation_pool[:8],
    }


def summarize_validation_report(report: dict[str, Any] | None) -> dict[str, Any]:
    report = report or {}
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    sections = report.get("sections") if isinstance(report.get("sections"), list) else []
    flagged = []
    for section in sections:
        if not isinstance(section, dict) or section.get("status") == "pass":
            continue
        flagged.append(
            {
                "section_id": section.get("section_id", ""),
                "title": section.get("title", ""),
                "status": section.get("status", ""),
                "finding_count": len(section.get("findings", [])) if isinstance(section.get("findings"), list) else 0,
            }
        )
    return {
        "overall_status": report.get("overall_status", "unknown"),
        "section_count": int(counts.get("section_count", len(sections)) or 0),
        "healthy_section_count": int(counts.get("healthy_section_count", 0) or 0),
        "weak_section_count": int(counts.get("weak_section_count", len(flagged)) or 0),
        "finding_count": int(counts.get("finding_count", 0) or 0),
        "severity_counts": counts.get("severity_counts", {}),
        "flagged_sections": flagged[:5],
    }


def _validate_section(
    section_id: str,
    outline_item: dict[str, Any],
    section_plan: dict[str, Any],
    paragraph_plan: dict[str, Any],
    section: dict[str, Any],
) -> dict[str, Any]:
    title = str(
        section.get("title")
        or section_plan.get("title")
        or outline_item.get("title")
        or section_id
    ).strip()
    role = _infer_role(title)
    expected_moves = _expected_moves(role, section_plan, paragraph_plan)
    paragraphs = _normalize_paragraphs(section)
    observed_moves = [str(p.get("move_type") or "").strip() for p in paragraphs if str(p.get("move_type") or "").strip()]
    move_counts = Counter(observed_moves)
    plan_gap_refs = _list_of_dicts(section_plan.get("gap_refs")) or _gap_refs_from_paragraph_plan(paragraph_plan)
    paragraph_count = len(paragraphs)
    cited_paragraph_count = sum(1 for paragraph in paragraphs if _coerce_string_list(paragraph.get("citation_keys")))

    findings: list[dict[str, Any]] = []
    section_recommendations: list[str] = []
    missing_moves: list[str] = []

    for move in expected_moves:
        if move not in move_counts:
            missing_moves.append(move)
            severity = "error" if move in {"framing", "evidence"} else "warning"
            if move == "gap" and role == "gap":
                severity = "error"
            findings.append(
                _finding(
                    code=f"missing_{move}_move",
                    severity=severity,
                    message=f"Missing expected {move} move for {role}-oriented section.",
                    recommendation=_recommendation_for_move(move, role),
                )
            )
    if missing_moves:
        findings.append(
            _finding(
                code="missing_expected_moves",
                severity="error" if any(move in {"framing", "evidence", "gap"} for move in missing_moves) else "warning",
                message=f"Section is missing expected moves: {', '.join(missing_moves)}.",
                recommendation="Restore the missing rhetorical moves so the section retains framing, evidence, synthesis, and gap handling where expected.",
            )
        )

    if paragraphs and cited_paragraph_count == 0:
        findings.append(
            _finding(
                code="missing_paragraph_citations",
                severity="error",
                message="Section contains paragraphs but none carry paragraph-level citations.",
                recommendation="Ground at least one citation in each evidence-bearing section paragraph.",
            )
        )

    if role in {"introduction", "taxonomy", "comparison", "gap"} and paragraph_count < _min_paragraph_count(role):
        findings.append(
            _finding(
                code="weak_paragraph_count",
                severity="warning",
                message=f"Section has only {paragraph_count} paragraph(s), which is light for a {role} section.",
                recommendation=f"Expand the section to at least {_min_paragraph_count(role)} paragraphs with clearer rhetorical progression.",
            )
        )

    if role in {"taxonomy", "comparison"} and "comparison" not in move_counts:
        findings.append(
            _finding(
                code="weak_move_mix_for_role",
                severity="warning",
                message="Section role suggests explicit comparison, but no comparison paragraph is present.",
                recommendation="Add a comparison paragraph that contrasts the strongest themes, datasets, or methods.",
            )
        )

    if role == "gap":
        actual_gap_refs = _gap_refs_from_paragraphs(paragraphs)
        if plan_gap_refs and not actual_gap_refs:
            findings.append(
                _finding(
                    code="missing_linked_gap_handling",
                    severity="error",
                    message="Gap-oriented section lost its linked gap references in the rendered paragraphs.",
                    recommendation="Carry section-plan gap references into at least one paragraph and make the unresolved issue explicit.",
                )
            )
        elif not plan_gap_refs and "gap" not in move_counts:
            findings.append(
                _finding(
                    code="missing_linked_gap_handling",
                    severity="warning",
                    message="Gap-oriented section lacks explicit linked gap handling.",
                    recommendation="Include a paragraph that states the unresolved gap, why evidence is insufficient, and the next research need.",
                )
            )

    for idx, paragraph in enumerate(paragraphs, start=1):
        move_type = str(paragraph.get("move_type") or "").strip() or "unknown"
        citations = _coerce_string_list(paragraph.get("citation_keys"))
        if move_type in {"evidence", "comparison", "gap"} and not citations:
            findings.append(
                _finding(
                    code="paragraph_missing_citations",
                    severity="warning",
                    message=f"Paragraph {idx} is a {move_type} move without citations.",
                    recommendation="Attach at least one citation key to each evidence, comparison, or gap paragraph.",
                    paragraph_index=idx,
                    move_type=move_type,
                )
            )
        if not str(paragraph.get("text") or "").strip():
            findings.append(
                _finding(
                    code="empty_paragraph_text",
                    severity="warning",
                    message=f"Paragraph {idx} is empty after rewrite.",
                    recommendation="Keep paragraph text non-empty when preserving planner structure.",
                    paragraph_index=idx,
                    move_type=move_type,
                )
            )

    for finding in findings:
        recommendation = str(finding.get("recommendation") or "").strip()
        if recommendation and recommendation not in section_recommendations:
            section_recommendations.append(recommendation)

    status = _section_status(findings)
    return {
        "section_id": section_id,
        "title": title,
        "role": role,
        "status": status,
        "expected_moves": expected_moves,
        "observed_moves": dict(move_counts),
        "paragraph_count": paragraph_count,
        "cited_paragraph_count": cited_paragraph_count,
        "section_citation_count": len(_coerce_string_list(section.get("citation_keys"))),
        "linked_gap_count": len(plan_gap_refs),
        "findings": findings,
        "recommendations": section_recommendations,
    }


def validate_review_writing(
    outline: list[dict[str, Any]] | None = None,
    section_plans: list[dict[str, Any]] | None = None,
    paragraph_plans: list[dict[str, Any]] | None = None,
    drafted_sections: list[dict[str, Any]] | None = None,
    grounded_sections: list[dict[str, Any]] | None = None,
    rewritten_sections: list[dict[str, Any]] | None = None,
    verified_gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    del verified_gaps
    sections = rewritten_sections or grounded_sections or drafted_sections or []
    return validate_review_artifact(outline, section_plans, paragraph_plans, sections)


def _index_by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        section_id = str(item.get("section_id") or "").strip()
        if section_id:
            index[section_id] = item
    return index


def _ordered_section_ids(*collections: list[dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for items in collections:
        for item in items:
            if not isinstance(item, dict):
                continue
            section_id = str(item.get("section_id") or "").strip()
            if section_id and section_id not in seen:
                seen.add(section_id)
                ordered.append(section_id)
    return ordered


def _infer_role(title: str) -> str:
    lowered = title.lower()
    for role, cues, _, _ in _SECTION_ROLE_RULES:
        if any(cue in lowered for cue in cues):
            return role
    return "body"


def _expected_moves(
    role: str,
    section_plan: dict[str, Any],
    paragraph_plan: dict[str, Any],
) -> list[str]:
    planned_moves = []
    for source in (section_plan.get("argument_moves"), paragraph_plan.get("blocks")):
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            move_type = str(item.get("move_type") or "").strip()
            if move_type and move_type not in planned_moves:
                planned_moves.append(move_type)
    if planned_moves:
        return planned_moves
    for candidate_role, _, default_moves, _ in _SECTION_ROLE_RULES:
        if candidate_role == role:
            return list(default_moves)
    return ["framing", "evidence", "synthesis"]


def _min_paragraph_count(role: str) -> int:
    for candidate_role, _, _, min_count in _SECTION_ROLE_RULES:
        if candidate_role == role:
            return min_count
    return 3


def _normalize_paragraphs(section: dict[str, Any]) -> list[dict[str, Any]]:
    raw = section.get("paragraphs")
    paragraphs: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                paragraphs.append({**item, "text": text})
    if paragraphs:
        return paragraphs

    text = str(section.get("text") or "").strip()
    if not text:
        return []
    return [{"text": chunk.strip()} for chunk in re.split(r"\n\s*\n+", text) if chunk.strip()]


def _gap_refs_from_paragraph_plan(paragraph_plan: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for block in paragraph_plan.get("blocks", []) if isinstance(paragraph_plan.get("blocks"), list) else []:
        if not isinstance(block, dict):
            continue
        refs.extend(_list_of_dicts(block.get("gap_refs")))
    return refs


def _gap_refs_from_paragraphs(paragraphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        refs.extend(_list_of_dicts(paragraph.get("gap_refs")))
    return refs


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_coerce_string_list(item))
        return [item for item in out if item]
    return []


def _finding(
    code: str,
    severity: str,
    message: str,
    recommendation: str,
    paragraph_index: int | None = None,
    move_type: str | None = None,
) -> dict[str, Any]:
    finding = {
        "code": code,
        "severity": severity,
        "message": message,
        "recommendation": recommendation,
    }
    if paragraph_index is not None:
        finding["paragraph_index"] = paragraph_index
    if move_type:
        finding["move_type"] = move_type
    return finding


def _recommendation_for_move(move: str, role: str) -> str:
    if move == "framing":
        return "Add an opening paragraph that states the section lens, scope, and why the evidence cluster matters."
    if move == "evidence":
        return "Add an evidence paragraph grounded in specific studies, metrics, or datasets."
    if move == "comparison":
        return "Add a comparison paragraph that contrasts at least two evidence clusters or reporting patterns."
    if move == "gap":
        return "Add a gap paragraph linking unresolved evidence, insufficiency, and concrete research need."
    if move == "synthesis":
        return f"Add a closing synthesis paragraph that explains what the {role} section implies for the broader review."
    return "Add the missing rhetorical move."


def _section_status(findings: list[dict[str, Any]]) -> str:
    severities = {str(finding.get("severity") or "") for finding in findings}
    if "error" in severities:
        return "fail"
    if "warning" in severities:
        return "warn"
    return "pass"


def _overall_status(severity_counts: Counter[str], weak_sections: list[dict[str, Any]], total_sections: int) -> str:
    if severity_counts.get("error", 0) > 0:
        return "fail"
    if severity_counts.get("warning", 0) > 0 or len(weak_sections) * 2 >= max(total_sections, 1):
        return "warn"
    return "pass"
