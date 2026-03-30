from __future__ import annotations

from collections import Counter
from typing import Any

from .review_validator import validate_review_artifact


def validate_section_tracks(
    outline: list[dict[str, Any]] | None,
    section_plans: list[dict[str, Any]] | None,
    paragraph_plans: list[dict[str, Any]] | None,
    sections: list[dict[str, Any]] | None,
    *,
    strict: bool = False,
    track: str = 'safe',
) -> dict[str, Any]:
    report = validate_review_artifact(outline, section_plans, paragraph_plans, sections)
    findings=[]
    for section in sections or []:
        role=str(section.get('role') or section.get('title') or '').lower()
        paragraphs=section.get('paragraphs') if isinstance(section.get('paragraphs'), list) else []
        if strict and any(key in role for key in ('comparison','gap','conclusion','discussion','synthesis')) and not paragraphs:
            findings.append({'section_id': section.get('section_id',''), 'code': 'missing_structured_paragraphs', 'severity': 'error'})
    sev=Counter(f['severity'] for f in findings)
    if findings:
        report['track']=track
        report['extended_findings']=findings
        report['summary']['finding_count']=int(report['summary'].get('finding_count',0))+len(findings)
        report['summary']['severity_counts']={**report['summary'].get('severity_counts',{}), **dict(sev)}
        report['status']='fail' if sev.get('error') or report.get('status')=='fail' else report.get('status','warn')
        report['summary']['overall_status']=report['status']
    else:
        report['track']=track
        report['extended_findings']=[]
    return report
