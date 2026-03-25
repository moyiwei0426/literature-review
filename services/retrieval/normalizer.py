from __future__ import annotations

from core.models import PaperCandidate


def normalize_candidate(data: dict) -> PaperCandidate:
    authors = data.get("authors") or []
    author_names = []
    for author in authors:
        if isinstance(author, str):
            author_names.append(author)
        elif isinstance(author, dict):
            author_names.append(author.get("display_name") or author.get("name") or "")

    return PaperCandidate(
        source=data.get("source", "unknown"),
        source_id=str(data.get("source_id") or data.get("id") or ""),
        title=data.get("title") or data.get("display_name") or "",
        authors=[name for name in author_names if name],
        year=data.get("year") or data.get("publication_year"),
        venue=data.get("venue"),
        doi=data.get("doi"),
        arxiv_id=data.get("arxiv_id"),
        abstract=data.get("abstract"),
        keywords=data.get("keywords") or [],
        citation_count=data.get("citation_count"),
        references=data.get("references") or [],
        related_urls=data.get("related_urls") or [],
        pdf_url=data.get("pdf_url"),
        is_open_access=data.get("is_open_access"),
        retrieval_query=data.get("retrieval_query") or "",
        retrieval_score=data.get("retrieval_score"),
    )
