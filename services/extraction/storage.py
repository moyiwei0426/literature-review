from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infra.settings import get_settings


class ExtractionStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.profile_dir = settings.data_dir / "generated" / "profiles"
        self.claims_dir = settings.data_dir / "generated" / "claims"
        self.links_dir = settings.data_dir / "generated" / "claim_links"
        self.reports_dir = settings.data_dir / "generated" / "reports"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.claims_dir.mkdir(parents=True, exist_ok=True)
        self.links_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(self, paper_id: str, payload: dict[str, Any]) -> Path:
        path = self.profile_dir / f"{paper_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_claims(self, paper_id: str, payload: list[dict[str, Any]]) -> Path:
        path = self.claims_dir / f"{paper_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_links(self, paper_id: str, payload: list[dict[str, Any]]) -> Path:
        path = self.links_dir / f"{paper_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_report(self, paper_id: str, payload: dict[str, Any]) -> Path:
        path = self.reports_dir / f"extraction_{paper_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
