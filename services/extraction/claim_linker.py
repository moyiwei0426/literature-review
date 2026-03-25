from __future__ import annotations

from core.models import ClaimEvidenceLink, PaperProfile


def build_claim_evidence_links(profile: PaperProfile) -> list[ClaimEvidenceLink]:
    links: list[ClaimEvidenceLink] = []
    for claim in profile.main_claims:
        for chunk_id in claim.evidence_chunk_ids:
            links.append(
                ClaimEvidenceLink(
                    claim_id=claim.claim_id,
                    chunk_id=chunk_id,
                    support_type="supports",
                    confidence=claim.confidence,
                )
            )
    return links
