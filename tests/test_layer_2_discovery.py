"""Tests for Layer2Discovery — Directive #280 (v7 single-source rewrite)"""
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.enrichment.signal_config import ServiceSignal, SignalConfig
from src.pipeline.layer_2_discovery import (
    DiscoveryStats,
    Layer2Discovery,
    _compute_trajectory,
    _is_au_domain,
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
    """Build a mock asyncpg connection."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1 if domain_exists else None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_dfs(results: list[dict] | None = None) -> MagicMock:
    """Build a mock DFSLabsClient returning given results."""
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(return_value=results or [])
    return dfs


def make_engine(
    discovery_config: dict | None = None,
    domain_exists: bool = False,
    dfs_results: list[dict] | None = None,
) -> tuple[Layer2Discovery, MagicMock, MagicMock]:
    """Assemble Layer2Discovery with mocked dependencies."""
    conn = make_conn(domain_exists=domain_exists)
    dfs = make_dfs(dfs_results)
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    return engine, conn, dfs


# ─── Unit: helpers ──────────────────────────────────────────────────────────


def test_normalise_domain_strips_url_cruft():
    assert _normalise_domain("https://www.Example.COM/") == "example.com"
    assert _normalise_domain("http://www.test.com.au/") == "test.com.au"
    assert _normalise_domain("BARE.COM") == "bare.com"
    assert _normalise_domain("www.example.com") == "example.com"
    assert _normalise_domain("example.com/") == "example.com"


def test_is_au_domain_keeps_au_tlds():
    assert _is_au_domain("agency.com.au") is True
    assert _is_au_domain("firm.net.au") is True
    assert _is_au_domain("org.org.au") is True


def test_is_au_domain_keeps_dotcom():
    assert _is_au_domain("acme.com") is True


def test_is_au_domain_kills_foreign_tlds():
    assert _is_au_domain("firm.co.uk") is False
    assert _is_au_domain("agency.ca") is False
    assert _is_au_domain("ads.de") is False
    assert _is_au_domain("firm.co.nz") is False


def test_is_au_domain_keeps_neutral_tlds():
    assert _is_au_domain("startup.io") is True
    assert _is_au_domain("firm.net") is True


def test_compute_trajectory_growing():
    assert _compute_trajectory(120.0, 100.0) == "GROWING"


def test_compute_trajectory_declining():
    assert _compute_trajectory(80.0, 100.0) == "DECLINING"


def test_compute_trajectory_stable():
    assert _compute_trajectory(105.0, 100.0) == "STABLE"


def test_compute_trajectory_unknown_when_no_prev():
    assert _compute_trajectory(500.0, None) == "UNKNOWN"


def test_compute_trajectory_unknown_when_prev_zero():
    assert _compute_trajectory(500.0, 0.0) == "UNKNOWN"


# ─── Integration: run() ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_inserts_new_domains():
    """Domains from DFS that pass all filters are inserted; domains_inserted > 0."""
    cfg = {"category_codes": [10233]}
    dfs_results = [
        {"domain": "newagency.com.au", "organic_etv": 500.0, "paid_etv": 200.0},
        {"domain": "another.com.au", "organic_etv": 300.0, "paid_etv": 100.0},
    ]
    engine, conn, dfs = make_engine(discovery_config=cfg, dfs_results=dfs_results)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.domains_inserted == 2
    assert conn.execute.call_count == 2


@pytest.mark.asyncio
async def test_run_deduplicates_existing_domains():
    """Domains already in BU (fetchval returns 1) are skipped — domains_deduped=1."""
    cfg = {"category_codes": [10233]}
    dfs_results = [{"domain": "existing.com.au", "organic_etv": 500.0, "paid_etv": 100.0}]
    engine, conn, dfs = make_engine(discovery_config=cfg, domain_exists=True, dfs_results=dfs_results)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.domains_deduped == 1
    assert stats.domains_inserted == 0
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_run_filters_non_au_domains():
    """Domains with foreign TLDs (.co.uk) are rejected; domains_au_filtered=1, inserted=0."""
    cfg = {"category_codes": [10233]}
    dfs_results = [{"domain": "agency.co.uk", "organic_etv": 1000.0, "paid_etv": 500.0}]
    engine, conn, dfs = make_engine(discovery_config=cfg, dfs_results=dfs_results)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.domains_au_filtered == 1
    assert stats.domains_inserted == 0
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_run_filters_blocklisted_domains():
    """Blocklisted domains (facebook.com) are rejected; domains_blocked=1, inserted=0."""
    cfg = {"category_codes": [10233]}
    dfs_results = [{"domain": "facebook.com", "organic_etv": 999999.0, "paid_etv": 1000.0}]
    engine, conn, dfs = make_engine(discovery_config=cfg, dfs_results=dfs_results)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.domains_blocked == 1
    assert stats.domains_inserted == 0
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_run_computes_trajectory_growing():
    """Domain with organic_etv 120 (prev 100) → trajectory_growing=1."""
    cfg = {"category_codes": [10233]}
    dfs_results = [
        {"domain": "growing.com.au", "organic_etv": 120.0, "organic_etv_prev": 100.0, "paid_etv": 0.0}
    ]
    engine, conn, dfs = make_engine(discovery_config=cfg, dfs_results=dfs_results)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.trajectory_growing == 1
    assert stats.trajectory_declining == 0


@pytest.mark.asyncio
async def test_run_computes_trajectory_declining():
    """Domain with organic_etv 80 (prev 100) → trajectory_declining=1."""
    cfg = {"category_codes": [10233]}
    dfs_results = [
        {"domain": "declining.com.au", "organic_etv": 80.0, "organic_etv_prev": 100.0, "paid_etv": 0.0}
    ]
    engine, conn, dfs = make_engine(discovery_config=cfg, dfs_results=dfs_results)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.trajectory_declining == 1
    assert stats.trajectory_growing == 0


@pytest.mark.asyncio
async def test_run_respects_budget_gate():
    """daily_budget_usd=0.00 → budget gate fires immediately, 0 DFS calls, 0 inserts."""
    cfg = {"category_codes": [10233, 10234]}
    engine, conn, dfs = make_engine(discovery_config=cfg)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=0.0)

    assert stats.budget_exceeded is True
    assert stats.domains_inserted == 0
    dfs.domain_metrics_by_categories.assert_not_called()


@pytest.mark.asyncio
async def test_run_returns_stats():
    """DiscoveryStats fields are populated correctly after a successful run."""
    cfg = {"category_codes": [10233]}
    dfs_results = [
        {"domain": "alpha.com.au", "organic_etv": 500.0, "paid_etv": 200.0},
        {"domain": "beta.com.au", "organic_etv": 300.0, "paid_etv": 100.0},
        {"domain": "foreign.co.uk", "organic_etv": 1000.0, "paid_etv": 500.0},  # filtered
    ]
    engine, conn, dfs = make_engine(discovery_config=cfg, dfs_results=dfs_results)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert isinstance(stats, DiscoveryStats)
    assert stats.category_codes == [10233]
    assert stats.domains_returned == 3
    assert stats.domains_au_filtered == 1
    assert stats.domains_blocked == 0
    assert stats.domains_deduped == 0
    assert stats.domains_inserted == 2
    assert stats.cost_usd == Decimal("0.10")
    assert isinstance(stats.run_id, uuid.UUID)
    assert stats.budget_exceeded is False


@pytest.mark.asyncio
async def test_run_handles_dfs_error_gracefully():
    """DFS error on one category is caught, logged, run continues; source_errors populated."""
    cfg = {"category_codes": [10233, 10234]}
    engine, conn, dfs = make_engine(discovery_config=cfg)
    dfs.domain_metrics_by_categories = AsyncMock(side_effect=[
        Exception("DFS timeout"),
        [{"domain": "good.com.au", "organic_etv": 100.0, "paid_etv": 0.0}],
    ])
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert len(stats.source_errors) == 1
    assert "10233" in stats.source_errors[0]
    assert stats.domains_inserted == 1  # second category succeeded


@pytest.mark.asyncio
async def test_run_no_category_codes_returns_empty_stats():
    """discovery_config with no category_codes → immediate return with zeros."""
    cfg = {}
    engine, conn, dfs = make_engine(discovery_config=cfg)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency")

    assert stats.domains_inserted == 0
    assert stats.domains_returned == 0
    dfs.domain_metrics_by_categories.assert_not_called()


@pytest.mark.asyncio
async def test_run_batch_processes_all_verticals():
    """run_batch() runs once per vertical and returns a dict keyed by slug."""
    engine, conn, dfs = make_engine(discovery_config={"category_codes": [10233]})
    config = make_signal_config({"category_codes": [10233]})

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        results = await engine.run_batch(["marketing_agency", "dental"])

    assert set(results.keys()) == {"marketing_agency", "dental"}
    assert all(isinstance(s, DiscoveryStats) for s in results.values())
