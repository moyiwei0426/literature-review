from __future__ import annotations

from uuid import uuid4


def chunk_sections(paper_id: str, sections: list[dict], chunk_size: int = 1200) -> list[dict]:
    chunks: list[dict] = []
    order_index = 0
    for section in sections:
        text = section.get("text", "").strip()
        if not text:
            continue
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for paragraph in paragraphs:
            start = 0
            while start < len(paragraph):
                piece = paragraph[start:start + chunk_size]
                chunks.append(
                    {
                        "chunk_id": str(uuid4()),
                        "paper_id": paper_id,
                        "section": section.get("section_name", "unknown"),
                        "page_start": section.get("page_start"),
                        "page_end": section.get("page_end"),
                        "text": piece,
                        "char_start": start,
                        "char_end": start + len(piece),
                        "order_index": order_index,
                    }
                )
                order_index += 1
                start += chunk_size
    return chunks
