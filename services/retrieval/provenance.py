from __future__ import annotations

from core.models import PaperCandidate


def provenance_record(candidate: PaperCandidate) -> dict:
    return {
        "source": candidate.source,
        "source_id": candidate.source_id,
        "title": candidate.title,
        "doi": candidate.doi,
        "arxiv_id": candidate.arxiv_id,
    }
