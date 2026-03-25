from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infra.settings import get_settings


class GapStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.gaps_dir = settings.data_dir / "generated" / "gaps"
        self.gaps_dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, payload: Any) -> Path:
        path = self.gaps_dir / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
