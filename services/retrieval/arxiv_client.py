from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from .normalizer import normalize_candidate


from infra.settings import get_settings


class ArxivClient:
    def __init__(self, base_url: str | None = None, timeout: float = 20.0):
        settings = get_settings()
        self.base_url = base_url or settings.arxiv_base_url
        self.timeout = timeout

    def search(self, query: str, max_results: int = 25) -> tuple[list, dict[str, Any]]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
        }
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            text = response.text

        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results = []
        for entry in root.findall("atom:entry", ns):
            arxiv_id = (entry.findtext("atom:id", default="", namespaces=ns).rsplit("/", 1)[-1])
            authors = [author.findtext("atom:name", default="", namespaces=ns) for author in entry.findall("atom:author", ns)]
            pdf_url = None
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href")
                    break
            candidate = normalize_candidate(
                {
                    "source": "arxiv",
                    "source_id": arxiv_id,
                    "arxiv_id": arxiv_id,
                    "title": entry.findtext("atom:title", default="", namespaces=ns).strip(),
                    "authors": authors,
                    "abstract": entry.findtext("atom:summary", default="", namespaces=ns).strip(),
                    "pdf_url": pdf_url,
                    "retrieval_query": query,
                }
            )
            results.append(candidate)

        return results, {"raw_xml": text}
