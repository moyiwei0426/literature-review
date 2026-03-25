from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.auth import OAuthClient

router = APIRouter(prefix="/auth", tags=["auth"])


class OAuthStartResponse(BaseModel):
    authorize_url: str
    state: str


class OAuthCallbackResponse(BaseModel):
    provider: str
    stored: bool
    expires_at: Optional[float] = None


class OAuthRefreshResponse(BaseModel):
    provider: str
    refreshed: bool
    expires_at: Optional[float] = None


class OAuthHealthResponse(BaseModel):
    provider: str
    configured: bool
    authorize_url: str
    token_url: str
    redirect_uri: str
    has_token: bool


class OAuthValidateStateResponse(BaseModel):
    provider: str
    state: str
    valid: bool


@router.get("/oauth/start", response_model=OAuthStartResponse)
def oauth_start() -> OAuthStartResponse:
    client = OAuthClient(provider="oauth_openai_compatible")
    if not client.is_configured():
        raise HTTPException(status_code=400, detail="OAuth is not fully configured")
    state, authorize_url = client.create_authorization_session()
    return OAuthStartResponse(authorize_url=authorize_url, state=state)


@router.get("/oauth/callback", response_model=OAuthCallbackResponse)
def oauth_callback(code: str = Query(...), state: str = Query(...)) -> OAuthCallbackResponse:
    client = OAuthClient(provider="oauth_openai_compatible")
    if not client.is_configured():
        raise HTTPException(status_code=400, detail="OAuth is not fully configured")
    if not client.validate_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    token = client.exchange_code(code)
    client.consume_state(state)
    return OAuthCallbackResponse(provider=client.provider, stored=True, expires_at=token.expires_at)


@router.post("/oauth/refresh", response_model=OAuthRefreshResponse)
def oauth_refresh() -> OAuthRefreshResponse:
    client = OAuthClient(provider="oauth_openai_compatible")
    if not client.is_configured():
        raise HTTPException(status_code=400, detail="OAuth is not fully configured")
    token = client.refresh_access_token()
    return OAuthRefreshResponse(provider=client.provider, refreshed=True, expires_at=token.expires_at)


@router.get("/oauth/health", response_model=OAuthHealthResponse)
def oauth_health() -> OAuthHealthResponse:
    client = OAuthClient(provider="oauth_openai_compatible")
    return OAuthHealthResponse(**client.provider_health())


@router.get("/oauth/state/validate", response_model=OAuthValidateStateResponse)
def oauth_validate_state(state: str = Query(...)) -> OAuthValidateStateResponse:
    client = OAuthClient(provider="oauth_openai_compatible")
    return OAuthValidateStateResponse(provider=client.provider, state=state, valid=client.validate_state(state))
