"""Tests for real ads_transparency (DFS-backed) — Directive #291."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.integrations.ads_transparency import check_google_ads


@pytest.mark.asyncio
async def test_no_client_returns_none():
    assert await check_google_ads("dental.com.au", dfs_client=None) is None


@pytest.mark.asyncio
async def test_with_client_calls_ads_search():
    client = MagicMock()
    client.ads_search_by_domain = AsyncMock(return_value={"is_running_ads": True, "ad_count": 5})
    result = await check_google_ads("dental.com.au", dfs_client=client)
    assert result["is_running_ads"] is True
    client.ads_search_by_domain.assert_called_once_with("dental.com.au")


@pytest.mark.asyncio
async def test_exception_returns_none():
    client = MagicMock()
    client.ads_search_by_domain = AsyncMock(side_effect=Exception("timeout"))
    result = await check_google_ads("dental.com.au", dfs_client=client)
    assert result is None
