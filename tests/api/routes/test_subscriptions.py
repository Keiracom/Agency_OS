"""KEI-151 (KEI-112B) — tests for src/api/routes/subscriptions.

The SQLAlchemy AsyncSession dependency is overridden with a fake that
records executed SQL + responds with pre-canned row mocks. No live DB.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import get_db_session
from src.api.main import app


def _row(
    *,
    sub_id=None,
    customer_id=None,
    tier_code="basic",
    paddle_subscription_id=None,
    sub_status="active",
    canceled_at=None,
):
    """Build a fake row with the columns the route's RETURNING/SELECT expect."""
    return SimpleNamespace(
        id=sub_id or uuid4(),
        customer_id=customer_id or uuid4(),
        tier_code=tier_code,
        paddle_subscription_id=paddle_subscription_id,
        status=sub_status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        canceled_at=canceled_at,
    )


def _make_db_session(execute_results: list):
    """Build an AsyncSession-like that yields each execute_results entry
    per .execute() call in order. Each entry is the .one()/.one_or_none()
    return value (or an Exception to raise from .execute())."""
    session = MagicMock()
    results_iter = iter(execute_results)

    async def fake_execute(_query, _params=None):
        item = next(results_iter)
        if isinstance(item, Exception):
            raise item
        result = MagicMock()
        result.one = MagicMock(return_value=item)
        result.one_or_none = MagicMock(return_value=item)
        return result

    session.execute = AsyncMock(side_effect=fake_execute)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def client_with_db():
    """Build a TestClient with the AsyncSession dependency override-able
    per test via the .db_results attribute."""
    holder: dict = {"results": []}

    def _override():
        session = _make_db_session(holder["results"])
        holder["session"] = session
        return session

    app.dependency_overrides[get_db_session] = _override
    try:
        client = TestClient(app)
        client.db_results = holder  # type: ignore[attr-defined]
        yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ─── POST /subscriptions ──────────────────────────────────────────────────


def test_create_subscription_basic(client_with_db):
    """Happy path: POST returns 201 + SubscriptionRead with limits attached."""
    cust_id = str(uuid4())
    client_with_db.db_results["results"] = [_row(customer_id=cust_id, tier_code="basic")]
    resp = client_with_db.post(
        "/api/v1/subscriptions",
        json={"customer_id": cust_id, "tier_code": "basic"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["customer_id"] == cust_id
    assert body["tier_code"] == "basic"
    assert body["status"] == "active"
    assert body["limit_per_window"] == 60
    assert body["window_size_s"] == 60


def test_create_subscription_pro_attaches_higher_limit(client_with_db):
    """Pro tier → limit_per_window = 300 in response."""
    client_with_db.db_results["results"] = [_row(tier_code="pro")]
    resp = client_with_db.post(
        "/api/v1/subscriptions",
        json={"customer_id": str(uuid4()), "tier_code": "pro"},
    )
    assert resp.status_code == 201
    assert resp.json()["limit_per_window"] == 300


def test_create_subscription_enterprise(client_with_db):
    client_with_db.db_results["results"] = [_row(tier_code="enterprise")]
    resp = client_with_db.post(
        "/api/v1/subscriptions",
        json={"customer_id": str(uuid4()), "tier_code": "enterprise"},
    )
    assert resp.status_code == 201
    assert resp.json()["limit_per_window"] == 1000


def test_create_subscription_rejects_unknown_tier(client_with_db):
    """Unknown tier → 422 from Pydantic Literal validation (before DB)."""
    resp = client_with_db.post(
        "/api/v1/subscriptions",
        json={"customer_id": str(uuid4()), "tier_code": "platinum"},
    )
    assert resp.status_code == 422


def test_create_subscription_conflict_on_duplicate_active(client_with_db):
    """Partial unique index raises IntegrityError → 409 with friendly msg."""
    client_with_db.db_results["results"] = [
        IntegrityError("dup", {}, Exception("active subscription exists"))
    ]
    resp = client_with_db.post(
        "/api/v1/subscriptions",
        json={"customer_id": str(uuid4()), "tier_code": "basic"},
    )
    assert resp.status_code == 409
    assert "active subscription" in resp.json()["detail"]


# ─── GET /subscriptions/{id} ──────────────────────────────────────────────


def test_get_subscription_returns_row_with_limits(client_with_db):
    sub_id = uuid4()
    client_with_db.db_results["results"] = [_row(sub_id=sub_id, tier_code="pro")]
    resp = client_with_db.get(f"/api/v1/subscriptions/{sub_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(sub_id)
    assert body["tier_code"] == "pro"
    assert body["limit_per_window"] == 300


def test_get_subscription_404_when_missing(client_with_db):
    client_with_db.db_results["results"] = [None]
    resp = client_with_db.get(f"/api/v1/subscriptions/{uuid4()}")
    assert resp.status_code == 404


# ─── PATCH /subscriptions/{id} ────────────────────────────────────────────


def test_patch_subscription_tier_upgrade(client_with_db):
    """Update tier: returns row with NEW tier's limit_per_window."""
    sub_id = uuid4()
    client_with_db.db_results["results"] = [_row(sub_id=sub_id, tier_code="pro")]
    resp = client_with_db.patch(
        f"/api/v1/subscriptions/{sub_id}",
        json={"tier_code": "pro"},
    )
    assert resp.status_code == 200
    assert resp.json()["tier_code"] == "pro"
    assert resp.json()["limit_per_window"] == 300


def test_patch_subscription_rejects_unknown_tier(client_with_db):
    resp = client_with_db.patch(
        f"/api/v1/subscriptions/{uuid4()}",
        json={"tier_code": "platinum"},
    )
    assert resp.status_code == 422


def test_patch_subscription_404_when_missing(client_with_db):
    """UPDATE ... WHERE id=? returns no row, second check also returns
    no row → 404."""
    client_with_db.db_results["results"] = [None, None]
    resp = client_with_db.patch(
        f"/api/v1/subscriptions/{uuid4()}",
        json={"tier_code": "basic"},
    )
    assert resp.status_code == 404


def test_patch_subscription_409_when_canceled(client_with_db):
    """UPDATE filter requires status='active' → no row updated; second
    check finds the row in 'canceled' status → 409 with explanation."""
    client_with_db.db_results["results"] = [
        None,
        SimpleNamespace(status="canceled"),
    ]
    resp = client_with_db.patch(
        f"/api/v1/subscriptions/{uuid4()}",
        json={"tier_code": "pro"},
    )
    assert resp.status_code == 409
    assert "canceled" in resp.json()["detail"]


# ─── DELETE /subscriptions/{id} ───────────────────────────────────────────


def test_delete_subscription_soft_cancels(client_with_db):
    """DELETE returns the canceled row with status='canceled' + canceled_at set."""
    sub_id = uuid4()
    canceled_at = datetime.now(UTC)
    client_with_db.db_results["results"] = [
        _row(sub_id=sub_id, sub_status="canceled", canceled_at=canceled_at)
    ]
    resp = client_with_db.delete(f"/api/v1/subscriptions/{sub_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "canceled"
    assert body["canceled_at"] is not None


def test_delete_subscription_404_when_missing(client_with_db):
    client_with_db.db_results["results"] = [None]
    resp = client_with_db.delete(f"/api/v1/subscriptions/{uuid4()}")
    assert resp.status_code == 404


def test_delete_subscription_idempotent_on_already_canceled(client_with_db):
    """A second DELETE on an already-canceled row returns 200 with the
    same row (COALESCE preserves the original canceled_at)."""
    sub_id = uuid4()
    original_canceled_at = datetime.now(UTC)
    client_with_db.db_results["results"] = [
        _row(sub_id=sub_id, sub_status="canceled", canceled_at=original_canceled_at)
    ]
    resp = client_with_db.delete(f"/api/v1/subscriptions/{sub_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"
