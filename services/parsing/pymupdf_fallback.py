from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz


class FallbackTextExtractor:
    def extract(self, pdf_path: str | Path) -> dict[str, Any]:
        path = Path(pdf_path)
        doc = fitz.open(path)
        pages: list[dict[str, Any]] = []
        full_text_parts: list[str] = []

        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            pages.append(
                {
                    "page_number": index,
                    "text": text,
                    "char_count": len(text),
                }
            )
            if text.strip():
                full_text_parts.append(text.strip())

        full_text = "\n\n".join(full_text_parts)
        doc.close()

        return {
            "parser": "pymupdf",
            "status": "ok",
            "pdf_path": str(path),
            "pages": pages,
            "full_text": full_text,
            "page_count": len(pages),
        }
