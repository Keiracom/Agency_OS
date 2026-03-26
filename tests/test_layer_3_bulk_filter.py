"""Tests for Layer3BulkFilter — Directive #274"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.enrichment.signal_config import ServiceSignal, SignalConfig
from src.pipeline.layer_3_bulk_filter import FilterStats, Layer3BulkFilter


# ─── Fixtures ────────────────────────────────────────────────────────────────


def make_signal_config(enrichment_gates: dict | None = None) -> SignalConfig:
    """Build a minimal SignalConfig with given enrichment_gates."""
    return SignalConfig(
        id=str(uuid.uuid4()),
        vertical="marketing_agency",
        services=[
            ServiceSignal(
                service_name="paid_ads",
                label="Paid Ads",
            )
        ],
        discovery_config={},
        enrichment_gates=enrichment_gates or {},
        competitor_config={},
        channel_config={"email": True},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_domain_row(domain: str, row_id: str | None = None) -> MagicMock:
    """Create an asyncpg-Record-like mock with id and domain."""
    row = MagicMock()
    row.__getitem__ = MagicMock(side_effect=lambda k: {
        "id": row_id or str(uuid.uuid4()),
        "domain": domain,
    }[k])
    return row


def make_conn(
    fetch_rows: list | None = None,
    execute_result: str = "UPDATE 0",
) -> MagicMock:
    """Build a mock asyncpg connection."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=fetch_rows or [])
    conn.execute = AsyncMock(return_value=execute_result)
    conn.fetchrow = AsyncMock(return_value=None)
    return conn


def make_dfs(metrics: list | None = None) -> MagicMock:
    """Build a mock DFSLabsClient with bulk_domain_metrics returning given metrics."""
    dfs = MagicMock()
    dfs.bulk_domain_metrics = AsyncMock(return_value=metrics or [])
    return dfs


def make_engine(
    fetch_rows: list | None = None,
    execute_result: str = "UPDATE 0",
    metrics: list | None = None,
    enrichment_gates: dict | None = None,
    config: SignalConfig | None = None,
) -> tuple[Layer3BulkFilter, MagicMock, MagicMock]:
    """Assemble Layer3BulkFilter with mocked dependencies."""
    conn = make_conn(fetch_rows=fetch_rows, execute_result=execute_result)
    dfs = make_dfs(metrics=metrics)
    engine = Layer3BulkFilter(conn=conn, dfs=dfs)
    return engine, conn, dfs


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reads_pipeline_stage_1_domains():
    """run() fetches only pipeline_stage=1, no_domain=false rows from BU."""
    engine, conn, dfs = make_engine()
    config = make_signal_config()

    with patch("src.pipeline.layer_3_bulk_filter.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        await engine.run("marketing_agency")

    # conn.fetch called for the domain query
    fetch_calls = conn.fetch.call_args_list
    assert len(fetch_calls) == 1
    sql = fetch_calls[0][0][0]
    assert "pipeline_stage = 1" in sql
    assert "no_domain = false" in sql


@pytest.mark.asyncio
async def test_batching_1001_domains_splits_into_two_calls():
    """1001 domains → bulk_domain_metrics called twice (batches of 1000 + 1)."""
    domain_ids = [str(uuid.uuid4()) for _ in range(1001)]
    domains = [f"domain{i}.com" for i in range(1001)]
    rows = [make_domain_row(d, domain_ids[i]) for i, d in enumerate(domains)]
    metrics = [
        {"domain": d, "organic_etv": 50.0, "paid_etv": 0.0, "backlinks_count": 10, "domain_rank": 20}
        for d in domains
    ]
    engine, conn, dfs = make_engine(fetch_rows=rows, metrics=metrics[:1000], execute_result="UPDATE 1")
    # Second call returns metrics for the remaining 1 domain
    dfs.bulk_domain_metrics = AsyncMock(side_effect=[metrics[:1000], metrics[1000:]])
    config = make_signal_config()

    with patch("src.pipeline.layer_3_bulk_filter.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)

    assert dfs.bulk_domain_metrics.call_count == 2
    assert stats.batches_called == 2
    assert stats.total_processed == 1001


@pytest.mark.asyncio
async def test_pass_threshold_organic_etv_above_zero():
    """Domain with organic_etv=50 passes → pipeline_stage=2 update issued."""
    domain_id = str(uuid.uuid4())
    rows = [make_domain_row("example.com", domain_id)]
    metrics = [{"domain": "example.com", "organic_etv": 50.0, "paid_etv": 0.0, "backlinks_count": 0, "domain_rank": 0}]
    engine, conn, dfs = make_engine(fetch_rows=rows, metrics=metrics, execute_result="UPDATE 1")
    config = make_signal_config()

    with patch("src.pipeline.layer_3_bulk_filter.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency")

    assert stats.passed == 1
    assert stats.rejected == 0
    # The UPDATE for passing should set pipeline_stage=2
    domain_update_calls = [c for c in conn.execute.call_args_list if "pipeline_stage = 2" in str(c)]
    assert len(domain_update_calls) >= 1


@pytest.mark.asyncio
async def test_reject_threshold_all_zeros():
    """Domain with organic_etv=0, paid_etv=0, backlinks=0 → rejected, filter_reason set."""
    domain_id = str(uuid.uuid4())
    rows = [make_domain_row("dead.com", domain_id)]
    metrics = [{"domain": "dead.com", "organic_etv": 0.0, "paid_etv": 0.0, "backlinks_count": 0, "domain_rank": 0}]
    engine, conn, dfs = make_engine(fetch_rows=rows, metrics=metrics, execute_result="UPDATE 1")
    config = make_signal_config()

    with patch("src.pipeline.layer_3_bulk_filter.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency")

    assert stats.rejected == 1
    assert stats.passed == 0
    # The UPDATE for rejecting should set pipeline_stage=-1
    reject_calls = [c for c in conn.execute.call_args_list if "pipeline_stage = -1" in str(c)]
    assert len(reject_calls) >= 1
    # filter_reason 'bulk_metrics_below_threshold' should appear in the call args
    all_call_args = str(conn.execute.call_args_list)
    assert "bulk_metrics_below_threshold" in all_call_args


@pytest.mark.asyncio
async def test_no_domain_rows_advanced_without_api_call():
    """When no_domain rows exist, they get stage=2 update, bulk_domain_metrics NOT called."""
    # conn.execute returns UPDATE 3 for the no_domain passthrough,
    # then conn.fetch returns empty (no further domains)
    conn = make_conn(fetch_rows=[], execute_result="UPDATE 3")
    dfs = make_dfs()
    engine = Layer3BulkFilter(conn=conn, dfs=dfs)
    config = make_signal_config()

    with patch("src.pipeline.layer_3_bulk_filter.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency")

    assert stats.no_domain_advanced == 3
    dfs.bulk_domain_metrics.assert_not_called()


@pytest.mark.asyncio
async def test_filter_reason_populated_on_reject():
    """Rejected domain must have filter_reason='bulk_metrics_below_threshold' in its UPDATE."""
    domain_id = str(uuid.uuid4())
    rows = [make_domain_row("parked.com", domain_id)]
    metrics = [{"domain": "parked.com", "organic_etv": 0.0, "paid_etv": 0.0, "backlinks_count": 2, "domain_rank": 0}]
    # backlinks=2 < DEFAULT_MIN_BACKLINKS=5 → reject
    engine, conn, dfs = make_engine(fetch_rows=rows, metrics=metrics, execute_result="UPDATE 1")
    config = make_signal_config()

    with patch("src.pipeline.layer_3_bulk_filter.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency")

    assert stats.rejected == 1
    # Verify the reject UPDATE included the filter_reason value
    reject_calls = [c for c in conn.execute.call_args_list if "filter_reason" in str(c)]
    assert len(reject_calls) >= 1
    assert "bulk_metrics_below_threshold" in str(reject_calls[0])


@pytest.mark.asyncio
async def test_budget_cap_stops_batching():
    """daily_budget_usd=0.0001 → budget exceeded before first batch, budget_exceeded=True."""
    domain_id = str(uuid.uuid4())
    rows = [make_domain_row("example.com", domain_id)]
    engine, conn, dfs = make_engine(fetch_rows=rows)
    config = make_signal_config()

    with patch("src.pipeline.layer_3_bulk_filter.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=0.0001)

    assert stats.budget_exceeded is True
    dfs.bulk_domain_metrics.assert_not_called()
    assert stats.batches_called == 0


@pytest.mark.asyncio
async def test_cost_tracking_correct():
    """500 domains → estimated_cost_usd ≈ 0.50 (500 * $0.001)."""
    domain_ids = [str(uuid.uuid4()) for _ in range(500)]
    domains = [f"site{i}.com" for i in range(500)]
    rows = [make_domain_row(d, domain_ids[i]) for i, d in enumerate(domains)]
    metrics = [
        {"domain": d, "organic_etv": 10.0, "paid_etv": 0.0, "backlinks_count": 8, "domain_rank": 15}
        for d in domains
    ]
    engine, conn, dfs = make_engine(fetch_rows=rows, metrics=metrics, execute_result="UPDATE 1")
    config = make_signal_config()

    with patch("src.pipeline.layer_3_bulk_filter.SignalConfigRepository") as MockRepo:
        MockRepo.return_value.get_config = AsyncMock(return_value=config)
        stats = await engine.run("marketing_agency", daily_budget_usd=100.0)

    assert abs(stats.estimated_cost_usd - 0.50) < 0.001
    assert stats.batches_called == 1
    assert stats.total_processed == 500
