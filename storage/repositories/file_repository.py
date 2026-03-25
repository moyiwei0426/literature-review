from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infra.settings import get_settings


class FileRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_dir = settings.data_dir / "repository"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, category: str, name: str, payload: Any) -> Path:
        target_dir = self.base_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_json(self, category: str, name: str) -> Any:
        path = self.base_dir / category / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def list_json(self, category: str) -> list[str]:
        target_dir = self.base_dir / category
        if not target_dir.exists():
            return []
        return sorted([p.stem for p in target_dir.glob("*.json")])
