#!/usr/bin/env python3
"""
Run PostgreSQL migrations.

Usage:
    python scripts/db/run_migrations.py [--dry-run]

Requires:
    DATABASE_URL environment variable or .env with postgres_url
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infra.settings import get_settings


MIGRATIONS_DIR = Path(__file__).resolve().parents[0] / "migrations"


def get_connection(url: str):
    return psycopg2.connect(url)


def ensure_migrations_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(50) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()


def applied_versions(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def run_migrations(dry_run: bool = False) -> None:
    settings = get_settings()
    url = settings.postgres_url
    print(f"Connecting to: {url.split('@')[1] if '@' in url else url}")

    conn = get_connection(url)
    ensure_migrations_table(conn)

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    applied = applied_versions(conn)

    for mf in migration_files:
        version = mf.stem  # e.g. "001_initial"
        if version in applied:
            print(f"  [skip] {version} already applied")
            continue
        sql = mf.read_text(encoding="utf-8")
        print(f"  [apply] {version}")
        if dry_run:
            print("       (dry-run, not executing)")
            continue
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            with conn.cursor() as cur:
                cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            conn.commit()
            print(f"       ✓ {version} applied")
        except Exception as exc:
            conn.rollback()
            print(f"       ✗ {version} failed: {exc}")
            sys.exit(1)

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_migrations(dry_run=args.dry_run)
