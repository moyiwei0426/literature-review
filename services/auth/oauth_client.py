from __future__ import annotations

import time
from urllib.parse import urlencode

import httpx

from infra.settings import get_settings
from .oauth_models import OAuthToken
from .oauth_store import OAuthTokenStore
from .oauth_state_store import OAuthStateStore


class OAuthClient:
    def __init__(self, provider: str | None = None, store: OAuthTokenStore | None = None, state_store: OAuthStateStore | None = None) -> None:
        settings = get_settings()
        self.settings = settings
        self.provider = provider or settings.llm_provider or "oauth"
        self.client_id = settings.oauth_client_id
        self.client_secret = settings.oauth_client_secret
        self.authorize_url = settings.oauth_authorize_url
        self.token_url = settings.oauth_token_url
        self.redirect_uri = settings.oauth_redirect_uri
        self.scope = settings.oauth_scope
        self.store = store or OAuthTokenStore()
        self.state_store = state_store or OAuthStateStore()
        self.timeout = settings.llm_timeout_seconds

    def is_configured(self) -> bool:
        return all([
            self.client_id,
            self.client_secret,
            self.authorize_url,
            self.token_url,
            self.redirect_uri,
        ])

    def build_authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": self.scope,
                "state": state,
            }
        )
        return f"{self.authorize_url}?{query}"

    def create_authorization_session(self, ttl_seconds: int = 600) -> tuple[str, str]:
        state = self._generate_state()
        self.state_store.save(self.provider, state, ttl_seconds=ttl_seconds)
        return state, self.build_authorize_url(state)

    def validate_state(self, state: str) -> bool:
        return self.state_store.validate(self.provider, state)

    def consume_state(self, state: str) -> dict:
        return self.state_store.consume(self.provider, state)

    def exchange_code(self, code: str) -> OAuthToken:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.token_url, data=payload, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
        token = self._token_from_payload(data)
        self.store.save(self.provider, token)
        return token

    def refresh_access_token(self, refresh_token: str | None = None) -> OAuthToken:
        token = self.store.get(self.provider)
        refresh_value = refresh_token or token.refresh_token
        if not refresh_value:
            raise ValueError("No refresh token available for OAuth refresh")
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_value,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.token_url, data=payload, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
        if "refresh_token" not in data:
            data["refresh_token"] = refresh_value
        token = self._token_from_payload(data)
        self.store.save(self.provider, token)
        return token

    def get_valid_access_token(self) -> str:
        token = self.store.get(self.provider)
        if self._needs_refresh(token):
            token = self.refresh_access_token(token.refresh_token)
        return token.access_token

    def _needs_refresh(self, token: OAuthToken) -> bool:
        if not token.expires_at:
            return False
        return time.time() >= token.expires_at - 60

    def provider_health(self) -> dict:
        return {
            "provider": self.provider,
            "configured": self.is_configured(),
            "authorize_url": self.authorize_url,
            "token_url": self.token_url,
            "redirect_uri": self.redirect_uri,
            "has_token": self.store.exists(self.provider),
        }

    def _generate_state(self) -> str:
        import secrets
        return secrets.token_urlsafe(24)

    def _token_from_payload(self, payload: dict) -> OAuthToken:
        expires_in = payload.get("expires_in")
        expires_at = time.time() + int(expires_in) if expires_in else None
        return OAuthToken.from_payload(payload, expires_at=expires_at)
