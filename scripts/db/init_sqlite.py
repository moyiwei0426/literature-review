from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "aris_lit.db"
SCHEMA_PATH = PROJECT_ROOT / "storage" / "repositories" / "sql" / "schema.sql"


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema)
        conn.commit()
        print(f"Initialized SQLite DB at: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
