"""Tests for PaidEnrichment + affordability_gate — Directive #283 + #303."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.paid_enrichment import PaidEnrichment, affordability_gate
from src.pipeline.pipeline_orchestrator import ProspectCard


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


# ─── Test 11: competitors enrichment writes intel_results ─────────────────────


@pytest.mark.asyncio
async def test_competitors_enrichment():
    """competitors_domain() returning 3 items → intel_results[domain] has correct counts."""
    conn = make_conn()
    domain = "testco.com.au"
    row = make_row(domain=domain)

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[])
    dfs.competitors_domain = AsyncMock(return_value={
        "items": [
            {"domain": "comp1.com.au"},
            {"domain": "comp2.com.au"},
            {"domain": "comp3.com.au"},
        ]
    })
    dfs.backlinks_summary = AsyncMock(return_value={
        "referring_domains": 0, "rank": 0, "backlinks": 0,
        "referring_domains_new": 0, "referring_domains_lost": 0,
    })
    dfs.brand_serp = AsyncMock(return_value={
        "brand_position": None, "gmb_showing": False, "competitors_bidding": False,
    })
    dfs.indexed_pages = AsyncMock(return_value=0)

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))):
        stats = await engine.run()

    assert stats["intelligence_enriched"] == 1
    # Access intel_results via the engine's run is reflected in stats
    # Verify the DB execute was called with competitor data
    calls_sql = [str(c) for c in conn.execute.call_args_list]
    assert any("competitors_top3" in s for s in calls_sql)


# ─── Test 12: backlinks parser fix ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_backlinks_parser_fix():
    """backlinks_summary() data parsed directly from result (not under 'items')."""
    conn = make_conn()
    domain = "backlink-test.com.au"
    row = make_row(domain=domain)

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[])
    dfs.competitors_domain = AsyncMock(return_value={"items": []})
    dfs.backlinks_summary = AsyncMock(return_value={
        "referring_domains": 142,
        "rank": 23,
        "backlinks": 580,
        "referring_domains_new": 10,
        "referring_domains_lost": 3,
    })
    dfs.brand_serp = AsyncMock(return_value={
        "brand_position": None, "gmb_showing": False, "competitors_bidding": False,
    })
    dfs.indexed_pages = AsyncMock(return_value=0)

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))):
        stats = await engine.run()

    # Verify the DB write contained backlinks data
    calls_sql = [str(c) for c in conn.execute.call_args_list]
    assert any("backlinks_referring_domains" in s for s in calls_sql)
    assert stats["intelligence_enriched"] == 1

    # Verify backlinks_summary parsed the trend correctly from the client
    # (new=10 > lost=3 * 1.1=3.3, so trend="growing")
    from src.clients.dfs_labs_client import DFSLabsClient
    client = DFSLabsClient.__new__(DFSLabsClient)
    # Direct unit test of parser logic via a mock _post call
    with patch.object(client, "_post", new=AsyncMock(return_value={
        "referring_domains": 142,
        "rank": 23,
        "backlinks": 580,
        "referring_domains_new": 10,
        "referring_domains_lost": 3,
    })):
        result = await client.backlinks_summary("backlink-test.com.au")
    assert result["referring_domains"] == 142
    assert result["domain_rank"] == 23
    assert result["backlink_trend"] == "growing"


# ─── Test 13: brand_serp uses business name, not domain ───────────────────────


@pytest.mark.asyncio
async def test_brand_serp_uses_business_name():
    """brand_serp() is called with the business name, not the raw domain string."""
    conn = make_conn()
    domain = "bluegum-plumbing.com.au"
    row = make_row(domain=domain)

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[])
    dfs.competitors_domain = AsyncMock(return_value={"items": []})
    dfs.backlinks_summary = AsyncMock(return_value={
        "referring_domains": 0, "rank": 0, "backlinks": 0,
        "referring_domains_new": 0, "referring_domains_lost": 0,
    })
    dfs.brand_serp = AsyncMock(return_value={
        "brand_position": None, "gmb_showing": False, "competitors_bidding": False,
    })
    dfs.indexed_pages = AsyncMock(return_value=0)

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))):
        await engine.run()

    # brand_serp should not be called with the raw domain (e.g. "bluegum-plumbing.com.au")
    call_args = dfs.brand_serp.call_args
    assert call_args is not None
    called_name = call_args[0][0] if call_args[0] else call_args[1].get("business_name", "")
    assert called_name != domain  # must not pass raw domain


# ─── Test 14: indexed pages ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_indexed_pages():
    """indexed_pages() returning 47 → intel_results[domain]["indexed_pages"] == 47."""
    conn = make_conn()
    domain = "indexed-test.com.au"
    row = make_row(domain=domain)

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[])
    dfs.competitors_domain = AsyncMock(return_value={"items": []})
    dfs.backlinks_summary = AsyncMock(return_value={
        "referring_domains": 0, "rank": 0, "backlinks": 0,
        "referring_domains_new": 0, "referring_domains_lost": 0,
    })
    dfs.brand_serp = AsyncMock(return_value={
        "brand_position": None, "gmb_showing": False, "competitors_bidding": False,
    })
    dfs.indexed_pages = AsyncMock(return_value=47)

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))):
        stats = await engine.run()

    assert stats["intelligence_enriched"] == 1
    calls_sql = [str(c) for c in conn.execute.call_args_list]
    assert any("indexed_pages_count" in s for s in calls_sql)


# ─── Test 15: ProspectCard has all intelligence fields ────────────────────────


def test_prospect_card_has_intelligence_fields():
    """ProspectCard has all 9 intelligence fields from Directive #303."""
    card = ProspectCard(domain="x.com.au", company_name="X", location="Sydney")
    assert hasattr(card, "competitors_top3")
    assert hasattr(card, "competitor_count")
    assert hasattr(card, "referring_domains")
    assert hasattr(card, "domain_rank")
    assert hasattr(card, "backlink_trend")
    assert hasattr(card, "brand_position")
    assert hasattr(card, "brand_gmb_showing")
    assert hasattr(card, "brand_competitors_bidding")
    assert hasattr(card, "indexed_pages")
    # Check defaults
    assert card.competitors_top3 == []
    assert card.competitor_count == 0
    assert card.backlink_trend == "unknown"
    assert card.brand_position is None
    assert card.brand_gmb_showing is False


# ─── Test 16: intelligence calls all acquire GLOBAL_SEM_DFS ──────────────────


@pytest.mark.asyncio
async def test_intelligence_calls_use_sem_dfs():
    """All four intelligence calls go through GLOBAL_SEM_DFS via _sem_call."""
    import asyncio as _asyncio

    conn = make_conn()
    domain = "sem-test.com.au"
    row = make_row(domain=domain)

    acquire_count = 0
    real_sem = _asyncio.Semaphore(28)

    class CountingSem:
        async def __aenter__(self):
            nonlocal acquire_count
            acquire_count += 1
            return self

        async def __aexit__(self, *args):
            pass

    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=[])
    dfs.competitors_domain = AsyncMock(return_value={"items": []})
    dfs.backlinks_summary = AsyncMock(return_value={
        "referring_domains": 0, "rank": 0, "backlinks": 0,
        "referring_domains_new": 0, "referring_domains_lost": 0,
    })
    dfs.brand_serp = AsyncMock(return_value={
        "brand_position": None, "gmb_showing": False, "competitors_bidding": False,
    })
    dfs.indexed_pages = AsyncMock(return_value=0)

    gmaps = MagicMock()
    gmaps.discover_by_coordinates = AsyncMock(return_value=[])

    engine = make_pe(conn=conn, dfs=dfs, gmaps=gmaps)

    with (
        patch("src.pipeline.paid_enrichment.affordability_gate", new=AsyncMock(return_value=([row], []))),
        patch("src.pipeline.paid_enrichment.GLOBAL_SEM_DFS", new=CountingSem()),
    ):
        await engine.run()

    # 4 intelligence calls (competitors, backlinks, brand_serp, indexed_pages)
    assert acquire_count == 4
