"""Tests for BrightDataGMBClient — Directive #260"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call
import httpx

from src.clients.bright_data_gmb_client import BrightDataGMBClient, COST_PER_RECORD_USD


def make_client():
    return BrightDataGMBClient(api_key="test-key")


def make_http_response(status=200, json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json = MagicMock(return_value=json_data or {})
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


@pytest.mark.asyncio
async def test_search_returns_mapped_result():
    """search_by_name returns mapped GMB dict on success."""
    client = make_client()
    raw_result = {
        "place_id": "ChIJ123",
        "category": "Marketing Agency",
        "rating": 4.8,
        "reviews": 42,
        "working_hours": {"monday": "9am-5pm"},
        "claimed": True,
        "url": "https://maps.google.com/...",
        "address": "123 Main St, Sydney NSW 2000",
    }
    with patch.object(client, "_trigger_snapshot", new_callable=AsyncMock, return_value="snap123"):
        with patch.object(
            client, "_poll_and_fetch", new_callable=AsyncMock, return_value=[raw_result]
        ):
            result = await client.search_by_name("Acme Marketing")
    assert result is not None
    assert result["gmb_place_id"] == "ChIJ123"
    assert result["gmb_rating"] == 4.8
    assert result["gmb_review_count"] == 42
    assert result["gmb_claimed"] is True


@pytest.mark.asyncio
async def test_search_returns_none_when_no_results():
    """search_by_name returns None when BD returns empty list."""
    client = make_client()
    with patch.object(client, "_trigger_snapshot", new_callable=AsyncMock, return_value="snap123"):
        with patch.object(client, "_poll_and_fetch", new_callable=AsyncMock, return_value=[]):
            result = await client.search_by_name("Unknown Business")
    assert result is None


@pytest.mark.asyncio
async def test_search_returns_none_when_trigger_fails():
    """search_by_name returns None when snapshot trigger fails."""
    client = make_client()
    with patch.object(client, "_trigger_snapshot", new_callable=AsyncMock, return_value=None):
        result = await client.search_by_name("Acme Marketing")
    assert result is None


@pytest.mark.asyncio
async def test_cost_tracking_increments():
    """total_cost_usd increments by COST_PER_RECORD_USD per successful result."""
    client = make_client()
    raw = {"place_id": "ChIJ123", "category": "Agency"}
    with patch.object(client, "_trigger_snapshot", new_callable=AsyncMock, return_value="snap1"):
        with patch.object(client, "_poll_and_fetch", new_callable=AsyncMock, return_value=[raw]):
            await client.search_by_name("Biz 1")
    assert client.total_cost_usd == COST_PER_RECORD_USD
    assert client._records_fetched == 1


@pytest.mark.asyncio
async def test_poll_returns_none_on_failed_status():
    """_poll_and_fetch returns None when snapshot status is 'failed'."""
    client = make_client()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"status": "failed"})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    result = await client._poll_and_fetch(mock_client, "snap_failed")
    assert result is None
