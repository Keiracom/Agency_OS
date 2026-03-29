"""Tests for Layer2Discovery.pull_batch — Directive #290."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.layer_2_discovery import Layer2Discovery


def _make_l2(results=None):
    conn = MagicMock()
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(return_value=results or [])
    return Layer2Discovery(conn=conn, dfs=dfs)


@pytest.mark.asyncio
async def test_returns_list():
    l2 = _make_l2([{"domain": "d1.com.au", "organic_etv": 500.0}])
    r = await l2.pull_batch("10514")
    assert isinstance(r, list)
    assert r[0]["domain"] == "d1.com.au"


@pytest.mark.asyncio
async def test_etv_range_filter():
    l2 = _make_l2([
        {"domain": "big.com.au", "organic_etv": 10000.0},
        {"domain": "ok.com.au", "organic_etv": 500.0},
        {"domain": "tiny.com.au", "organic_etv": 50.0},
    ])
    r = await l2.pull_batch("10514", etv_min=200.0, etv_max=5000.0)
    domains = [x["domain"] for x in r]
    assert "ok.com.au" in domains
    assert "big.com.au" not in domains
    assert "tiny.com.au" not in domains


@pytest.mark.asyncio
async def test_pagination():
    l2 = _make_l2([{"domain": f"d{i}.com.au", "organic_etv": 500.0} for i in range(10)])
    p1 = await l2.pull_batch("10514", limit=3, offset=0)
    p2 = await l2.pull_batch("10514", limit=3, offset=3)
    assert len(p1) == 3 and len(p2) == 3
    assert p1[0]["domain"] != p2[0]["domain"]


@pytest.mark.asyncio
async def test_invalid_category_returns_empty():
    l2 = _make_l2()
    assert await l2.pull_batch("notanumber") == []


@pytest.mark.asyncio
async def test_dfs_error_returns_empty():
    conn = MagicMock()
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(side_effect=Exception("DFS down"))
    l2 = Layer2Discovery(conn=conn, dfs=dfs)
    assert await l2.pull_batch("10514") == []
