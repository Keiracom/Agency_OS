"""Tests for PaidEnrichment + affordability_gate — Directive #283."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.paid_enrichment import PaidEnrichment, affordability_gate


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_conn() -> MagicMock:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_row(
    domain: str = "example.com.au",
    state: str = "NSW",
    website_cms: str | None = "wordpress",
    website_tech_stack: str | None = None,
    website_contact_emails: str | None = None,
    abn_matched: bool = True,
    gst_registered: bool = True,
    entity_type: str | None = "Company",
    bu_id: str | None = None,
) -> MagicMock:
    """Build a mock asyncpg.Record with dict-like access."""
    row = MagicMock()
    data = {
        "id": bu_id or str(uuid.uuid4()),
        "domain": domain,
        "state": state,
        "website_cms": website_cms,
        "website_tech_stack": website_tech_stack,
        "website_contact_emails": website_contact_emails,
        "abn_matched": abn_matched,
        "gst_registered": gst_registered,
        "entity_type": entity_type,
    }
    row.__getitem__ = lambda self, key: data[key]
    row.get = lambda key, default=None: data.get(key, default)
    return row


def make_pe(conn=None, dfs=None, gmaps=None) -> PaidEnrichment:
    conn = conn or make_conn()
    dfs = dfs or MagicMock()
    gmaps = gmaps or MagicMock()
    return PaidEnrichment(conn, dfs, gmaps)


# ─── Test 1: gate passes GST-registered company ───────────────────────────────


@pytest.mark.asyncio
async def test_affordability_gate_passes_gst_registered():
    """Row with abn_matched + gst_registered + Company entity passes all gates."""
    conn = make_conn()
    row = make_row(website_cms="wordpress", abn_matched=True, gst_registered=True, entity_type="Company")
    conn.fetch = AsyncMock(return_value=[row])

    passing, failing = await affordability_gate(conn, 10)

    assert len(passing) == 1
    assert len(failing) == 0
    conn.execute.assert_not_called()


# ─── Test 2: gate rejects dead site (no signals) ──────────────────────────────


@pytest.mark.asyncio
async def test_affordability_gate_rejects_dead_site():
    """Row with no CMS/tech/email signals fails GATE 1."""
    conn = make_conn()
    row = make_row(website_cms=None, website_tech_stack=None, website_contact_emails=None,
                   abn_matched=True, gst_registered=True, entity_type="Company")
    conn.fetch = AsyncMock(return_value=[row])

    passing, failing = await affordability_gate(conn, 10)

    assert len(passing) == 0
    assert len(failing) == 1
    conn.execute.assert_called_once()  # skip reason + timestamp written


# ─── Test 3: gate rejects sole trader ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_affordability_gate_rejects_sole_trader():
    """Row with entity_type='Individual/Sole Trader' fails GATE 4."""
    conn = make_conn()
    row = make_row(website_cms="wordpress", abn_matched=True, gst_registered=True,
                   entity_type="Individual/Sole Trader")
    conn.fetch = AsyncMock(return_value=[row])

    passing, failing = await affordability_gate(conn, 10)

    assert len(passing) == 0
    assert len(failing) == 1


# ─── Test 4: gate rejects no-GST ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_affordability_gate_rejects_no_gst():
    """Row with gst_registered=False fails GATE 3."""
    conn = make_conn()
    row = make_row(website_cms="wordpress", abn_matched=True, gst_registered=False, entity_type="Company")
    conn.fetch = AsyncMock(return_value=[row])

    passing, failing = await affordability_gate(conn, 10)

    assert len(passing) == 0
    assert len(failing) == 1


# ─── Test 5: None entity_type passes gate 4 ───────────────────────────────────


@pytest.mark.asyncio
async def test_affordability_gate_passes_null_entity_type():
    """None entity_type should not be rejected — sole trader check is explicit match only."""
    conn = make_conn()
    row = make_row(website_cms="wordpress", abn_matched=True, gst_registered=True, entity_type=None)
    conn.fetch = AsyncMock(return_value=[row])

    passing, failing = await affordability_gate(conn, 10)

    assert len(passing) == 1
    assert len(failing) == 0


# ─── Test 6: DFS bulk metrics written to BU ───────────────────────────────────


@pytest.mark.asyncio
async def test_bulk_domain_metrics_writes_to_bu():
    """DFS bulk_domain_metrics result is written to business_universe."""
    conn = make_conn()
    domain = "test.com.au"
    row = make_row(domain=domain)

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[{
        "domain": domain,
        "organic_etv": 1500.0,
        "domain_rank": 45,
        "backlinks_count": 200,
        "referring_domains": 50,
    }])

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))):
        stats = await engine.run()

    assert stats["dfs_enriched"] == 1
    # Ensure execute was called with an UPDATE containing dfs_organic_traffic
    calls_sql = [str(c) for c in conn.execute.call_args_list]
    assert any("dfs_organic_traffic" in s for s in calls_sql)


# ─── Test 7: GMB maps result written to BU ────────────────────────────────────


@pytest.mark.asyncio
async def test_gmb_maps_serp_writes_to_bu():
    """GMB discover result is written to business_universe."""
    conn = make_conn()
    row = make_row()

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[])

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[{
        "gmb_rating": 4.5,
        "gmb_review_count": 120,
        "phone": "0412345678",
        "address": "1 Main St Sydney NSW",
    }])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))):
        stats = await engine.run()

    assert stats["gmb_enriched"] == 1
    calls_sql = [str(c) for c in conn.execute.call_args_list]
    assert any("gmb_rating" in s for s in calls_sql)


# ─── Test 8: DFS failure continues to GMB step ────────────────────────────────


@pytest.mark.asyncio
async def test_dfs_failure_continues_to_next_step():
    """DFS batch error is caught; GMB step still runs."""
    conn = make_conn()
    row = make_row()

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(side_effect=Exception("DFS error"))

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[{
        "gmb_rating": 4.2,
        "gmb_review_count": 80,
        "phone": "0400000000",
        "address": "5 Test Rd",
    }])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))):
        stats = await engine.run()

    assert len(stats["errors"]) == 1
    assert stats["errors"][0]["step"] == "dfs_bulk"
    assert stats["gmb_enriched"] == 1


# ─── Test 9: skipped rows get timestamp written ───────────────────────────────


@pytest.mark.asyncio
async def test_skipped_domains_get_timestamp():
    """Rows failing the gate have paid_enrichment_skipped_reason + completed_at written."""
    conn = make_conn()
    row = make_row(website_cms=None, website_tech_stack=None, website_contact_emails=None)
    conn.fetch = AsyncMock(return_value=[row])

    passing, failing = await affordability_gate(conn)

    assert len(failing) == 1
    conn.execute.assert_called_once()
    call_args = conn.execute.call_args
    assert "paid_enrichment_skipped_reason" in call_args[0][0]


# ─── Test 10: completion timestamp set for passing rows ───────────────────────


@pytest.mark.asyncio
async def test_completion_timestamp_set():
    """All passing rows have paid_enrichment_completed_at set after run()."""
    conn = make_conn()
    row = make_row()

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[])

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))):
        stats = await engine.run()

    assert stats["completed"] == 1
    calls_sql = [str(c) for c in conn.execute.call_args_list]
    assert any("paid_enrichment_completed_at" in s for s in calls_sql)
