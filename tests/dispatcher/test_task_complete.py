"""Tests for POST /dispatcher/task_complete (result-back-to-Slack hook).

No real Slack call — slack_relay subprocess is monkeypatched.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.dispatcher.main import TaskCompleteRequest, app, dispatcher_task_complete


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def test_task_complete_request_defaults():
    r = TaskCompleteRequest(task_id="t-1", status="done")
    assert r.callsign == "worker"
    assert r.title == ""
    assert r.rc == 0


# ---------------------------------------------------------------------------
# Endpoint — happy path
# ---------------------------------------------------------------------------


def test_task_complete_done_returns_notified(monkeypatch):
    """status='done' → slack_relay called with ✅ prefix, returns notified=True."""
    captured = {}

    def fake_run(cmd, *, capture_output, text, timeout, env):
        captured["cmd"] = cmd
        captured["callsign"] = env.get("CALLSIGN")
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        return result

    monkeypatch.setattr("subprocess.run", fake_run)
    import asyncio

    resp = asyncio.run(
        dispatcher_task_complete(
            TaskCompleteRequest(
                task_id="t-1", callsign="atlas", title="Wire X", status="done", rc=0
            )
        )
    )
    assert resp == {"notified": True}
    assert captured["callsign"] == "elliot"
    assert "✅" in captured["cmd"][-1]
    assert "ATLAS" in captured["cmd"][-1]
    assert "Wire X" in captured["cmd"][-1]
    assert "t-1" in captured["cmd"][-1]


def test_task_complete_blocked_uses_red_icon(monkeypatch):
    """status='blocked' → 🔴 icon in the message."""
    captured = {}

    def fake_run(cmd, **_kw):
        captured["msg"] = cmd[-1]
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        return result

    monkeypatch.setattr("subprocess.run", fake_run)
    import asyncio

    asyncio.run(
        dispatcher_task_complete(
            TaskCompleteRequest(task_id="t-2", callsign="orion", status="blocked", rc=1)
        )
    )
    assert "🔴" in captured["msg"]
    assert "blocked" in captured["msg"]


# ---------------------------------------------------------------------------
# Fail-open: Slack errors must never propagate
# ---------------------------------------------------------------------------


def test_task_complete_slack_relay_nonzero_returns_not_notified(monkeypatch):
    """slack_relay rc != 0 → notified=False, no exception raised."""

    def fake_run(cmd, **_kw):
        result = MagicMock()
        result.returncode = 1
        result.stderr = "SLACK_BOT_TOKEN not set"
        return result

    monkeypatch.setattr("subprocess.run", fake_run)
    import asyncio

    resp = asyncio.run(dispatcher_task_complete(TaskCompleteRequest(task_id="t-3", status="done")))
    assert resp["notified"] is False
    assert "rc=1" in resp["reason"]


def test_task_complete_exception_returns_not_notified(monkeypatch):
    """subprocess.run raises → notified=False, no exception propagated."""
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: (_ for _ in ()).throw(OSError("boom")))
    import asyncio

    resp = asyncio.run(dispatcher_task_complete(TaskCompleteRequest(task_id="t-4", status="done")))
    assert resp["notified"] is False
    assert resp["reason"] == "exception"
