from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from infra.settings import get_settings
from .base import BaseRepository


class SQLiteRepository(BaseRepository):
    def __init__(self, db_path: str | None = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path) if db_path else settings.data_dir / "aris_lit.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS json_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, name)
                );
                """
            )
            conn.commit()

    def save_json(self, category: str, name: str, payload: Any) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO json_records(category, name, payload)
                VALUES(?, ?, ?)
                ON CONFLICT(category, name) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (category, name, data),
            )
            conn.commit()
        return {"category": category, "name": name, "db_path": str(self.db_path)}

    def read_json(self, category: str, name: str) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM json_records WHERE category = ? AND name = ?",
                (category, name),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"No record found for {category}/{name}")
        return json.loads(row["payload"])

    def list_json(self, category: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM json_records WHERE category = ? ORDER BY name",
                (category,),
            ).fetchall()
        return [row["name"] for row in rows]

    def list_records(self, category: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT category, name, payload, created_at, updated_at FROM json_records WHERE category = ? ORDER BY updated_at DESC, name ASC",
                (category,),
            ).fetchall()
        return [
            {
                "category": row["category"],
                "name": row["name"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def exists(self, category: str, name: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM json_records WHERE category = ? AND name = ? LIMIT 1",
                (category, name),
            ).fetchone()
        return row is not None

    def delete_json(self, category: str, name: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM json_records WHERE category = ? AND name = ?",
                (category, name),
            )
            conn.commit()
        return cur.rowcount > 0

    def get_latest(self, category: str) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM json_records WHERE category = ? ORDER BY updated_at DESC, name ASC LIMIT 1",
                (category,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"No records found for category {category}")
        return json.loads(row["payload"])

    def filter_records(self, category: str, predicate) -> list[dict[str, Any]]:
        records = self.list_records(category)
        return [record for record in records if predicate(record["payload"], record)]
