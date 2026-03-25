from __future__ import annotations

from core.models import ClaimEvidenceLink, PaperProfile


class ExtractionValidationError(ValueError):
    pass


def validate_profile_payload(payload: dict) -> PaperProfile:
    profile = PaperProfile.model_validate(payload)
    for claim in profile.main_claims:
        if not claim.evidence_chunk_ids:
            raise ExtractionValidationError(f"Claim {claim.claim_id} must include at least one evidence chunk id.")
    for limitation in profile.limitations:
        if limitation.source not in {"explicit", "inferred"}:
            raise ExtractionValidationError("Invalid limitation source.")
    return profile


def validate_claim_evidence_links(links: list[ClaimEvidenceLink], valid_chunk_ids: set[str]) -> None:
    for link in links:
        if link.chunk_id not in valid_chunk_ids:
            raise ExtractionValidationError(f"Unknown chunk id in link: {link.chunk_id}")
