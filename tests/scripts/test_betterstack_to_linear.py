"""Tests for scripts/betterstack_to_linear.py — KEI-26 subprocess wrapper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "betterstack_to_linear.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("bs_to_linear", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bs_to_linear"] = m
    spec.loader.exec_module(m)
    return m


def test_state_path_under_allowed_root(mod, tmp_path, monkeypatch):
    """tmp_path lives under /tmp, an allowed root."""
    state = tmp_path / "bs.json"
    monkeypatch.setenv("AGENCY_OS_BS_INCIDENTS_STATE", str(state))
    assert mod._state_path() == state.resolve()


def test_state_path_traversal_falls_back_to_default(mod, monkeypatch):
    """Env override outside allowed roots falls back to default path."""
    monkeypatch.setenv("AGENCY_OS_BS_INCIDENTS_STATE", "/etc/passwd")
    p = mod._state_path()
    assert "agency-os" in str(p)
    assert "/etc/passwd" not in str(p)


def test_handle_incident_idempotent_skip(mod, monkeypatch, tmp_path):
    state_path = tmp_path / "bs.json"
    monkeypatch.setenv("AGENCY_OS_BS_INCIDENTS_STATE", str(state_path))
    state_path.write_text(json.dumps({"964390352": {"linear_issue_id": "lin-id"}}))

    def _no_graphql(*args, **kwargs):
        raise AssertionError("graphql must not be called for idempotent skip")

    monkeypatch.setattr(mod, "_linear_graphql", _no_graphql)
    monkeypatch.setenv("LINEAR_API_KEY", "test-key")
    rc = mod.handle_incident({"incident_id": "964390352", "monitor_name": "x", "cause": "c", "monitor_url": "u", "monitor_id": "m", "started_at": "t"})
    assert rc == 0


def test_handle_incident_no_api_key_returns_2(mod, monkeypatch, tmp_path):
    """Missing LINEAR_API_KEY → return 2 (operator misconfig signal for systemd logs)."""
    monkeypatch.setenv("AGENCY_OS_BS_INCIDENTS_STATE", str(tmp_path / "bs.json"))
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    rc = mod.handle_incident({"incident_id": "x", "monitor_name": "y", "cause": "z", "monitor_url": "u", "monitor_id": "m", "started_at": "t"})
    assert rc == 2


def test_handle_incident_creates_linear_issue(mod, monkeypatch, tmp_path):
    state_path = tmp_path / "bs.json"
    monkeypatch.setenv("AGENCY_OS_BS_INCIDENTS_STATE", str(state_path))
    monkeypatch.setenv("LINEAR_API_KEY", "test-key")
    monkeypatch.setenv("AGENCY_OS_LINEAR_USER_ELLIOT", "uuid-elliot")

    captured: list[tuple] = []

    def _fake(api_key, query, variables=None):
        captured.append((query, variables))
        if "team(id" in query:
            return {"data": {"team": {"states": {"nodes": [{"id": "state-started", "type": "started"}]}}}}
        if "issueCreate" in query:
            return {"data": {"issueCreate": {"success": True, "issue": {"id": "lin-uuid", "identifier": "KEI-99", "url": "https://linear.app/keiracom/issue/KEI-99/x"}}}}
        return {"data": {"users": {"nodes": []}}}

    monkeypatch.setattr(mod, "_linear_graphql", _fake)
    rc = mod.handle_incident({
        "incident_id": "964390352",
        "monitor_name": "railway-prefect",
        "cause": "DNS lookup failure",
        "monitor_url": "https://prefect.keiracom.app/api/health",
        "monitor_id": "4400119",
        "started_at": "2026-05-12T12:48:08Z",
    })
    assert rc == 0
    # state file should have the mapping
    state = json.loads(state_path.read_text())
    assert "964390352" in state
    assert state["964390352"]["linear_issue_id"] == "lin-uuid"
    assert state["964390352"]["linear_identifier"] == "KEI-99"
    # issueCreate must have been called
    assert any("issueCreate" in c[0] for c in captured)


def test_handle_incident_no_incident_id_skip(mod, monkeypatch):
    rc = mod.handle_incident({"monitor_name": "x"})
    assert rc == 0


def test_main_unknown_op_returns_zero(mod, tmp_path):
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({}))  # empty event
    rc = mod.main(["--event-file", str(event_file)])
    assert rc == 0
