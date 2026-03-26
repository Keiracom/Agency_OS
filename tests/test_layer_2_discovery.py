"""Tests for Layer2Discovery — Directive #272"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.enrichment.signal_config import ServiceSignal, SignalConfig
from src.pipeline.layer_2_discovery import (
    DiscoveryStats,
    Layer2Discovery,
    _normalise_domain,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


def make_signal_config(discovery_config: dict | None = None) -> SignalConfig:
    """Build a minimal SignalConfig with given discovery_config."""
    return SignalConfig(
        id=str(uuid.uuid4()),
        vertical="marketing_agency",
        services=[
            ServiceSignal(
                service_name="paid_ads",
                label="Paid Ads",
                dfs_technologies=["Google Ads"],
                gmb_categories=["marketing_agency"],
                scoring_weights={},
            )
        ],
        discovery_config=discovery_config or {},
        enrichment_gates={},
        competitor_config={},
        channel_config={"email": True},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_conn(domain_exists: bool = False) -> MagicMock:
    """
    Build a mock asyncpg connection.
    - fetchval: returns a UUID string if domain_exists else None
    - fetch: returns [] by default (no prior BU rows for source_e)
    - execute: no-op
    """
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=str(uuid.uuid4()) if domain_exists else None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_dfs() -> MagicMock:
    """Build a mock DFSLabsClient with all Layer 2 methods returning empty lists."""
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(return_value=[])
    dfs.google_ads_advertisers = AsyncMock(return_value=[])
    dfs.domains_by_html_terms = AsyncMock(return_value=[])
    dfs.google_jobs_advertisers = AsyncMock(return_value=[])
    dfs.competitors_domain = AsyncMock(return_value={"items": []})
    return dfs


def make_engine(
    discovery_config: dict | None = None,
    domain_exists: bool = False,
    dfs: MagicMock | None = None,
) -> tuple[Layer2Discovery, MagicMock, MagicMock]:
    """Assemble Layer2Discovery with mocked dependencies."""
    conn = make_conn(domain_exists=domain_exists)
    dfs_client = dfs or make_dfs()
    engine = Layer2Discovery(conn=conn, dfs=dfs_client)
    return engine, conn, dfs_client


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reads_signal_config_for_vertical():
    """run() calls SignalConfigRepository.get_config with the correct vertical slug."""
    engine, conn, dfs = make_engine()
    config = make_signal_config()

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        await engine.run("marketing_agency")
        MockRepo.return_value.get_config.assert_called_once_with("marketing_agency")


@pytest.mark.asyncio
async def test_source_a_calls_domain_metrics_with_category_codes():
    """source_a calls domain_metrics_by_categories with codes from discovery_config."""
    cfg = {"category_codes": [10233, 10234], "ad_spend_threshold": 100.0}
    engine, conn, dfs = make_engine(discovery_config=cfg)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        await engine.run("marketing_agency", daily_budget_usd=100.0)

    dfs.domain_metrics_by_categories.assert_called_once_with(
        category_codes=[10233, 10234],
        paid_etv_min=100.0,
    )


@pytest.mark.asyncio
async def test_source_b_calls_ads_search_per_keyword():
    """source_b calls google_ads_advertisers once per keyword in keywords_for_ads_search."""
    cfg = {"keywords_for_ads_search": ["digital marketing", "seo agency"]}
    engine, conn, dfs = make_engine(discovery_config=cfg)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        await engine.run("marketing_agency", daily_budget_usd=100.0)

    assert dfs.google_ads_advertisers.call_count == 2
    calls = [c.kwargs["keyword"] for c in dfs.google_ads_advertisers.call_args_list]
    assert "digital marketing" in calls
    assert "seo agency" in calls


@pytest.mark.asyncio
async def test_source_c_calls_html_terms_per_combo():
    """source_c calls domains_by_html_terms once per html_gap_combo entry."""
    cfg = {
        "html_gap_combos": [
            {"has": "Google Analytics", "missing": "HubSpot"},
            {"has": "Facebook Pixel"},
        ]
    }
    engine, conn, dfs = make_engine(discovery_config=cfg)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        await engine.run("marketing_agency", daily_budget_usd=100.0)

    assert dfs.domains_by_html_terms.call_count == 2
    first_call = dfs.domains_by_html_terms.call_args_list[0]
    assert first_call.kwargs["include_term"] == "Google Analytics"
    assert first_call.kwargs["exclude_term"] == "HubSpot"
    second_call = dfs.domains_by_html_terms.call_args_list[1]
    assert second_call.kwargs["include_term"] == "Facebook Pixel"
    assert second_call.kwargs.get("exclude_term") is None


@pytest.mark.asyncio
async def test_source_d_calls_jobs_per_keyword():
    """source_d calls google_jobs_advertisers once per job_search_keywords entry."""
    cfg = {"job_search_keywords": ["marketing manager", "ppc specialist"]}
    engine, conn, dfs = make_engine(discovery_config=cfg)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        await engine.run("marketing_agency", daily_budget_usd=100.0)

    assert dfs.google_jobs_advertisers.call_count == 2


@pytest.mark.asyncio
async def test_source_e_skipped_when_no_prior_bu_data():
    """source_e skips competitors_domain when no prior BU rows qualify."""
    cfg = {"competitor_expansion": True}
    engine, conn, dfs = make_engine(discovery_config=cfg)
    # conn.fetch returns [] by default (no prior rows)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        await engine.run("marketing_agency", daily_budget_usd=100.0)

    dfs.competitors_domain.assert_not_called()


@pytest.mark.asyncio
async def test_deduplication_keeps_first_occurrence():
    """Two sources returning the same domain → unique_domains=1, not 2."""
    cfg = {
        "keywords_for_ads_search": ["marketing"],
        "job_search_keywords": ["marketing manager"],
    }
    engine, conn, dfs = make_engine(discovery_config=cfg)
    # Both sources return the same domain
    dfs.google_ads_advertisers = AsyncMock(return_value=[{"domain": "acme.com.au", "title": "Acme", "url": "https://acme.com.au"}])
    dfs.google_jobs_advertisers = AsyncMock(return_value=[{"domain": "acme.com.au", "employer_name": "Acme"}])
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=100.0)

    assert stats.unique_domains == 1


@pytest.mark.asyncio
async def test_domain_normalisation():
    """_normalise_domain strips https://, www., trailing slash, and lowercases."""
    assert _normalise_domain("https://www.Example.COM/") == "example.com"
    assert _normalise_domain("http://www.test.com.au/") == "test.com.au"
    assert _normalise_domain("BARE.COM") == "bare.com"
    assert _normalise_domain("www.example.com") == "example.com"
    assert _normalise_domain("example.com/") == "example.com"


@pytest.mark.asyncio
async def test_blocklist_filters_platform_domains():
    """facebook.com from a source is blocked — not written to BU, blocked_count=1."""
    cfg = {"keywords_for_ads_search": ["marketing"]}
    engine, conn, dfs = make_engine(discovery_config=cfg)
    dfs.google_ads_advertisers = AsyncMock(
        return_value=[{"domain": "facebook.com", "title": "FB", "url": "https://facebook.com"}]
    )
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=100.0)

    assert stats.blocked_count == 1
    assert stats.written_new == 0
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_budget_cap_stops_sources():
    """daily_budget_usd=0.0 means all sources with non-zero cost are skipped, budget_exceeded=True."""
    cfg = {
        "category_codes": [10233],          # source_a costs $0.10
        "keywords_for_ads_search": ["seo"],  # source_b costs $0.006
    }
    engine, conn, dfs = make_engine(discovery_config=cfg)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=0.0)

    assert stats.budget_exceeded is True
    dfs.domain_metrics_by_categories.assert_not_called()
    dfs.google_ads_advertisers.assert_not_called()


@pytest.mark.asyncio
async def test_source_error_does_not_abort_run():
    """If source_a raises, sources b/c/d/e still run and source_errors is populated."""
    cfg = {
        "category_codes": [10233],          # ensures source_a calls domain_metrics_by_categories
        "keywords_for_ads_search": ["marketing"],
        "job_search_keywords": ["manager"],
    }
    engine, conn, dfs = make_engine(discovery_config=cfg)
    dfs.domain_metrics_by_categories = AsyncMock(side_effect=Exception("DFS timeout"))
    dfs.google_ads_advertisers = AsyncMock(return_value=[{"domain": "good.com.au", "title": "", "url": "https://good.com.au"}])
    dfs.google_jobs_advertisers = AsyncMock(return_value=[])
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=100.0)

    # source_a failed, but other sources ran
    assert len(stats.source_errors) >= 1
    assert "source_a" in stats.source_errors[0]
    dfs.google_ads_advertisers.assert_called()


@pytest.mark.asyncio
async def test_idempotency_skips_existing_domain():
    """If domain already exists in BU (fetchval returns UUID), written_new=0 and written_skip=1."""
    cfg = {"keywords_for_ads_search": ["marketing"]}
    engine, conn, dfs = make_engine(discovery_config=cfg, domain_exists=True)
    dfs.google_ads_advertisers = AsyncMock(
        return_value=[{"domain": "existing.com.au", "title": "Existing", "url": "https://existing.com.au"}]
    )
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=100.0)

    assert stats.written_new == 0
    assert stats.written_skip == 1
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_stats_returned_correctly():
    """End-to-end with mocks: total_raw, unique_domains, written_new counts are correct."""
    cfg = {
        "keywords_for_ads_search": ["marketing"],
        "job_search_keywords": ["ppc"],
    }
    engine, conn, dfs = make_engine(discovery_config=cfg)
    # source_b returns 2 distinct domains, source_d returns 1 (overlap with source_b = 1 new)
    dfs.google_ads_advertisers = AsyncMock(return_value=[
        {"domain": "alpha.com.au", "title": "Alpha", "url": "https://alpha.com.au"},
        {"domain": "beta.com.au", "title": "Beta", "url": "https://beta.com.au"},
    ])
    dfs.google_jobs_advertisers = AsyncMock(return_value=[
        {"domain": "alpha.com.au", "employer_name": "Alpha Co"},  # duplicate of source_b
    ])
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=100.0)

    assert stats.total_raw == 3            # 2 from source_b + 1 from source_d
    assert stats.unique_domains == 2       # alpha.com.au deduplicated
    assert stats.written_new == 2          # both are new (fetchval returns None)
    assert stats.written_skip == 0
    assert stats.blocked_count == 0
    assert stats.estimated_cost_usd > 0
