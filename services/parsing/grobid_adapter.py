from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

import httpx

from infra.settings import get_settings


class GrobidAdapter:
    """Real GROBID service adapter with fallback to pymupdf_fallback."""

    def __init__(self, grobid_url: str | None = None) -> None:
        settings = get_settings()
        self.grobid_url = grobid_url or settings.grobid_url
        self.timeout = 120.0
        self._available: Optional[bool] = None

    def _is_available(self) -> bool:
        """Check if GROBID service is reachable."""
        if self._available is not None:
            return self._available
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{self.grobid_url}/api/status")
                self._available = r.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def _parse_tei_text(self, tei_xml: str) -> dict[str, Any]:
        """Parse GROBID TEI-XML and extract structured fields."""
        try:
            root = ET.fromstring(tei_xml)
        except ET.ParseError as exc:
            return {"parser": "grobid", "parse_error": str(exc), "tei_excerpt": tei_xml[:500]}

        ns = {"tei": "http://www.tei-c.org/ns/1.0"}

        def tag(local: str) -> str:
            return f"{{{ns['tei']}}}{local}"

        body = root.find(f".//{tag('text')}")
        if body is None:
            body = root

        title_parts: list[str] = []
        for titletag in body.findall(f".//{tag('title')}"):
            if titletag.text and titletag.text.strip():
                title_parts.append(titletag.text.strip() if titletag.text else "")

        abstract_parts: list[str] = []
        for abstag in body.findall(f".//{tag('abstract')}"):
            for p in abstag.findall(f"./{tag('p')}"):
                if p.text:
                    abstract_parts.append(p.text.strip())

        sections: list[dict[str, str]] = []
        for head in body.findall(f".//{tag('head')}"):
            section_title = head.text.strip() if head.text else ""
            sibling = head.getnext()
            section_text_parts: list[str] = []
            while sibling is not None:
                if sibling.tag == tag("head"):
                    break
                if sibling.tag == tag("p") and sibling.text:
                    section_text_parts.append(sibling.text.strip())
                if sibling.tag == tag("s") and sibling.text:
                    section_text_parts.append(sibling.text.strip())
                sibling = sibling.getnext()
            if section_text_parts:
                sections.append({
                    "title": section_title or "Untitled",
                    "text": " ".join(section_text_parts),
                })

        references: list[dict[str, str]] = []
        for ref_tag in root.findall(f".//{tag('biblStruct')}"):
            authors: list[str] = []
            for author_tag in ref_tag.findall(f".//{tag('author')}"):
                persname = author_tag.find(f"./{tag('persName')}")
                if persname is not None:
                    forename = persname.find(f"./{tag('forename')}")
                    surname = persname.find(f"./{tag('surname')}")
                    name = " ".join(
                        x.text for x in [forename, surname]
                        if x is not None and x.text
                    )
                    if name:
                        authors.append(name)
            title_tag = ref_tag.find(f".//{tag('title')}")
            title_text = title_tag.text if title_tag is not None else ""
            ref_text = f"{', '.join(authors)}. {title_text}".strip()
            references.append({"raw": ref_text, "authors": authors, "title": title_text or ""})

        authors_out: list[str] = []
        for author_tag in root.findall(f".//{tag('author')}"):
            persname = author_tag.find(f"./{tag('persName')}")
            if persname is not None:
                forename = persname.find(f"./{tag('forename')}")
                surname = persname.find(f"./{tag('surname')}")
                name = " ".join(
                    x.text for x in [forename, surname] if x is not None and x.text
                )
                if name:
                    authors_out.append(name)

        return {
            "parser": "grobid",
            "title": " ".join(title_parts) or None,
            "abstract": " ".join(abstract_parts) or None,
            "authors": authors_out or None,
            "sections": sections,
            "references": references,
        }

    def parse(self, pdf_path: str | Path) -> dict[str, Any]:
        """Call real GROBID /api/processFulltextDocument endpoint."""
        path = Path(pdf_path)
        if not path.exists():
            return {
                "parser": "grobid",
                "status": "file_not_found",
                "pdf_path": str(path),
                "title": path.stem,
                "abstract": None,
                "sections": [],
                "references": [],
            }

        if not self._is_available():
            return {
                "parser": "grobid",
                "status": "service_unavailable",
                "grobid_url": self.grobid_url,
                "pdf_path": str(path),
                "fallback": "pymupdf",
                "title": path.stem,
                "abstract": None,
                "sections": [],
                "references": [],
            }

        try:
            with open(path, "rb") as f:
                files = {"input": (path.name, f.read(), "application/pdf")}
                data = {"consolidateCoordinates": "0", "generateIDs": "1"}
                with httpx.Client(timeout=self.timeout) as client:
                    r = client.post(
                        f"{self.grobid_url}/api/processFulltextDocument",
                        files=files,
                        data=data,
                    )
            if r.status_code == 503:
                return {
                    "parser": "grobid",
                    "status": "service_busy",
                    "grobid_url": self.grobid_url,
                    "pdf_path": str(path),
                    "fallback": "pymupdf",
                    "title": path.stem,
                    "abstract": None,
                    "sections": [],
                    "references": [],
                }
            r.raise_for_status()
            result = self._parse_tei_text(r.text)
            result["pdf_path"] = str(path)
            result["status"] = "success"
            return result

        except httpx.TimeoutException:
            return {
                "parser": "grobid",
                "status": "timeout",
                "grobid_url": self.grobid_url,
                "pdf_path": str(path),
                "fallback": "pymupdf",
                "title": path.stem,
                "abstract": None,
                "sections": [],
                "references": [],
            }
        except Exception as exc:
            return {
                "parser": "grobid",
                "status": "error",
                "error": str(exc),
                "pdf_path": str(path),
                "fallback": "pymupdf",
                "title": path.stem,
                "abstract": None,
                "sections": [],
                "references": [],
            }
