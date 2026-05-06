"""Tests for Stage1Discovery — Directive #259"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from contextlib import asynccontextmanager

from src.pipeline.stage_1_discovery import Stage1Discovery, PIPELINE_STAGE_S1, DISCOVERY_SOURCE
from src.enrichment.signal_config import SignalConfig, ServiceSignal


# ─── Fixtures ───────────────────────────────────────────────────────────────


def make_signal_config(technologies: list[str] | None = None):
    """Build a minimal SignalConfig with given technology list."""
    import uuid
    from datetime import datetime

    services = [
        ServiceSignal(
            service_name="paid_ads",
            label="Paid Ads",
            dfs_technologies=technologies or ["Google Ads", "Facebook Pixel"],
            gmb_categories=["marketing_agency"],
            scoring_weights={"budget": 30, "pain": 30, "gap": 25, "fit": 15},
        )
    ]
    return SignalConfig(
        id=str(uuid.uuid4()),
        vertical="marketing_agency",
        services=services,
        discovery_config={},
        enrichment_gates={
            "min_score_to_enrich": 30,
            "min_score_to_dm": 50,
            "min_score_to_outreach": 65,
        },
        competitor_config={},
        channel_config={"email": True, "linkedin": True, "voice": True, "sms": False},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_dfs_response(domains: list[str], total_count: int | None = None):
    """Build a mock DFS domains_by_technology response."""
    items = [
        {"domain": d, "title": f"Title {d}", "description": "", "technologies": {}} for d in domains
    ]
    return {"total_count": total_count or len(domains), "items": items}


def make_conn(existing_domain: str | None = None):
    """Build a mock asyncpg connection.

    Directive #267: _upsert_domain now uses INSERT ... ON CONFLICT ... RETURNING (xmax=0) AS inserted
    via conn.fetchrow (not conn.execute).
    - existing_domain=None  → returns {"inserted": True}  (new row)
    - existing_domain=<str> → returns {"inserted": False} (conflict/duplicate)
    """
    conn = MagicMock()
    row = MagicMock()
    inserted_val = existing_domain is None  # True when no existing domain
    row.__getitem__ = lambda self, k: inserted_val if k == "inserted" else None
    conn.fetchrow = AsyncMock(return_value=row)
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_stage(techs=None, existing_domain=None, dfs_items=None):
    """Assemble a Stage1Discovery with mocked dependencies."""
    dfs_client = MagicMock()
    dfs_client.total_cost_usd = 0.015
    dfs_client.domains_by_technology = AsyncMock(
        return_value=make_dfs_response(dfs_items or ["example.com.au"])
    )
    signal_repo = MagicMock()
    signal_repo.get_config = AsyncMock(return_value=make_signal_config(techs))
    conn = make_conn(existing_domain)
    stage = Stage1Discovery(dfs_client, signal_repo, conn, delay_between_techs=0)
    return stage, dfs_client, signal_repo, conn


# ─── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_discovers_domains_from_signal_config():
    """run() loads config, iterates technologies, inserts new domains."""
    stage, dfs, repo, conn = make_stage(techs=["Google Ads"])
    result = await stage.run("marketing_agency")
    repo.get_config.assert_called_once_with("marketing_agency")
    dfs.domains_by_technology.assert_called_once()
    assert result["discovered"] == 1
    assert result["duplicates_skipped"] == 0
    # Directive #267: upsert uses fetchrow (INSERT ... ON CONFLICT ... RETURNING)
    conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_skips_existing_domains():
    """Existing domain → duplicate counted (ON CONFLICT returns inserted=False)."""
    stage, dfs, repo, conn = make_stage(
        techs=["Google Ads"],
        existing_domain="example.com.au",  # triggers inserted=False mock
    )
    result = await stage.run_batch("marketing_agency", ["Google Ads"])
    assert result["discovered"] == 0
    assert result["duplicates_skipped"] == 1
    # Directive #267: execute should NOT be called (upsert goes via fetchrow)
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_appends_new_tech_to_existing_domain():
    """Existing domain but different tech → ON CONFLICT upsert, returns inserted=False."""
    stage, dfs, repo, conn = make_stage(
        techs=["Facebook Pixel"],
        existing_domain="example.com.au",  # triggers inserted=False mock
    )
    result = await stage.run_batch("marketing_agency", ["Facebook Pixel"])
    # Existing domain → counted as duplicate (not a new row)
    assert result["duplicates_skipped"] == 1
    assert result["discovered"] == 0
    # Directive #267: ON CONFLICT merges tech via fetchrow (no separate execute)
    conn.fetchrow.assert_called_once()
    upsert_sql = conn.fetchrow.call_args[0][0]
    assert "ON CONFLICT" in upsert_sql


@pytest.mark.asyncio
async def test_handles_empty_dfs_response():
    """Empty DFS response → no inserts, zero counts, no error."""
    stage, dfs, repo, conn = make_stage()
    dfs.domains_by_technology = AsyncMock(return_value={"total_count": 0, "items": []})
    result = await stage.run_batch("marketing_agency", ["Google Ads"])
    assert result["discovered"] == 0
    assert result["duplicates_skipped"] == 0
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_respects_max_domains_per_tech_limit():
    """max_domains_per_tech=1 should stop after 1 domain even if total_count is higher."""
    stage, dfs, repo, conn = make_stage()
    dfs.domains_by_technology = AsyncMock(
        return_value={
            "total_count": 500,
            "items": [
                {"domain": "one.com.au", "title": "One", "description": "", "technologies": {}}
            ],
        }
    )
    result = await stage.run_batch("marketing_agency", ["Google Ads"], max_domains_per_tech=1)
    assert dfs.domains_by_technology.call_count == 1
    assert result["discovered"] == 1


@pytest.mark.asyncio
async def test_deduplicates_technologies_across_services():
    """all_dfs_technologies on config with 2 services sharing a tech deduplicates correctly."""
    import uuid
    from datetime import datetime

    services = [
        ServiceSignal("svc1", "S1", ["Google Ads", "Facebook Pixel"], [], {}),
        ServiceSignal("svc2", "S2", ["Google Ads", "HubSpot"], [], {}),
    ]
    config = SignalConfig(
        id=str(uuid.uuid4()),
        vertical="test",
        services=services,
        discovery_config={},
        enrichment_gates={},
        competitor_config={},
        channel_config={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    techs = config.all_dfs_technologies
    assert techs.count("Google Ads") == 1  # deduped
    assert set(techs) == {"Google Ads", "Facebook Pixel", "HubSpot"}


@pytest.mark.asyncio
async def test_returns_correct_counts():
    """run_batch with 2 techs, 1 new domain each → discovered=2."""
    stage, dfs, repo, conn = make_stage()
    call_count = 0
    domains = [["alpha.com.au"], ["beta.com.au"]]

    async def side_effect(**kwargs):
        nonlocal call_count
        r = make_dfs_response(domains[call_count])
        call_count += 1
        return r

    dfs.domains_by_technology = AsyncMock(side_effect=side_effect)

    result = await stage.run_batch("marketing_agency", ["Google Ads", "Facebook Pixel"])
    assert result["discovered"] == 2
    assert result["duplicates_skipped"] == 0
    assert result["technologies_searched"] == 2
    assert result["api_calls"] == 2


@pytest.mark.asyncio
async def test_sets_pipeline_stage_s1_discovered():
    """New domain INSERT uses PIPELINE_STAGE_S1 (integer 1)."""
    stage, dfs, repo, conn = make_stage()
    await stage.run_batch("marketing_agency", ["Google Ads"])
    # Directive #267: upsert uses fetchrow (INSERT ... ON CONFLICT ... RETURNING)
    conn.fetchrow.assert_called_once()
    call_args = conn.fetchrow.call_args[0]
    assert PIPELINE_STAGE_S1 == 1
    assert 1 in call_args  # pipeline_stage=1 is in the positional args


# ─── Directive #267 tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_duplicate_domains_across_techs():
    """ON CONFLICT upsert prevents duplicate rows when same domain appears in multiple techs."""
    stage, dfs, repo, conn = make_stage()
    # Both techs return the same domain → second call returns inserted=False
    call_count = 0

    async def side_effect(**kwargs):
        return make_dfs_response(["shared.com.au"])

    dfs.domains_by_technology = AsyncMock(side_effect=side_effect)

    # First call → inserted=True, second → inserted=False (conflict)
    inserted_values = [True, False]
    call_idx = 0
    original_fetchrow = conn.fetchrow

    async def fetchrow_side_effect(*args, **kwargs):
        nonlocal call_idx
        row = MagicMock()
        val = inserted_values[min(call_idx, len(inserted_values) - 1)]
        row.__getitem__ = lambda self, k: val if k == "inserted" else None
        call_idx += 1
        return row

    conn.fetchrow = AsyncMock(side_effect=fetchrow_side_effect)

    result = await stage.run_batch("marketing_agency", ["Google Ads", "Facebook Pixel"])
    assert result["discovered"] == 1  # only first call counted as new
    assert result["duplicates_skipped"] == 1  # second call was a conflict


@pytest.mark.asyncio
async def test_blocks_platform_domains():
    """Platform/social domains are not inserted into BU (blocklist check)."""
    stage, dfs, repo, conn = make_stage()
    dfs.domains_by_technology = AsyncMock(
        return_value=make_dfs_response(["facebook.com", "instagram.com", "google.com"])
    )
    result = await stage.run_batch("marketing_agency", ["Google Ads"])
    assert result["discovered"] == 0
    assert result["duplicates_skipped"] == 3  # all blocked → counted as skipped
    conn.fetchrow.assert_not_called()  # DB never touched for blocked domains


@pytest.mark.asyncio
async def test_allows_legitimate_business_domains():
    """Normal business domains pass the blocklist check and are inserted."""
    stage, dfs, repo, conn = make_stage()
    dfs.domains_by_technology = AsyncMock(return_value=make_dfs_response(["acme-dental.com.au"]))
    result = await stage.run_batch("marketing_agency", ["Google Ads"])
    assert result["discovered"] == 1
    conn.fetchrow.assert_called_once()  # DB upsert called for legitimate domain
