from __future__ import annotations


def score_parse_quality(parsed: dict, chunks: list[dict]) -> dict:
    has_abstract = bool(parsed.get("abstract")) or any((s.get("section_name") == "abstract") for s in parsed.get("sections", []))
    has_references = any((s.get("section_name") == "references") for s in parsed.get("sections", []))
    total_text_length = sum(len(chunk.get("text", "")) for chunk in chunks)

    score = 0.0
    score += 0.3 if has_abstract else 0.0
    score += 0.2 if has_references else 0.0
    score += 0.5 if total_text_length > 2000 else 0.2 if total_text_length > 200 else 0.0

    return {
        "has_abstract": has_abstract,
        "has_references": has_references,
        "total_text_length": total_text_length,
        "parse_quality_score": round(score, 3),
    }
