"""
Integration tests for stage_9_10_flow.py — P4

Tests use mocked pool and stage classes. No DB or AI calls are made.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestration.flows.stage_9_10_flow import (
    stage_9_10_pipeline,
    verify_stage_9,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AGENCY_PROFILE = {
    "name": "Test Agency",
    "services": ["SEO", "Paid Ads"],
    "tone": "professional",
    "founder_name": "Alex",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pool(fetchval_return=None, fetch_return=None):
    """Return a mock asyncpg.Pool with acquire() context manager."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=fetchval_return)
    conn.fetch = AsyncMock(return_value=fetch_return or [])

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    pool.close = AsyncMock()
    return pool, conn


# ---------------------------------------------------------------------------
# test_flow_dry_run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flow_dry_run():
    """Dry run returns bdm_count without calling Stage 9 or Stage 10."""
    with (
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool,
        patch(
            "src.orchestration.flows.stage_9_10_flow.Stage9VulnerabilityEnrichment"
        ) as mock_s9_cls,
        patch("src.orchestration.flows.stage_9_10_flow.Stage10MessageGenerator") as mock_s10_cls,
    ):
        pool, conn = _make_pool()
        # select_bdms with explicit bdm_ids won't touch DB
        mock_create_pool.return_value = pool

        result = await stage_9_10_pipeline.fn(
            bdm_ids=["fake-id"],
            agency_profile=AGENCY_PROFILE,
            dry_run=True,
        )

    assert result["dry_run"] is True
    assert result["bdm_count"] == 1
    assert result["bdm_ids"] == ["fake-id"]
    assert "cost_estimate" in result
    assert result["cost_estimate"]["total_usd"] > 0
    assert "expected_writes" in result
    assert result["expected_writes"]["dm_messages"] == 4  # 1 BDM × 4 channels
    assert result["within_budget"] is True
    mock_s9_cls.assert_not_called()
    mock_s10_cls.assert_not_called()


# ---------------------------------------------------------------------------
# test_budget_cap_enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_cap_enforcement():
    """Budget cap triggers ValueError before Stage 9 is called."""
    with (
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool,
        patch(
            "src.orchestration.flows.stage_9_10_flow.Stage9VulnerabilityEnrichment"
        ) as mock_s9_cls,
    ):
        pool, _ = _make_pool()
        mock_create_pool.return_value = pool

        with pytest.raises(ValueError, match="Estimated cost"):
            await stage_9_10_pipeline.fn(
                bdm_ids=["id1", "id2", "id3"],
                agency_profile=AGENCY_PROFILE,
                budget_cap_usd=0.001,
                dry_run=False,
            )

    mock_s9_cls.assert_not_called()


# ---------------------------------------------------------------------------
# test_stage_9_verification_gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_9_verification_gate():
    """If VR count is less than selected, RuntimeError is raised."""
    with (
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool,
        patch(
            "src.orchestration.flows.stage_9_10_flow.select_bdms",
            new=AsyncMock(return_value=["id1"]),
        ),
        patch(
            "src.orchestration.flows.stage_9_10_flow.run_stage_9",
            new=AsyncMock(return_value={"cost_total_usd": 0.05}),
        ),
        patch(
            "src.orchestration.flows.stage_9_10_flow.verify_stage_9",
            new=AsyncMock(return_value=0),  # 0 VRs < 1 selected → RuntimeError
        ),
        patch(
            "src.orchestration.flows.stage_9_10_flow.Stage9VulnerabilityEnrichment"
        ) as mock_s9_cls,
        patch("src.orchestration.flows.stage_9_10_flow.Stage10MessageGenerator") as mock_s10_cls,
    ):
        pool, conn = _make_pool(fetchval_return=0)
        mock_create_pool.return_value = pool

        mock_s9_instance = AsyncMock()
        mock_s9_instance.run = AsyncMock(return_value={"cost_total_usd": 0.05})
        mock_s9_cls.return_value = mock_s9_instance

        with pytest.raises(RuntimeError, match="Stage 9 incomplete"):
            await stage_9_10_pipeline.fn(
                bdm_ids=["id1"],
                agency_profile=AGENCY_PROFILE,
                budget_cap_usd=5.0,
                dry_run=False,
            )

    mock_s10_cls.assert_not_called()


# ---------------------------------------------------------------------------
# test_post_s9_budget_exhaustion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_s9_budget_exhaustion():
    """Budget exhausted after Stage 9 halts before Stage 10."""
    with (
        patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool,
        patch(
            "src.orchestration.flows.stage_9_10_flow.Stage9VulnerabilityEnrichment"
        ) as mock_s9_cls,
        patch("src.orchestration.flows.stage_9_10_flow.Stage10MessageGenerator") as mock_s10_cls,
    ):
        pool, conn = _make_pool(fetchval_return=1)  # VR verification passes
        mock_create_pool.return_value = pool

        mock_s9_instance = AsyncMock()
        mock_s9_instance.run = AsyncMock(return_value={"cost_total_usd": 10.0})
        mock_s9_cls.return_value = mock_s9_instance

        with pytest.raises(ValueError, match="Budget exhausted after Stage 9"):
            await stage_9_10_pipeline.fn(
                bdm_ids=["id1"],
                agency_profile=AGENCY_PROFILE,
                budget_cap_usd=5.0,
                dry_run=False,
            )

    mock_s10_cls.assert_not_called()


# ---------------------------------------------------------------------------
# test_on_failure_hook_wired
# ---------------------------------------------------------------------------


def test_on_failure_hook_wired():
    """Flow has on_failure hook configured for TG alerting."""
    from src.orchestration.flows.stage_9_10_flow import stage_9_10_pipeline as flow_obj
    from src.prefect_utils.hooks import on_failure_hook

    assert on_failure_hook in flow_obj.on_failure_hooks
