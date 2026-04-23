"""
Tests for src/api/routes/approvals.py

Uses FastAPI TestClient + dependency overrides.
Fake DB simulates the approvals table via in-memory row mocks.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.api.routes.approvals import router
from src.api.dependencies import get_current_client, get_db_session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLIENT_A = uuid4()
CLIENT_B = uuid4()
USER_ID = uuid4()
APPROVAL_ID = uuid4()

BASE = f"/api/v1/approvals/clients/{CLIENT_A}/{APPROVAL_ID}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client_ctx(client_id: UUID = CLIENT_A):
    ctx = MagicMock()
    ctx.client_id = client_id
    ctx.user_id = USER_ID
    return ctx


def _make_sync_result(row=None, rowcount=0):
    """Synchronous execute result — fetchone() is NOT async."""
    result = MagicMock()
    result.fetchone.return_value = row
    result.rowcount = rowcount
    return result


def _make_row(approval_id: UUID, client_id: UUID = CLIENT_A, status_val: str = "pending"):
    row = MagicMock()
    row._mapping = {
        "id": approval_id,
        "client_id": client_id,
        "status": status_val,
        "payload": {},
        "decided_at": None,
        "decided_by": None,
        "reason": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    return row


def _make_app(approval_row=None, client_id: UUID = CLIENT_A):
    app = FastAPI()
    app.include_router(router)

    sync_result = _make_sync_result(row=approval_row)

    async def _fake_db():
        db = AsyncMock()
        # db.execute() is async but returns a sync-capable result
        db.execute.return_value = sync_result
        db.commit = AsyncMock()
        yield db

    app.dependency_overrides[get_current_client] = lambda: _make_client_ctx(client_id)
    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_unauth_returns_non_200():
    """Case 1: no auth override → dependency chain fails, not 200."""
    app = FastAPI()
    app.include_router(router)
    # No dependency override for get_current_client
    client = TestClient(app, raise_server_exceptions=False)
    r = client.post(f"{BASE}/approve")
    # Without a real JWT, FastAPI/dep chain returns 4xx or 5xx — never 200
    assert r.status_code != status.HTTP_200_OK


def test_approve_happy_path():
    """Case 2: approve happy path → 200, status=approved."""
    row = _make_row(APPROVAL_ID)
    client = _make_app(approval_row=row)
    r = client.post(f"{BASE}/approve")
    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["status"] == "approved"
    assert data["approval_id"] == str(APPROVAL_ID)
    assert "decided_at" in data


def test_reject_happy_path():
    """Case 3: reject happy path → 200 with reason accepted."""
    row = _make_row(APPROVAL_ID)
    client = _make_app(approval_row=row)
    r = client.post(f"{BASE}/reject", json={"reason": "not suitable"})
    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["status"] == "rejected"


def test_defer_happy_path():
    """Case 4: defer happy path → 200 with defer_hours parsed."""
    row = _make_row(APPROVAL_ID)
    client = _make_app(approval_row=row)
    r = client.post(f"{BASE}/defer", json={"defer_hours": 24})
    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["status"] == "deferred"
    assert data["defer_hours"] == 24


def test_edit_happy_path():
    """Case 5: edit happy path → 200 with edits applied."""
    row = _make_row(APPROVAL_ID)
    client = _make_app(approval_row=row)
    r = client.post(f"{BASE}/edit", json={"edits": {"subject": "new subject"}})
    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["status"] == "edit_applied"


def test_404_when_not_found():
    """Case 6: approval_id not found → 404."""
    client = _make_app(approval_row=None)
    r = client.post(f"{BASE}/approve")
    assert r.status_code == status.HTTP_404_NOT_FOUND, r.text


def test_403_cross_tenant():
    """Case 7: approval belongs to different client → 403."""
    row = _make_row(APPROVAL_ID, client_id=CLIENT_B)
    # Auth context is CLIENT_A, row belongs to CLIENT_B
    client = _make_app(approval_row=row, client_id=CLIENT_A)
    r = client.post(f"{BASE}/approve")
    assert r.status_code == status.HTTP_403_FORBIDDEN, r.text
    assert "not owned by client" in r.json()["detail"]


def test_409_already_terminal():
    """Case 8: approval already approved → 409."""
    row = _make_row(APPROVAL_ID, status_val="approved")
    client = _make_app(approval_row=row)
    r = client.post(f"{BASE}/approve")
    assert r.status_code == status.HTTP_409_CONFLICT, r.text


def test_reject_missing_reason_422():
    """Case 9: reject with no reason → 422 pydantic validation."""
    row = _make_row(APPROVAL_ID)
    client = _make_app(approval_row=row)
    r = client.post(f"{BASE}/reject", json={})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text


def test_defer_out_of_range_422():
    """Case 10: defer with hours=0 or hours=800 → 422 pydantic validation."""
    row = _make_row(APPROVAL_ID)
    client = _make_app(approval_row=row)
    r0 = client.post(f"{BASE}/defer", json={"defer_hours": 0})
    assert r0.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r0.text
    r800 = client.post(f"{BASE}/defer", json={"defer_hours": 800})
    assert r800.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r800.text
