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


# ---------------------------------------------------------------------------
# KEI-152: dispatch + handler tests
# ---------------------------------------------------------------------------


def _make_paid_payload(sub_id: str = "sub_abc123") -> bytes:
    return json.dumps({"event_type": "invoice.paid", "data": {"subscription_id": sub_id}}).encode()


def _make_txn_payload(sub_id: str = "sub_abc123") -> bytes:
    return json.dumps(
        {"event_type": "transaction.completed", "data": {"subscription_id": sub_id}}
    ).encode()


def _make_sub_updated_payload(sub_id: str = "sub_abc123", price_id: str = "pri_abc") -> bytes:
    return json.dumps(
        {
            "event_type": "subscription.updated",
            "data": {
                "id": sub_id,
                "items": [{"price": {"id": price_id}}],
            },
        }
    ).encode()


def test_invoice_paid_dispatches_to_handler(client, mod, monkeypatch):
    """invoice.paid with subscription_id → _handle_invoice_paid called, UPDATE contains last_paid_at."""
    executed_sql: list[str] = []

    class FakeCursor:
        rowcount = 1

        def execute(self, sql, params=None):
            executed_sql.append(sql)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    import types

    fake_psycopg = types.SimpleNamespace(connect=lambda *a, **kw: FakeConn())
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
    monkeypatch.setattr(mod, "_dsn_from_env", lambda: "postgresql://fake/db")

    import sys

    sys.modules["psycopg"] = fake_psycopg

    body = _make_paid_payload()
    sig = _make_sig(TEST_SECRET, body)
    resp = _post(client, body, sig)
    assert resp.status_code == 200
    assert any("last_paid_at" in sql for sql in executed_sql)

    del sys.modules["psycopg"]


def test_transaction_completed_alias_dispatches(client, mod, monkeypatch):
    """transaction.completed (Paddle v2 name) also routes to _handle_invoice_paid."""
    called: list[dict] = []

    def fake_handle(payload):
        called.append(payload)

    monkeypatch.setattr(mod, "_handle_invoice_paid", fake_handle)

    body = _make_txn_payload()
    sig = _make_sig(TEST_SECRET, body)
    resp = _post(client, body, sig)
    assert resp.status_code == 200
    assert len(called) == 1


def test_invoice_paid_missing_sub_id_no_db_call(mod, monkeypatch):
    """Empty subscription_id → no psycopg.connect call, warning logged."""
    connect_called: list[bool] = []

    import types

    fake_psycopg = types.SimpleNamespace(connect=lambda *a, **kw: connect_called.append(True))

    import sys

    sys.modules["psycopg"] = fake_psycopg
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")

    payload = {"event_type": "invoice.paid", "data": {"subscription_id": ""}}
    mod._handle_invoice_paid(payload)
    assert connect_called == []

    del sys.modules["psycopg"]


def test_subscription_updated_dispatches_with_tier_map(client, mod, monkeypatch):
    """subscription.updated + valid PADDLE_PRICE_TO_TIER → UPDATE SQL contains tier."""
    executed_sql: list[str] = []

    class FakeCursor:
        rowcount = 1

        def execute(self, sql, params=None):
            executed_sql.append(sql)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    import types

    fake_psycopg = types.SimpleNamespace(connect=lambda *a, **kw: FakeConn())
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
    monkeypatch.setenv("PADDLE_PRICE_TO_TIER", json.dumps({"pri_abc": "pro"}))
    monkeypatch.setattr(mod, "_dsn_from_env", lambda: "postgresql://fake/db")

    import sys

    sys.modules["psycopg"] = fake_psycopg

    body = _make_sub_updated_payload(price_id="pri_abc")
    sig = _make_sig(TEST_SECRET, body)
    resp = _post(client, body, sig)
    assert resp.status_code == 200
    assert any("tier" in sql for sql in executed_sql)

    del sys.modules["psycopg"]


def test_subscription_updated_unmapped_price_no_db_call(mod, monkeypatch):
    """price_id not in PADDLE_PRICE_TO_TIER → no DB call, warning."""
    connect_called: list[bool] = []

    import types

    fake_psycopg = types.SimpleNamespace(connect=lambda *a, **kw: connect_called.append(True))

    import sys

    sys.modules["psycopg"] = fake_psycopg
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
    monkeypatch.setenv("PADDLE_PRICE_TO_TIER", json.dumps({"pri_other": "pro"}))

    payload = {
        "event_type": "subscription.updated",
        "data": {"id": "sub_abc", "items": [{"price": {"id": "pri_abc"}}]},
    }
    mod._handle_subscription_updated(payload)
    assert connect_called == []

    del sys.modules["psycopg"]


def test_handler_db_failure_fails_open_returns_200(client, mod, monkeypatch):
    """psycopg.connect raises → handler swallows exception, webhook still returns 200."""
    import types

    fake_psycopg = types.SimpleNamespace(
        connect=lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("db down"))
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
    monkeypatch.setattr(mod, "_dsn_from_env", lambda: "postgresql://fake/db")

    import sys

    sys.modules["psycopg"] = fake_psycopg

    body = _make_paid_payload()
    sig = _make_sig(TEST_SECRET, body)
    resp = _post(client, body, sig)
    assert resp.status_code == 200

    del sys.modules["psycopg"]
