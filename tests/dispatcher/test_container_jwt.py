"""KEI-164 — tests for container JWT minting + verification."""

from __future__ import annotations

import jwt
import pytest

from src.dispatcher.container_jwt import (
    DEFAULT_SCOPES,
    mint_container_jwt,
    verify_container_jwt,
)


@pytest.fixture(autouse=True)
def _isolate_jwt_secret(monkeypatch):
    """Pin the signing secret + clear ENVIRONMENT so dev path is exercised
    in every test except the explicit production-required-secret case."""
    monkeypatch.setenv("CONTAINER_JWT_SECRET", "test-secret-kei164")
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def test_mint_returns_three_part_jwt_string():
    tok = mint_container_jwt("tenant-abc")
    assert isinstance(tok, str)
    assert tok.count(".") == 2  # header.payload.signature


def test_mint_includes_tenant_id():
    claims = verify_container_jwt(mint_container_jwt("tenant-abc"))
    assert claims["tenant_id"] == "tenant-abc"


def test_default_scopes_are_task_read_and_task_write():
    claims = verify_container_jwt(mint_container_jwt("tenant-abc"))
    assert claims["scope"] == ["task:read", "task:write"]
    assert set(claims["scope"]) == set(DEFAULT_SCOPES)


def test_custom_scopes_override_defaults():
    claims = verify_container_jwt(mint_container_jwt("tenant-abc", scopes=["task:read"]))
    assert claims["scope"] == ["task:read"]


def test_iat_and_exp_claims_present_and_ordered():
    claims = verify_container_jwt(mint_container_jwt("tenant-abc", expires_in_seconds=60))
    assert "iat" in claims and "exp" in claims
    assert claims["exp"] > claims["iat"]


def test_verify_rejects_wrong_secret(monkeypatch):
    tok = mint_container_jwt("tenant-abc")
    monkeypatch.setenv("CONTAINER_JWT_SECRET", "different-secret")
    with pytest.raises(jwt.InvalidSignatureError):
        verify_container_jwt(tok)


def test_verify_rejects_tampered_payload():
    tok = mint_container_jwt("tenant-abc")
    parts = tok.split(".")
    parts[1] = "eyJ0ZW5hbnRfaWQiOiJoYWNrZXIifQ"  # different payload
    with pytest.raises(jwt.InvalidTokenError):
        verify_container_jwt(".".join(parts))


def test_verify_rejects_expired_token():
    tok = mint_container_jwt("tenant-abc", expires_in_seconds=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_container_jwt(tok)


def test_mint_rejects_blank_tenant_id():
    with pytest.raises(ValueError, match="tenant_id is required"):
        mint_container_jwt("")
    with pytest.raises(ValueError, match="tenant_id is required"):
        mint_container_jwt("   ")


def test_production_requires_explicit_secret(monkeypatch):
    monkeypatch.delenv("CONTAINER_JWT_SECRET", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="must be set in production"):
        mint_container_jwt("tenant-abc")
