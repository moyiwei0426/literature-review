from __future__ import annotations

import time
from typing import Any

from storage.repositories import SQLiteRepository


class OAuthStateStore:
    def __init__(self, repo: SQLiteRepository | None = None) -> None:
        self.repo = repo or SQLiteRepository()
        self.category = "oauth_states"

    def save(self, provider: str, state: str, ttl_seconds: int = 600) -> dict[str, Any]:
        now = time.time()
        payload = {
            "provider": provider,
            "state": state,
            "created_at": now,
            "expires_at": now + ttl_seconds,
            "consumed": False,
        }
        return self.repo.save_json(self.category, f"{provider}:{state}", payload)

    def get(self, provider: str, state: str) -> dict[str, Any]:
        return self.repo.read_json(self.category, f"{provider}:{state}")

    def exists(self, provider: str, state: str) -> bool:
        return self.repo.exists(self.category, f"{provider}:{state}")

    def validate(self, provider: str, state: str) -> bool:
        payload = self.get(provider, state)
        if payload.get("consumed"):
            return False
        expires_at = payload.get("expires_at")
        if expires_at and time.time() > float(expires_at):
            return False
        return True

    def consume(self, provider: str, state: str) -> dict[str, Any]:
        payload = self.get(provider, state)
        payload["consumed"] = True
        payload["consumed_at"] = time.time()
        self.repo.save_json(self.category, f"{provider}:{state}", payload)
        return payload

    def purge_expired(self, provider: str | None = None) -> int:
        count = 0
        records = self.repo.list_records(self.category)
        now = time.time()
        for record in records:
            payload = record["payload"]
            if provider and payload.get("provider") != provider:
                continue
            if payload.get("expires_at") and now > float(payload["expires_at"]):
                if self.repo.delete_json(self.category, record["name"]):
                    count += 1
        return count
