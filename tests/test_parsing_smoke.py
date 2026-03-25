from services.parsing.chunker import chunk_sections
from services.parsing.quality_scorer import score_parse_quality
from services.parsing.section_splitter import split_sections


def test_section_split_and_chunk() -> None:
    parsed = {
        "abstract": "Short abstract",
        "sections": [
            {"title": "Introduction", "text": "Intro para 1.\n\nIntro para 2.", "page_start": 1, "page_end": 1},
            {"title": "References", "text": "[1] A", "page_start": 5, "page_end": 5},
        ],
    }
    sections = split_sections(parsed)
    chunks = chunk_sections("paper-1", sections, chunk_size=20)
    report = score_parse_quality({**parsed, "sections": sections}, chunks)
    assert len(sections) == 2
    assert len(chunks) >= 2
    assert report["parse_quality_score"] > 0
