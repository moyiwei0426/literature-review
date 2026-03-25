from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models import PaperMaster
from services.parsing.chunker import chunk_sections
from services.parsing.pdf_fetcher import PDFFetcher
from services.parsing.pymupdf_fallback import FallbackTextExtractor
from services.parsing.quality_scorer import score_parse_quality
from services.parsing.section_splitter import split_sections
from services.parsing.storage import ParsingStorage
from services.retrieval.aggregator import RetrievalAggregator
from services.retrieval.query_builder import QueryInput, build_query_plan


def main() -> None:
    plan = build_query_plan(QueryInput(query="automated literature review llm", max_results=4, include_sources=["arxiv"]))
    result = RetrievalAggregator().run(plan)
    first = next((c for c in result["candidates"] if c.pdf_url), None)
    if not first:
        print("No candidate with pdf_url found.")
        return

    paper = PaperMaster(
        paper_id=f"demo-{first.source_id}",
        canonical_title=first.title,
        normalized_title=first.title.lower(),
        authors=first.authors,
        year=first.year,
        venue=first.venue,
        doi=first.doi,
        arxiv_id=first.arxiv_id,
        abstract=first.abstract,
        sources=[first.source],
        pdf_candidates=[first.pdf_url] if first.pdf_url else [],
        citation_count=first.citation_count,
    )

    fetch_result = PDFFetcher().fetch(paper)
    print("fetch_result:", fetch_result)
    if fetch_result.get("status") != "downloaded":
        return

    parsed = FallbackTextExtractor().extract(fetch_result["path"])
    pseudo_parsed = {
        "abstract": first.abstract,
        "sections": [
            {
                "title": "Body",
                "text": parsed["full_text"],
                "page_start": 1,
                "page_end": parsed.get("page_count"),
            }
        ],
    }
    sections = split_sections(pseudo_parsed)
    chunks = chunk_sections(paper.paper_id, sections)
    report = score_parse_quality({**pseudo_parsed, "sections": sections}, chunks)

    storage = ParsingStorage()
    storage.save_parsed(paper.paper_id, parsed)
    storage.save_chunks(paper.paper_id, chunks)
    storage.save_quality_report(paper.paper_id, report)

    print("title:", paper.canonical_title)
    print("pages:", parsed.get("page_count"))
    print("chunks:", len(chunks))
    print("quality:", report)


if __name__ == "__main__":
    main()
