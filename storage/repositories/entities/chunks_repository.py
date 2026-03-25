from __future__ import annotations

from typing import Any

from ..sqlite_repository import SQLiteRepository


class ChunksRepository:
    def __init__(self, repo: SQLiteRepository | None = None) -> None:
        self.repo = repo or SQLiteRepository()
        self.category = "chunks"

    def save(self, chunk_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repo.save_json(self.category, chunk_id, payload)

    def get(self, chunk_id: str) -> dict[str, Any]:
        return self.repo.read_json(self.category, chunk_id)

    def get_latest(self) -> dict[str, Any]:
        return self.repo.get_latest(self.category)

    def list_ids(self) -> list[str]:
        return self.repo.list_json(self.category)

    def list_records(self) -> list[dict[str, Any]]:
        return self.repo.list_records(self.category)

    def exists(self, chunk_id: str) -> bool:
        return self.repo.exists(self.category, chunk_id)

    def delete(self, chunk_id: str) -> bool:
        return self.repo.delete_json(self.category, chunk_id)

    def find_by_paper_id(self, paper_id: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(
            self.category,
            lambda payload, _: payload.get("paper_id") == paper_id,
        )

    def find_by_section(self, section: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(
            self.category,
            lambda payload, _: payload.get("section") == section,
        )

    def find_by_quality_above(self, threshold: float) -> list[dict[str, Any]]:
        return self.repo.filter_records(
            self.category,
            lambda payload, _: (payload.get("quality_score") or 0) >= threshold,
        )
