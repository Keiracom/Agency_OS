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


# ---------------------------------------------------------------------------
# Tests 7-10: KEI-183 follow-up (Dave 2026-05-18) — structural dep enforcement
# ---------------------------------------------------------------------------


def test_kei183_followup_deps_clause_present_in_all_query_paths():
    """The dependencies-enforcement clause must inject into every path: v1 +
    v2, with and without open-PR filter. Structural-impossibility guarantee.
    """
    for v2 in (False, True):
        for open_prs in (set(), {"KEI-999"}):
            sql, _params = fs._build_task_query(v2, open_prs, "elliot", 99)
            assert "dependencies IS NULL" in sql, (
                f"v2={v2} open_prs={open_prs}: dep-NULL guard missing"
            )
            assert "cardinality(dependencies) = 0" in sql, (
                f"v2={v2} open_prs={open_prs}: empty-array guard missing"
            )
            assert "FROM unnest(dependencies)" in sql, (
                f"v2={v2} open_prs={open_prs}: dep-row sub-query missing"
            )
            assert "t_dep.status != 'done'" in sql, (
                f"v2={v2} open_prs={open_prs}: status-not-done predicate missing"
            )


def test_kei183_followup_order_by_phase_then_priority():
    """ORDER BY must put phase ahead of priority — Dave directive 2026-05-18.
    Lower-phase work drains first; priority sort breaks ties within a phase.
    """
    sql, _params = fs._build_task_query(False, set(), "elliot", 99)
    phase_idx = sql.find("phase ASC")
    priority_idx = sql.find("priority ASC")
    assert phase_idx != -1, "ORDER BY phase ASC missing"
    assert priority_idx != -1, "ORDER BY priority ASC missing"
    assert phase_idx < priority_idx, "phase must precede priority in ORDER BY (Dave 2026-05-18)"


def test_kei183_followup_deps_clause_does_not_double_inject():
    """The dep clause appears exactly once per query (avoid double-AND
    rewrite if _build_task_query is called twice).
    """
    sql, _params = fs._build_task_query(True, {"KEI-999"}, "elliot", 99)
    assert sql.count("FROM unnest(dependencies)") == 1


def test_kei183_followup_deps_clause_uses_qualified_join():
    """The dep-row join must reference public.tasks explicitly so the SQL
    works regardless of search_path (defensive against runtime schema drift).
    """
    sql, _params = fs._build_task_query(False, set(), "elliot", 99)
    assert "public.tasks t_dep" in sql, "dep join must be schema-qualified"
