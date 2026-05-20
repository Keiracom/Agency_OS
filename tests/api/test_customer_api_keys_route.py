"""Tests for src/api/routes/customer_api_keys.py — KEI-155 BYO key entry.

Mocks the auth dep + store_key so the route is exercised without hitting
Supabase or pgcrypto. Each test confirms:
  - happy path returns 201 + UUID + provider echo
  - plaintext never appears in response body
  - plaintext never logged
  - invalid provider rejected by Pydantic (422)
  - too-short plaintext rejected by Pydantic (422)
  - RuntimeError from store_key surfaces as 500
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_current_user_from_token
from src.api.routes.customer_api_keys import router

USER_ID = uuid4()
ROW_ID = uuid4()
PLAINTEXT = "sk-anthropic-supersecret-abc123xyz"


def _user_stub() -> SimpleNamespace:
    return SimpleNamespace(
        id=USER_ID, email="t@example.com", full_name=None, is_platform_admin=False
    )


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user_from_token] = _user_stub
    return app


def test_byo_key_happy_path_returns_201_and_row_id():
    app = _make_app()
    with patch("src.api.routes.customer_api_keys.keys_service.store_key", return_value=ROW_ID) as m:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/dispatcher/byo-key",
            json={"provider": "anthropic", "plaintext": PLAINTEXT},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == str(ROW_ID)
    assert body["provider"] == "anthropic"
    m.assert_called_once_with(customer_id=USER_ID, provider="anthropic", plaintext=PLAINTEXT)


def test_byo_key_plaintext_never_in_response_body():
    app = _make_app()
    with patch("src.api.routes.customer_api_keys.keys_service.store_key", return_value=ROW_ID):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/dispatcher/byo-key",
            json={"provider": "openai", "plaintext": PLAINTEXT},
        )
    assert resp.status_code == 201
    assert PLAINTEXT not in resp.text
    assert "plaintext" not in resp.json()


def test_byo_key_plaintext_never_logged(caplog):
    app = _make_app()
    caplog.set_level(logging.DEBUG)
    with patch("src.api.routes.customer_api_keys.keys_service.store_key", return_value=ROW_ID):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/dispatcher/byo-key",
            json={"provider": "anthropic", "plaintext": PLAINTEXT},
        )
    assert resp.status_code == 201
    for rec in caplog.records:
        assert PLAINTEXT not in rec.getMessage()


def test_byo_key_invalid_provider_returns_422():
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/dispatcher/byo-key",
        json={"provider": "google", "plaintext": PLAINTEXT},
    )
    assert resp.status_code == 422


def test_byo_key_short_plaintext_returns_422():
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/dispatcher/byo-key",
        json={"provider": "anthropic", "plaintext": "short"},
    )
    assert resp.status_code == 422


def test_byo_key_missing_provider_returns_422():
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/dispatcher/byo-key",
        json={"plaintext": PLAINTEXT},
    )
    assert resp.status_code == 422


def test_byo_key_store_key_runtimeerror_returns_500():
    """Unset CUSTOMER_KEY_ENCRYPTION_KEY env triggers RuntimeError from store_key —
    route surfaces it as 500 with the underlying message exposed in detail."""
    app = _make_app()
    with patch(
        "src.api.routes.customer_api_keys.keys_service.store_key",
        side_effect=RuntimeError("CUSTOMER_KEY_ENCRYPTION_KEY env var required"),
    ):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/dispatcher/byo-key",
            json={"provider": "anthropic", "plaintext": PLAINTEXT},
        )
    assert resp.status_code == 500
    assert "misconfigured" in resp.json()["detail"]
