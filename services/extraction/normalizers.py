from __future__ import annotations

from typing import Any


VALID_CLAIM_TYPES = {"performance", "methodological", "application", "theoretical"}
VALID_LIMITATION_SOURCES = {"explicit", "inferred"}


def normalize_profile_payload(payload: dict[str, Any], *, paper_id: str) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["paper_id"] = normalized.get("paper_id") or paper_id

    title = normalized.get("title")
    normalized["title"] = title.strip() if isinstance(title, str) and title.strip() else "Untitled"

    authors = normalized.get("authors") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(",") if a.strip()]
    elif not isinstance(authors, list):
        authors = []
    normalized["authors"] = [str(a).strip() for a in authors if str(a).strip()]

    year = normalized.get("year")
    if isinstance(year, str):
        year = year.strip()
        if year.isdigit():
            year = int(year)
        else:
            year = None
    elif not isinstance(year, int):
        year = None
    normalized["year"] = year

    venue = normalized.get("venue")
    normalized["venue"] = venue.strip() if isinstance(venue, str) and venue.strip() else None

    method_family = normalized.get("method_family") or []
    if isinstance(method_family, str):
        normalized["method_family"] = [method_family]
    elif method_family is None:
        normalized["method_family"] = []

    for key in ["datasets", "tasks", "metrics", "baselines", "future_work"]:
        value = normalized.get(key)
        if value is None:
            normalized[key] = []
        elif isinstance(value, str):
            normalized[key] = [value]

    claims = []
    for idx, claim in enumerate(normalized.get("main_claims") or [], start=1):
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("claim_id") or f"claim-{idx}"
        claim_text = claim.get("claim_text") or claim.get("claim") or claim.get("text") or ""
        claim_type = (claim.get("claim_type") or claim.get("type") or "application").lower()
        if claim_type not in VALID_CLAIM_TYPES:
            claim_type = "application"
        evidence_chunk_ids = claim.get("evidence_chunk_ids") or claim.get("evidence") or []
        if isinstance(evidence_chunk_ids, str):
            evidence_chunk_ids = [evidence_chunk_ids]
        confidence = claim.get("confidence")
        claims.append(
            {
                "claim_id": claim_id,
                "claim_text": claim_text,
                "claim_type": claim_type,
                "evidence_chunk_ids": evidence_chunk_ids,
                "confidence": confidence,
            }
        )
    normalized["main_claims"] = claims

    limitations = []
    for item in normalized.get("limitations") or []:
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("limitation") or ""
        source = (item.get("source") or "inferred").lower()
        if source not in VALID_LIMITATION_SOURCES:
            source = "inferred"
        evidence_chunk_ids = item.get("evidence_chunk_ids") or []
        if isinstance(evidence_chunk_ids, str):
            evidence_chunk_ids = [evidence_chunk_ids]
        limitations.append(
            {
                "text": text,
                "source": source,
                "evidence_chunk_ids": evidence_chunk_ids,
            }
        )
    normalized["limitations"] = limitations

    # Normalize notes: ensure it's a string, not a list
    notes = normalized.get("notes")
    if isinstance(notes, list):
        normalized["notes"] = "; ".join(str(n) for n in notes if n)
    elif notes is None:
        normalized["notes"] = None

    return normalized
