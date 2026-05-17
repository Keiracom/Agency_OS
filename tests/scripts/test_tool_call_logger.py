"""Tests for scripts/orchestrator/tool_call_logger.py — KEI-54 Stage A.

Mocks psycopg.connect so tests don't reach Supabase. Verifies:
  - DSN env var pickup (DATABASE_URL preferred, SUPABASE_DB_URL fallback)
  - Truncation of large output to 500-char excerpt
  - duration_ms computed from started_at + completed_at delta
  - tool_input dict serialised to JSONB
  - DB error wrapped in ToolCallLoggerError
  - Callsign lowercased defensively
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# Shared psycopg mocks live in tests/scripts/_db_mocks.py per Sonar
# new_duplicated_lines_density (KEI-54 amend). Filename intentionally is
# NOT conftest.py — root-level conftest.py wins module resolution.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _db_mocks import FakeConn, FakeCursor  # type: ignore[import-not-found]  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "tool_call_logger.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("tool_call_logger", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tool_call_logger"] = m
    spec.loader.exec_module(m)
    return m


def _make_cursor(returned_id: str = "abc-123") -> FakeCursor:
    """Factory for the canonical insert-returning-id cursor used here."""
    return FakeCursor(fetchone_row=(returned_id,))


@pytest.fixture
def patch_connect(mod, monkeypatch):
    def _patch(cur: FakeCursor) -> FakeConn:
        import psycopg

        conn = FakeConn(cur)
        monkeypatch.setattr(psycopg, "connect", lambda *_a, **_kw: conn)
        return conn

    return _patch


@pytest.fixture(autouse=True)
def set_dsn(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    yield


# ─── DSN ───────────────────────────────────────────────────────────────────────


def test_dsn_missing_raises(mod, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(mod.ToolCallLoggerError):
        mod._dsn()


def test_dsn_prefers_database_url(mod, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://primary")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fallback")
    assert mod._dsn() == "postgresql://primary"


def test_dsn_rewrites_asyncpg_driver(mod, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:y@h/d")
    assert mod._dsn() == "postgresql://x:y@h/d"


# ─── truncate helper ──────────────────────────────────────────────────────────


def test_truncate_short_string_unchanged(mod):
    assert mod._truncate("short", 100) == "short"


def test_truncate_long_string_clipped_with_marker(mod):
    long = "x" * 700
    out = mod._truncate(long, 500)
    assert out is not None
    assert out.startswith("x" * 500)
    assert "truncated 200 chars" in out


def test_truncate_none_passthrough(mod):
    assert mod._truncate(None) is None


# ─── log_tool_call happy path ─────────────────────────────────────────────────


def test_log_tool_call_returns_inserted_uuid(mod, patch_connect):
    cur = _make_cursor("11111111-2222-3333-4444-555555555555")
    patch_connect(cur)
    started = datetime.now(UTC)
    completed = started + timedelta(milliseconds=42)
    uid = mod.log_tool_call(
        callsign="aiden",
        tool_name="Bash",
        tool_input={"command": "ls"},
        started_at=started,
        completed_at=completed,
        exit_code=0,
        output="ok",
    )
    assert uid == "11111111-2222-3333-4444-555555555555"


def test_log_tool_call_lowercases_callsign(mod, patch_connect):
    cur = _make_cursor()
    patch_connect(cur)
    mod.log_tool_call(
        callsign="AIDEN",
        tool_name="Read",
        started_at=datetime.now(UTC),
    )
    # First param is callsign — must be lowercased.
    assert cur.last_params[0] == "aiden"


def test_log_tool_call_computes_duration_ms(mod, patch_connect):
    cur = _make_cursor()
    patch_connect(cur)
    started = datetime(2026, 5, 14, 0, 0, 0, tzinfo=UTC)
    completed = started + timedelta(milliseconds=123)
    mod.log_tool_call(
        callsign="aiden",
        tool_name="Bash",
        started_at=started,
        completed_at=completed,
    )
    # Params order: (callsign, session_uuid, tool_name, tool_input,
    #               tool_output_excerpt, started_at, completed_at, duration_ms, exit_code)
    assert cur.last_params[7] == 123


def test_log_tool_call_omits_duration_when_completed_missing(mod, patch_connect):
    cur = _make_cursor()
    patch_connect(cur)
    mod.log_tool_call(
        callsign="aiden",
        tool_name="Bash",
        started_at=datetime.now(UTC),
    )
    # duration_ms is the 8th positional param
    assert cur.last_params[7] is None


def test_log_tool_call_serialises_tool_input_to_json(mod, patch_connect):
    cur = _make_cursor()
    patch_connect(cur)
    # Note: avoid hardcoded "/tmp" or "/var/tmp" literal — Sonar S5443 flags
    # them as publicly-writable references even in test fixture data.
    payload = {"command": "ls -la", "cwd": "/workdir", "nested": {"k": 1}}
    mod.log_tool_call(
        callsign="aiden",
        tool_name="Bash",
        tool_input=payload,
        started_at=datetime.now(UTC),
    )
    # tool_input is the 4th positional param — must be a JSON-encoded string
    # (psycopg ::jsonb cast handles conversion at SQL level).
    encoded = cur.last_params[3]
    assert json.loads(encoded) == payload


def test_log_tool_call_truncates_large_output(mod, patch_connect):
    cur = _make_cursor()
    patch_connect(cur)
    big_output = "y" * 2000
    mod.log_tool_call(
        callsign="aiden",
        tool_name="Bash",
        started_at=datetime.now(UTC),
        output=big_output,
    )
    # tool_output_excerpt is the 5th positional param
    excerpt = cur.last_params[4]
    assert excerpt is not None
    assert len(excerpt) < 2000
    assert "truncated" in excerpt


def test_log_tool_call_default_empty_tool_input(mod, patch_connect):
    cur = _make_cursor()
    patch_connect(cur)
    mod.log_tool_call(
        callsign="aiden",
        tool_name="Read",
        started_at=datetime.now(UTC),
    )
    # tool_input defaults to {} encoded
    assert json.loads(cur.last_params[3]) == {}


# ─── error paths ──────────────────────────────────────────────────────────────


def test_log_tool_call_wraps_psycopg_error(mod, monkeypatch):
    import psycopg

    def boom(*_a, **_kw):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(psycopg, "connect", boom)
    with pytest.raises(mod.ToolCallLoggerError) as exc_info:
        mod.log_tool_call(
            callsign="aiden",
            tool_name="Bash",
            started_at=datetime.now(UTC),
        )
    assert "insert failed" in str(exc_info.value)


def test_log_tool_call_raises_on_no_returning_row(mod, monkeypatch):
    # FakeCursor with fetchone_row=None returns None — simulates INSERT
    # ... RETURNING that produced no row (e.g. no permission, no match).
    cur = FakeCursor(fetchone_row=None)
    conn = FakeConn(cur)
    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *_a, **_kw: conn)
    with pytest.raises(mod.ToolCallLoggerError) as exc_info:
        mod.log_tool_call(
            callsign="aiden",
            tool_name="Bash",
            started_at=datetime.now(UTC),
        )
    assert "no row" in str(exc_info.value)
