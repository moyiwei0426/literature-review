from __future__ import annotations

from typing import Any

from ..sqlite_repository import SQLiteRepository


class DraftsRepository:
    def __init__(self, repo: SQLiteRepository | None = None) -> None:
        self.repo = repo or SQLiteRepository()
        self.category = "drafts"

    def save(self, draft_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repo.save_json(self.category, draft_id, payload)

    def get(self, draft_id: str) -> dict[str, Any]:
        return self.repo.read_json(self.category, draft_id)

    def get_latest(self) -> dict[str, Any]:
        return self.repo.get_latest(self.category)

    def list_ids(self) -> list[str]:
        return self.repo.list_json(self.category)

    def list_records(self) -> list[dict[str, Any]]:
        return self.repo.list_records(self.category)

    def exists(self, draft_id: str) -> bool:
        return self.repo.exists(self.category, draft_id)

    def delete(self, draft_id: str) -> bool:
        return self.repo.delete_json(self.category, draft_id)

    def find_by_title(self, title: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(self.category, lambda payload, _: payload.get("title") == title)

    def find_with_compile_status(self, status: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(
            self.category,
            lambda payload, _: (payload.get("compile_result") or {}).get("status") == status,
        )

    def find_by_version(self, version: int) -> list[dict[str, Any]]:
        return self.repo.filter_records(self.category, lambda payload, _: payload.get("version") == version)
