"""KEI-20 — receiver-side severity routing end-to-end.

Synthesises POST /api/webhooks/betterstack with priority=P0 and asserts the
receiver routes to #ceo. Same shape for P1 → #execution and P2 → #alerts.
Both downstream side-effects (Linear dispatch + Slack POST) are stubbed so
the test runs offline and asserts the receiver makes the right routing call.

Dispatch acceptance: "synthetic P0 alert lands in #ceo, P1 in #execution".
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.webhooks.betterstack_severity_router import (
    CHANNEL_ALERTS,
    CHANNEL_CEO,
    CHANNEL_EXECUTION,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "src" / "api" / "webhooks" / "betterstack.py"
SECRET = "test-bs-secret"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("bs_webhook_kei20", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bs_webhook_kei20"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def client(mod, monkeypatch):
    monkeypatch.setenv("BETTERSTACK_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(mod, "_dispatch_to_linear", lambda event: None)
    posted: list[tuple[str, str]] = []
    monkeypatch.setattr(mod, "_post_to_slack", lambda ch, text: posted.append((ch, text)))
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app), posted


def _incident_payload(priority: str | None) -> dict:
    attrs: dict = {
        "name": f"Synthetic {priority or 'unspecified'} incident",
        "cause": "synthetic test",
        "status": "started",
        "started_at": "2026-05-18T11:00:00Z",
        "metadata": {"Monitor URL": "https://example.test"},
    }
    if priority is not None:
        attrs["priority"] = priority
    return {
        "data": {
            "id": "incident-synthetic-1",
            "attributes": attrs,
            "relationships": {"monitor": {"data": {"id": "monitor-1"}}},
        }
    }


def _post(c: TestClient, payload: dict):
    return c.post(
        "/api/webhooks/betterstack",
        json=payload,
        headers={"x-webhook-secret": SECRET},
    )


# ---------------------------------------------------------------------------
# Synthetic P0 / P1 / P2 routing
# ---------------------------------------------------------------------------


def test_synthetic_p0_lands_in_ceo(client) -> None:
    c, posted = client
    resp = _post(c, _incident_payload("P0"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["severity"] == "P0"
    assert body["channel"] == CHANNEL_CEO
    assert len(posted) == 1, "Slack post should fire exactly once per webhook"
    channel, text = posted[0]
    assert channel == CHANNEL_CEO
    assert "[P0]" in text
    assert "Synthetic P0 incident" in text


def test_synthetic_p1_lands_in_execution(client) -> None:
    c, posted = client
    resp = _post(c, _incident_payload("P1"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["severity"] == "P1"
    assert body["channel"] == CHANNEL_EXECUTION
    assert posted[-1][0] == CHANNEL_EXECUTION
    assert "[P1]" in posted[-1][1]


def test_synthetic_p2_lands_in_alerts(client) -> None:
    c, posted = client
    resp = _post(c, _incident_payload("P2"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["severity"] == "OTHER"
    assert body["channel"] == CHANNEL_ALERTS
    assert posted[-1][0] == CHANNEL_ALERTS


def test_synthetic_no_severity_lands_in_alerts(client) -> None:
    c, posted = client
    resp = _post(c, _incident_payload(priority=None))
    assert resp.status_code == 200
    body = resp.json()
    # Missing severity must not silently drop — route to #alerts so an
    # operator notices a payload-format change.
    assert body["channel"] == CHANNEL_ALERTS


def test_synthetic_critical_synonym_routes_to_ceo(client) -> None:
    # BS sometimes emits human-readable severity tokens. The receiver must
    # treat "critical" as P0 → #ceo.
    c, posted = client
    resp = _post(c, _incident_payload("critical"))
    assert resp.json()["channel"] == CHANNEL_CEO


def test_ignored_status_does_not_post(client) -> None:
    # Non-actionable statuses (resolved, acknowledged) skip both dispatch
    # paths. The current receiver short-circuits before Linear and Slack —
    # KEI-20 should not regress that.
    c, posted = client
    payload = _incident_payload("P0")
    payload["data"]["attributes"]["status"] = "resolved"
    resp = _post(c, payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert posted == [], "resolved events must not fire a Slack post"
