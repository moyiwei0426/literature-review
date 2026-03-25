from __future__ import annotations

from datetime import datetime

from .arxiv_client import ArxivClient
from .openalex_client import OpenAlexClient
from .query_builder import QueryPlan
from .storage import RetrievalStorage


class RetrievalAggregator:
    def __init__(self) -> None:
        self.openalex = OpenAlexClient()
        self.arxiv = ArxivClient()
        self.storage = RetrievalStorage()

    def run(self, plan: QueryPlan) -> dict:
        all_candidates = []
        raw_logs = {}

        per_source = max(1, plan.max_results // max(len(plan.include_sources), 1))

        if "openalex" in plan.include_sources:
            candidates, raw = self.openalex.search(plan.query, max_results=per_source)
            all_candidates.extend(candidates)
            raw_logs["openalex"] = raw

        if "arxiv" in plan.include_sources:
            candidates, raw = self.arxiv.search(plan.query, max_results=per_source)
            all_candidates.extend(candidates)
            raw_logs["arxiv"] = raw

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.storage.save_raw(f"retrieval_{stamp}", raw_logs)
        self.storage.save_candidates(
            f"candidates_{stamp}",
            [candidate.model_dump() for candidate in all_candidates],
        )

        return {
            "count": len(all_candidates),
            "sources": list(raw_logs.keys()),
            "candidates": all_candidates,
            "raw_logs": raw_logs,
        }
