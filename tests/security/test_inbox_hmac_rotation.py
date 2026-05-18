"""KEI-138 — Tests for verify_dict + dual-secret rotation in src/security/inbox_hmac.py.

Covers the rotation window contract: when INBOX_HMAC_SECRET is the new value
and INBOX_HMAC_SECRET_PREV holds the old value, verify_dict accepts payloads
signed with EITHER secret. The returned secret_index discriminates so callers
can audit how long the PREV slot is still in use.
"""

from __future__ import annotations

import pytest

from src.security.inbox_hmac import canonical_hash, sign, verify_dict


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("INBOX_HMAC_SECRET", raising=False)
    monkeypatch.delenv("INBOX_HMAC_SECRET_PREV", raising=False)
    yield


def test_verify_dict_primary_secret_returns_index_zero(monkeypatch):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "current-secret")
    signed = sign({"type": "task_dispatch", "from": "elliot"})
    ok, reason, idx = verify_dict(signed)
    assert ok is True
    assert reason == "ok"
    assert idx == 0


def test_verify_dict_prev_secret_returns_index_one(monkeypatch):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "new-secret")
    monkeypatch.setenv("INBOX_HMAC_SECRET_PREV", "old-secret")
    signed_with_old = sign({"type": "task_dispatch"}, secret="old-secret")
    ok, reason, idx = verify_dict(signed_with_old)
    assert ok is True
    assert reason == "ok"
    assert idx == 1


def test_verify_dict_unknown_secret_rejected(monkeypatch):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "current")
    monkeypatch.setenv("INBOX_HMAC_SECRET_PREV", "previous")
    signed_with_unknown = sign({"type": "task_dispatch"}, secret="rogue-secret")
    ok, reason, idx = verify_dict(signed_with_unknown)
    assert ok is False
    assert "mismatch" in reason.lower()
    assert idx == -1


def test_verify_dict_missing_hmac_field(monkeypatch):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "current")
    ok, reason, idx = verify_dict({"type": "task_dispatch"})
    assert ok is False
    assert "missing" in reason
    assert idx == -1


def test_verify_dict_no_env_secret(monkeypatch):
    """With neither current nor prev set, verify_dict fails fast."""
    ok, reason, idx = verify_dict({"type": "task_dispatch", "hmac": "anything"})
    assert ok is False
    assert "INBOX_HMAC_SECRET not set" in reason
    assert idx == -1


def test_verify_dict_explicit_secret_overrides_env(monkeypatch):
    """When the caller passes a secret explicitly, the env is ignored for primary
    (but PREV may still be consulted from env — the contract is current-via-arg)."""
    monkeypatch.setenv("INBOX_HMAC_SECRET", "wrong")
    signed = sign({"type": "task_dispatch"}, secret="explicit-secret")
    ok, reason, idx = verify_dict(signed, secret="explicit-secret")
    assert ok is True
    assert idx == 0


def test_verify_dict_only_prev_set(monkeypatch):
    """Edge case: post-rollback state where PREV is the only secret available.

    Implementation accepts this (PREV is filtered into the secrets list); idx=0
    because there's only one entry. Documents the behaviour rather than asserts
    a policy — operator runbook says don't ship without primary.
    """
    monkeypatch.setenv("INBOX_HMAC_SECRET_PREV", "fallback-only")
    signed = sign({"type": "task_dispatch"}, secret="fallback-only")
    ok, _, idx = verify_dict(signed)
    assert ok is True
    assert idx == 0


def test_verify_dict_dedups_when_prev_equals_current(monkeypatch):
    """If operator accidentally sets PREV = current, the duplicate is filtered
    so verify still works (idx=0) and there's no double-compute waste."""
    monkeypatch.setenv("INBOX_HMAC_SECRET", "same")
    monkeypatch.setenv("INBOX_HMAC_SECRET_PREV", "same")
    signed = sign({"type": "task_dispatch"})
    ok, _, idx = verify_dict(signed)
    assert ok is True
    assert idx == 0


def test_canonical_hash_stable_across_hmac_field(monkeypatch):
    """canonical_hash excludes the hmac field — same hash whether payload is
    signed yet or not."""
    payload = {"type": "task_dispatch", "from": "elliot", "brief": "hello"}
    h_unsigned = canonical_hash(payload)
    monkeypatch.setenv("INBOX_HMAC_SECRET", "any")
    signed = sign(payload)
    h_signed = canonical_hash(signed)
    assert h_unsigned == h_signed
    assert len(h_unsigned) == 64  # SHA-256 hex


def test_canonical_hash_changes_with_payload_content():
    h1 = canonical_hash({"type": "task_dispatch", "brief": "a"})
    h2 = canonical_hash({"type": "task_dispatch", "brief": "b"})
    assert h1 != h2
