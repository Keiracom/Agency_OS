"""Tests for src/api/webhooks/linear.py — PR-1 Linear→Beads inbound sync.

Mocks the subprocess dispatch + HTTP request. Verifies:
  - HMAC signature verify rejects bad / missing / wrong-secret signatures
  - Issue.create event → 'create' op dispatched with correct shape
  - Issue.update to completed → 'status' op with bd_status='closed'
  - Issue.update to started → 'status' op with bd_status='active'
  - Non-Issue payloads ignored (status='ignored')
  - Malformed JSON returns 200 with status='malformed' (fail-open)
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
    spec = importlib.util.spec_from_file_location("linear_webhook", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["linear_webhook"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def client(mod, monkeypatch):
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", TEST_SECRET)
    captured: list[dict] = []
    monkeypatch.setattr(mod, "_dispatch_to_bd", lambda event: captured.append(event))
    # KEI-22: stub the tasks-table dispatch so unit tests don't reach Supabase.
    monkeypatch.setattr(mod, "_dispatch_to_tasks", lambda event: None)
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


# Signature verify ────────────────────────────────────────────────────────────


def test_missing_signature_returns_401(client):
    c, _ = client
    resp = c.post("/api/webhooks/linear", json={"action": "create", "type": "Issue"})
    assert resp.status_code == 401


def test_wrong_signature_returns_401(client):
    c, _ = client
    raw = json.dumps({"action": "create", "type": "Issue"}).encode()
    resp = c.post(
        "/api/webhooks/linear",
        content=raw,
        headers={"linear-signature": "0" * 64, "content-type": "application/json"},
    )
    assert resp.status_code == 401


def test_correct_signature_passes_through(client):
    c, _captured = client
    resp = _signed_request(
        c,
        {
            "action": "create",
            "type": "Issue",
            "data": {
                "identifier": "KEI-99",
                "title": "x",
                "priority": 2,
                "url": "https://linear.app/x",
            },
        },
    )
    assert resp.status_code == 200


# Event normalisation ─────────────────────────────────────────────────────────


def test_issue_create_dispatches_create_op(client):
    c, captured = client
    resp = _signed_request(
        c,
        {
            "action": "create",
            "type": "Issue",
            "data": {
                "identifier": "KEI-77",
                "title": "Build sync receiver",
                "priority": 1,  # urgent → bd 0
                "url": "https://linear.app/keiracom/issue/KEI-77/build-sync",
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json()["op"] == "create"
    assert len(captured) == 1
    ev = captured[0]
    assert ev["op"] == "create"
    assert ev["identifier"] == "KEI-77"
    assert ev["priority"] == 0  # Linear urgent maps to bd critical


def test_issue_update_completed_dispatches_status_closed(client):
    c, captured = client
    resp = _signed_request(
        c,
        {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "KEI-77",
                "state": {"name": "Done", "type": "completed"},
                "url": "https://linear.app/keiracom/issue/KEI-77/done",
            },
        },
    )
    assert resp.status_code == 200
    assert captured[-1]["op"] == "status"
    assert captured[-1]["bd_status"] == "closed"


def test_issue_update_started_dispatches_status_active(client):
    c, captured = client
    resp = _signed_request(
        c,
        {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "KEI-77",
                "state": {"name": "In Progress", "type": "started"},
                "url": "https://linear.app/keiracom/issue/KEI-77/in-progress",
            },
        },
    )
    assert resp.status_code == 200
    assert captured[-1]["op"] == "status"
    assert captured[-1]["bd_status"] == "active"


def test_non_issue_payload_ignored(client):
    c, captured = client
    resp = _signed_request(
        c,
        {"action": "create", "type": "Comment", "data": {"id": "comment-1"}},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert captured == []


def test_unhandled_state_ignored(client):
    c, captured = client
    resp = _signed_request(
        c,
        {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "KEI-77",
                "state": {"name": "Backlog", "type": "backlog"},
                "url": "https://linear.app/x",
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert captured == []


def test_malformed_json_returns_200_malformed(mod, monkeypatch):
    """Fail-open: malformed JSON returns 200 (no Linear retry storm)."""
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setattr(mod, "_dispatch_to_bd", lambda event: None)
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)
    raw = b"{not-json"
    sig = hmac.new(TEST_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    resp = client.post(
        "/api/webhooks/linear",
        content=raw,
        headers={"linear-signature": sig, "content-type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "malformed"
