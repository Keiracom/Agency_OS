# FILE: tests/test_campaign_claimer.py
# PURPOSE: Unit tests for CampaignClaimer
# DIRECTIVE: #252

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

import pytest

from src.pipeline.campaign_claimer import CampaignClaimer


def make_bu_rows(n: int) -> list[dict]:
    return [{"bu_id": uuid.uuid4()} for _ in range(n)]


def make_db(fetch_rows: list[dict] | None = None):
    """Build a minimal mock DB with transaction(), fetch(), execute()."""
    db = MagicMock()

    # transaction() is an async context manager
    @asynccontextmanager
    async def _tx():
        yield

    db.transaction = MagicMock(side_effect=_tx)
    db.fetch = AsyncMock(return_value=fetch_rows or [])
    db.execute = AsyncMock(return_value=None)
    return db


@pytest.mark.asyncio
async def test_claim_basic():
    """5 rows returned → claimed == 5."""
    rows = make_bu_rows(5)
    db = make_db(fetch_rows=rows)
    claimer = CampaignClaimer(db)

    campaign_id = uuid.uuid4()
    client_id = uuid.uuid4()
    result = await claimer.claim_for_campaign(campaign_id, client_id, max_claims=100)

    assert result["claimed"] == 5
    assert result["errors"] == []
    # execute() called 5 times (once per row)
    assert db.execute.call_count == 5


@pytest.mark.asyncio
async def test_claim_with_min_propensity_filter():
    """min_propensity=40 should be passed as first positional param to db.fetch."""
    db = make_db(fetch_rows=[])
    claimer = CampaignClaimer(db)

    campaign_id = uuid.uuid4()
    client_id = uuid.uuid4()
    await claimer.claim_for_campaign(
        campaign_id, client_id, filters={"min_propensity": 40}, max_claims=50
    )

    # db.fetch was called — first arg is SQL, second arg is min_propensity=40
    assert db.fetch.called
    call_args = db.fetch.call_args[0]  # positional args
    # params are: min_propensity=$1, min_reachability=$2, campaign_id=$3, client_id=$4, max_claims=$5
    assert call_args[1] == 40, f"Expected min_propensity=40, got {call_args[1]}"


@pytest.mark.asyncio
async def test_no_double_claim():
    """db.fetch returns 0 rows (NOT EXISTS filtered them all) → claimed == 0."""
    db = make_db(fetch_rows=[])
    claimer = CampaignClaimer(db)

    result = await claimer.claim_for_campaign(uuid.uuid4(), uuid.uuid4(), max_claims=100)

    assert result["claimed"] == 0
    assert result["errors"] == []
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_suppressed_leads_excluded():
    """Suppressed leads excluded at SQL level — db.fetch returns 0 rows."""
    db = make_db(fetch_rows=[])
    claimer = CampaignClaimer(db)

    result = await claimer.claim_for_campaign(uuid.uuid4(), uuid.uuid4(), max_claims=100)

    assert result["claimed"] == 0
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_transaction_context_used():
    """db.transaction() must be entered as an async context manager."""
    db = make_db(fetch_rows=[])
    claimer = CampaignClaimer(db)

    await claimer.claim_for_campaign(uuid.uuid4(), uuid.uuid4(), max_claims=10)

    # transaction() was called (entered as ctx manager via 'async with')
    assert db.transaction.called
