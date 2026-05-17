"""
Tests for src/api/routes/strangler.py — KEI-180 Strangler Fig routing layer.

Uses FastAPI TestClient + dependency overrides to avoid real DB/network calls.
Covers both routing paths, fail-open behaviour, logging, and error cases.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_db_session
from src.api.routes.strangler import router

# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

TENANT_A = uuid4()
TENANT_B = uuid4()


def _make_app(use_model_b: bool):
    """Return a TestClient whose DB dependency returns use_model_b for any tenant."""
    app = FastAPI()
    app.include_router(router)

    async def _fake_db():
        db = AsyncMock()
        # Simulate fetchone() returning (use_model_b,) for a found tenant
        row_mock = MagicMock()
        row_mock.fetchone.return_value = (use_model_b,)
        db.execute = AsyncMock(return_value=row_mock)
        db.commit = AsyncMock()
        yield db

    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_routes_to_model_a_when_use_model_b_false():
    """use_model_b=False → _route_model_a called, _route_model_b NOT called."""
    client = _make_app(use_model_b=False)
    with (
        patch("src.api.routes.strangler._route_model_a", new_callable=AsyncMock) as mock_a,
        patch("src.api.routes.strangler._route_model_b", new_callable=AsyncMock) as mock_b,
        patch("src.api.routes.strangler._log_route_decision", new_callable=AsyncMock),
    ):
        mock_a.return_value = {"model": "a"}
        resp = client.post(
            "/api/strangler/outreach",
            json={"tenant_id": str(TENANT_A), "payload": {}},
        )
    assert resp.status_code == 200
    assert resp.json()["route"] == "model_a"
    mock_a.assert_called_once()
    mock_b.assert_not_called()


def test_routes_to_model_b_when_use_model_b_true():
    """use_model_b=True → _route_model_b called once."""
    client = _make_app(use_model_b=True)
    with (
        patch("src.api.routes.strangler._route_model_b", new_callable=AsyncMock) as mock_b,
        patch("src.api.routes.strangler._route_model_a", new_callable=AsyncMock) as mock_a,
        patch("src.api.routes.strangler._log_route_decision", new_callable=AsyncMock),
    ):
        mock_b.return_value = {"model": "b"}
        resp = client.post(
            "/api/strangler/outreach",
            json={"tenant_id": str(TENANT_B), "payload": {}},
        )
    assert resp.status_code == 200
    assert resp.json()["route"] == "model_b"
    mock_b.assert_called_once()
    mock_a.assert_not_called()


def test_logs_route_decision_with_tenant_and_latency():
    """_log_route_decision is called with (tenant_id, route_str, positive latency_ms)."""
    client = _make_app(use_model_b=False)
    with (
        patch("src.api.routes.strangler._route_model_a", new_callable=AsyncMock),
        patch("src.api.routes.strangler._log_route_decision", new_callable=AsyncMock) as mock_log,
    ):
        resp = client.post(
            "/api/strangler/outreach",
            json={"tenant_id": str(TENANT_A), "payload": {}},
        )
    assert resp.status_code == 200
    mock_log.assert_called_once()
    args = mock_log.call_args[0]  # positional: (tenant_id, route, latency_ms, db)
    tenant_id_arg, route_arg, latency_arg, _ = args
    assert str(tenant_id_arg) == str(TENANT_A)
    assert route_arg in ("model_a", "model_b", "model_b_failover")
    assert isinstance(latency_arg, float)
    assert latency_arg >= 0


def test_fail_open_on_dispatcher_5xx():
    """_route_model_b raises → falls back to _route_model_a, route='model_b_failover'."""
    client = _make_app(use_model_b=True)
    with (
        patch(
            "src.api.routes.strangler._route_model_b",
            new_callable=AsyncMock,
            side_effect=Exception("dispatcher 500"),
        ),
        patch("src.api.routes.strangler._route_model_a", new_callable=AsyncMock) as mock_a,
        patch("src.api.routes.strangler._log_route_decision", new_callable=AsyncMock),
    ):
        mock_a.return_value = {"model": "a"}
        resp = client.post(
            "/api/strangler/outreach",
            json={"tenant_id": str(TENANT_B), "payload": {}},
        )
    assert resp.status_code == 200
    assert resp.json()["route"] == "model_b_failover"
    mock_a.assert_called_once()


def test_missing_tenant_id_returns_400():
    """Payload without tenant_id → 422 (FastAPI validation error)."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.post("/api/strangler/outreach", json={"payload": {}})
    assert resp.status_code == 422


def test_unknown_tenant_returns_404():
    """DB lookup returns None (tenant not found) → 404."""
    app = FastAPI()
    app.include_router(router)

    async def _missing_db():
        db = AsyncMock()
        row_mock = MagicMock()
        row_mock.fetchone.return_value = None  # not found
        db.execute = AsyncMock(return_value=row_mock)
        db.commit = AsyncMock()
        yield db

    app.dependency_overrides[get_db_session] = _missing_db
    client = TestClient(app)
    resp = client.post(
        "/api/strangler/outreach",
        json={"tenant_id": str(uuid4()), "payload": {}},
    )
    assert resp.status_code == 404


def test_latency_delta_under_50ms_for_in_process_routing():
    """Routing decision overhead (both paths mocked) must be <50ms wall-clock."""
    client = _make_app(use_model_b=False)
    with (
        patch("src.api.routes.strangler._route_model_a", new_callable=AsyncMock),
        patch("src.api.routes.strangler._log_route_decision", new_callable=AsyncMock),
    ):
        t0 = time.perf_counter()
        resp = client.post(
            "/api/strangler/outreach",
            json={"tenant_id": str(TENANT_A), "payload": {}},
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

    assert resp.status_code == 200
    assert elapsed_ms < 50, f"Routing took {elapsed_ms:.1f}ms — over 50ms budget"
