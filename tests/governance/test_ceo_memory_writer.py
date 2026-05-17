"""Tests for src/governance/ceo_memory_writer.py — KEI-87.

Mocks psycopg.connect via a minimal fake. Verifies the wrapper's
SQL emission order (SET LOCAL agency_os.callsign first, then the
INSERT/UPDATE) — the trigger from the matching migration depends on
the session var being set in the same transaction before the write.

Trigger semantics themselves are covered by the migration's own
acceptance probe (live Supabase test post-deploy); these tests cover
the wrapper contract.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from src.governance import ceo_memory_writer


class _Cursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple | None]] = []
        self.rowcount = 1

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


class _Conn:
    def __init__(self) -> None:
        self.cur = _Cursor()
        self.commits = 0

    def cursor(self) -> _Cursor:
        return self.cur

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> _Conn:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")


def test_upsert_sets_local_callsign_before_write() -> None:
    conn = _Conn()
    with patch("psycopg.connect", return_value=conn):
        ceo_memory_writer.upsert_ceo_memory_key("elliot", "ceo:phase_lock", {"v": 1})
    sqls = [s for s, _ in conn.cur.executed]
    assert "SET LOCAL agency_os.callsign" in sqls[0]
    assert conn.cur.executed[0][1] == ("elliot",)
    assert "INSERT INTO public.ceo_memory" in sqls[1]
    assert conn.commits == 1


def test_update_sets_local_callsign_then_update() -> None:
    conn = _Conn()
    with patch("psycopg.connect", return_value=conn):
        ceo_memory_writer.update_ceo_memory_value("dave", "ceo:phase_lock", {"v": 2})
    sqls = [s for s, _ in conn.cur.executed]
    assert "SET LOCAL agency_os.callsign" in sqls[0]
    assert conn.cur.executed[0][1] == ("dave",)
    assert "UPDATE public.ceo_memory" in sqls[1]
    assert conn.commits == 1


def test_update_missing_row_raises_key_error() -> None:
    conn = _Conn()
    conn.cur.rowcount = 0
    with patch("psycopg.connect", return_value=conn), pytest.raises(KeyError):
        ceo_memory_writer.update_ceo_memory_value("max", "ceo:phase_lock", {"v": 3})


def test_callsign_required() -> None:
    with pytest.raises(ValueError):
        ceo_memory_writer.upsert_ceo_memory_key("", "ceo:phase_lock", {"v": 4})
    with pytest.raises(ValueError):
        ceo_memory_writer.update_ceo_memory_value("   ", "ceo:phase_lock", {"v": 5})


def test_dsn_falls_back_to_supabase_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fallback/x")
    assert ceo_memory_writer._dsn() == "postgresql://fallback/x"
