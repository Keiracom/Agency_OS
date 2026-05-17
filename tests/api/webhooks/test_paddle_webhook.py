"""Tests for src/api/webhooks/paddle.py — KEI-150 Paddle MoR webhook scaffold.

Covers:
  - HMAC verify passes with correct secret + well-formed Paddle-Signature
  - HMAC verify fails with wrong secret → 401
  - HMAC verify fails with missing header → 401
  - HMAC verify fails with malformed header (no ts, no h1) → 401
  - Malformed JSON payload → 200 fail-open with status='malformed'
  - Valid payload with known event_type → 200 + event_type echoed
  - Valid payload missing event_type → 200 + event_type='unknown'
  - verify_paddle_signature unit: correct → True
  - verify_paddle_signature unit: wrong secret → False
  - verify_paddle_signature unit: empty secret → False
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "src" / "api" / "webhooks" / "paddle.py"
TEST_SECRET = "test-paddle-secret"

# Use a very large tolerance so tests don't race against the clock.
_LARGE_TOLERANCE = str(10**9)


def _load_module():
    spec = importlib.util.spec_from_file_location("paddle_webhook", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["paddle_webhook"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load_module()


def _make_sig(secret: str, body: bytes, ts: int | None = None) -> str:
    """Build a valid Paddle-Signature header value for the given body."""
    ts_str = str(ts if ts is not None else int(time.time()))
    signed = f"{ts_str}:{body.decode('utf-8', errors='replace')}"
    h1 = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts_str};h1={h1}"


@pytest.fixture
def client(mod, monkeypatch):
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setenv("PADDLE_TS_TOLERANCE", _LARGE_TOLERANCE)
    # Reload tolerance constant so monkeypatch takes effect in the handler.
    mod._TS_TOLERANCE_SECONDS = int(_LARGE_TOLERANCE)
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Integration tests via TestClient
# ---------------------------------------------------------------------------


def _post(client: TestClient, body: bytes, sig: str):  # noqa: ANN201
    return client.post(
        "/api/webhooks/paddle",
        content=body,
        headers={"paddle-signature": sig, "content-type": "application/json"},
    )


def test_valid_signature_returns_200(client, mod, monkeypatch):
    """Correct secret + valid ts;h1 → 200 ok."""
    body = json.dumps({"event_type": "subscription.created"}).encode()
    sig = _make_sig(TEST_SECRET, body)
    resp = _post(client, body, sig)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["event_type"] == "subscription.created"


def test_wrong_secret_returns_401(client):
    """Wrong secret → 401 regardless of well-formed header."""
    body = json.dumps({"event_type": "subscription.created"}).encode()
    sig = _make_sig("wrong-secret", body)
    resp = _post(client, body, sig)
    assert resp.status_code == 401


def test_missing_signature_header_returns_401(client):
    """No Paddle-Signature header → 401."""
    body = json.dumps({"event_type": "subscription.created"}).encode()
    resp = client.post(
        "/api/webhooks/paddle",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401


def test_malformed_header_no_h1_returns_401(client):
    """Header with ts= but no h1= → verify fails → 401."""
    body = json.dumps({"event_type": "subscription.created"}).encode()
    ts = int(time.time())
    bad_sig = f"ts={ts}"  # missing h1
    resp = _post(client, body, bad_sig)
    assert resp.status_code == 401


def test_malformed_json_payload_returns_200_fail_open(client):
    """Malformed JSON with valid signature → 200 fail-open, status=malformed."""
    body = b"{not valid json"
    sig = _make_sig(TEST_SECRET, body)
    resp = _post(client, body, sig)
    assert resp.status_code == 200
    assert resp.json()["status"] == "malformed"


def test_event_type_logged_and_echoed(client):
    """Known event_type echoed in response."""
    body = json.dumps({"event_type": "transaction.completed"}).encode()
    sig = _make_sig(TEST_SECRET, body)
    resp = _post(client, body, sig)
    assert resp.status_code == 200
    assert resp.json()["event_type"] == "transaction.completed"


def test_missing_event_type_returns_unknown(client):
    """Payload with no event_type field → event_type='unknown' in response."""
    body = json.dumps({"notification_id": "ntf_abc123"}).encode()
    sig = _make_sig(TEST_SECRET, body)
    resp = _post(client, body, sig)
    assert resp.status_code == 200
    assert resp.json()["event_type"] == "unknown"


# ---------------------------------------------------------------------------
# Unit tests for verify_paddle_signature helper
# ---------------------------------------------------------------------------


def test_verify_unit_correct(mod, monkeypatch):
    """verify_paddle_signature returns True for correct secret + fresh ts."""
    monkeypatch.setattr(mod, "_TS_TOLERANCE_SECONDS", int(_LARGE_TOLERANCE))
    body = b'{"event_type":"subscription.activated"}'
    sig = _make_sig(TEST_SECRET, body)
    assert mod.verify_paddle_signature(TEST_SECRET, body, sig) is True


def test_verify_unit_wrong_secret(mod, monkeypatch):
    """verify_paddle_signature returns False when secret differs."""
    monkeypatch.setattr(mod, "_TS_TOLERANCE_SECONDS", int(_LARGE_TOLERANCE))
    body = b'{"event_type":"subscription.activated"}'
    sig = _make_sig(TEST_SECRET, body)
    assert mod.verify_paddle_signature("different-secret", body, sig) is False


def test_verify_unit_empty_secret(mod):
    """verify_paddle_signature returns False when secret is empty string."""
    body = b'{"event_type":"subscription.activated"}'
    sig = _make_sig(TEST_SECRET, body)
    assert mod.verify_paddle_signature("", body, sig) is False
