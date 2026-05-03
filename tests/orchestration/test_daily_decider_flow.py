"""
Tests for src/orchestration/flows/daily_decider_flow.py.

- no db_conn -> empty summary, no raise
- zero clients -> empty summary
- multiple clients, mixed actions -> totals aggregated correctly
- dry_run = True: no db.execute (no insert), counts still aggregate
- one client raises -> counted as error, others succeed
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.orchestration.flows.daily_decider_flow import daily_decider_flow
from src.outreach.cadence.daily_decider import DeciderAction


def _fake_db_with_clients(client_ids: list[str]):
    db = AsyncMock()
    # First db.fetch call is _list_active_clients
    db.fetch = AsyncMock(return_value=[{"id": c} for c in client_ids])
    db.execute = AsyncMock(return_value=None)
    return db


def _action(action: str, ch: str = "email") -> DeciderAction:
    when = datetime.now(UTC) + timedelta(days=1)
    return DeciderAction(
        lead_id=f"l-{action}",
        action=action,
        channel=ch if action in ("schedule_next", "nurture") else None,
        scheduled_at=when if action in ("schedule_next", "nurture") else None,
        reason=action,
        sequence_step=1 if action == "schedule_next" else None,
    )


@pytest.mark.asyncio
async def test_missing_db_returns_empty_summary():
    summary = await daily_decider_flow(db_conn=None)
    assert summary["clients"] == 0 and summary["evaluated"] == 0


@pytest.mark.asyncio
async def test_zero_clients_returns_empty_summary():
    db = _fake_db_with_clients([])
    summary = await daily_decider_flow(db_conn=db)
    assert summary["clients"] == 0
    assert summary["evaluated"] == 0


@pytest.mark.asyncio
async def test_aggregates_actions_across_clients():
    db = _fake_db_with_clients(["c1", "c2"])

    decider = AsyncMock()
    # c1 returns [schedule_next, skip]; c2 returns [nurture, escalate]
    returns = {
        "c1": [_action("schedule_next"), _action("skip")],
        "c2": [_action("nurture"), _action("escalate")],
    }

    async def fake_evaluate(db_conn, client_id):
        return returns[client_id]

    decider.evaluate_all.side_effect = fake_evaluate

    summary = await daily_decider_flow(db_conn=db, decider=decider)
    assert summary["clients"] == 2
    assert summary["evaluated"] == 4
    assert summary["scheduled"] == 1
    assert summary["nurture"] == 1
    assert summary["skipped"] == 1
    assert summary["escalated"] == 1
    # Two INSERTs (one per schedule_next+nurture) + two BU mark_active calls
    assert db.execute.await_count == 4


@pytest.mark.asyncio
async def test_dry_run_skips_inserts_but_counts():
    db = _fake_db_with_clients(["c1"])
    decider = AsyncMock()
    decider.evaluate_all = AsyncMock(return_value=[
        _action("schedule_next"), _action("nurture"), _action("skip"),
    ])
    summary = await daily_decider_flow(db_conn=db, decider=decider, dry_run=True)
    assert summary["scheduled"] == 1
    assert summary["nurture"] == 1
    assert summary["skipped"] == 1
    assert summary["evaluated"] == 3
    assert db.execute.await_count == 0


@pytest.mark.asyncio
async def test_per_client_exception_is_contained():
    db = _fake_db_with_clients(["c1", "c2"])
    decider = AsyncMock()

    async def fake_evaluate(db_conn, client_id):
        if client_id == "c1":
            raise RuntimeError("boom")
        return [_action("schedule_next")]

    decider.evaluate_all.side_effect = fake_evaluate

    summary = await daily_decider_flow(db_conn=db, decider=decider)
    assert summary["clients"] == 2
    assert summary["errors"] >= 1
    assert summary["scheduled"] == 1
