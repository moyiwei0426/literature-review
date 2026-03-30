from __future__ import annotations

from collections import Counter
from typing import Any


def validate_paragraphs(sections: list[dict[str, Any]] | None, *, strict: bool = False) -> dict[str, Any]:
    findings=[]
    paragraph_count=0
    for section in sections or []:
        for idx, paragraph in enumerate(section.get('paragraphs', []) if isinstance(section.get('paragraphs'), list) else [], start=1):
            if not isinstance(paragraph, dict):
                continue
            paragraph_count += 1
            citations=_str_list(paragraph.get('citation_keys'))
            bundle=paragraph.get('evidence_bundle') if isinstance(paragraph.get('evidence_bundle'), dict) else {}
            allowed=set(_str_list(bundle.get('allowed_citation_keys')))
            required=max(0, int(bundle.get('required_citation_count') or 0))
            move_type=str(paragraph.get('move_type') or '')
            if move_type in {'evidence','comparison','gap'} and len(citations) < max(required, 1):
                findings.append(_finding(section, idx, 'insufficient_citations', 'error' if strict else 'warning'))
            if allowed and any(key not in allowed for key in citations):
                findings.append(_finding(section, idx, 'citation_outside_bundle', 'error'))
            if strict and move_type in {'synthesis','comparison','gap'} and not paragraph.get('polish_pass') in {True, None}:
                findings.append(_finding(section, idx, 'polish_guard_failed', 'warning'))
    sev=Counter(f['severity'] for f in findings)
    status='fail' if sev.get('error') else 'warn' if sev.get('warning') else 'pass'
    return {'status': status, 'summary': {'paragraph_count': paragraph_count, 'finding_count': len(findings), 'severity_counts': dict(sev)}, 'findings': findings}


def _str_list(v: Any) -> list[str]:
    if isinstance(v, str): return [v] if v.strip() else []
    if isinstance(v, (list, tuple, set)): return [str(x).strip() for x in v if str(x).strip()]
    return []


def _finding(section: dict[str, Any], idx: int, code: str, severity: str) -> dict[str, Any]:
    return {'section_id': section.get('section_id',''), 'paragraph_index': idx, 'code': code, 'severity': severity}
