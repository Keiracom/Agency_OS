# FILE: tests/test_stage1_discovery.py
# PURPOSE: Tests for Stage1Discovery — GMB discovery orchestration
# DIRECTIVE: #249

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.stage1_discovery import Stage1Discovery
from src.clients.dfs_gmaps_client import COST_PER_SEARCH_AUD, DFSInvalidLocationError


def make_businesses(count: int) -> list[dict]:
    return [
        {"gmb_place_id": f"place_{i}", "display_name": f"Biz {i}", "state": "NSW"}
        for i in range(count)
    ]


def make_suburbs(count: int) -> list[dict]:
    return [
        {
            "lat": -33.8688 + i * 0.01,
            "lng": 151.2093,
            "suburb": f"Suburb{i}",
            "state": "NSW",
        }
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_discovery_inserts_new_dedupes_existing():
    """Test 1: first 2 businesses are duplicates, remaining 3 are new."""
    dfs_client = MagicMock()
    dfs_client.estimated_cost_aud = Decimal("0")
    dfs_client.discover_by_coordinates = AsyncMock(return_value=make_businesses(5))

    suburb_loader = MagicMock()
    suburb_loader.get_suburbs_by_state.return_value = make_suburbs(1)

    db = MagicMock()
    test_uuid = str(uuid.uuid4())

    # Call pattern per item:
    #   fetchval(SELECT 1 dedup check) → 1 or None
    #   fetchval(INSERT ... RETURNING id) → uuid (only if dedup returned None)
    # place_0: dedup→1 (dup), no insert
    # place_1: dedup→1 (dup), no insert
    # place_2: dedup→None (new), insert→uuid
    # place_3: dedup→None (new), insert→uuid
    # place_4: dedup→None (new), insert→uuid
    db.fetchval = AsyncMock(
        side_effect=[1, 1, None, test_uuid, None, test_uuid, None, test_uuid]
    )
    db.execute = AsyncMock(return_value="UPDATE 3")

    stage1 = Stage1Discovery(dfs_client, suburb_loader, db)
    result = await stage1.run(
        {
            "category": "plumber",
            "state": "NSW",
            "campaign_id": str(uuid.uuid4()),
            "client_id": str(uuid.uuid4()),
        }
    )

    assert result["discovered"] == 3
    assert result["duplicates_skipped"] == 2


@pytest.mark.asyncio
async def test_spend_cap_stops_after_threshold():
    """Test 2: spend cap of 0.005 AUD stops iteration after 1 suburb (cost 0.003 each)."""
    dfs_client = MagicMock()
    dfs_client.estimated_cost_aud = Decimal("0")

    call_count = [0]

    async def discover_with_cost(*args, **kwargs):
        call_count[0] += 1
        dfs_client.estimated_cost_aud = COST_PER_SEARCH_AUD * call_count[0]
        return [{"gmb_place_id": f"place_{call_count[0]}", "display_name": "Biz"}]

    dfs_client.discover_by_coordinates = AsyncMock(side_effect=discover_with_cost)

    suburb_loader = MagicMock()
    suburb_loader.get_suburbs_by_state.return_value = make_suburbs(5)

    db = MagicMock()
    test_uuid = str(uuid.uuid4())
    # Alternating: dedup→None (new), insert→uuid, repeated enough times
    db.fetchval = AsyncMock(side_effect=[None, test_uuid] * 10)
    db.execute = AsyncMock(return_value="UPDATE 0")

    stage1 = Stage1Discovery(dfs_client, suburb_loader, db)
    result = await stage1.run(
        {
            "category": "plumber",
            "state": "NSW",
            "campaign_id": str(uuid.uuid4()),
            "client_id": str(uuid.uuid4()),
            "daily_spend_cap_aud": 0.005,
        }
    )

    assert result["suburbs_searched"] < 5
    assert "spend_cap_reached" in str(result["errors"])


@pytest.mark.asyncio
async def test_abr_match_populates_abn():
    """Test 3: after inserting a new BU, the ABR execute returns UPDATE 1."""
    dfs_client = MagicMock()
    dfs_client.estimated_cost_aud = Decimal("0")
    dfs_client.discover_by_coordinates = AsyncMock(
        return_value=[{"gmb_place_id": "place_abc", "display_name": "Biz ABC"}]
    )

    suburb_loader = MagicMock()
    suburb_loader.get_suburbs_by_state.return_value = make_suburbs(1)

    db = MagicMock()
    test_uuid = str(uuid.uuid4())
    # dedup → None (new), insert → uuid
    db.fetchval = AsyncMock(side_effect=[None, test_uuid])
    db.execute = AsyncMock(return_value="UPDATE 1")

    stage1 = Stage1Discovery(dfs_client, suburb_loader, db)
    result = await stage1.run(
        {
            "category": "plumber",
            "state": "NSW",
            "campaign_id": str(uuid.uuid4()),
            "client_id": str(uuid.uuid4()),
        }
    )

    assert result["abr_matched"] == 1


@pytest.mark.asyncio
async def test_error_resilience_continues_past_failure():
    """Test 4: DFS raises Exception on suburb 2; other 4 suburbs continue successfully."""
    dfs_client = MagicMock()
    dfs_client.estimated_cost_aud = Decimal("0")

    call_idx = [0]

    async def discover_with_failure(*args, **kwargs):
        idx = call_idx[0]
        call_idx[0] += 1
        if idx == 2:
            raise Exception("timeout")
        return [{"gmb_place_id": f"place_{idx}", "display_name": f"Biz {idx}"}]

    dfs_client.discover_by_coordinates = AsyncMock(side_effect=discover_with_failure)

    suburb_loader = MagicMock()
    suburb_loader.get_suburbs_by_state.return_value = make_suburbs(5)

    db = MagicMock()
    test_uuid = str(uuid.uuid4())
    # 4 successful suburbs × (dedup→None, insert→uuid) = 8 calls
    db.fetchval = AsyncMock(side_effect=[None, test_uuid] * 10)
    db.execute = AsyncMock(return_value="UPDATE 0")

    stage1 = Stage1Discovery(dfs_client, suburb_loader, db)
    result = await stage1.run(
        {
            "category": "plumber",
            "state": "NSW",
            "campaign_id": str(uuid.uuid4()),
            "client_id": str(uuid.uuid4()),
        }
    )

    assert result["suburbs_searched"] == 4
    assert len(result["errors"]) == 1
    assert result["discovered"] >= 4
