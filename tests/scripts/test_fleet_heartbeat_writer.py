"""Tests for KEI-97 fleet_heartbeat_writer.py — per-agent-process heartbeat.

Covers env-var validation, DSN normalisation, fail-open semantics. The actual
UPSERT path is verified by the bd_fleet_check tests (which exercise the read
side against the same table contract).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "fleet_heartbeat_writer.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("fleet_heartbeat_writer", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_heartbeat_writer"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_module_loads():
    _load_module()


def test_missing_callsign_returns_2(monkeypatch):
    monkeypatch.delenv("CALLSIGN", raising=False)
    mod = _load_module()
    assert mod.main() == 2


def test_missing_dsn_fails_open(monkeypatch):
    """No DATABASE_URL → exit 0 (fail-open so timer keeps firing)."""
    monkeypatch.setenv("CALLSIGN", "scout")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    mod = _load_module()
    assert mod.main() == 0


def test_resolve_dsn_strips_asyncpg_prefix(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    mod = _load_module()
    assert mod._resolve_dsn() == "postgresql://u:p@h/db"


def test_resolve_dsn_passes_plain_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    mod = _load_module()
    assert mod._resolve_dsn() == "postgresql://u:p@h/db"


def test_upsert_sql_is_idempotent_and_returns_row():
    """The UPSERT must use ON CONFLICT and RETURN the timestamp for logging."""
    mod = _load_module()
    sql = mod._UPSERT_SQL
    assert "INSERT INTO public.fleet_agents" in sql
    assert "ON CONFLICT (callsign) DO UPDATE" in sql
    assert "last_heartbeat = EXCLUDED.last_heartbeat" in sql
    assert "RETURNING callsign, last_heartbeat" in sql


def test_script_runs_with_missing_dsn_exit_0():
    """Smoke: invoke as a subprocess with no DSN — must exit 0 (fail-open)."""
    env = {"CALLSIGN": "scout", "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0


def test_script_runs_without_callsign_exit_2():
    """Smoke: invoke as a subprocess without CALLSIGN — must exit 2."""
    env = {"PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert "CALLSIGN" in result.stderr
