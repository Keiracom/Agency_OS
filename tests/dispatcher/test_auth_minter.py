"""KEI-209 — tests for auth_minter mint + verify."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.dispatcher.auth_minter import (
    TOKEN_TTL_SECONDS,
    mint_token,
    verify_token,
)


@pytest.fixture(autouse=True)
def _isolate_jwt_secret(monkeypatch):
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "test-secret-kei209")


def test_mint_returns_three_part_jwt_string():
    tok = mint_token("tenant-abc", "orion", "sess-1")
    assert isinstance(tok, str)
    assert tok.count(".") == 2


def test_mint_includes_all_required_claims():
    claims = verify_token(mint_token("tenant-abc", "orion", "sess-1"))
    assert claims is not None
    assert claims["tenant_id"] == "tenant-abc"
    assert claims["callsign"] == "orion"
    assert claims["session_id"] == "sess-1"
    assert "iat" in claims
    assert "exp" in claims


def test_token_ttl_is_15_minutes():
    claims = verify_token(mint_token("tenant-abc", "orion", "sess-1"))
    assert claims is not None
    assert claims["exp"] - claims["iat"] == TOKEN_TTL_SECONDS
    assert TOKEN_TTL_SECONDS == 900


def test_verify_valid_token_returns_dict():
    tok = mint_token("tenant-abc", "orion", "sess-1")
    result = verify_token(tok)
    assert isinstance(result, dict)
    assert result["callsign"] == "orion"


def test_verify_expired_token_returns_none():
    past = datetime.now(UTC) - timedelta(hours=1)
    tok = jwt.encode(
        {
            "tenant_id": "t",
            "callsign": "orion",
            "session_id": "s",
            "iat": past,
            "exp": past,
        },
        "test-secret-kei209",
        algorithm="HS256",
    )
    assert verify_token(tok) is None


def test_verify_tampered_payload_returns_none():
    tok = mint_token("tenant-abc", "orion", "sess-1")
    parts = tok.split(".")
    parts[1] = "eyJ0ZW5hbnRfaWQiOiJoYWNrZXIifQ"
    assert verify_token(".".join(parts)) is None


def test_verify_wrong_secret_returns_none(monkeypatch):
    tok = mint_token("tenant-abc", "orion", "sess-1")
    monkeypatch.setenv("DISPATCHER_JWT_SECRET", "rotated-secret")
    assert verify_token(tok) is None


def test_verify_malformed_token_returns_none():
    assert verify_token("not-a-jwt") is None


def test_mint_rejects_blank_tenant_id():
    with pytest.raises(ValueError, match="tenant_id is required"):
        mint_token("", "orion", "sess-1")
    with pytest.raises(ValueError, match="tenant_id is required"):
        mint_token("   ", "orion", "sess-1")


def test_mint_rejects_blank_callsign():
    with pytest.raises(ValueError, match="callsign is required"):
        mint_token("tenant-abc", "", "sess-1")


def test_mint_rejects_blank_session_id():
    with pytest.raises(ValueError, match="session_id is required"):
        mint_token("tenant-abc", "orion", "")


def test_secret_required_no_dev_fallback(monkeypatch):
    monkeypatch.delenv("DISPATCHER_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="DISPATCHER_JWT_SECRET must be set"):
        mint_token("tenant-abc", "orion", "sess-1")
