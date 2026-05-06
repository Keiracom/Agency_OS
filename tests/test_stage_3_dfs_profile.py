"""Tests for Stage3DFSProfile — Directive #261"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.pipeline.stage_3_dfs_profile import Stage3DFSProfile, PIPELINE_STAGE_S3
from src.enrichment.signal_config import SignalConfig, ServiceSignal


# ─── Fixtures ────────────────────────────────────────────────────────────────


def make_signal_config(technologies: list[str] = None):
    import uuid

    services = [
        ServiceSignal(
            service_name="paid_ads",
            label="Paid Ads",
            dfs_technologies=technologies or ["Google Ads", "Facebook Pixel", "HubSpot"],
            gmb_categories=[],
            scoring_weights={},
        )
    ]
    return SignalConfig(
        id=str(uuid.uuid4()),
        vertical="marketing_agency",
        services=services,
        discovery_config={},
        enrichment_gates={},
        competitor_config={},
        channel_config={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


MOCK_RANK_DATA = {
    "dfs_organic_etv": 1250.50,
    "dfs_paid_etv": 340.0,
    "dfs_organic_keywords": 450,
    "dfs_paid_keywords": 28,
    "dfs_organic_pos_1": 5,
    "dfs_organic_pos_2_3": 12,
    "dfs_organic_pos_4_10": 45,
    "dfs_organic_pos_11_20": 88,
}

MOCK_TECH_DATA = {
    "tech_stack": ["Google Ads", "WordPress", "Google Analytics"],
    "tech_categories": {
        "cms": {"wordpress": ["WordPress"]},
        "analytics": {"google_analytics": ["Google Analytics"]},
    },
    "tech_stack_depth": 3,
}


def make_dfs_client(rank_data=MOCK_RANK_DATA, tech_data=MOCK_TECH_DATA):
    client = MagicMock()
    client.total_cost_usd = 0.03
    client.domain_rank_overview = AsyncMock(return_value=rank_data)
    client.domain_technologies = AsyncMock(return_value=tech_data)
    return client


def make_row(domain="example.com.au", row_id="uuid-1"):
    row = MagicMock()
    row.__getitem__ = lambda self, k: {"id": row_id, "domain": domain}[k]
    return row


def make_conn(rows=None):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows or [make_row()])
    conn.execute = AsyncMock(return_value=None)
    return conn


def make_stage(rank_data=MOCK_RANK_DATA, tech_data=MOCK_TECH_DATA, rows=None, technologies=None):
    dfs = make_dfs_client(rank_data, tech_data)
    signal_repo = MagicMock()
    signal_repo.get_config = AsyncMock(return_value=make_signal_config(technologies))
    conn = make_conn(rows)
    stage = Stage3DFSProfile(dfs, signal_repo, conn, delay=0)
    return stage, dfs, signal_repo, conn


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_profiles_s2_domains_with_rank_and_tech():
    """run() calls both DFS endpoints and writes all fields to BU."""
    stage, dfs, repo, conn = make_stage()
    result = await stage.run("marketing_agency")
    assert result["profiled"] == 1
    assert result["api_errors"] == 0
    dfs.domain_rank_overview.assert_called_once()
    dfs.domain_technologies.assert_called_once()
    conn.execute.assert_called_once()
    update_sql = conn.execute.call_args[0][0]
    assert "dfs_organic_etv" in update_sql
    assert "tech_stack" in update_sql


@pytest.mark.asyncio
async def test_calculates_tech_gaps_from_signal_config():
    """tech_gaps = signal technologies NOT in detected tech_stack."""
    # Signal wants: Google Ads, Facebook Pixel, HubSpot
    # Domain has:   Google Ads, WordPress, Google Analytics
    # Expected gaps: Facebook Pixel, HubSpot
    stage, dfs, repo, conn = make_stage(technologies=["Google Ads", "Facebook Pixel", "HubSpot"])
    await stage.run("marketing_agency")
    update_sql = conn.execute.call_args[0][0]
    update_args = conn.execute.call_args[0]
    # Find the tech_gaps value — it will be a list
    gaps = None
    for arg in update_args:
        if isinstance(arg, list) and any(t in ["Facebook Pixel", "HubSpot"] for t in (arg or [])):
            gaps = arg
            break
    assert gaps is not None
    assert "Facebook Pixel" in gaps
    assert "HubSpot" in gaps
    assert "Google Ads" not in gaps  # domain already has it


@pytest.mark.asyncio
async def test_calculates_tech_stack_depth():
    """tech_stack_depth = count of detected technologies."""
    stage, _, _, conn = make_stage()
    await stage.run("marketing_agency")
    args = conn.execute.call_args[0]
    # tech_stack_depth should be 3 (matching MOCK_TECH_DATA)
    assert 3 in args


@pytest.mark.asyncio
async def test_handles_no_rank_data():
    """If rank endpoint returns None, still progress to stage 3."""
    stage, dfs, repo, conn = make_stage(rank_data=None)
    result = await stage.run("marketing_agency")
    assert result["profiled"] == 1
    assert result["api_errors"] == 0
    conn.execute.assert_called_once()
    update_sql = conn.execute.call_args[0][0]
    assert "pipeline_stage" in update_sql


@pytest.mark.asyncio
async def test_handles_no_tech_data():
    """If tech endpoint returns None, still progress to stage 3."""
    stage, dfs, repo, conn = make_stage(tech_data=None)
    result = await stage.run("marketing_agency")
    assert result["profiled"] == 1
    conn.execute.assert_called_once()
    update_sql = conn.execute.call_args[0][0]
    assert "pipeline_stage" in update_sql
    # tech_stack should NOT appear in update (no data)
    assert "tech_stack" not in update_sql


@pytest.mark.asyncio
async def test_respects_batch_size():
    """run() passes batch_size LIMIT to the DB query."""
    stage, _, _, conn = make_stage()
    await stage.run("marketing_agency", batch_size=10)
    fetch_sql = conn.fetch.call_args[0][0]
    assert "LIMIT" in fetch_sql
    assert conn.fetch.call_args[0][1] == 10


@pytest.mark.asyncio
async def test_tracks_cost_accurately():
    """result includes cost_usd from DFS client."""
    stage, dfs, _, _ = make_stage()
    dfs.total_cost_usd = 0.09  # 3 domains * $0.03
    result = await stage.run("marketing_agency")
    assert result["cost_usd"] == 0.09
    assert result["cost_aud"] == round(0.09 * 1.55, 4)


@pytest.mark.asyncio
async def test_updates_pipeline_stage_to_3():
    """pipeline_stage=3 is written after S3 processing."""
    stage, _, _, conn = make_stage()
    await stage.run("marketing_agency")
    args = conn.execute.call_args[0]
    assert PIPELINE_STAGE_S3 in args


@pytest.mark.asyncio
async def test_maps_dfs_fields_to_bu_columns_correctly():
    """All rank fields from domain_rank_overview appear in the UPDATE."""
    stage, _, _, conn = make_stage()
    await stage.run("marketing_agency")
    update_sql = conn.execute.call_args[0][0]
    expected_cols = [
        "dfs_organic_etv",
        "dfs_paid_etv",
        "dfs_organic_keywords",
        "dfs_paid_keywords",
        "dfs_organic_pos_1",
        "dfs_organic_pos_2_3",
        "dfs_organic_pos_4_10",
        "dfs_organic_pos_11_20",
        "dfs_rank_fetched_at",
        "tech_stack",
        "tech_categories",
        "tech_stack_depth",
        "tech_gaps",
        "dfs_tech_fetched_at",
        "pipeline_stage",
        "pipeline_updated_at",
    ]
    for col in expected_cols:
        assert col in update_sql, f"Expected column '{col}' in UPDATE but not found"


# ─── BUG-265-2 regression tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_skips_null_domain_rows():
    """Rows with NULL domain should be skipped, not cause DFS errors."""
    null_row = MagicMock()
    null_row.__getitem__ = lambda self, k: {"id": "uuid-null", "domain": None}[k]
    stage, dfs, _, conn = make_stage(rows=[null_row])
    result = await stage.run("marketing_agency")
    # Row is skipped — no DFS call, no error count
    dfs.domain_rank_overview.assert_not_called()
    dfs.domain_technologies.assert_not_called()
    assert result["api_errors"] == 0
    assert result["profiled"] == 0
