"""
Happy-path smoke tests for src/api/routes/dashboard.py.

Mocks the AsyncSession + ClientContext deps so we can exercise the route
wiring + response shape WITHOUT hitting Supabase. Each test confirms:
  - 200 response
  - response_model shape parses
  - SQL passes ctx.client_id (multi-tenant filter is wired)

Zero paid API calls, zero real DB.
"""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_current_client, get_db_session
from src.api.routes.dashboard import router

CLIENT_ID = uuid4()


def _client_ctx() -> SimpleNamespace:
    """Stand-in ClientContext — only client_id is touched by the routes."""
    return SimpleNamespace(client_id=CLIENT_ID)


def _result_with_rows(mappings_rows: list[dict]) -> MagicMock:
    """Build a SQLAlchemy-style Result whose .mappings().all() returns rows."""
    res = MagicMock()
    res.mappings.return_value.all.return_value = mappings_rows
    res.mappings.return_value.first.return_value = mappings_rows[0] if mappings_rows else {}
    res.scalar_one_or_none.return_value = (
        mappings_rows[0]["n"] if mappings_rows and "n" in mappings_rows[0] else 0
    )
    return res


def _make_app(execute_side_effect):
    """FastAPI app with overridden dependencies + scripted db.execute outputs."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=execute_side_effect)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_client] = _client_ctx
    app.dependency_overrides[get_db_session] = lambda: db
    return app, db


# ─── /bu-hot-leads ──────────────────────────────────────────────────────────

def test_bu_hot_leads_happy_path():
    page_rows = [
        {
            "id": uuid4(), "domain": "acme.com.au", "display_name": "Acme",
            "dm_name": "Amy Boss", "dm_title": "CEO",
            "propensity_score": 88, "pipeline_stage": 7,
            "has_email": True, "has_mobile": False,
        },
    ]
    total_row = [{"n": 42}]
    execute_returns = iter([
        _result_with_rows(page_rows),
        _result_with_rows(total_row),
    ])

    async def side_effect(_sql, _params=None):
        return next(execute_returns)

    app, db = _make_app(side_effect)
    res = TestClient(app).get("/dashboard/bu-hot-leads")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 42
    assert body["items"][0]["company"] == "Acme"
    assert body["items"][0]["has_email"] is True

    # Multi-tenant gate: every SQL call passed ctx.client_id.
    for call in db.execute.await_args_list:
        params = call.args[1] if len(call.args) > 1 else {}
        assert params.get("client_id") == CLIENT_ID, "missing client_id in params"


# ─── /bu-stats ──────────────────────────────────────────────────────────────

def test_bu_stats_happy_path():
    stats_row = [{
        "total_businesses": 100,
        "with_email": 60,
        "with_mobile": 25,
        "enriched_24h": 12,
    }]
    bdm_row = [{"n": 73}]
    execute_returns = iter([
        _result_with_rows(stats_row),
        _result_with_rows(bdm_row),
    ])

    async def side_effect(_sql, _params=None):
        return next(execute_returns)

    app, db = _make_app(side_effect)
    res = TestClient(app).get("/dashboard/bu-stats")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "total_businesses":      100,
        "businesses_with_email": 60,
        "businesses_with_mobile": 25,
        "total_bdms":            73,
        "enriched_last_24h":     12,
    }
    for call in db.execute.await_args_list:
        params = call.args[1] if len(call.args) > 1 else {}
        assert params.get("client_id") == CLIENT_ID


# ─── /bu-funnel ─────────────────────────────────────────────────────────────

def test_bu_funnel_returns_all_12_stages():
    funnel_row = [
        {"stage": 1, "n": 50},
        {"stage": 6, "n": 12},
        {"stage": 11, "n": 4},
    ]
    execute_returns = iter([_result_with_rows(funnel_row)])

    async def side_effect(_sql, _params=None):
        return next(execute_returns)

    app, db = _make_app(side_effect)
    res = TestClient(app).get("/dashboard/bu-funnel")
    assert res.status_code == 200
    body = res.json()
    # 12 stages (0..11) — quality fix A added stage 0 'Queued'.
    assert len(body["stages"]) == 12
    by_stage = {s["stage"]: s for s in body["stages"]}
    assert by_stage[0]["label"] == "Queued"
    assert by_stage[1]["count"] == 50
    assert by_stage[6]["count"] == 12
    assert by_stage[11]["count"] == 4
    assert body["total"] == 66

    params = db.execute.await_args.args[1]
    assert params.get("client_id") == CLIENT_ID


# ─── /bu-activity ───────────────────────────────────────────────────────────

def test_bu_activity_merges_enrichment_and_outreach():
    enrich_rows = [
        {
            "id": uuid4(), "domain": "acme.com.au", "display_name": "Acme",
            "last_enriched_at": datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
            "pipeline_stage": 7, "enrichment_cost_usd": 0.18,
        },
    ]
    outreach_rows = [
        {
            "id": uuid4(), "channel": "email",
            "sent_at": datetime(2026, 4, 25, 13, 0, tzinfo=UTC),
            "final_outcome": "delivered",
            "domain": "beta.com.au",  # quality fix D: domain joined in
        },
    ]
    execute_returns = iter([
        _result_with_rows(enrich_rows),
        _result_with_rows(outreach_rows),
    ])

    async def side_effect(_sql, _params=None):
        return next(execute_returns)

    app, db = _make_app(side_effect)
    res = TestClient(app).get("/dashboard/bu-activity?limit=10")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 2
    # Outreach is later → first after desc sort.
    assert body["items"][0]["kind"] == "outreach"
    assert body["items"][0]["domain"] == "beta.com.au"  # quality fix D
    assert body["items"][1]["kind"] == "enrichment"
    assert body["items"][1]["domain"] == "acme.com.au"

    for call in db.execute.await_args_list:
        params = call.args[1] if len(call.args) > 1 else {}
        assert params.get("client_id") == CLIENT_ID


def test_bu_activity_handles_outreach_table_missing():
    """When cis_outreach_outcomes raises (e.g. dev DB), endpoint still
    returns enrichment rows — quality fix C ensures the error is logged."""
    enrich_rows = [
        {
            "id": uuid4(), "domain": "acme.com.au", "display_name": "Acme",
            "last_enriched_at": datetime(2026, 4, 25, tzinfo=UTC),
            "pipeline_stage": 5, "enrichment_cost_usd": None,
        },
    ]

    @pytest.fixture()
    def _unused():  # noqa: ARG001
        ...

    call_count = {"i": 0}

    async def side_effect(_sql, _params=None):
        call_count["i"] += 1
        if call_count["i"] == 1:
            return _result_with_rows(enrich_rows)
        raise RuntimeError("relation cis_outreach_outcomes does not exist")

    app, _db = _make_app(side_effect)
    res = TestClient(app).get("/dashboard/bu-activity")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["kind"] == "enrichment"
