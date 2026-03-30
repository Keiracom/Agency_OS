"""Tests for DFSLabsClient.ads_search_by_domain — Directive #291."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from src.clients.dfs_labs_client import DFSLabsClient


def _c():
    return DFSLabsClient(login="test", password="test")


@pytest.mark.asyncio
async def test_ads_found_returns_dict():
    client = _c()
    mock = {"items": [
        {"type": "ads_search", "format": "text", "first_shown": "2025-01-01", "last_shown": "2026-03-29"},
        {"type": "ads_search", "format": "video", "first_shown": "2024-06-01", "last_shown": "2026-03-28"},
    ]}
    with patch.object(client, "_post", new_callable=AsyncMock, return_value=mock):
        r = await client.ads_search_by_domain("dental.com.au")
    assert r["is_running_ads"] is True
    assert r["ad_count"] == 2
    assert "text" in r["formats"]


@pytest.mark.asyncio
async def test_no_items_returns_not_running():
    client = _c()
    with patch.object(client, "_post", new_callable=AsyncMock, return_value={"items": []}):
        r = await client.ads_search_by_domain("unknown.com.au")
    assert r["is_running_ads"] is False
    assert r["ad_count"] == 0


@pytest.mark.asyncio
async def test_post_error_returns_none():
    client = _c()
    with patch.object(client, "_post", new_callable=AsyncMock, side_effect=Exception("network")):
        r = await client.ads_search_by_domain("broken.com.au")
    assert r is None


def test_cost_attribute_initialised():
    c = _c()
    assert hasattr(c, "_cost_ads_search_by_domain")
    assert c._cost_ads_search_by_domain == Decimal("0")
