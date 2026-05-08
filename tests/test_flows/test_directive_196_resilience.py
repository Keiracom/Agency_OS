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
# REMOVED: src/integrations/siege_waterfall.py was deleted in 89272b2d
# (PR-A cleanup, "replaced by current pipeline waterfall"). The
# SiegeWaterfall class and its EnrichmentTier/TierResult types no longer
# exist; the per-tier graceful-degradation guarantee this test asserted
# now lives in src/pipeline/ and should be re-tested there if needed.


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
