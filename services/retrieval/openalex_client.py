from __future__ import annotations

from typing import Any

import httpx

from infra.settings import get_settings
from .normalizer import normalize_candidate


class OpenAlexClient:
    def __init__(self, base_url: str | None = None, timeout: float = 20.0):
        settings = get_settings()
        self.base_url = base_url or settings.openalex_base_url
        self.timeout = timeout

    def search(self, query: str, max_results: int = 25) -> tuple[list, dict[str, Any]]:
        params = {
            "search": query,
            "per-page": max_results,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/works", params=params)
            response.raise_for_status()
            payload = response.json()

        results = []
        for item in payload.get("results", []):
            candidate = normalize_candidate(
                {
                    "source": "openalex",
                    "source_id": item.get("id"),
                    "title": item.get("display_name"),
                    "authors": [a.get("author", {}) for a in item.get("authorships", [])],
                    "year": item.get("publication_year"),
                    "doi": item.get("doi"),
                    "abstract": None,
                    "citation_count": item.get("cited_by_count"),
                    "pdf_url": ((item.get("primary_location") or {}).get("pdf_url")),
                    "is_open_access": ((item.get("open_access") or {}).get("is_oa")),
                    "retrieval_query": query,
                }
            )
            results.append(candidate)

        return results, payload
