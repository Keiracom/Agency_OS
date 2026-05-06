"""tests/api/test_email_routes.py — unit tests for Task #20 email backend.

Covers contract behaviour with Resend send + DB layer mocked. A real-network
smoke test lives in `scripts/smoke_email_backend.py` (committed alongside).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import email as email_route
from src.integrations import resend_client


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def mock_db(monkeypatch):
    """Replace _connect() with a mock that records execute() calls and
    returns a fixed row from fetchone()."""
    cur = MagicMock()
    cur.fetchone.return_value = (
        "msg_test_123", "to@x.com", "from@x.com", "subj",
        "delivered", '[{"type":"email.delivered","ts":"2026-05-05T00:00:00+00:00"}]',
        None, None,
    )
    cur.execute = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.commit = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    monkeypatch.setattr(email_route, "_connect", lambda: conn)
    return cur


def test_send_returns_message_id(client, mock_db, monkeypatch):
    monkeypatch.setattr(
        email_route, "send_email",
        lambda **kw: {"id": "msg_abc_456"},
    )
    resp = client.post(
        "/api/email/send",
        json={
            "to": "dest@example.com",
            "subject": "Hello",
            "body_text": "World",
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["message_id"] == "msg_abc_456"
    assert body["status"] == "queued"
    # DB INSERT was attempted with the same message_id.
    args = mock_db.execute.call_args[0]
    assert "INSERT INTO keiracom_admin.email_events" in args[0]
    assert "msg_abc_456" in args[1]


def test_send_rejects_no_body(client):
    resp = client.post(
        "/api/email/send",
        json={"to": "x@y.com", "subject": "subj"},
    )
    assert resp.status_code == 422


def test_send_resend_failure_returns_502(client, monkeypatch):
    def _boom(**kw):
        raise resend_client.ResendError("upstream down")
    monkeypatch.setattr(email_route, "send_email", _boom)
    resp = client.post(
        "/api/email/send",
        json={"to": "x@y.com", "subject": "s", "body_text": "t"},
    )
    assert resp.status_code == 502
    assert "upstream down" in resp.json()["detail"]


def test_send_db_failure_returns_202_with_warning(client, monkeypatch):
    """When Resend send succeeds but DB INSERT fails, return 202 with warning
    instead of 500 — avoids duplicate-send on caller retry."""
    monkeypatch.setattr(
        email_route, "send_email",
        lambda **kw: {"id": "msg_db_fail"},
    )
    monkeypatch.setattr(
        email_route, "_connect",
        lambda: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    resp = client.post(
        "/api/email/send",
        json={"to": "x@y.com", "subject": "s", "body_text": "t"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["message_id"] == "msg_db_fail"
    assert body["warning"] == "tracking_insert_failed"
    assert "DB insert failed" in body["detail"]


def test_status_returns_row(client, mock_db):
    resp = client.get("/api/email/status/msg_test_123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["message_id"] == "msg_test_123"
    assert body["status"] == "delivered"
    assert isinstance(body["events"], list)
    assert body["events"][0]["type"] == "email.delivered"


def test_status_404_when_missing(client, monkeypatch):
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.execute = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    monkeypatch.setattr(email_route, "_connect", lambda: conn)

    resp = client.get("/api/email/status/missing")
    assert resp.status_code == 404


def test_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", "shh")
    body = b'{"type":"email.delivered","data":{"email_id":"x"}}'
    resp = client.post(
        "/api/email/webhook",
        content=body,
        headers={"svix-signature": "v1,deadbeef"},
    )
    assert resp.status_code == 401


def test_webhook_accepts_valid_signature_and_updates_status(
    client, mock_db, monkeypatch,
):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", "shh")
    body = json.dumps({
        "type": "email.delivered",
        "data": {"email_id": "msg_test_123"},
    }).encode("utf-8")
    digest = hmac.new(b"shh", body, hashlib.sha256).digest()
    sig_b64 = base64.b64encode(digest).decode("ascii")
    resp = client.post(
        "/api/email/webhook",
        content=body,
        headers={
            "svix-signature": f"v1,{sig_b64}",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 200, resp.text
    body_json = resp.json()
    assert body_json["ok"] is True
    assert body_json["applied_status"] == "delivered"
    # DB UPDATE was attempted.
    args = mock_db.execute.call_args[0]
    assert "UPDATE keiracom_admin.email_events" in args[0]


def test_webhook_secret_unset_rejects_all(client, monkeypatch):
    monkeypatch.delenv("RESEND_WEBHOOK_SECRET", raising=False)
    body = b'{"type":"email.delivered","data":{"email_id":"x"}}'
    sig = "v1," + hmac.new(b"any", body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/api/email/webhook",
        content=body,
        headers={"svix-signature": sig},
    )
    assert resp.status_code == 401


def test_webhook_unknown_event_type_keeps_status(client, mock_db, monkeypatch):
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", "shh")
    body = json.dumps({
        "type": "email.something_new",
        "data": {"email_id": "msg_test_123"},
    }).encode("utf-8")
    digest = hmac.new(b"shh", body, hashlib.sha256).digest()
    sig_b64 = base64.b64encode(digest).decode("ascii")
    resp = client.post(
        "/api/email/webhook",
        content=body,
        headers={"svix-signature": f"v1,{sig_b64}"},
    )
    assert resp.status_code == 200
    assert resp.json()["applied_status"] is None


def test_webhook_accepts_multiple_space_separated_signatures(
    client, mock_db, monkeypatch,
):
    """Svix delivers multiple v1,<sig> tokens space-separated when keys
    rotate. At least one matching token should pass."""
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", "current_secret")
    body = json.dumps({
        "type": "email.delivered",
        "data": {"email_id": "msg_test_123"},
    }).encode("utf-8")
    good = base64.b64encode(
        hmac.new(b"current_secret", body, hashlib.sha256).digest()
    ).decode("ascii")
    bad = base64.b64encode(
        hmac.new(b"old_rotated_secret", body, hashlib.sha256).digest()
    ).decode("ascii")
    resp = client.post(
        "/api/email/webhook",
        content=body,
        headers={"svix-signature": f"v1,{bad} v1,{good}"},
    )
    assert resp.status_code == 200, resp.text


def test_webhook_rejects_hex_signature(client, monkeypatch):
    """Hex digests must NOT be accepted — Svix is base64-only. Guards
    against accidental regression to the old hex-accepting behaviour."""
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", "shh")
    body = json.dumps({
        "type": "email.delivered",
        "data": {"email_id": "msg_test_123"},
    }).encode("utf-8")
    sig_hex = hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/api/email/webhook",
        content=body,
        headers={"svix-signature": f"v1,{sig_hex}"},
    )
    assert resp.status_code == 401
