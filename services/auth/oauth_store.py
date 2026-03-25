from __future__ import annotations

from typing import Any

from storage.repositories import SQLiteRepository
from .oauth_models import OAuthToken


class OAuthTokenStore:
    def __init__(self, repo: SQLiteRepository | None = None) -> None:
        self.repo = repo or SQLiteRepository()
        self.category = "oauth_tokens"

    def save(self, provider: str, token: OAuthToken) -> dict[str, Any]:
        return self.repo.save_json(self.category, provider, token.to_dict())

    def get(self, provider: str) -> OAuthToken:
        payload = self.repo.read_json(self.category, provider)
        return OAuthToken(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "Bearer"),
            expires_in=payload.get("expires_in"),
            refresh_token=payload.get("refresh_token"),
            scope=payload.get("scope"),
            expires_at=payload.get("expires_at"),
            raw=payload.get("raw") or {},
        )

    def exists(self, provider: str) -> bool:
        return self.repo.exists(self.category, provider)

    def delete(self, provider: str) -> bool:
        return self.repo.delete_json(self.category, provider)
