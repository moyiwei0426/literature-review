from __future__ import annotations

from uuid import uuid4

from core.models import PaperCandidate, PaperMaster
from .merge_rules import exact_match, fuzzy_match_score
from .provenance import provenance_record
from .title_normalizer import normalize_title


def dedupe_candidates(candidates: list[PaperCandidate], fuzzy_threshold: float = 0.93) -> tuple[list[PaperMaster], dict]:
    masters: list[PaperMaster] = []
    merged_groups: list[list[dict]] = []

    for candidate in candidates:
        matched_index = None
        for idx, master in enumerate(masters):
            probe = PaperCandidate(
                source=master.sources[0] if master.sources else "merged",
                source_id=master.paper_id,
                title=master.canonical_title,
                authors=master.authors,
                year=master.year,
                venue=master.venue,
                doi=master.doi,
                arxiv_id=master.arxiv_id,
                abstract=master.abstract,
                pdf_url=master.pdf_candidates[0] if master.pdf_candidates else None,
                retrieval_query="dedup",
            )
            if exact_match(candidate, probe) or fuzzy_match_score(candidate, probe) >= fuzzy_threshold:
                matched_index = idx
                break

        if matched_index is None:
            master = PaperMaster(
                paper_id=str(uuid4()),
                canonical_title=candidate.title,
                normalized_title=normalize_title(candidate.title),
                authors=candidate.authors,
                year=candidate.year,
                venue=candidate.venue,
                doi=candidate.doi,
                arxiv_id=candidate.arxiv_id,
                abstract=candidate.abstract,
                sources=[candidate.source],
                pdf_candidates=[candidate.pdf_url] if candidate.pdf_url else [],
                citation_count=candidate.citation_count,
            )
            masters.append(master)
            merged_groups.append([provenance_record(candidate)])
        else:
            master = masters[matched_index]
            if candidate.source not in master.sources:
                master.sources.append(candidate.source)
            if candidate.pdf_url and candidate.pdf_url not in master.pdf_candidates:
                master.pdf_candidates.append(candidate.pdf_url)
            if not master.doi and candidate.doi:
                master.doi = candidate.doi
            if not master.arxiv_id and candidate.arxiv_id:
                master.arxiv_id = candidate.arxiv_id
            if not master.abstract and candidate.abstract:
                master.abstract = candidate.abstract
            merged_groups[matched_index].append(provenance_record(candidate))

    report = {
        "before_count": len(candidates),
        "after_count": len(masters),
        "merged_count": len(candidates) - len(masters),
        "groups": merged_groups,
    }
    return masters, report
