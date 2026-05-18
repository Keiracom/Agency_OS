"""KEI-138 — dual-key verify support for INBOX_HMAC_SECRET rotation.

Covers the rotation lane added to src/security/inbox_hmac.verify():

  (1) primary secret only  → payload signed with primary verifies.
  (2) rotation window      → INBOX_HMAC_SECRET_PREVIOUS set; payload signed
                             with EITHER secret verifies.
  (3) old secret rejected  → after PREVIOUS unset, old-signed payload fails.
  (4) duplicate secrets    → primary == PREVIOUS dedup-ed (no double compare).
  (5) candidate ordering   → primary attempted first (perf-critical path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.security.inbox_hmac import _candidate_secrets, sign, verify


def _write_signed(tmp_path: Path, payload: dict, secret: str) -> Path:
    """Helper: sign payload with the given secret, write to file, return path."""
    signed = sign(payload, secret=secret)
    out = tmp_path / "dispatch.json"
    out.write_text(json.dumps(signed))
    return out


def test_primary_secret_only_verifies(monkeypatch, tmp_path):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "primary-secret-aaaa")
    monkeypatch.delenv("INBOX_HMAC_SECRET_PREVIOUS", raising=False)
    p = _write_signed(tmp_path, {"type": "test", "brief": "primary"}, "primary-secret-aaaa")
    ok, reason = verify(p)
    assert ok, reason


def test_rotation_window_accepts_either_secret(monkeypatch, tmp_path):
    """During rotation, payloads signed with old OR new secret must verify."""
    monkeypatch.setenv("INBOX_HMAC_SECRET", "new-secret-bbbb")
    monkeypatch.setenv("INBOX_HMAC_SECRET_PREVIOUS", "old-secret-aaaa")

    # Payload signed with the OLD secret — must still verify during window.
    p_old = _write_signed(tmp_path, {"type": "test", "n": 1}, "old-secret-aaaa")
    ok_old, reason_old = verify(p_old)
    assert ok_old, f"old-signed payload rejected: {reason_old}"

    # Payload signed with the NEW secret — must verify too.
    p_new = tmp_path / "dispatch_new.json"
    signed_new = sign({"type": "test", "n": 2}, secret="new-secret-bbbb")
    p_new.write_text(json.dumps(signed_new))
    ok_new, reason_new = verify(p_new)
    assert ok_new, f"new-signed payload rejected: {reason_new}"


def test_old_secret_rejected_after_rotation_closes(monkeypatch, tmp_path):
    """Once PREVIOUS is unset, old-secret payloads must FAIL — that's the
    point of closing the window."""
    monkeypatch.setenv("INBOX_HMAC_SECRET", "new-secret-bbbb")
    monkeypatch.delenv("INBOX_HMAC_SECRET_PREVIOUS", raising=False)

    p_old = _write_signed(tmp_path, {"type": "test", "stale": True}, "old-secret-aaaa")
    ok, reason = verify(p_old)
    assert not ok
    assert "mismatch" in reason.lower() or "unknown" in reason.lower()


def test_duplicate_primary_and_previous_dedupes(monkeypatch):
    """Misconfigured rotation where someone copies the same value into both
    env vars — should still work (no crash) and only build one candidate."""
    monkeypatch.setenv("INBOX_HMAC_SECRET", "same-secret-cccc")
    monkeypatch.setenv("INBOX_HMAC_SECRET_PREVIOUS", "same-secret-cccc")
    candidates = _candidate_secrets(None)
    assert candidates == ["same-secret-cccc"]


def test_candidate_ordering_primary_first(monkeypatch):
    """Primary MUST be tried first — common path stays one compare; rotation
    only pays the second compare during the window."""
    monkeypatch.setenv("INBOX_HMAC_SECRET", "primary-pri")
    monkeypatch.setenv("INBOX_HMAC_SECRET_PREVIOUS", "previous-prev")
    candidates = _candidate_secrets(None)
    assert candidates == ["primary-pri", "previous-prev"]


def test_no_secret_at_all_fails(monkeypatch, tmp_path):
    monkeypatch.delenv("INBOX_HMAC_SECRET", raising=False)
    monkeypatch.delenv("INBOX_HMAC_SECRET_PREVIOUS", raising=False)
    p = tmp_path / "dispatch.json"
    p.write_text(json.dumps({"type": "test", "hmac": "deadbeef"}))
    ok, reason = verify(p)
    assert not ok
    assert "INBOX_HMAC_SECRET not set" in reason


def test_explicit_secret_arg_overrides_env(monkeypatch, tmp_path):
    """Pre-existing API: explicit secret kwarg short-circuits env lookup."""
    monkeypatch.setenv("INBOX_HMAC_SECRET", "env-secret")
    monkeypatch.delenv("INBOX_HMAC_SECRET_PREVIOUS", raising=False)
    p = _write_signed(tmp_path, {"type": "test"}, "arg-secret")
    ok, reason = verify(p, secret="arg-secret")
    assert ok, reason
