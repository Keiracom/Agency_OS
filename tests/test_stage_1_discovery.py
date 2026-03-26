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
        vertical_slug="marketing_agency",
        display_name="Marketing Agency",
        description="Test",
        service_signals=services,
        discovery_config={},
        enrichment_gates={"min_score_to_enrich": 30, "min_score_to_dm": 50, "min_score_to_outreach": 65},
        channel_config={"email": True, "linkedin": True, "voice": True, "sms": False},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_dfs_response(domains: list[str], total_count: int | None = None):
    """Build a mock DFS domains_by_technology response."""
    items = [{"domain": d, "title": f"Title {d}", "description": "", "technologies": {}} for d in domains]
    return {"total_count": total_count or len(domains), "items": items}


def make_conn(existing_domain: str | None = None):
    """Build a mock asyncpg connection."""
    conn = MagicMock()
    if existing_domain:
        row = MagicMock()
        row.__getitem__ = lambda self, k: existing_domain if k == "domain" else ([] if k == "dfs_technologies" else None)
        conn.fetchrow = AsyncMock(return_value=row)
    else:
        conn.fetchrow = AsyncMock(return_value=None)
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
    conn.execute.assert_called_once()  # INSERT called


@pytest.mark.asyncio
async def test_skips_existing_domains():
    """Existing domain (same tech) → duplicate counted, no INSERT."""
    stage, dfs, repo, conn = make_stage(
        techs=["Google Ads"],
        existing_domain="example.com.au",
    )
    # Make existing row return tech already present
    row = MagicMock()
    row.__getitem__ = lambda self, k: (["Google Ads"] if k == "dfs_technologies" else None)
    conn.fetchrow = AsyncMock(return_value=row)

    result = await stage.run_batch("marketing_agency", ["Google Ads"])
    assert result["discovered"] == 0
    assert result["duplicates_skipped"] == 1
    # execute should NOT be called (tech already present)
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_appends_new_tech_to_existing_domain():
    """Existing domain but different tech → UPDATE called, not INSERT, returns False."""
    stage, dfs, repo, conn = make_stage(
        techs=["Facebook Pixel"],
        existing_domain="example.com.au",
    )
    row = MagicMock()
    row.__getitem__ = lambda self, k: (["Google Ads"] if k == "dfs_technologies" else None)
    conn.fetchrow = AsyncMock(return_value=row)

    result = await stage.run_batch("marketing_agency", ["Facebook Pixel"])
    # Existing domain with new tech → counted as duplicate (not new row)
    assert result["duplicates_skipped"] == 1
    assert result["discovered"] == 0
    # But UPDATE should have been called to append the tech
    conn.execute.assert_called_once()
    update_sql = conn.execute.call_args[0][0]
    assert "UPDATE" in update_sql


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
        return_value={"total_count": 500, "items": [{"domain": "one.com.au", "title": "One", "description": "", "technologies": {}}]}
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
        id=str(uuid.uuid4()), vertical_slug="test", display_name="T", description=None,
        service_signals=services, discovery_config={}, enrichment_gates={}, channel_config={},
        created_at=datetime.now(), updated_at=datetime.now(),
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
    conn.execute.assert_called_once()
    # Verify the pipeline_stage value passed is integer 1
    call_args = conn.execute.call_args[0]
    # args: sql, display_name, domain, [techs], [sources], detected_at, pipeline_stage, pipeline_updated_at, discovered_at
    assert PIPELINE_STAGE_S1 == 1
    assert 1 in call_args  # pipeline_stage=1 is in the positional args
