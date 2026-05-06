"""
Tests for src/security/webhook_sigs.py — per-provider HMAC-SHA256
verification used by outreach webhooks + operator actions.
"""

from __future__ import annotations

import hashlib
import hmac

import pytest
from fastapi import FastAPI, HTTPException, Request

from src.security.webhook_sigs import (
    PROVIDERS,
    ProviderSpec,
    SignatureError,
    compute_signature,
    require_header_signature,
    require_signature,
    verify_provider,
    verify_signature,
)


# -- compute_signature + verify_signature ---------------------------------


def test_compute_signature_matches_manual_hmac():
    secret, payload = "topsecret", b'{"a":1}'
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert compute_signature(secret, payload) == expected


def test_verify_valid_signature(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "shh")
    payload = b"hello"
    sig = compute_signature("shh", payload)
    assert verify_signature("MY_SECRET", payload, sig) is True


def test_verify_invalid_signature(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "shh")
    assert verify_signature("MY_SECRET", b"hello", "deadbeef") is False


def test_verify_missing_secret_returns_false(monkeypatch):
    monkeypatch.delenv("MY_SECRET", raising=False)
    # Any signature must be rejected when the secret is unset.
    assert verify_signature("MY_SECRET", b"hello", "anything") is False


def test_verify_empty_secret_returns_false(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "")
    assert verify_signature("MY_SECRET", b"hello", "anything") is False


def test_verify_missing_signature_returns_false(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "shh")
    assert verify_signature("MY_SECRET", b"hello", None) is False
    assert verify_signature("MY_SECRET", b"hello", "") is False


# -- verify_provider -------------------------------------------------------


def test_verify_provider_maps_to_correct_env(monkeypatch):
    monkeypatch.setenv("SALESFORGE_WEBHOOK_SECRET", "sf-secret")
    sig = compute_signature("sf-secret", b"payload")
    assert verify_provider("salesforge", b"payload", sig) is True


def test_verify_provider_unknown_raises():
    with pytest.raises(SignatureError):
        verify_provider("nope", b"payload", "sig")


def test_providers_registry_includes_four_targets():
    assert set(PROVIDERS) == {"salesforge", "unipile", "elevenagents", "operator"}
    assert PROVIDERS["operator"].header == "X-Signature"
    assert PROVIDERS["unipile"].header == "X-Unipile-Signature"


# -- require_signature + require_header_signature (FastAPI-bound) ---------


@pytest.mark.asyncio
async def test_require_signature_reads_body_and_passes(monkeypatch):
    monkeypatch.setenv("SALESFORGE_WEBHOOK_SECRET", "secret")
    body = b'{"from":"a@b"}'
    sig = compute_signature("secret", body)

    # Build a minimal Request with the required body + headers.
    app = FastAPI()
    scope = {
        "type": "http",
        "headers": [(b"x-salesforge-signature", sig.encode())],
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "app": app,
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    req = Request(scope, receive)
    out = await require_signature(req, "salesforge")
    assert out == body


@pytest.mark.asyncio
async def test_require_signature_raises_401_on_mismatch(monkeypatch):
    monkeypatch.setenv("SALESFORGE_WEBHOOK_SECRET", "secret")
    body = b'{"from":"a@b"}'

    app = FastAPI()
    scope = {
        "type": "http",
        "headers": [(b"x-salesforge-signature", b"wrong")],
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "app": app,
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    req = Request(scope, receive)
    with pytest.raises(HTTPException) as exc:
        await require_signature(req, "salesforge")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_signature_unknown_provider_500(monkeypatch):
    app = FastAPI()
    scope = {
        "type": "http",
        "headers": [],
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "app": app,
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    req = Request(scope, receive)
    with pytest.raises(HTTPException) as exc:
        await require_signature(req, "unknown")
    assert exc.value.status_code == 500


def test_require_header_signature_sync_passes(monkeypatch):
    monkeypatch.setenv("UNIPILE_WEBHOOK_SECRET", "sh!")
    body = b"x"
    sig = compute_signature("sh!", body)
    # Should not raise
    require_header_signature(body, sig, "unipile")


def test_require_header_signature_sync_raises_401(monkeypatch):
    monkeypatch.setenv("UNIPILE_WEBHOOK_SECRET", "sh!")
    with pytest.raises(HTTPException) as exc:
        require_header_signature(b"x", "bad", "unipile")
    assert exc.value.status_code == 401


def test_require_header_signature_sync_missing_secret_fails_loud(monkeypatch):
    # No env var = rejection (production caller should have set the secret).
    monkeypatch.delenv("UNIPILE_WEBHOOK_SECRET", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_header_signature(b"x", "any", "unipile")
    assert exc.value.status_code == 401


# -- ProviderSpec as documented ------------------------------------------


def test_provider_spec_is_immutable():
    spec = PROVIDERS["salesforge"]
    with pytest.raises(Exception):
        spec.name = "other"  # frozen dataclass
