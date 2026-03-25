from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx

from core.models import PaperMaster
from infra.settings import get_settings


class PDFFetcher:
    def __init__(self, timeout: float = 30.0) -> None:
        settings = get_settings()
        self.timeout = timeout
        self.base_dir = settings.data_dir / "raw" / "pdfs"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, paper: PaperMaster) -> dict:
        pdf_url: Optional[str] = None
        if paper.pdf_candidates:
            pdf_url = paper.pdf_candidates[0]
        if not pdf_url:
            return {"status": "missing_pdf_url", "paper_id": paper.paper_id, "path": None}

        path = self.base_dir / f"{paper.paper_id}.pdf"
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(pdf_url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
                return {
                    "status": "unexpected_content_type",
                    "paper_id": paper.paper_id,
                    "path": None,
                    "content_type": content_type,
                }
            path.write_bytes(response.content)

        return {
            "status": "downloaded",
            "paper_id": paper.paper_id,
            "path": str(path),
            "source_url": pdf_url,
        }
