from __future__ import annotations

from typing import Any

from ..sqlite_repository import SQLiteRepository


class GapsRepository:
    def __init__(self, repo: SQLiteRepository | None = None) -> None:
        self.repo = repo or SQLiteRepository()
        self.category = "gaps"

    def save(self, gap_set_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repo.save_json(self.category, gap_set_id, payload)

    def get(self, gap_set_id: str) -> dict[str, Any]:
        return self.repo.read_json(self.category, gap_set_id)

    def get_latest(self) -> dict[str, Any]:
        return self.repo.get_latest(self.category)

    def list_ids(self) -> list[str]:
        return self.repo.list_json(self.category)

    def list_records(self) -> list[dict[str, Any]]:
        return self.repo.list_records(self.category)

    def exists(self, gap_set_id: str) -> bool:
        return self.repo.exists(self.category, gap_set_id)

    def delete(self, gap_set_id: str) -> bool:
        return self.repo.delete_json(self.category, gap_set_id)

    def find_verified(self) -> list[dict[str, Any]]:
        return self.repo.filter_records(
            self.category,
            lambda payload, _: any(item.get("status") == "verified" for item in payload.get("verified_gaps", [])),
        )

    def find_scored_above(self, threshold: float) -> list[dict[str, Any]]:
        return self.repo.filter_records(
            self.category,
            lambda payload, _: any(item.get("review_worthiness", 0) >= threshold for item in payload.get("scored_gaps", [])),
        )
