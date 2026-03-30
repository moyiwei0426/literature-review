from __future__ import annotations

from typing import Any


_MOVE_SENTENCE_BLUEPRINTS: dict[str, dict[str, str]] = {
    "framing": {"topic_role": "Introduce the subsection focus and explain why this evidence cluster matters for the review argument.", "evidence_role": "Anchor the framing in the strongest relevant evidence, themes, or matrix signals rather than generic setup.", "closing_role": "Close with a sentence that narrows toward the next evidence-bearing claim."},
    "evidence": {"topic_role": "Open with the main analytical claim for the paragraph instead of a paper-by-paper recap.", "evidence_role": "State the strongest evidence-bearing observation drawn from the planner targets and supporting points.", "closing_role": "End by interpreting what the evidence means for the section argument or the next paragraph."},
    "comparison": {"topic_role": "Set up the comparison dimension and clarify what is being contrasted.", "evidence_role": "Use the most relevant matched evidence to explain where studies converge or diverge.", "closing_role": "Close by stating the comparative takeaway and transition into the remaining limitation or implication."},
    "gap": {"topic_role": "Name the unresolved issue directly and frame it as a review-relevant limitation in the evidence base.", "evidence_role": "Point to the partial evidence or reporting pattern that makes the gap visible.", "closing_role": "End with the implication of leaving this gap unresolved and a transition toward synthesis or future work."},
    "synthesis": {"topic_role": "Open with the field-level takeaway that follows from the preceding evidence.", "evidence_role": "Briefly restate the strongest supporting pattern or tension that justifies the synthesis.", "closing_role": "Conclude with a transition that either closes the section or opens the next analytical move."},
}


def build_paragraph_plans(section_plans: list[dict[str, Any]], matrix: list[dict[str, Any]], verified_gaps: list[dict[str, Any]], synthesis_map: dict[str, Any] | None = None, organization: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [build_paragraph_plan(section_plan, matrix, verified_gaps, synthesis_map=synthesis_map, organization=organization) for section_plan in section_plans if isinstance(section_plan, dict)]


def build_paragraph_plan(section_plan: dict[str, Any], matrix: list[dict[str, Any]], verified_gaps: list[dict[str, Any]], synthesis_map: dict[str, Any] | None = None, organization: dict[str, Any] | None = None) -> dict[str, Any]:
    del synthesis_map, organization
    known_ids=[str(row.get('paper_id') or '').strip() for row in matrix if str(row.get('paper_id') or '').strip()]
    blocks=[]
    for idx, move in enumerate(section_plan.get('argument_moves', []), start=1):
        if not isinstance(move, dict):
            continue
        move_type=str(move.get('move_type') or 'synthesis')
        blueprint=_sentence_blueprint(move_type)
        citation_targets=_string_list(move.get('citation_targets'))
        supporting_citations=_string_list(move.get('supporting_citations')) or citation_targets
        gap_refs=move.get('gap_refs', []) if isinstance(move.get('gap_refs'), list) else []
        supporting_points=[str(point).strip() for point in move.get('supporting_points', []) if str(point).strip()]
        if move_type == 'gap' and not supporting_points:
            supporting_points=[str(item.get('gap_statement') or '').strip() for item in gap_refs or verified_gaps[:1] if str(item.get('gap_statement') or '').strip()]
        allowed=_dedupe([key for key in citation_targets + supporting_citations if key in known_ids] or citation_targets + supporting_citations)
        blocks.append({
            'block_id': f"{section_plan.get('section_id', 'sec')}-block-{idx}",
            'move_id': move.get('move_id', ''),
            'move_type': move_type,
            'purpose': move.get('purpose', ''),
            'intended_purpose': move.get('purpose', ''),
            'theme_refs': move.get('theme_refs', []),
            'gap_refs': gap_refs,
            'citation_targets': citation_targets,
            'supporting_citations': supporting_citations,
            'supporting_points': supporting_points,
            'rhetorical_role': move_type,
            'required_evidence_count': 1 if move_type in {'evidence','comparison','gap'} else 0,
            'max_citations': min(3, max(1, len(allowed))) if allowed else 0,
            'allowed_citation_keys': allowed,
            'coverage_policy': 'grounded_only' if move_type in {'evidence','comparison','gap'} else 'optional',
            'must_include_gap_statement': move_type == 'gap',
            'forbidden_patterns': ['paper-by-paper recap', 'uncited claim'] if move_type in {'evidence','comparison','gap'} else ['generic filler'],
            'evidence_bundle_id': f"{section_plan.get('section_id', 'sec')}-block-{idx}-evidence",
            'polish_eligible': move_type in {'synthesis','comparison','contradiction','gap'},
            'sentence_plan': [
                {'role': 'topic', 'directive': blueprint['topic_role']},
                {'role': 'evidence', 'directive': blueprint['evidence_role']},
                {'role': 'closing', 'directive': blueprint['closing_role']},
            ],
        })
    return {'section_id': section_plan.get('section_id', ''), 'title': section_plan.get('title', ''), 'section_goal': section_plan.get('section_goal', ''), 'blocks': blocks}


def _sentence_blueprint(move_type: str) -> dict[str, str]:
    return _MOVE_SENTENCE_BLUEPRINTS.get(move_type, _MOVE_SENTENCE_BLUEPRINTS['synthesis'])


def _string_list(value: Any) -> list[str]:
    if value is None: return []
    if isinstance(value, str): return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)): return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _dedupe(items: list[str]) -> list[str]:
    seen=set(); out=[]
    for item in items:
        if item not in seen:
            seen.add(item); out.append(item)
    return out
