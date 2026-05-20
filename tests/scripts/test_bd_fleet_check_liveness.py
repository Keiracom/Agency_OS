"""Tests for KEI-97 zombie detection in bd_fleet_check — reconcile_liveness().

The DB heartbeat layer downgrades a tmux ALIVE verdict to DEAD when the
fleet_agents row is older than HEARTBEAT_STALE_SEC. Acceptance per KEI-97:
kill an agent → fleet-check reports dead within 90s.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "bd_fleet_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("bd_fleet_check", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bd_fleet_check"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_heartbeat_stale_threshold_is_90s():
    """Dispatch spec: last_heartbeat > 90s → report dead, not active."""
    mod = _load()
    assert mod.HEARTBEAT_STALE_SEC == 90


def test_reconcile_stale_heartbeat_overrides_alive():
    mod = _load()
    final, reason = mod.reconcile_liveness("scout", "ALIVE", {"scout": 120})
    assert final == "DEAD"
    assert reason is not None
    assert "120s" in reason


def test_reconcile_fresh_heartbeat_keeps_alive():
    mod = _load()
    final, reason = mod.reconcile_liveness("scout", "ALIVE", {"scout": 10})
    assert final == "ALIVE"
    assert reason is None


def test_reconcile_at_threshold_keeps_alive():
    """Boundary: age == 90s is NOT stale (must be > 90)."""
    mod = _load()
    final, _ = mod.reconcile_liveness("scout", "ALIVE", {"scout": 90})
    assert final == "ALIVE"


def test_reconcile_one_second_over_threshold_is_dead():
    mod = _load()
    final, reason = mod.reconcile_liveness("scout", "ALIVE", {"scout": 91})
    assert final == "DEAD"
    assert "91s" in reason


def test_reconcile_no_db_row_does_not_downgrade():
    """A callsign missing from fleet_agents leaves tmux verdict untouched."""
    mod = _load()
    final, reason = mod.reconcile_liveness("scout", "ALIVE", {})
    assert final == "ALIVE"
    assert reason is None


def test_reconcile_already_dead_passes_through():
    """If tmux already says DEAD, DB doesn't add noise but doesn't suppress."""
    mod = _load()
    final, reason = mod.reconcile_liveness("scout", "DEAD", {"scout": 5})
    assert final == "DEAD"
    assert reason is None


def test_query_db_liveness_fails_open_without_dsn(monkeypatch):
    """No DATABASE_URL → return empty map (don't crash the CEO check)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    mod = _load()
    assert mod.query_db_liveness() == {}


def test_query_db_liveness_fails_open_on_bad_dsn(monkeypatch):
    """Unreachable DSN → return empty map (fail-open)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:wrong@127.0.0.1:1/nonexistent_db")
    mod = _load()
    assert mod.query_db_liveness() == {}


def test_liveness_sql_targets_fleet_agents_table():
    """SQL must read public.fleet_agents.last_heartbeat per the migration contract."""
    mod = _load()
    assert "public.fleet_agents" in mod._LIVENESS_SQL
    assert "last_heartbeat" in mod._LIVENESS_SQL
