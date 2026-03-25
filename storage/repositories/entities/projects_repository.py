from __future__ import annotations

from typing import Any

from ..sqlite_repository import SQLiteRepository


class ProjectsRepository:
    def __init__(self, repo: SQLiteRepository | None = None) -> None:
        self.repo = repo or SQLiteRepository()
        self.category = "projects"

    def save(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repo.save_json(self.category, project_id, payload)

    def get(self, project_id: str) -> dict[str, Any]:
        return self.repo.read_json(self.category, project_id)

    def get_latest(self) -> dict[str, Any]:
        return self.repo.get_latest(self.category)

    def list_ids(self) -> list[str]:
        return self.repo.list_json(self.category)

    def list_records(self) -> list[dict[str, Any]]:
        return self.repo.list_records(self.category)

    def exists(self, project_id: str) -> bool:
        return self.repo.exists(self.category, project_id)

    def delete(self, project_id: str) -> bool:
        return self.repo.delete_json(self.category, project_id)

    def find_by_status(self, status: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(
            self.category,
            lambda payload, _: payload.get("status") == status,
        )

    def find_by_owner(self, owner: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(
            self.category,
            lambda payload, _: payload.get("owner") == owner,
        )

    def update_field(self, project_id: str, field: str, value: Any) -> dict[str, Any]:
        payload = self.repo.read_json(self.category, project_id)
        payload[field] = value
        return self.repo.save_json(self.category, project_id, payload)
