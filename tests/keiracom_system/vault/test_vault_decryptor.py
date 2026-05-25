"""Tests for src/keiracom_system/vault/vault_decryptor.py — Phase A2.

Negative-path discipline per feedback_negative_path_test_before_approve:
the decryptor's job is fail-closed for any non-success Vault response.
Each branch needs explicit negative coverage.

13 cases — 3 happy + 10 negative/edge.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.vault.vault_decryptor import (  # noqa: E402
    DEFAULT_KEY_NAME_PREFIX,
    VaultDecryptError,
    VaultDecryptor,
    _HTTPResponse,
    from_env,
)


def _resp(status: int, body: Any) -> _HTTPResponse:
    if isinstance(body, (dict, list)):
        body = json.dumps(body).encode("utf-8")
    elif isinstance(body, str):
        body = body.encode("utf-8")
    return _HTTPResponse(status_code=status, body=body)


def _make_post(response: _HTTPResponse | Exception):
    """Build an http_post stub that returns `response` (or raises if Exception)."""
    calls: list[tuple] = []

    def _post(url: str, payload: dict, headers: dict, timeout: float) -> _HTTPResponse:
        calls.append((url, payload, headers, timeout))
        if isinstance(response, Exception):
            raise response
        return response

    _post.calls = calls  # type: ignore[attr-defined]
    return _post


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


# ─────────────────────────────────────────────────────────────────────────────
# Happy paths


def test_decrypt_round_trip_returns_plaintext():
    """(1) happy: 200 + valid plaintext base64 -> decoded UTF-8 str."""
    post = _make_post(_resp(200, {"data": {"plaintext": _b64("sk-tenant-secret")}}))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    assert d("vault:v1:abc", "tenant1") == "sk-tenant-secret"
    url, payload, headers, _ = post.calls[0]  # type: ignore[attr-defined]
    assert url == "http://vault/v1/transit/decrypt/keiracom-tenant-tenant1"
    assert payload == {"ciphertext": "vault:v1:abc"}
    assert headers["X-Vault-Token"] == "tok"


def test_decrypt_uses_configured_key_name_prefix():
    """(2) custom prefix flows through to URL path."""
    post = _make_post(_resp(200, {"data": {"plaintext": _b64("ok")}}))
    d = VaultDecryptor(addr="http://vault", token="tok", key_name_prefix="custom-", http_post=post)
    d("ct", "t1")
    url, _, _, _ = post.calls[0]  # type: ignore[attr-defined]
    assert url.endswith("/transit/decrypt/custom-t1")


def test_decrypt_handles_trailing_slash_in_addr():
    """(3) trailing slash on addr is stripped (no double slash in URL)."""
    post = _make_post(_resp(200, {"data": {"plaintext": _b64("x")}}))
    d = VaultDecryptor(addr="http://vault/", token="tok", http_post=post)
    d("ct", "t1")
    url, _, _, _ = post.calls[0]  # type: ignore[attr-defined]
    assert url == "http://vault/v1/transit/decrypt/keiracom-tenant-t1"
    assert "//v1" not in url


# ─────────────────────────────────────────────────────────────────────────────
# Negative + edge


def test_decrypt_empty_ciphertext_raises():
    """(4) empty ciphertext -> VaultDecryptError, no HTTP call."""
    post = _make_post(_resp(500, "should not be called"))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    with pytest.raises(VaultDecryptError, match="ciphertext is empty"):
        d("", "t1")
    assert len(post.calls) == 0  # type: ignore[attr-defined]


def test_decrypt_empty_tenant_id_raises():
    """(5) empty tenant_id -> VaultDecryptError, no HTTP call."""
    post = _make_post(_resp(500, "should not be called"))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    with pytest.raises(VaultDecryptError, match="tenant_id is empty"):
        d("ct", "")
    assert len(post.calls) == 0  # type: ignore[attr-defined]


def test_decrypt_vault_403_raises_with_status_in_message():
    """(6) Vault 403 (forbidden — bad token / policy) -> VaultDecryptError."""
    post = _make_post(_resp(403, {"errors": ["permission denied"]}))
    d = VaultDecryptor(addr="http://vault", token="bad", http_post=post)
    with pytest.raises(VaultDecryptError, match="HTTP 403"):
        d("ct", "t1")


def test_decrypt_vault_400_wrong_key_fail_closed():
    """(7) Vault 400 'cipher: message authentication failed' (wrong-tenant key) -> VaultDecryptError.

    The il34 spike criterion #3 fail-closed shape applied to real Vault.
    """
    post = _make_post(_resp(400, {"errors": ["cipher: message authentication failed"]}))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    with pytest.raises(VaultDecryptError, match="HTTP 400"):
        d("vault:v1:abc-from-other-tenant", "t1")


def test_decrypt_vault_404_key_not_found_raises():
    """(8) Vault 404 (key not in transit) -> VaultDecryptError."""
    post = _make_post(_resp(404, {"errors": ["encryption key not found"]}))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    with pytest.raises(VaultDecryptError, match="HTTP 404"):
        d("ct", "missing-tenant")


def test_decrypt_transport_error_wrapped_as_decrypt_error():
    """(9) urllib/connection error -> VaultDecryptError (not raw exception)."""
    post = _make_post(ConnectionRefusedError("vault unreachable"))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    with pytest.raises(VaultDecryptError, match="vault transport error"):
        d("ct", "t1")


def test_decrypt_response_missing_data_plaintext_raises():
    """(10) Vault returned 200 but no data.plaintext -> VaultDecryptError."""
    post = _make_post(_resp(200, {"data": {}}))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    with pytest.raises(VaultDecryptError, match="missing data.plaintext"):
        d("ct", "t1")


def test_decrypt_response_not_json_raises():
    """(11) Vault returned 200 with non-JSON body -> VaultDecryptError."""
    post = _make_post(_resp(200, b"\xff\xfe garbage not json"))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    with pytest.raises(VaultDecryptError, match="not JSON"):
        d("ct", "t1")


def test_decrypt_response_invalid_base64_raises():
    """(12) Vault returned 200 with non-base64 plaintext -> VaultDecryptError."""
    post = _make_post(_resp(200, {"data": {"plaintext": "!!! not base64 !!!"}}))
    d = VaultDecryptor(addr="http://vault", token="tok", http_post=post)
    with pytest.raises(VaultDecryptError, match="not valid base64"):
        d("ct", "t1")


def test_default_key_name_prefix_constant_locked():
    """(13) DEFAULT_KEY_NAME_PREFIX must match the canonical naming in dev/vault/.

    Cross-references /home/elliotbot/clawd/keiracom_system/dev/vault/setup_transit.sh
    which creates keys with the same prefix. Regression guard.
    """
    assert DEFAULT_KEY_NAME_PREFIX == "keiracom-tenant-"


# ─────────────────────────────────────────────────────────────────────────────
# from_env() factory


def test_from_env_constructs_with_addr_and_token(monkeypatch):
    """(14) VAULT_ADDR + VAULT_TOKEN set -> factory returns a valid VaultDecryptor."""
    monkeypatch.setenv("VAULT_ADDR", "http://vault.example:8200")
    monkeypatch.setenv("VAULT_TOKEN", "tok-from-env")
    monkeypatch.delenv("KEIRACOM_VAULT_KEY_PREFIX", raising=False)
    d = from_env()
    assert d.addr == "http://vault.example:8200"
    assert d.key_name_prefix == "keiracom-tenant-"


def test_from_env_missing_addr_raises(monkeypatch):
    """(15) missing VAULT_ADDR -> OSError with specific message."""
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    with pytest.raises(OSError, match="VAULT_ADDR=unset"):
        from_env()


def test_from_env_missing_token_raises(monkeypatch):
    """(16) missing VAULT_TOKEN -> OSError."""
    monkeypatch.setenv("VAULT_ADDR", "http://vault")
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    with pytest.raises(OSError, match="VAULT_TOKEN=unset"):
        from_env()


def test_from_env_custom_key_prefix_honoured(monkeypatch):
    """(17) KEIRACOM_VAULT_KEY_PREFIX overrides default."""
    monkeypatch.setenv("VAULT_ADDR", "http://vault")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    monkeypatch.setenv("KEIRACOM_VAULT_KEY_PREFIX", "custom-")
    d = from_env()
    assert d.key_name_prefix == "custom-"


# ─────────────────────────────────────────────────────────────────────────────
# Integration test — opt-in against live dev Vault


_INTEGRATION_ENABLED = os.environ.get("KEIRACOM_VAULT_INTEGRATION", "").strip() == "1"


@pytest.mark.skipif(
    not _INTEGRATION_ENABLED,
    reason="KEIRACOM_VAULT_INTEGRATION=1 not set — live dev Vault test skipped",
)
def test_integration_live_vault_round_trip():
    """(integration) — round-trip against live dev Vault.

    Requires:
      - dev Vault running at $VAULT_ADDR (default http://127.0.0.1:8200)
      - $EXT_TOKEN env (or /tmp/keiracom_vault_ext_token file) — token bound to keiracom-tenant-extension policy
      - keiracom-tenant-devtest key pre-created via setup_transit.sh
    """
    import urllib.request as ur

    addr = os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
    token = os.environ.get("EXT_TOKEN") or Path("/tmp/keiracom_vault_ext_token").read_text().strip()
    plaintext = "sk-live-test-byok-key"
    b64_plain = base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

    # Encrypt via raw API (decryptor only handles decrypt)
    enc_req = ur.Request(
        f"{addr}/v1/transit/encrypt/keiracom-tenant-devtest",
        method="POST",
        data=json.dumps({"plaintext": b64_plain}).encode("utf-8"),
        headers={"X-Vault-Token": token, "Content-Type": "application/json"},
    )
    with ur.urlopen(enc_req, timeout=10) as resp:  # noqa: S310
        ciphertext = json.loads(resp.read())["data"]["ciphertext"]

    # Decrypt via the VaultDecryptor class — should round-trip
    d = VaultDecryptor(addr=addr, token=token)
    recovered = d(ciphertext, "devtest")
    assert recovered == plaintext

    # Wrong tenant -> fail-closed
    with pytest.raises(VaultDecryptError):
        d(ciphertext, "other")
    # Note: 'other' tenant key might not exist (404) or might exist but reject (400);
    # both are fail-closed. The test asserts SOME VaultDecryptError is raised.
