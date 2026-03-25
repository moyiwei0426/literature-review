from __future__ import annotations

from typing import Any

from ..sqlite_repository import SQLiteRepository


class PapersRepository:
    def __init__(self, repo: SQLiteRepository | None = None) -> None:
        self.repo = repo or SQLiteRepository()
        self.category = "papers"

    def save(self, paper_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repo.save_json(self.category, paper_id, payload)

    def get(self, paper_id: str) -> dict[str, Any]:
        return self.repo.read_json(self.category, paper_id)

    def get_latest(self) -> dict[str, Any]:
        return self.repo.get_latest(self.category)

    def list_ids(self) -> list[str]:
        return self.repo.list_json(self.category)

    def list_records(self) -> list[dict[str, Any]]:
        return self.repo.list_records(self.category)

    def exists(self, paper_id: str) -> bool:
        return self.repo.exists(self.category, paper_id)

    def delete(self, paper_id: str) -> bool:
        return self.repo.delete_json(self.category, paper_id)

    def find_by_year(self, year: int) -> list[dict[str, Any]]:
        return self.repo.filter_records(self.category, lambda payload, _: payload.get("year") == year)

    def find_by_venue(self, venue: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(self.category, lambda payload, _: payload.get("venue") == venue)

    def find_by_doi(self, doi: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(self.category, lambda payload, _: payload.get("doi") == doi)

    def find_by_arxiv_id(self, arxiv_id: str) -> list[dict[str, Any]]:
        return self.repo.filter_records(self.category, lambda payload, _: payload.get("arxiv_id") == arxiv_id)
