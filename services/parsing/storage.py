from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infra.settings import get_settings


class ParsingStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.parsed_dir = settings.data_dir / "parsed"
        self.chunks_dir = settings.data_dir / "generated" / "chunks"
        self.reports_dir = settings.data_dir / "generated" / "reports"
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def save_parsed(self, paper_id: str, payload: dict[str, Any]) -> Path:
        path = self.parsed_dir / f"{paper_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_chunks(self, paper_id: str, payload: list[dict[str, Any]]) -> Path:
        path = self.chunks_dir / f"{paper_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_quality_report(self, paper_id: str, payload: dict[str, Any]) -> Path:
        path = self.reports_dir / f"parse_quality_{paper_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
