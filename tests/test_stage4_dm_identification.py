# FILE: tests/test_stage4_dm_identification.py
# PURPOSE: Tests for Stage4DMIdentification — full flow, spend cap, propensity gate
# DIRECTIVE: #250

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.clients.dfs_serp_client import COST_PER_SERP_AUD
from src.pipeline.stage4_dm_identification import Stage4DMIdentification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stage4(serp_mock=None, daily_spend_cap_aud: float = 10.0):
    db = MagicMock()
    db.fetch = AsyncMock()
    db.execute = AsyncMock()
    serp = serp_mock or MagicMock()
    serp.find_decision_maker = AsyncMock()
    serp.estimated_cost_aud = Decimal("0")
    serp.queries_made = 0
    return Stage4DMIdentification(dfs_serp_client=serp, db=db), db, serp


def _make_row(row_id: str, propensity_score: int) -> MagicMock:
    row = MagicMock()
    data = {
        "id": row_id,
        "display_name": f"Business {row_id}",
        "suburb": "Sydney",
        "state": "NSW",
        "propensity_score": propensity_score,
    }
    row.__getitem__ = lambda self, k, _d=data: _d[k]
    return row


def _dm_result(name: str = "John Doe", title: str = "CEO") -> dict:
    return {
        "dm_name": name,
        "dm_title": title,
        "dm_linkedin_url": f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}",
        "dm_source": "dfs_serp",
        "dm_confidence": Decimal("0.90"),
    }


# ---------------------------------------------------------------------------
# Test 1: Full flow — dm_found, dm_not_found, skipped_below_threshold
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_flow_dm_found_not_found_skipped():
    stage4, db, serp = _make_stage4()

    rows = [
        _make_row("id-1", 75),  # above threshold → DM found
        _make_row("id-2", 60),  # above threshold → DM not found
        _make_row("id-3", 20),  # below threshold → skipped
    ]
    db.fetch.return_value = rows

    # serp: first call returns DM, second returns None
    dm_found_result = _dm_result("John Doe", "CEO")
    serp.find_decision_maker.side_effect = [dm_found_result, None]

    # Update estimated_cost_aud after each call to avoid spend cap
    serp.estimated_cost_aud = Decimal("0")

    result = await stage4.run(propensity_threshold=40, batch_size=3)

    assert result["dm_found"] == 1, f"Expected dm_found=1, got {result['dm_found']}"
    assert result["dm_not_found"] == 1, f"Expected dm_not_found=1, got {result['dm_not_found']}"
    assert result["skipped_below_threshold"] == 1, (
        f"Expected skipped_below_threshold=1, got {result['skipped_below_threshold']}"
    )


# ---------------------------------------------------------------------------
# Test 2: Spend cap stops queries before they start
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_spend_cap_stops_queries():
    stage4, db, serp = _make_stage4()

    # Set spend cap below 1 query cost
    # COST_PER_SERP_AUD = 0.00930; cap = 0.005 → cap + cost > cap → first query blocked
    daily_spend_cap_aud = 0.005

    rows = [
        _make_row("id-1", 80),
        _make_row("id-2", 80),
        _make_row("id-3", 80),
    ]
    db.fetch.return_value = rows

    # estimated_cost_aud starts at 0, but 0 + 0.00930 > 0.005 → immediately capped
    serp.estimated_cost_aud = Decimal("0")

    result = await stage4.run(
        propensity_threshold=40,
        batch_size=3,
        daily_spend_cap_aud=daily_spend_cap_aud,
    )

    assert result["attempted"] == 0, (
        f"Expected 0 attempted queries (spend cap), got {result['attempted']}"
    )
    assert len(result["errors"]) > 0, "Expected spend_cap_reached error in results"
    # Verify at least one error has spend_cap_reached reason
    reasons = [e.get("reason") for e in result["errors"]]
    assert "spend_cap_reached" in reasons, f"Expected spend_cap_reached in errors: {result['errors']}"


# ---------------------------------------------------------------------------
# Test 3: Propensity gate limits queries to above-threshold rows only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_propensity_gate_limits_queries():
    stage4, db, serp = _make_stage4()

    rows = [
        _make_row("id-1", 80),  # above threshold
        _make_row("id-2", 80),  # above threshold
        _make_row("id-3", 10),  # below threshold
        _make_row("id-4", 10),  # below threshold
        _make_row("id-5", 10),  # below threshold
    ]
    db.fetch.return_value = rows

    # serp returns None for both above-threshold calls
    serp.find_decision_maker.return_value = None
    serp.estimated_cost_aud = Decimal("0")

    result = await stage4.run(propensity_threshold=40, batch_size=5)

    assert serp.find_decision_maker.call_count == 2, (
        f"Expected exactly 2 SERP calls (only above threshold), "
        f"got {serp.find_decision_maker.call_count}"
    )
    assert result["skipped_below_threshold"] == 3, (
        f"Expected 3 skipped, got {result['skipped_below_threshold']}"
    )
