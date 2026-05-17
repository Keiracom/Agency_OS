"""KEI-91 Gate 4 — heartbeat wiring tests for the Linear webhook handler.

This is the LOAD-BEARING case the Gate was designed to catch: the handler
keeps returning HTTP responses (alive) but the HMAC-verify silently fails,
so no real work happens. The outcome counter — incremented ONLY on HMAC
success — must stay at 0 in that case, while the alive-but-broken status
remains visible to the monitor.

Tests verify:
  - HMAC fail: counter does NOT increment (outcome_increment=0) AND status=error
  - HMAC pass + valid event: counter increments AND status=ok
  - HMAC pass + malformed json: counter still increments (work happened)
    but status=degraded so the asymmetry is visible
  - HMAC pass + ignored event: counter increments AND status=ok (event-type
    filter is meaningful work)
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "src" / "api" / "webhooks" / "linear.py"
TEST_SECRET = "test-webhook-secret"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("linear_webhook_hb", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["linear_webhook_hb"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def client_with_hb(mod, monkeypatch):
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setattr(mod, "_dispatch_to_bd", lambda event: None)
    monkeypatch.setattr(mod, "_dispatch_to_tasks", lambda event: None)
    monkeypatch.setattr(mod, "_dispatch_to_indexing_queue", lambda source, payload: None)

    # Capture every heartbeat tick. The webhook's wired callable is the
    # symbol `_heartbeat_tick` on the module — replace it with a list-appender.
    captured: list[dict] = []

    def _capture_tick(
        service_name, *, outcome_increment=1, status="ok", error_message=None, period_seconds=300
    ):
        captured.append(
            {
                "service_name": service_name,
                "outcome_increment": outcome_increment,
                "status": status,
                "error_message": error_message,
                "period_seconds": period_seconds,
            }
        )

    monkeypatch.setattr(mod, "_heartbeat_tick", _capture_tick)

    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app), captured


def _signed_request(client, body: dict, secret: str = TEST_SECRET) -> object:
    raw = json.dumps(body).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post(
        "/api/webhooks/linear",
        content=raw,
        headers={"linear-signature": sig, "content-type": "application/json"},
    )


def test_hmac_fail_emits_heartbeat_with_outcome_zero_status_error(client_with_hb):
    """LOAD-BEARING — today's incident pattern. HMAC silently fails, the
    handler keeps responding, but the outcome counter stays 0 and status
    self-reports error.
    """
    c, captured = client_with_hb
    raw = json.dumps({"action": "create", "type": "Issue"}).encode()
    resp = c.post(
        "/api/webhooks/linear",
        content=raw,
        headers={"linear-signature": "0" * 64, "content-type": "application/json"},
    )
    assert resp.status_code == 401
    assert len(captured) == 1
    tick = captured[0]
    assert tick["service_name"] == "linear-webhook-handler"
    assert tick["outcome_increment"] == 0
    assert tick["status"] == "error"
    assert "HMAC" in (tick["error_message"] or "")


def test_hmac_pass_valid_event_increments_counter_status_ok(client_with_hb):
    c, captured = client_with_hb
    resp = _signed_request(
        c,
        {
            "action": "create",
            "type": "Issue",
            "data": {
                "identifier": "KEI-200",
                "title": "test",
                "priority": 2,
                "url": "https://linear.app/x",
            },
        },
    )
    assert resp.status_code == 200
    assert len(captured) == 1
    tick = captured[0]
    assert tick["service_name"] == "linear-webhook-handler"
    assert tick["outcome_increment"] == 1
    assert tick["status"] == "ok"


def test_hmac_pass_malformed_json_increments_but_status_degraded(client_with_hb):
    c, captured = client_with_hb
    raw = b"not-valid-json{{{"
    sig = hmac.new(TEST_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    resp = c.post(
        "/api/webhooks/linear",
        content=raw,
        headers={"linear-signature": sig, "content-type": "application/json"},
    )
    assert resp.status_code == 200
    assert len(captured) == 1
    tick = captured[0]
    assert tick["service_name"] == "linear-webhook-handler"
    assert tick["outcome_increment"] == 1
    assert tick["status"] == "degraded"


def test_hmac_pass_ignored_event_still_increments(client_with_hb):
    """Non-Issue payloads (e.g. Comment) are dropped by the event normaliser
    but they ARE meaningful work — HMAC was verified, type was inspected.
    Counter still increments; status stays ok.
    """
    c, captured = client_with_hb
    resp = _signed_request(
        c,
        {"action": "create", "type": "Comment", "data": {"id": "x"}},
    )
    assert resp.status_code == 200
    assert len(captured) == 1
    tick = captured[0]
    assert tick["outcome_increment"] == 1
    assert tick["status"] == "ok"
