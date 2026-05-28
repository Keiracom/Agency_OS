"""Tests for scripts/three_store_save.py — LAW XVII callsign discipline."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Load the script as a module (it's in scripts/, not src/)
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "three_store_save.py"
spec = importlib.util.spec_from_file_location("three_store_save", SCRIPT_PATH)
tss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tss)


def test_callsign_defaults_to_elliot(monkeypatch):
    """When CALLSIGN env var is unset, default is 'elliot'."""
    monkeypatch.delenv("CALLSIGN", raising=False)
    assert tss.get_callsign() == "elliot"


def test_callsign_respects_aiden(monkeypatch):
    """When CALLSIGN=aiden, return aiden."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    assert tss.get_callsign() == "aiden"


def test_callsign_empty_string_fails_loud(monkeypatch):
    """LAW XVII: empty CALLSIGN refuses to save (raises SystemExit)."""
    monkeypatch.setenv("CALLSIGN", "")
    with pytest.raises(SystemExit, match="LAW XVII"):
        tss.get_callsign()


# manual_entry tests removed 2026-05-27 (PR #1214 Agency_OS-uik) — docs/MANUAL.md
# archived; three_store_save.py no longer touches the Manual.


# ─── asyncpg migration (REST → pgbouncer-friendly direct DB) ──────────────


class _FakeConn:
    """Minimal asyncpg-conn double — records every execute call."""

    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self.closed = False

    async def execute(self, sql, *args):
        self.executed.append((sql, args))
        return "INSERT 0 1"

    async def close(self):
        self.closed = True


def _patch_asyncpg(monkeypatch, conn):
    """Stub `import asyncpg; await asyncpg.connect(...)` inside save_*."""
    import sys
    import types

    fake = types.SimpleNamespace()

    async def _connect(dsn, **kw):
        # Verify the pgbouncer-compat flag is set.
        assert kw.get("statement_cache_size") == 0
        assert dsn.startswith("postgresql://")
        return conn

    fake.connect = _connect
    monkeypatch.setitem(sys.modules, "asyncpg", fake)


def test_resolve_dsn_prefers_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert tss._resolve_dsn() == "postgresql://u:p@host/db"


def test_resolve_dsn_falls_back_to_supabase(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://x:y@h/d")
    assert tss._resolve_dsn() == "postgresql://x:y@h/d"


def test_resolve_dsn_strips_sqlalchemy_prefix(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/d")
    assert tss._resolve_dsn() == "postgresql://u:p@h/d"


def test_resolve_dsn_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    # Make settings.database_url empty too.
    import sys
    import types

    fake_mod = types.ModuleType("src.config.settings")
    fake_mod.settings = types.SimpleNamespace(database_url="")
    monkeypatch.setitem(sys.modules, "src.config.settings", fake_mod)
    assert tss._resolve_dsn() is None


def test_save_ceo_memory_dry_run_no_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    # Dry-run path must not even resolve DSN.
    assert tss.save_ceo_memory("D9", 999, "x", dry_run=True, callsign="atlas") is True


def test_save_ceo_memory_no_dsn_returns_false(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    import sys
    import types

    fake_mod = types.ModuleType("src.config.settings")
    fake_mod.settings = types.SimpleNamespace(database_url="")
    monkeypatch.setitem(sys.modules, "src.config.settings", fake_mod)
    assert tss.save_ceo_memory("D9", 999, "x", dry_run=False) is False


def test_save_ceo_memory_calls_wrapper(monkeypatch):
    """save_ceo_memory delegates to upsert_ceo_memory_key (KEI-87 wrapper)."""
    calls: list[tuple] = []

    def _fake_upsert(callsign: str, key: str, value: dict) -> None:
        calls.append((callsign, key, value))

    monkeypatch.setattr(tss, "upsert_ceo_memory_key", _fake_upsert)
    result = tss.save_ceo_memory("D7", 707, "atlas summary", dry_run=False, callsign="atlas")
    assert result is True
    assert len(calls) == 1
    cs, key, val = calls[0]
    assert cs == "atlas"
    assert key == "ceo:directive_D7_complete"
    assert val["pr"] == 707
    assert val["source"] == "atlas"


def test_save_metrics_dry_run_no_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert tss.save_metrics("D9", 999, "x", dry_run=True) is True


def test_save_metrics_executes_insert_via_asyncpg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    conn = _FakeConn()
    _patch_asyncpg(monkeypatch, conn)
    assert tss.save_metrics("D7", 707, "summary", dry_run=False, callsign="atlas") is True
    assert conn.closed
    sql, args = conn.executed[0]
    assert "INSERT INTO cis_directive_metrics" in sql
    # directive_id=0 / directive_ref="D7" because non-numeric label
    assert args[0] == 0
    assert args[1] == "D7"
    assert args[10] == "atlas"  # callsign positional


def test_save_metrics_numeric_directive_uses_directive_id(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    conn = _FakeConn()
    _patch_asyncpg(monkeypatch, conn)
    tss.save_metrics("309", 707, "summary", dry_run=False)
    _, args = conn.executed[0]
    assert args[0] == 309
    assert args[1] is None


def test_save_metrics_includes_on_conflict_compound_key(monkeypatch):
    """Wave 1 Item 2: replay must not duplicate rows. INSERT uses ON CONFLICT
    (directive_id, directive_ref) DO UPDATE for the compound-key upsert
    (NULLS NOT DISTINCT in the migration handles numeric directives where
    directive_ref is always NULL)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    conn = _FakeConn()
    _patch_asyncpg(monkeypatch, conn)
    tss.save_metrics("D7", 707, "summary", dry_run=False, callsign="max")
    sql, _ = conn.executed[0]
    assert "INSERT INTO cis_directive_metrics" in sql
    assert "ON CONFLICT (directive_id, directive_ref) DO UPDATE SET" in sql


def test_save_metrics_on_conflict_increments_execution_rounds(monkeypatch):
    """ON CONFLICT path increments execution_rounds (captures replay count)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    conn = _FakeConn()
    _patch_asyncpg(monkeypatch, conn)
    tss.save_metrics("D7", 707, "summary", dry_run=False)
    sql, _ = conn.executed[0]
    assert "execution_rounds = cis_directive_metrics.execution_rounds + 1" in sql


def test_save_metrics_on_conflict_updates_mutable_fields(monkeypatch):
    """ON CONFLICT replaces completed_date, notes, callsign, agents_used, and
    the three boolean status flags with EXCLUDED.* — the replay's new values."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    conn = _FakeConn()
    _patch_asyncpg(monkeypatch, conn)
    tss.save_metrics("D7", 707, "summary", dry_run=False)
    sql, _ = conn.executed[0]
    for field in (
        "completed_date = EXCLUDED.completed_date",
        "scope_creep = EXCLUDED.scope_creep",
        "verification_first_pass = EXCLUDED.verification_first_pass",
        "save_completed = EXCLUDED.save_completed",
        "agents_used = EXCLUDED.agents_used",
        "notes = EXCLUDED.notes",
        "callsign = EXCLUDED.callsign",
    ):
        assert field in sql, f"missing {field!r} in DO UPDATE SET"


def test_save_ceo_memory_swallows_wrapper_error(monkeypatch):
    """save_ceo_memory returns False when the wrapper raises."""

    def _boom(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(tss, "upsert_ceo_memory_key", _boom)
    assert tss.save_ceo_memory("D7", 707, "x", dry_run=False) is False
