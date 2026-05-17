"""Unit tests for scripts/orchestrator/heartbeat_writer.py (KEI-105).

No live DB. Pure-mock tests covering env validation, DSN stripping,
SQL shape, fail-open error handling, and debug-log on zero rows.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "heartbeat_writer.py"

# Insert orchestrator dir so the script can resolve sibling imports when loaded
sys.path.insert(0, str(SCRIPT.parent))


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("heartbeat_writer", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["heartbeat_writer"] = m
    spec.loader.exec_module(m)
    return m


# ── entry-point (subprocess) tests ──────────────────────────────────────────


def test_missing_callsign_exits_2(tmp_path):
    """CALLSIGN unset → exit code 2 with stderr message."""
    import subprocess

    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}  # no CALLSIGN
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "CALLSIGN" in result.stderr


def test_missing_dsn_logs_and_exits_0(tmp_path):
    """No DATABASE_URL or SUPABASE_DB_URL → log warning, exit 0 (fail-open)."""
    import subprocess

    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "CALLSIGN": "orion"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Warning goes to stderr (logging default stream via basicConfig)
    assert "DATABASE_URL" in result.stderr or "SUPABASE_DB_URL" in result.stderr


# ── direct main() tests (mock psycopg) ───────────────────────────────────────


def _make_fake_conn(rows: list[tuple]) -> MagicMock:
    """Build a minimal fake psycopg connection + cursor returning `rows`."""
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    return conn, cur


def test_update_sql_shape(mod, monkeypatch):
    """SQL passed to cur.execute contains claimed_by param + status='active' guard."""
    monkeypatch.setenv("CALLSIGN", "orion")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/db")

    conn, cur = _make_fake_conn([])
    with patch("psycopg.connect", return_value=conn):
        rc = mod.main()

    assert rc == 0
    sql_called, params_called = cur.execute.call_args[0]
    assert "UPDATE public.tasks" in sql_called
    assert "heartbeat_at = NOW()" in sql_called
    assert "claimed_by" in sql_called
    assert "status = 'active'" in sql_called
    assert params_called == ("orion",)


def test_dsn_asyncpg_stripped(mod, monkeypatch):
    """DSN with postgresql+asyncpg:// prefix is stripped before connect."""
    monkeypatch.setenv("CALLSIGN", "orion")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://host/db")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    conn, _ = _make_fake_conn([])
    with patch("psycopg.connect", return_value=conn) as mock_connect:
        mod.main()

    dsn_used = mock_connect.call_args[0][0]
    assert dsn_used == "postgresql://host/db"
    assert "asyncpg" not in dsn_used


def test_db_failure_fails_open_exit_0(mod, monkeypatch):
    """psycopg.connect raising → log warning, return 0 (fail-open)."""
    monkeypatch.setenv("CALLSIGN", "orion")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/db")

    with patch("psycopg.connect", side_effect=Exception("connection refused")):
        rc = mod.main()

    assert rc == 0


def test_zero_rows_logs_debug(mod, monkeypatch, caplog):
    """fetchall returns [] → DEBUG message about no active claims for callsign."""
    import logging

    monkeypatch.setenv("CALLSIGN", "orion")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/db")

    conn, _ = _make_fake_conn([])
    with (
        patch("psycopg.connect", return_value=conn),
        caplog.at_level(logging.DEBUG, logger="heartbeat_writer"),
    ):
        rc = mod.main()

    assert rc == 0
    assert any("no active claims" in r.message for r in caplog.records)
