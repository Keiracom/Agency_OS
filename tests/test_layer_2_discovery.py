"""Tests for Layer2Discovery — Directive #280 Gate 1 + 7 integration tests."""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest

from src.enrichment.signal_config import ServiceSignal, SignalConfig
from src.pipeline.layer_2_discovery import (
    DiscoverySource,
    Layer2Discovery,
    _compute_trajectory,
    _normalise_domain,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def make_signal_config(discovery_config: dict | None = None) -> SignalConfig:
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


def make_conn(domain_exists: bool = False, execute_returns: list[str] | None = None) -> MagicMock:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1 if domain_exists else None)
    conn.fetch = AsyncMock(return_value=[])
    if execute_returns is not None:
        conn.execute = AsyncMock(side_effect=execute_returns)
    else:
        conn.execute = AsyncMock(return_value=None)
    return conn


def make_dfs(results: list[dict] | None = None) -> MagicMock:
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(return_value=results or [])
    return dfs


# ─── Test 1: calls categories endpoint with AU location ───────────────────────


@pytest.mark.asyncio
async def test_discovery_calls_categories_endpoint():
    """DFS domain_metrics_by_categories is called with location_name='Australia'."""
    cfg = {"category_codes": [10233]}
    conn = make_conn()
    # Gate 1 execute calls return "UPDATE 0"
    conn.execute = AsyncMock(return_value="UPDATE 0")
    conn.fetchval = AsyncMock(return_value=0)
    dfs = make_dfs(results=[])
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        await engine.run("marketing_agency", daily_budget_usd=10.0)

    dfs.domain_metrics_by_categories.assert_called_once_with(
        category_codes=[10233],
        location_name="Australia",
        paid_etv_min=ANY,
    )


# ─── Test 2: filters non-AU and .gov.au (blocklisted) domains ─────────────────


@pytest.mark.asyncio
async def test_discovery_filters_non_au_domains():
    """
    .co.uk domains → domains_au_filtered.
    .gov.au domains → domains_blocked (gov.au is on the blocklist).
    Neither should be inserted.
    """
    cfg = {"category_codes": [10233]}
    results = [
        {"domain": "agency.co.uk", "organic_etv": 500.0, "paid_etv": 100.0},
        {"domain": "acme.com", "organic_etv": 200.0, "paid_etv": 50.0},   # non-AU .com kept
        {"domain": "dept.gov.au", "organic_etv": 1000.0, "paid_etv": 0.0},
    ]
    conn = make_conn()
    conn.execute = AsyncMock(return_value="UPDATE 0")
    conn.fetchval = AsyncMock(return_value=0)  # no existing, then gate count
    dfs = make_dfs(results=results)
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.domains_au_filtered >= 1          # .co.uk rejected
    assert stats.domains_blocked >= 1              # .gov.au rejected
    assert stats.domains_au_filtered + stats.domains_blocked >= 2


# ─── Test 3: deduplicates against business_universe ───────────────────────────


@pytest.mark.asyncio
async def test_discovery_dedupes_against_bu():
    """Domain already in BU (fetchval returns 1) is skipped — domains_deduped=1, inserted=0."""
    cfg = {"category_codes": [10233]}
    results = [{"domain": "existing.com.au", "organic_etv": 500.0, "paid_etv": 100.0}]
    conn = make_conn(domain_exists=True)
    # Gate 1: fetchval for dedup returns 1, then gate fetchval returns 0
    conn.fetchval = AsyncMock(side_effect=[1, 0])   # dedup hit, then gate count
    conn.execute = AsyncMock(return_value="UPDATE 0")
    dfs = make_dfs(results=results)
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.domains_deduped == 1
    assert stats.domains_inserted == 0


# ─── Test 4: computes trajectory correctly ────────────────────────────────────


@pytest.mark.asyncio
async def test_discovery_computes_trajectory():
    """
    GROWING: organic_etv=120, prev=100 (>10% change).
    DECLINING: organic_etv=80, prev=100 (<-10% change).
    STABLE: organic_etv=105, prev=100 (5% change — within ±10%).
    Trajectory is computed in-memory; stats counters must match.
    """
    # _compute_trajectory now returns fractional change as float | None
    assert _compute_trajectory(120.0, 100.0) == pytest.approx(0.20)
    assert _compute_trajectory(80.0, 100.0) == pytest.approx(-0.20)
    assert _compute_trajectory(105.0, 100.0) == pytest.approx(0.05)
    assert _compute_trajectory(100.0, None) is None
    assert _compute_trajectory(100.0, 0.0) is None

    cfg = {"category_codes": [10233]}
    results = [
        {"domain": "growing.com.au", "organic_etv": 120.0, "organic_etv_prev": 100.0, "paid_etv": 0.0},
        {"domain": "declining.com.au", "organic_etv": 80.0, "organic_etv_prev": 100.0, "paid_etv": 0.0},
        {"domain": "stable.com.au", "organic_etv": 105.0, "organic_etv_prev": 100.0, "paid_etv": 0.0},
    ]
    conn = make_conn()
    conn.fetchval = AsyncMock(return_value=None)  # no existing domain, gate count=0 at end
    conn.execute = AsyncMock(return_value="UPDATE 0")
    # fetchval side_effect: 3 dedup checks (None) then gate passed count (3)
    conn.fetchval = AsyncMock(side_effect=[None, None, None, 3])
    dfs = make_dfs(results=results)
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    # All 3 domains have organic_etv_prev set, so trajectory is a float for each
    assert stats.trajectory_with_value == 3
    assert stats.trajectory_none == 0


# ─── Test 5: Gate 1 — budget floor filter ─────────────────────────────────────


@pytest.mark.asyncio
async def test_discovery_applies_budget_floor():
    """
    apply_gate_1 with a row where dfs_paid_traffic_cost=500 (<1000):
    → filtered_budget=1, pipeline_stage set to -1 with filter_reason='below_budget_floor'.
    """
    batch_id = uuid.uuid4()
    conn = MagicMock()
    # execute: budget UPDATE returns "UPDATE 1", organic UPDATE returns "UPDATE 0"
    conn.execute = AsyncMock(side_effect=["UPDATE 1", "UPDATE 0"])
    conn.fetchval = AsyncMock(return_value=0)  # 0 passed after gate

    dfs = MagicMock()
    engine = Layer2Discovery(conn=conn, dfs=dfs)

    result = await engine.apply_gate_1(batch_id)

    assert result["filtered_budget"] == 1
    assert result["filtered_organic"] == 0
    assert result["passed"] == 0

    # First execute call must reference 'below_budget_floor' in SQL
    budget_sql = conn.execute.call_args_list[0][0][0]
    assert "below_budget_floor" in budget_sql
    assert "dfs_paid_traffic_cost" in budget_sql


# ─── Test 6: Gate 1 — no organic signal filter ────────────────────────────────


@pytest.mark.asyncio
async def test_discovery_applies_organic_signal_gate():
    """
    apply_gate_1 with a row where dfs_organic_etv=0, dfs_organic_keywords=0:
    → filtered_organic=1, pipeline_stage set to -1 with filter_reason='no_organic_signal'.
    """
    batch_id = uuid.uuid4()
    conn = MagicMock()
    # execute: budget UPDATE returns "UPDATE 0", organic UPDATE returns "UPDATE 1"
    conn.execute = AsyncMock(side_effect=["UPDATE 0", "UPDATE 1"])
    conn.fetchval = AsyncMock(return_value=0)

    dfs = MagicMock()
    engine = Layer2Discovery(conn=conn, dfs=dfs)

    result = await engine.apply_gate_1(batch_id)

    assert result["filtered_organic"] == 1
    assert result["filtered_budget"] == 0

    # Second execute call must reference 'no_organic_signal' in SQL
    organic_sql = conn.execute.call_args_list[1][0][0]
    assert "no_organic_signal" in organic_sql
    assert "dfs_organic_etv" in organic_sql
    assert "dfs_organic_keywords" in organic_sql


# ─── Test 7: inserts valid AU domain to business_universe ─────────────────────


@pytest.mark.asyncio
async def test_discovery_inserts_to_bu():
    """
    Valid AU domain from DFS → INSERT executed with domain, pipeline_stage=1,
    discovery_source='dfs_categories'.
    """
    cfg = {"category_codes": [10233]}
    results = [{"domain": "validagency.com.au", "organic_etv": 400.0, "paid_etv": 100.0}]
    conn = MagicMock()
    # fetchval: dedup check returns None (not existing), gate count returns 1
    conn.fetchval = AsyncMock(side_effect=[None, 1])
    conn.execute = AsyncMock(return_value="UPDATE 0")
    dfs = make_dfs(results=results)
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.domains_inserted == 1

    # The INSERT execute call should include expected values
    insert_call_args = conn.execute.call_args_list[0]
    sql = insert_call_args[0][0]
    positional_args = insert_call_args[0][1:]  # positional args after SQL

    assert "INSERT INTO business_universe" in sql
    assert "validagency.com.au" in positional_args
    assert 1 in positional_args               # pipeline_stage=1
    assert "dfs_categories" in positional_args  # discovery_source


# ─── Test 8: blocklist filters platform domains ────────────────────────────────


@pytest.mark.asyncio
async def test_blocklist_filters_platform_domains():
    """
    DFS returns facebook.com, instagram.com, linkedin.com (all platform domains),
    and acme.com.au. Only acme.com.au passes through the blocklist.
    """
    cfg = {"category_codes": [10233]}
    results = [
        {"domain": "facebook.com", "organic_etv": 500.0, "paid_etv": 100.0},
        {"domain": "instagram.com", "organic_etv": 400.0, "paid_etv": 80.0},
        {"domain": "linkedin.com", "organic_etv": 300.0, "paid_etv": 60.0},
        {"domain": "acme.com.au", "organic_etv": 200.0, "paid_etv": 40.0},
    ]
    conn = make_conn()
    # fetchval: dedup check for acme.com.au returns None (not existing), then gate count
    conn.fetchval = AsyncMock(side_effect=[None, 1])
    conn.execute = AsyncMock(return_value="UPDATE 0")
    dfs = make_dfs(results=results)
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    # Only acme.com.au makes it through; the 3 platform domains are blocked
    assert stats.domains_blocked == 3
    assert stats.domains_inserted == 1


# ─── Test 9: domain normalisation ─────────────────────────────────────────────


def test_domain_normalisation():
    """_normalise_domain strips scheme, www., trailing slash, and lowercases."""
    assert _normalise_domain("https://www.acme.com.au/") == "acme.com.au"
    assert _normalise_domain("WWW.ACME.COM.AU") == "acme.com.au"
    assert _normalise_domain("http://acme.com.au") == "acme.com.au"
    assert _normalise_domain("acme.com.au") == "acme.com.au"


# ─── Test 10: source error does not abort run ──────────────────────────────────


@pytest.mark.asyncio
async def test_source_error_does_not_abort_run():
    """
    If the DFS source raises an exception for a category, run() continues
    and returns a DiscoveryStats dict without propagating the exception.
    """
    cfg = {"category_codes": [10233, 10234]}
    conn = make_conn()
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value="UPDATE 0")

    dfs = MagicMock()
    # First category raises, second succeeds with empty list
    dfs.domain_metrics_by_categories = AsyncMock(
        side_effect=[RuntimeError("DFS timeout"), []]
    )
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    # run() must complete and return DiscoveryStats
    assert isinstance(stats, __import__("src.pipeline.layer_2_discovery", fromlist=["DiscoveryStats"]).DiscoveryStats)
    assert len(stats.source_errors) == 1


# ─── Test 11: idempotency skips existing domain ────────────────────────────────


@pytest.mark.asyncio
async def test_idempotency_skips_existing_domain():
    """
    Domain already in business_universe (fetchval returns 1) is skipped.
    DB INSERT must NOT be called for that domain.
    """
    cfg = {"category_codes": [10233]}
    results = [{"domain": "existing.com.au", "organic_etv": 500.0, "paid_etv": 100.0}]
    conn = make_conn()
    # fetchval: dedup check returns existing row (1), then gate count returns 0
    conn.fetchval = AsyncMock(side_effect=[1, 0])
    conn.execute = AsyncMock(return_value="UPDATE 0")
    dfs = make_dfs(results=results)
    engine = Layer2Discovery(conn=conn, dfs=dfs)
    config = make_signal_config(cfg)

    with patch("src.pipeline.layer_2_discovery.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert stats.domains_deduped == 1
    assert stats.domains_inserted == 0

    # Verify no INSERT was called — only Gate 1 UPDATE calls should be present
    for call_args in conn.execute.call_args_list:
        sql = call_args[0][0]
        assert "INSERT INTO business_universe" not in sql


# ─── Test 12: DiscoverySource.MAPS_SERP raises NotImplementedError ─────────────


@pytest.mark.asyncio
async def test_maps_serp_raises_not_implemented():
    """Layer2Discovery with source=MAPS_SERP must raise NotImplementedError on run()."""
    conn = make_conn()
    dfs = make_dfs()
    engine = Layer2Discovery(conn=conn, dfs=dfs, source=DiscoverySource.MAPS_SERP)

    with pytest.raises(NotImplementedError, match="Maps SERP"):
        await engine.run("marketing_agency")
