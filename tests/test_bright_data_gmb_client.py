"""Tests for BrightDataGMBClient — Directive #260"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.bright_data_gmb_client import COST_PER_RECORD_USD, BrightDataGMBClient


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


# ── Live smoke (Phase 1a pre-cohort sweep) ────────────────────────────────────
# Closes audit checklist item #7 (template § C) for bright_data_gmb_client.py.
# Real BD dataset trigger + poll + fetch — costs per-record on the result set.
# Marked @pytest.mark.live so default `pytest -m "not live"` skips it.

import os as _os


@pytest.mark.live
@pytest.mark.asyncio
async def test_bd_gmb_live_smoke():
    """Real BD GMB dataset trigger against a known-stable AU chain location.

    Asserts the snapshot completes and the mapped row carries the keys we
    rely on downstream (place_id, name, address). Failure here indicates
    BD URL/auth/contract drift, NOT a behaviour bug — mocks cover behaviour.

    Cost: per-record on the result set. Result count is bounded by BD's
    discover_new behaviour for the keyword; AU chain locations typically
    return single-digit rows. Budget: ≤ ~$0.50 AUD per run.
    """
    if not _os.environ.get("BRIGHTDATA_API_KEY"):
        pytest.skip("BRIGHTDATA_API_KEY env var unset; live smoke skipped")

    # Use env override to swap the target for ad-hoc debugging.
    target = _os.environ.get(
        "BD_GMB_LIVE_SMOKE_TARGET",
        # Major AU chain — stable permanent listing, dense GMB coverage.
        # (Atlassian Sydney was the dispatch suggestion but returned 0 rows
        # on the discover_new dataset; McDonald's verified to return rows
        # consistently within ~90s poll on first verification run.)
        "McDonald's Sydney",
    )

    client = BrightDataGMBClient()
    result = await client.search_by_name(target, country="Australia")
    # `search_by_name` returns None on no-match. For a known-stable target
    # that's a contract regression, fail loudly.
    assert result is not None, (
        f"BD GMB returned None for target={target!r} — likely URL/auth/"
        "dataset-contract drift (mocks would not catch this)"
    )
    # Dataset shape we depend on downstream — `_map_item` returns rows
    # keyed gmb_place_id / gmb_category / address / phone / lat / lng.
    # gmb_place_id is required (mapper returns None without it); address
    # is the field downstream BU writes consume for matching.
    for required_key in ("gmb_place_id", "address"):
        assert result.get(required_key), (
            f"BD GMB result missing {required_key!r} — schema drift?: "
            f"{result!r}"
        )
