"""KEI-138 — dispatch_audit helpers: fingerprint + emit_audit fail-open."""

from __future__ import annotations

import hashlib

from src.security.dispatch_audit import emit_audit, fingerprint


def test_fingerprint_first_twelve_hex_of_sha256():
    """fingerprint(s) == first 12 hex chars of SHA-256(s) — stable identifier
    for which key was used, without leaking the key itself."""
    input_value = "abc123-shared-input-string"  # NOT a real secret; fingerprint() input fixture
    expected = hashlib.sha256(input_value.encode("utf-8")).hexdigest()[:12]
    assert fingerprint(input_value) == expected
    assert len(fingerprint(input_value)) == 12


def test_fingerprint_none_for_empty_or_none():
    assert fingerprint(None) is None
    assert fingerprint("") is None


def test_emit_audit_no_dsn_returns_false_no_raise(monkeypatch):
    """No DATABASE_URL / SUPABASE_DB_URL → False (skipped) — never raises."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    rc = emit_audit(
        "sign",
        result="ok",
        payload_id="x",
        target="atlas",
        actor="elliot",
        secret_fingerprint="abc123abc123",
    )
    assert rc is False


def test_emit_audit_unreachable_db_returns_false_no_raise(monkeypatch):
    """Bogus DSN → False (DB unreachable) — fail-open contract: NEVER raise
    out of audit, since audit MUST NOT block a dispatch."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://nonexistent-host-y52ohx:5432/nope")
    rc = emit_audit(
        "verify",
        result="mismatch",
        payload_id="x",
        target="atlas",
        actor="unknown",
        reason="HMAC mismatch",
    )
    assert rc is False


def test_emit_audit_accepts_all_optional_fields_none(monkeypatch):
    """Required args = action + result; everything else optional. No-DSN path
    exercises the kwarg defaults without hitting the DB."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    rc = emit_audit("sign", result="ok")
    assert rc is False
