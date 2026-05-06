"""
Tests for kill + state endpoints added to src/api/routes/campaigns.py

Uses FastAPI TestClient + dependency overrides.
Fake DB simulates campaigns + scheduled_touches via MagicMock.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.api.routes.campaigns import router
from src.api.dependencies import get_current_client, get_db_session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLIENT_A = uuid4()
CLIENT_B = uuid4()
CAMPAIGN_ID = uuid4()

KILL_URL = f"/clients/{CLIENT_A}/campaigns/kill"
STATE_URL = f"/clients/{CLIENT_A}/campaigns/{CAMPAIGN_ID}/state"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client_ctx(client_id: UUID = CLIENT_A):
    ctx = MagicMock()
    ctx.client_id = client_id
    ctx.user_id = uuid4()
    return ctx


def _sync_result(row=None, rowcount=0):
    """A synchronous result (fetchone is not a coroutine)."""
    r = MagicMock()
    r.fetchone.return_value = row
    r.rowcount = rowcount
    return r


def _campaign_row(campaign_id: UUID = CAMPAIGN_ID, cstatus: str = "active"):
    row = MagicMock()
    row._mapping = {"id": campaign_id, "status": cstatus}
    return row


def _agg_row(total=5, pending=3, sent=1, failed=1, last=None):
    row = MagicMock()
    row._mapping = {
        "total_touches": total,
        "pending_touches": pending,
        "sent_touches": sent,
        "failed_touches": failed,
        "last_touch_at": last,
    }
    return row


def _make_app_kill(campaign_row=None, cancel_rowcount=3, client_id: UUID = CLIENT_A):
    """App wired for kill endpoint (3 DB calls: lookup, update campaign, cancel touches)."""
    app = FastAPI()
    app.include_router(router)

    responses = [
        _sync_result(row=campaign_row),  # 1: campaign existence check
        _sync_result(rowcount=0),  # 2: UPDATE campaigns SET status='killed'
        _sync_result(rowcount=cancel_rowcount),  # 3: UPDATE scheduled_touches
    ]
    call_idx = [0]

    async def _fake_db():
        db = AsyncMock()

        async def execute_side_effect(sql, params=None):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx < len(responses):
                return responses[idx]
            return _sync_result()

        db.execute.side_effect = execute_side_effect
        db.commit = AsyncMock()
        yield db

    app.dependency_overrides[get_current_client] = lambda: _make_client_ctx(client_id)
    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app, raise_server_exceptions=True)


def _make_app_state(campaign_row=None, agg=None, client_id: UUID = CLIENT_A):
    """App wired for state endpoint (2 DB calls: lookup, aggregate)."""
    app = FastAPI()
    app.include_router(router)

    responses = [
        _sync_result(row=campaign_row),  # 1: campaign existence check
        _sync_result(row=agg or _agg_row()),  # 2: aggregation
    ]
    call_idx = [0]

    async def _fake_db():
        db = AsyncMock()

        async def execute_side_effect(sql, params=None):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx < len(responses):
                return responses[idx]
            return _sync_result()

        db.execute.side_effect = execute_side_effect
        db.commit = AsyncMock()
        yield db

    app.dependency_overrides[get_current_client] = lambda: _make_client_ctx(client_id)
    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_kill_happy_path():
    """Case 1: Kill happy path → 200, returns killed_touches count."""
    client = _make_app_kill(campaign_row=_campaign_row(), cancel_rowcount=3)
    r = client.post(KILL_URL, json={"campaign_id": str(CAMPAIGN_ID), "reason": "shutting down"})
    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["campaign_id"] == str(CAMPAIGN_ID)
    assert data["killed_touches"] == 3
    assert "killed_at" in data


def test_kill_unauthorized_client():
    """Case 2: Kill with wrong client returns 404 (campaign not found for that client)."""
    # Simulate: campaign lookup returns None (DB filtered by client_id)
    client = _make_app_kill(campaign_row=None, client_id=CLIENT_B)
    r = client.post(
        f"/clients/{CLIENT_B}/campaigns/kill",
        json={"campaign_id": str(CAMPAIGN_ID), "reason": "test"},
    )
    assert r.status_code == status.HTTP_404_NOT_FOUND, r.text


def test_state_endpoint():
    """Case 3: State endpoint → returns aggregated counts."""
    agg = _agg_row(total=10, pending=4, sent=5, failed=1)
    client = _make_app_state(campaign_row=_campaign_row(cstatus="active"), agg=agg)
    r = client.get(STATE_URL)
    assert r.status_code == status.HTTP_200_OK, r.text
    data = r.json()
    assert data["campaign_id"] == str(CAMPAIGN_ID)
    assert data["status"] == "active"
    assert data["total_touches"] == 10
    assert data["pending_touches"] == 4
    assert data["sent_touches"] == 5
    assert data["failed_touches"] == 1


def test_kill_nonexistent_campaign():
    """Case 4: Kill on non-existent campaign → 404."""
    client = _make_app_kill(campaign_row=None)
    r = client.post(KILL_URL, json={"campaign_id": str(uuid4()), "reason": "test"})
    assert r.status_code == status.HTTP_404_NOT_FOUND, r.text


def test_state_nonexistent_campaign():
    """Case 5: State on non-existent campaign → 404."""
    client = _make_app_state(campaign_row=None)
    r = client.get(f"/clients/{CLIENT_A}/campaigns/{uuid4()}/state")
    assert r.status_code == status.HTTP_404_NOT_FOUND, r.text


def test_kill_idempotent():
    """Case 6: Kill twice → second call returns 0 killed_touches (all already cancelled)."""
    client1 = _make_app_kill(campaign_row=_campaign_row(cstatus="active"), cancel_rowcount=5)
    r1 = client1.post(KILL_URL, json={"campaign_id": str(CAMPAIGN_ID), "reason": "first kill"})
    assert r1.status_code == status.HTTP_200_OK, r1.text
    assert r1.json()["killed_touches"] == 5

    # Second kill: campaign is now 'killed' status, but row still exists; 0 pending touches
    client2 = _make_app_kill(campaign_row=_campaign_row(cstatus="killed"), cancel_rowcount=0)
    r2 = client2.post(KILL_URL, json={"campaign_id": str(CAMPAIGN_ID), "reason": "second kill"})
    assert r2.status_code == status.HTTP_200_OK, r2.text
    assert r2.json()["killed_touches"] == 0
