"""Unit tests for KEI-183 additions to scripts/fleet_supervisor.py.

Covers:
  - v1 routing (default): claim_next_task uses no persona filter
  - v2 routing: claim_next_task uses persona = $callsign OR persona IS NULL
  - Mixed mode: some agents v1, some v2 — each gets correct query
  - NATS publish called on v2 idle (KEI-205: Valkey→NATS messaging redirect)
  - NATS publish NOT called on v1 idle
  - _is_v2 / _agent_routing helpers
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import fleet_supervisor as fs  # noqa: E402

AGENT_ELLIOT = {"callsign": "elliot", "tmux": "elliottbot:0", "service": "elliot-agent"}
AGENT_AIDEN = {"callsign": "aiden", "tmux": "aiden:0", "service": "aiden-agent"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn():
    return MagicMock()


# ---------------------------------------------------------------------------
# Test 1: _agent_routing returns v1 by default
# ---------------------------------------------------------------------------


def test_agent_routing_defaults_v1(monkeypatch):
    monkeypatch.delenv("AGENT_ROUTING_ELLIOT", raising=False)
    assert fs._agent_routing("elliot") == "v1"


def test_agent_routing_returns_v2_when_set(monkeypatch):
    monkeypatch.setenv("AGENT_ROUTING_ELLIOT", "v2")
    assert fs._agent_routing("elliot") == "v2"


# ---------------------------------------------------------------------------
# Test 2: _is_v2 requires BOTH global flag AND per-agent routing
# ---------------------------------------------------------------------------


def test_is_v2_false_when_global_flag_off(monkeypatch):
    monkeypatch.setattr(fs, "SUPERVISOR_V2_ENABLED", False)
    monkeypatch.setenv("AGENT_ROUTING_ELLIOT", "v2")
    assert fs._is_v2("elliot") is False


def test_is_v2_false_when_agent_routing_v1(monkeypatch):
    monkeypatch.setattr(fs, "SUPERVISOR_V2_ENABLED", True)
    monkeypatch.setenv("AGENT_ROUTING_ELLIOT", "v1")
    assert fs._is_v2("elliot") is False


def test_is_v2_true_when_both_set(monkeypatch):
    monkeypatch.setattr(fs, "SUPERVISOR_V2_ENABLED", True)
    monkeypatch.setenv("AGENT_ROUTING_ELLIOT", "v2")
    assert fs._is_v2("elliot") is True


# ---------------------------------------------------------------------------
# Test 3: v1 claim_next_task uses no persona filter in SQL
# ---------------------------------------------------------------------------


def test_claim_next_task_v1_no_persona_filter(monkeypatch):
    """v1 path: SQL must NOT include persona filter.

    Note: merged claim_next_task now uses fetchall (dep-blocked scan via
    KEI-204); mock returns a single-row list.
    """
    monkeypatch.setattr(fs, "_is_v2", lambda callsign: False)
    monkeypatch.setattr(fs, "fetch_open_pr_kei_ids", lambda: set())

    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    # fetchall returns list of (id, title, description) tuples
    cursor.fetchall.return_value = [("KEI-100", "Some task", "")]

    fs.claim_next_task(conn, "elliot", 99)

    executed_sql = cursor.execute.call_args_list[0][0][0]
    assert "persona" not in executed_sql, "v1 path must not include persona filter"


# ---------------------------------------------------------------------------
# Test 4: v2 claim_next_task includes persona filter
# ---------------------------------------------------------------------------


def test_claim_next_task_v2_includes_persona_filter(monkeypatch):
    """v2 path: SQL must include 'persona = %s OR persona IS NULL'.

    KEI-183 + KEI-199/204 merged: fetchall + dep-blocked scan + persona lane.
    """
    monkeypatch.setattr(fs, "_is_v2", lambda callsign: True)
    monkeypatch.setattr(fs, "fetch_open_pr_kei_ids", lambda: set())

    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    # fetchall returns list of (id, title, description) tuples
    cursor.fetchall.return_value = [("KEI-200", "Lane task", "")]

    fs.claim_next_task(conn, "elliot", 99)

    executed_sql = cursor.execute.call_args_list[0][0][0]
    params = cursor.execute.call_args_list[0][0][1]
    assert "persona" in executed_sql, "v2 path must include persona filter"
    assert "persona IS NULL" in executed_sql
    # callsign is a param in the v2 query
    assert "elliot" in params


# ---------------------------------------------------------------------------
# Test 5: v2 idle → NATS publish called (KEI-205: Valkey→NATS redirect)
# ---------------------------------------------------------------------------


def test_idle_v2_publishes_nats_ready(monkeypatch):
    """_handle_idle_no_queue with _is_v2=True must call _nats_publish_state.

    KEI-205: messaging redirected from Redis pub/sub to NATS streams.
    Subject: keiracom.agent.status.<callsign>
    """
    conn = MagicMock()
    nats_mock = MagicMock()

    monkeypatch.setattr(fs, "get_phase_max", lambda c: 99)
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: None)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: None)
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    monkeypatch.setattr(fs, "inject_task", MagicMock())
    monkeypatch.setattr(fs, "_is_v2", lambda callsign: True)
    monkeypatch.setattr(fs, "_nats_publish_state", nats_mock)

    fs.process_agent(AGENT_ELLIOT, conn, [], 99)

    nats_mock.assert_called_once_with("elliot", "ready")


# ---------------------------------------------------------------------------
# Test 6: v1 idle → NATS publish NOT called
# ---------------------------------------------------------------------------


def test_idle_v1_does_not_publish_nats(monkeypatch):
    """_handle_idle_no_queue with _is_v2=False must NOT call _nats_publish_state."""
    conn = MagicMock()
    nats_mock = MagicMock()

    monkeypatch.setattr(fs, "get_phase_max", lambda c: 99)
    monkeypatch.setattr(fs, "get_active_claim", lambda c, cs: None)
    monkeypatch.setattr(fs, "claim_next_task", lambda c, cs, ph: None)
    monkeypatch.setattr(fs, "tmux_has_session", lambda s: True)
    monkeypatch.setattr(fs, "inject_task", MagicMock())
    monkeypatch.setattr(fs, "_is_v2", lambda callsign: False)
    monkeypatch.setattr(fs, "_nats_publish_state", nats_mock)

    fs.process_agent(AGENT_AIDEN, conn, [], 99)

    nats_mock.assert_not_called()
