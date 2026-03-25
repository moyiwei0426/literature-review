from __future__ import annotations

from core.models import PaperProfile


def build_claims_evidence_matrix(profiles: list[PaperProfile]) -> list[dict]:
    rows: list[dict] = []
    for profile in profiles:
        limitations = [item.text for item in profile.limitations]
        for claim in profile.main_claims:
            rows.append(
                {
                    "paper_id": profile.paper_id,
                    "title": profile.title,
                    "authors": "; ".join(profile.authors),
                    "year": profile.year,
                    "venue": profile.venue,
                    "research_problem": profile.research_problem,
                    "method_summary": profile.method_summary,
                    "method_family": "; ".join(profile.method_family),
                    "tasks": "; ".join(profile.tasks),
                    "datasets": "; ".join(profile.datasets),
                    "metrics": "; ".join(profile.metrics),
                    "claim_id": claim.claim_id,
                    "claim_text": claim.claim_text,
                    "claim_type": claim.claim_type.value if hasattr(claim.claim_type, 'value') else str(claim.claim_type),
                    "evidence_chunk_ids": "; ".join(claim.evidence_chunk_ids),
                    "limitations": " | ".join(limitations),
                    "notes": profile.notes or "",
                }
            )
    return rows
