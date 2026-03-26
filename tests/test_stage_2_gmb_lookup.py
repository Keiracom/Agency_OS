"""Tests for Stage2GMBLookup — Directive #260"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.pipeline.stage_2_gmb_lookup import Stage2GMBLookup, PIPELINE_STAGE_S2


def make_gmb_client(return_data=None):
    """Mock BrightDataGMBClient."""
    client = MagicMock()
    client.total_cost_usd = 0.001
    client.search_by_name = AsyncMock(return_value=return_data)
    return client


def make_row(domain="example.com.au", gmb_place_id=None, row_id="uuid-1"):
    row = MagicMock()
    row.__getitem__ = lambda self, k: {
        "id": row_id,
        "domain": domain,
        "gmb_place_id": gmb_place_id,
    }[k]
    return row


def make_conn(rows=None):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows or [])
    conn.execute = AsyncMock(return_value=None)
    conn.fetchrow = AsyncMock(return_value=None)
    return conn


def make_stage(gmb_data=None, rows=None):
    client = make_gmb_client(gmb_data)
    conn = make_conn(rows)
    stage = Stage2GMBLookup(client, conn, delay=0)
    return stage, client, conn


@pytest.mark.asyncio
async def test_enriches_s1_domains_with_gmb_data():
    """run() updates BU with GMB data when found."""
    gmb_result = {"gmb_place_id": "ChIJ123", "gmb_category": "Marketing Agency",
                  "gmb_rating": 4.8, "gmb_review_count": 42, "address": "123 Main St, Sydney NSW 2000"}
    rows = [make_row("acme-marketing.com.au")]
    stage, client, conn = make_stage(gmb_result, rows)
    result = await stage.run()
    assert result["enriched"] == 1
    assert result["no_gmb_found"] == 0
    conn.execute.assert_called_once()
    update_sql = conn.execute.call_args[0][0]
    assert "UPDATE" in update_sql
    assert "gmb_place_id" in update_sql


@pytest.mark.asyncio
async def test_handles_no_gmb_found():
    """run() progresses domain to stage 2 even with no GMB match."""
    rows = [make_row("no-gmb-here.com.au")]
    stage, client, conn = make_stage(None, rows)
    result = await stage.run()
    assert result["enriched"] == 0
    assert result["no_gmb_found"] == 1
    conn.execute.assert_called_once()
    update_sql = conn.execute.call_args[0][0]
    assert "pipeline_stage" in update_sql


@pytest.mark.asyncio
async def test_skips_already_enriched_domains():
    """Rows with existing gmb_place_id are counted as already_enriched."""
    rows = [make_row("already-done.com.au", gmb_place_id="ChIJexisting")]
    stage, client, conn = make_stage(rows=rows)
    result = await stage.run()
    assert result["already_enriched"] == 1
    assert result["enriched"] == 0
    client.search_by_name.assert_not_called()


@pytest.mark.asyncio
async def test_extracts_suburb_and_state_from_address():
    """_lookup_and_update writes address_source='gmb' on GMB match."""
    gmb_result = {"gmb_place_id": "ChIJ999", "address": "45 Church St, Parramatta NSW 2150"}
    rows = [make_row("test-biz.com.au")]
    stage, client, conn = make_stage(gmb_result, rows)
    await stage.run()
    update_sql = conn.execute.call_args[0][0]
    assert "address_source" in update_sql


@pytest.mark.asyncio
async def test_updates_pipeline_stage_to_2():
    """pipeline_stage is set to 2 after S2 processes the row."""
    rows = [make_row("some-biz.com.au")]
    stage, client, conn = make_stage(None, rows)
    await stage.run()
    args = conn.execute.call_args[0]
    assert PIPELINE_STAGE_S2 in args  # pipeline_stage=2 in positional args


@pytest.mark.asyncio
async def test_deduplicates_by_gmb_place_id():
    """run_single returns 'not_found' for unknown domain."""
    conn = make_conn()
    conn.fetchrow = AsyncMock(return_value=None)
    stage = Stage2GMBLookup(make_gmb_client(), conn, delay=0)
    result = await stage.run_single("unknown.com.au")
    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_respects_batch_size():
    """run() passes batch_size LIMIT to the DB query."""
    stage, _, conn = make_stage()
    await stage.run(batch_size=10)
    fetch_sql = conn.fetch.call_args[0][0]
    assert "LIMIT" in fetch_sql
    assert conn.fetch.call_args[0][1] == 10


@pytest.mark.asyncio
async def test_returns_correct_counts():
    """run() with mix of enriched/no_gmb/already_enriched."""
    rows = [
        make_row("found.com.au"),
        make_row("notfound.com.au"),
        make_row("existing.com.au", gmb_place_id="ChIJexist"),
    ]
    conn = make_conn(rows)
    call_count = [0]
    async def side_effect(name, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"gmb_place_id": "ChIJnew"}
        return None
    client = MagicMock()
    client.total_cost_usd = 0.001
    client.search_by_name = AsyncMock(side_effect=side_effect)
    stage = Stage2GMBLookup(client, conn, delay=0)
    result = await stage.run()
    assert result["enriched"] == 1
    assert result["no_gmb_found"] == 1
    assert result["already_enriched"] == 1
