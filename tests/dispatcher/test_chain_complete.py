"""Tests for POST /dispatcher/chain_complete (V1 chain final-result hook, Agency_OS-zqni).

No real Slack call — slack_relay subprocess and cost lookup are monkeypatched.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.dispatcher import main as dmain


@pytest.fixture()
def client():
    return TestClient(dmain.app, raise_server_exceptions=True)


def _stub_relay(monkeypatch, *, rc: int = 0, stderr: str = ""):
    """Replace subprocess.run with a recorder + a configurable rc."""
    captured: dict = {}

    def fake_run(cmd, *, capture_output, text, timeout, env):
        captured["cmd"] = cmd
        captured["msg"] = cmd[-1]
        captured["callsign"] = env.get("CALLSIGN")
        result = MagicMock()
        result.returncode = rc
        result.stderr = stderr
        return result

    monkeypatch.setattr("subprocess.run", fake_run)
    return captured


# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------


def test_chain_complete_request_defaults():
    r = dmain.ChainCompleteRequest(task_id="t-1", chain_id="c-1")
    assert r.brief == ""
    assert r.steps == []


# ---------------------------------------------------------------------------
# Endpoint — happy path with cost
# ---------------------------------------------------------------------------


def test_chain_complete_with_cost_posts_multiline_to_ceo(client, monkeypatch):
    """Happy path: posts Scout's multi-line markdown with cost line, notified=True."""
    captured = _stub_relay(monkeypatch)
    monkeypatch.setattr(dmain, "_lookup_chain_cost_aud", lambda _tid: 0.1234)

    resp = client.post(
        "/dispatcher/chain_complete",
        json={
            "task_id": "t-zq",
            "chain_id": "chain-abcdef12",
            "brief": "wire X to Y",
            "steps": ["aiden_plan", "max_challenge", "nova_build", "orion_spec", "atlas_safety"],
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"notified": True}
    msg = captured["msg"]
    assert "✅ Chain complete — t-zq" in msg
    assert "**Brief:** wire X to Y" in msg
    assert "**Steps:** aiden_plan → max_challenge → nova_build → orion_spec → atlas_safety" in msg
    assert "**Cost:** A$0.1234" in msg
    assert "**chain_id:** chain-abcdef12" in msg
    assert captured["callsign"] == "elliot"
    assert "-c" in captured["cmd"] and "ceo" in captured["cmd"]


def test_chain_complete_omits_cost_line_when_unavailable(client, monkeypatch):
    """Cost lookup returns None → no 'Cost:' line in the message; still notified=True."""
    captured = _stub_relay(monkeypatch)
    monkeypatch.setattr(dmain, "_lookup_chain_cost_aud", lambda _tid: None)

    resp = client.post(
        "/dispatcher/chain_complete",
        json={"task_id": "t-nocost", "chain_id": "c-nc", "brief": "no cost"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"notified": True}
    msg = captured["msg"]
    assert "**Cost:**" not in msg
    assert "**chain_id:** c-nc" in msg


# ---------------------------------------------------------------------------
# Endpoint — fail-open
# ---------------------------------------------------------------------------


def test_chain_complete_fail_open_on_slack_relay_nonzero(client, monkeypatch):
    """slack_relay rc != 0 → notified=False but endpoint still returns 200."""
    _stub_relay(monkeypatch, rc=2, stderr="SLACK_ACCESS_DENIED")
    monkeypatch.setattr(dmain, "_lookup_chain_cost_aud", lambda _tid: None)

    resp = client.post(
        "/dispatcher/chain_complete",
        json={"task_id": "t-fail", "chain_id": "c-f"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["notified"] is False
    assert "slack_relay rc=2" in body["reason"]


def test_lookup_chain_cost_aud_returns_none_when_no_matching_entries(monkeypatch):
    """Cost helper returns None when there are no attribution entries for the task_id."""
    monkeypatch.setattr(
        "src.keiracom_system.attribution.logger.load_attribution_last_24h",
        lambda **_kw: [],
    )
    assert dmain._lookup_chain_cost_aud("t-empty") is None


def test_lookup_chain_cost_aud_sums_matching_and_converts_usd_to_aud(monkeypatch):
    """Cost helper sums cost_usd across source_id matches and multiplies by 1.55."""
    monkeypatch.setattr(
        "src.keiracom_system.attribution.logger.load_attribution_last_24h",
        lambda **_kw: [
            {"source_id": "t-1", "cost_usd": 0.10},
            {"source_id": "t-1", "cost_usd": 0.20},
            {"source_id": "t-other", "cost_usd": 9.99},  # ignored
        ],
    )
    out = dmain._lookup_chain_cost_aud("t-1")
    assert out is not None
    assert abs(out - 0.30 * 1.55) < 1e-9
