"""Tests for FreeEnrichment.enrich() — Directive #290, updated pool mock — #300."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.free_enrichment import FreeEnrichment


def _make_pool_mock() -> MagicMock:
    """Return a MagicMock that behaves like asyncpg.Pool.acquire() context manager."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)

    acquire_ctx = MagicMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock(spec=["acquire"])
    pool.acquire = MagicMock(return_value=acquire_ctx)
    return pool


def _make_fe(spider=None, dns=None, abn=None):
    pool = _make_pool_mock()
    fe = FreeEnrichment(pool)
    fe._dns_precheck = MagicMock(return_value=True)
    fe._scrape_website = AsyncMock(return_value=spider or {"title": "Test Dental"})
    fe._enrich_dns = MagicMock(return_value=dns or {"has_spf": True})
    fe._match_abn = AsyncMock(return_value=abn or {"abn_matched": False})
    return fe


@pytest.mark.asyncio
async def test_returns_dict_with_domain():
    fe = _make_fe()
    r = await fe.enrich("testdental.com.au")
    assert isinstance(r, dict)
    assert r["domain"] == "testdental.com.au"


@pytest.mark.asyncio
async def test_merges_all_sources():
    fe = _make_fe(
        spider={"title": "Pymble Dental", "website_cms": "wordpress"},
        dns={"has_spf": True, "mx_provider": "google"},
        abn={"abn_matched": True, "gst_registered": True},
    )
    r = await fe.enrich("pymbledental.com.au")
    assert r["website_cms"] == "wordpress"
    assert r["has_spf"] is True
    assert r["abn_matched"] is True
    assert "Pymble Dental" in r["company_name"]


@pytest.mark.asyncio
async def test_returns_none_on_exception():
    pool = _make_pool_mock()
    fe = FreeEnrichment(pool)
    fe._scrape_website = AsyncMock(side_effect=Exception("Spider down"))
    fe._enrich_dns = MagicMock(return_value={})
    fe._match_abn = AsyncMock(return_value={"abn_matched": False})
    assert await fe.enrich("broken.com.au") is None


@pytest.mark.asyncio
async def test_company_name_from_title():
    fe = _make_fe(spider={"title": "Sydney Smile Dental | Family Dentist"})
    r = await fe.enrich("sydneysmile.com.au")
    assert "Sydney Smile Dental" in r.get("company_name", "")


@pytest.mark.asyncio
async def test_company_name_fallback_to_domain():
    fe = _make_fe(spider={"title": ""})
    r = await fe.enrich("bright-smile-dental.com.au")
    assert r.get("company_name", "") != ""
