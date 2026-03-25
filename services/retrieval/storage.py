from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infra.settings import get_settings


class RetrievalStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.raw_dir = settings.data_dir / "raw" / "retrieval"
        self.generated_dir = settings.data_dir / "generated" / "candidates"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    def save_raw(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.raw_dir / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_candidates(self, name: str, candidates: list[dict[str, Any]]) -> Path:
        path = self.generated_dir / f"{name}.json"
        path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
