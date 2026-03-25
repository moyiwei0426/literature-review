from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AppSettings(BaseSettings):
    app_name: str = Field(default="ARIS-Lit")
    env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    data_dir: Path = Field(default=PROJECT_ROOT / "data")
    local_watch_dir: Path = Field(default=PROJECT_ROOT / "data" / "manual_uploads")

    postgres_url: str = Field(default="postgresql://localhost:5432/aris_lit")
    grobid_url: str = Field(default="http://localhost:8070")
    redis_url: str = Field(default="redis://localhost:6379/0")

    openalex_base_url: str = Field(default="https://api.openalex.org")
    arxiv_base_url: str = Field(default="https://export.arxiv.org/api/query")
    semanticscholar_base_url: str = Field(default="https://api.semanticscholar.org/graph/v1")
    crossref_base_url: str = Field(default="https://api.crossref.org")
    unpaywall_base_url: str = Field(default="https://api.unpaywall.org/v2")

    llm_provider: str = Field(default="")
    llm_model: str = Field(default="")
    llm_base_url: str = Field(default="")
    llm_api_key: str = Field(default="")
    llm_timeout_seconds: int = Field(default=120)

    oauth_client_id: str = Field(default="")
    oauth_client_secret: str = Field(default="")
    oauth_authorize_url: str = Field(default="")
    oauth_token_url: str = Field(default="")
    oauth_redirect_uri: str = Field(default="")
    oauth_scope: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings


if __name__ == "__main__":
    settings = get_settings()
    print(settings.model_dump_json(indent=2, exclude_none=True))
