"""
FILE: tests/test_flows/test_directive_196_resilience.py
PURPOSE: Tests for Directive #196 — Pipeline Resilience
         - BD _scraper_request retry on timeout
         - Pool population graceful return when GMB returns 0 records
         - Per-tier graceful degradation in enrich_lead
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ============================================
# FIX 5: test_pool_population_handles_empty_gmb
# ============================================

@pytest.mark.asyncio
async def test_pool_population_handles_empty_gmb():
    """
    FIX 5: populate_pool_from_icp_task should return success with added=0 when
    BD returns 0 records (even after the fallback retry), rather than crashing.
    """
    from src.orchestration.flows.pool_population_flow import populate_pool_from_icp_task

    client_id = uuid4()
    icp_criteria = {
        "icp_industries": ["marketing"],
        "icp_locations": ["Australia"],
    }

    # Mock BD client: both primary and fallback calls return empty list
    mock_bd = AsyncMock()
    mock_bd._scraper_request = AsyncMock(return_value=[])

    with (
        patch(
            "src.integrations.bright_data_client.get_bright_data_client",
            return_value=mock_bd,
        ),
    ):
        result = await populate_pool_from_icp_task.fn(
            client_id=client_id,
            icp_criteria=icp_criteria,
            limit=25,
        )

    assert result["success"] is True
    assert result["added"] == 0
    assert result.get("fallback") == "no_gmb_records"


# ============================================
# FIX 3: test_enrich_tier_failure_continues
# ============================================

@pytest.mark.asyncio
async def test_enrich_tier_failure_continues():
    """
    FIX 3: When one enrichment tier raises an unexpected exception, subsequent tiers
    must still run. Specifically: T1 ABN raising should NOT prevent T3 Leadmagic.
    """
    from src.integrations.siege_waterfall import EnrichmentTier, SiegeWaterfall, TierResult

    waterfall = SiegeWaterfall()

    # T1 ABN: raises an unexpected exception
    async def boom_abn(lead):
        raise RuntimeError("ABN service exploded")

    # T1.5 LinkedIn: returns skipped (no URL)
    async def skip_linkedin(lead, icp_passed=True):
        return TierResult(
            tier=EnrichmentTier.LINKEDIN_COMPANY,
            success=False,
            skipped=True,
            skip_reason="No company LinkedIn URL available",
        )

    # T3 Leadmagic: returns success (verifies it ran despite T1 failure)
    async def success_leadmagic(lead):
        return TierResult(
            tier=EnrichmentTier.LEADMAGIC_EMAIL,
            success=True,
            data={"email": "test@example.com"},
            cost_aud=0.015,
        )

    # T2 GMB: returns skipped
    async def skip_gmb(lead):
        return TierResult(
            tier=EnrichmentTier.GMB,
            success=False,
            skipped=True,
            skip_reason="T0 discovery already has GMB data (T0/T2 merge)",
        )

    # T5: skipped
    async def skip_t5(lead, als, force=False):
        return TierResult(
            tier=EnrichmentTier.IDENTITY,
            success=False,
            skipped=True,
            skip_reason="ALS 40 < 85 threshold",
        )

    waterfall.tier1_abn = boom_abn
    waterfall.tier1_5_linkedin_company = skip_linkedin
    waterfall.tier2_gmb = skip_gmb
    waterfall.tier3_leadmagic_email = success_leadmagic
    waterfall.tier5_identity = skip_t5

    # Also mock resolve_linkedin_url — tag linkedin_url_unknown=True so SIZE_GATE is bypassed
    async def skip_resolve(lead):
        return TierResult(
            tier=EnrichmentTier.LINKEDIN_COMPANY,
            success=False,
            data={"linkedin_url_unknown": True},  # Bypass SIZE_GATE (Directive #148)
            skip_reason="No company LinkedIn URL found via SERP",
        )

    waterfall.resolve_linkedin_url = skip_resolve

    # Patch _calculate_als to return 40 (above T3 gate of 35, below T5 gate of 85)
    with patch.object(waterfall, "_calculate_als", return_value=40):
        result = await waterfall.enrich_lead(
            {
                "company_name": "Acme Corp",
                "email": "owner@acme.com.au",
                "domain": "acme.com.au",
                "company_linkedin_url": None,
            },
            skip_tiers=[],
        )

    # T1 failed (exception swallowed) — should appear as failed tier
    t1_results = [r for r in result.tier_results if r.tier == EnrichmentTier.ABN]
    assert len(t1_results) == 1
    assert t1_results[0].success is False
    assert "ABN service exploded" in (t1_results[0].error or "")

    # T3 Leadmagic should have succeeded (proving it ran despite T1 failure)
    t3_results = [r for r in result.tier_results if r.tier == EnrichmentTier.LEADMAGIC_EMAIL]
    assert len(t3_results) == 1, "Tier 3 should have run despite Tier 1 failure"
    assert t3_results[0].success is True, "Tier 3 should have succeeded"

    # At least 1 source used (T3)
    assert result.sources_used >= 1


# ============================================
# FIX 1: test_scraper_request_retries_on_timeout
# ============================================

@pytest.mark.asyncio
async def test_scraper_request_retries_on_timeout():
    """
    FIX 1: _scraper_request should retry once (with 30s wait) when the first
    attempt times out, and succeed on the second attempt.
    """
    from src.integrations.bright_data_client import BrightDataClient, BrightDataError

    call_count = 0

    async def mock_attempt(dataset_id, inputs, discover_by=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise BrightDataError("Scraper timeout for snapshot snap-abc123")
        return [{"name": "Test Biz"}]

    client = BrightDataClient.__new__(BrightDataClient)
    client._scraper_request_attempt = mock_attempt

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client._scraper_request("ds-123", [{"keyword": "plumber", "country": "AU"}])

    assert call_count == 2, "Should have retried exactly once"
    assert result == [{"name": "Test Biz"}]
    # Verify 30s wait between attempts
    mock_sleep.assert_called_once_with(30)
