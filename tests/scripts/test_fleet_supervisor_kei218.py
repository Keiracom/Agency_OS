"""KEI-218 — regression: _db_dsn() must strip SQLAlchemy '+asyncpg' suffix.

The .env DATABASE_URL uses SQLAlchemy-style scheme `postgresql+asyncpg://`.
psycopg3 raises ProgrammingError on that prefix at connect time, causing
fleet-supervisor.service to crash-loop every 5min via fleet-supervisor.timer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import fleet_supervisor as fs


def test_db_dsn_strips_asyncpg_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@host:5432/db?sslmode=require",
    )
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert fs._db_dsn() == "postgresql://user:pass@host:5432/db?sslmode=require"


def test_db_dsn_bare_postgresql_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@host:5432/db",
    )
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert fs._db_dsn() == "postgresql://user:pass@host:5432/db"


def test_db_dsn_raises_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        fs._db_dsn()


def test_db_dsn_only_replaces_prefix_not_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    # Defensive: replace('...', '...', 1) means only the first occurrence is
    # rewritten. Verify a DSN whose password coincidentally contains the
    # literal string is left alone after the leading scheme is fixed.
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:postgresql+asyncpg://@host/db",
    )
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert fs._db_dsn() == "postgresql://u:postgresql+asyncpg://@host/db"
