"""
Tests for src/orchestration/flows/hourly_cadence_flow.py.

Dry-run of the flow with a mocked asyncpg-like connection and a mocked
dispatcher. Verifies:
- empty pending -> zero summary
- dry_run=True fetches but skips dispatch + status update
- mixed results (sent/skipped/failed) roll up into correct summary
- one touch raising does not break the rest
- per-touch UPDATE scheduled_touches fires for each completed touch
- missing db_conn -> zero summary, no raise
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.orchestration.flows.hourly_cadence_flow import hourly_cadence_flow
from src.outreach.dispatcher import DispatchResult


def _fake_db(touches: list[dict]):
    db = AsyncMock()
    db.fetch = AsyncMock(return_value=[dict(t) for t in touches])
    db.execute = AsyncMock(return_value=None)
    return db


def _touch(i: int, channel="email") -> dict:
    return {
        "id": f"t{i}", "channel": channel,
        "prospect": {"email": f"lead{i}@x.com"},
        "client_id": "c1", "lead_id": f"l{i}", "activity_id": f"a{i}",
        "campaign_id": None, "content": {}, "sequence_step": 1,
        "scheduled_at": None,
    }


@pytest.mark.asyncio
async def test_flow_empty_pending_zero_summary():
    db = _fake_db([])
    dispatcher = AsyncMock()
    summary = await hourly_cadence_flow(db_conn=db, dispatcher=dispatcher)
    assert summary == {"total": 0, "sent": 0, "skipped": 0, "failed": 0}
    dispatcher.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_flow_dry_run_skips_dispatch():
    db = _fake_db([_touch(1), _touch(2)])
    dispatcher = AsyncMock()
    summary = await hourly_cadence_flow(db_conn=db, dispatcher=dispatcher, dry_run=True)
    assert summary == {"total": 2, "sent": 0, "skipped": 0, "failed": 0}
    dispatcher.dispatch.assert_not_called()
    # no UPDATE fired in dry-run
    assert db.execute.await_count == 0


@pytest.mark.asyncio
async def test_flow_mixed_results_roll_up():
    touches = [_touch(1), _touch(2, channel="linkedin"), _touch(3, channel="voice")]
    db = _fake_db(touches)

    dispatcher = AsyncMock()
    outcomes = {
        "t1": DispatchResult(status="sent", channel="email", provider_message_id="m1"),
        "t2": DispatchResult(status="skipped", channel="linkedin", reason="timing:weekend"),
        "t3": DispatchResult(status="failed", channel="voice", reason="provider_error"),
    }

    async def fake_dispatch(touch):
        return outcomes[touch["id"]]

    dispatcher.dispatch.side_effect = fake_dispatch

    summary = await hourly_cadence_flow(db_conn=db, dispatcher=dispatcher)
    assert summary == {"total": 3, "sent": 1, "skipped": 1, "failed": 1}
    # One UPDATE per touch
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_flow_per_touch_exception_is_contained():
    touches = [_touch(1), _touch(2)]
    db = _fake_db(touches)

    dispatcher = AsyncMock()

    async def fake_dispatch(touch):
        if touch["id"] == "t1":
            raise RuntimeError("kaboom")
        return DispatchResult(status="sent", channel="email")

    dispatcher.dispatch.side_effect = fake_dispatch

    summary = await hourly_cadence_flow(db_conn=db, dispatcher=dispatcher)
    # The raising touch counts as failed; the other succeeds
    assert summary["total"] == 2
    assert summary["sent"] == 1
    assert summary["failed"] == 1


@pytest.mark.asyncio
async def test_flow_missing_db_returns_zero():
    dispatcher = AsyncMock()
    summary = await hourly_cadence_flow(db_conn=None, dispatcher=dispatcher)
    assert summary == {"total": 0, "sent": 0, "skipped": 0, "failed": 0}
    dispatcher.dispatch.assert_not_called()
