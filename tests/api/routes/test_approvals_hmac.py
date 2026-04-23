"""
Tests for operator signature gate wired into src/api/routes/approvals.py
via src/security/webhook_sigs.verify_signature (PHASE-2-SLICE-8 Track C).

- Dev mode (OPERATOR_WEBHOOK_SECRET unset) -> gate bypassed.
- Prod mode (secret set) -> X-Signature mandatory; mismatch -> 401.
- Signed payload shape: f"{client_id}\\n{approval_id}\\n{action}".
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from src.api.routes.approvals import (
    OPERATOR_SECRET_ENV,
    _require_operator_signature,
)
from src.security.webhook_sigs import compute_signature


def test_gate_bypassed_when_secret_unset(monkeypatch):
    monkeypatch.delenv(OPERATOR_SECRET_ENV, raising=False)
    _require_operator_signature(None, uuid4(), uuid4(), "approve")   # no raise


def test_gate_rejects_missing_signature_when_secret_set(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setenv(OPERATOR_SECRET_ENV, "prod-secret")
    with pytest.raises(HTTPException) as exc:
        _require_operator_signature(None, uuid4(), uuid4(), "approve")
    assert exc.value.status_code == 401


def test_gate_rejects_bad_signature_when_secret_set(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setenv(OPERATOR_SECRET_ENV, "prod-secret")
    with pytest.raises(HTTPException) as exc:
        _require_operator_signature("deadbeef", uuid4(), uuid4(), "approve")
    assert exc.value.status_code == 401


def test_gate_accepts_valid_signature(monkeypatch):
    monkeypatch.setenv(OPERATOR_SECRET_ENV, "prod-secret")
    client_id = uuid4()
    approval_id = uuid4()
    action = "approve"
    payload = f"{client_id}\n{approval_id}\n{action}".encode()
    sig = compute_signature("prod-secret", payload)
    _require_operator_signature(sig, client_id, approval_id, action)  # no raise


def test_gate_action_is_part_of_signed_payload(monkeypatch):
    """Signature valid for 'approve' must NOT validate for 'reject'."""
    from fastapi import HTTPException

    monkeypatch.setenv(OPERATOR_SECRET_ENV, "prod-secret")
    client_id = uuid4()
    approval_id = uuid4()
    sig_for_approve = compute_signature(
        "prod-secret", f"{client_id}\n{approval_id}\napprove".encode(),
    )
    with pytest.raises(HTTPException):
        _require_operator_signature(sig_for_approve, client_id, approval_id, "reject")
