"""Tests for scripts/roadmap_status.py — Dave directive 2026-05-31.

Covers:
  (1) happy path — table render with emoji status + correct column ordering.
  (2) DB-unreachable fallback — STATUS_BLOCK_UNAVAILABLE stub, exit 0.
  (3) --write rewrites the STATUS block between the markers in ROADMAP_V2.md.

Uses monkeypatch to swap psycopg.connect for a fake connection; does NOT
hit the live Supabase DB.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "roadmap_status.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("roadmap_status_mod", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["roadmap_status_mod"] = m
    spec.loader.exec_module(m)
    return m


_SAMPLE_ROWS = [
    (
        "temporal_chain",
        "Phase 1",
        "build",
        "gate_crash_recovery",
        "built",
        "atlas",
        "Agency_OS-jn14",
        None,
        datetime(2026, 5, 31, 12, 34, 56, tzinfo=UTC),
    ),
    (
        "atom_capture",
        "Phase 3",
        None,
        "gate_atoms",
        "not_started",
        "orion",
        None,
        "table missing",
        None,
    ),
]


class _FakeCursor:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows
        self.last_query: str | None = None

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *a: Any) -> None:
        return None

    def execute(self, sql: str) -> None:
        self.last_query = sql

    def fetchall(self) -> list[tuple]:
        return list(self._rows)


class _FakeConn:
    def __init__(self, rows: list[tuple]) -> None:
        self._cur = _FakeCursor(rows)

    def cursor(self) -> _FakeCursor:
        return self._cur

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


# ─── (1) happy path ──────────────────────────────────────────────────────────


def test_render_happy_path_emits_table_with_emoji(monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: _FakeConn(_SAMPLE_ROWS))

    rc = mod.main(["--render"])
    out = capsys.readouterr().out

    assert rc == 0
    # Header is intact and column ordering is locked
    assert "| Component | Phase | Status | Owner | Last Verified | Gate |" in out
    # Both rows render
    assert "temporal_chain" in out
    assert "atom_capture" in out
    # Status emoji mapping fires for known statuses
    assert "🔨 built" in out
    assert "⬜ not_started" in out
    # Phase + subphase compose correctly when both present
    assert "Phase 1 / build" in out
    # NULL last_verified surfaces as an em-dash rather than 'None'
    assert "| — |" in out


# ─── (2) DB unreachable fallback ─────────────────────────────────────────────


def test_render_db_unreachable_emits_unavailable_stub_and_exits_zero(monkeypatch, capsys):
    mod = _load_module()
    # No DSN env → _fetch_rows returns an error sentinel
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_DSN", raising=False)

    rc = mod.main(["--render"])
    out = capsys.readouterr().out

    assert rc == 0, "renderer must NEVER non-zero — CI auto-commit relies on it"
    assert "STATUS_BLOCK_UNAVAILABLE" in out
    assert "DATABASE_URL" in out or "SUPABASE_DB_DSN" in out


def test_render_psycopg_connect_error_emits_unavailable_stub(monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    import psycopg

    def _boom(*a, **kw):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(psycopg, "connect", _boom)

    rc = mod.main(["--render"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "STATUS_BLOCK_UNAVAILABLE" in out
    assert "connection refused" in out


# ─── (3) --write rewrites STATUS block between markers ───────────────────────


def test_write_replaces_block_between_markers(monkeypatch, tmp_path):
    mod = _load_module()

    target = tmp_path / "ROADMAP_V2.md"
    target.write_text(
        "# header\n\n"
        "some narrative\n\n"
        "## Current status\n\n"
        f"{mod.STATUS_BLOCK_START}\n"
        "STALE CONTENT TO REPLACE\n"
        f"{mod.STATUS_BLOCK_END}\n"
        "\ntrailing prose\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "ROADMAP_PATH", target)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: _FakeConn(_SAMPLE_ROWS))

    rc = mod.main(["--write"])
    assert rc == 0

    after = target.read_text(encoding="utf-8")
    # Stale content gone
    assert "STALE CONTENT TO REPLACE" not in after
    # Markers preserved
    assert mod.STATUS_BLOCK_START in after
    assert mod.STATUS_BLOCK_END in after
    # New table content lives between them
    assert "temporal_chain" in after
    assert "🔨 built" in after
    # Surrounding prose untouched
    assert "# header" in after
    assert "trailing prose" in after


def test_write_no_markers_warns_and_exits_zero(monkeypatch, tmp_path, capsys):
    mod = _load_module()

    target = tmp_path / "ROADMAP_V2.md"
    target.write_text("# header\n\nno markers here\n", encoding="utf-8")
    original = target.read_text(encoding="utf-8")

    monkeypatch.setattr(mod, "ROADMAP_PATH", target)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")

    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: _FakeConn(_SAMPLE_ROWS))

    rc = mod.main(["--write"])
    err = capsys.readouterr().err

    assert rc == 0
    assert "STATUS_BLOCK markers not found" in err
    # File unchanged when markers missing — no silent corruption
    assert target.read_text(encoding="utf-8") == original
