"""Tests for DFSLabsClient.maps_search_gmb — Directive #290."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.dfs_labs_client import DFSLabsClient


def _client():
    return DFSLabsClient(login="test", password="test")


@pytest.mark.asyncio
async def test_returns_dict_with_review_count():
    c = _client()
    mock = {
        "items": [
            {
                "place_id": "abc",
                "rating": 4.5,
                "rating_count": 42,
                "address": "123 Main St",
                "phone": "+61299999999",
            }
        ]
    }
    with patch.object(c, "_post", new_callable=AsyncMock, return_value=mock):
        r = await c.maps_search_gmb("Sydney Dental", "Australia")
    assert r["gmb_review_count"] == 42
    assert r["gmb_rating"] == 4.5
    assert r["gmb_found"] is True


@pytest.mark.asyncio
async def test_returns_none_when_empty():
    c = _client()
    with patch.object(c, "_post", new_callable=AsyncMock, return_value={"items": []}):
        assert await c.maps_search_gmb("Nobody", "Australia") is None


def test_cost_attribute_exists():
    c = _client()
    assert hasattr(c, "_cost_maps_search_gmb")
    assert c._cost_maps_search_gmb == Decimal("0")
