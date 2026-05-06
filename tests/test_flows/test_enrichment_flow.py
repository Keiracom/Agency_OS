"""
FILE: tests/test_flows/test_enrichment_flow.py
PURPOSE: Unit tests for daily enrichment flow
PHASE: 5 (Orchestration)
TASK: ORC-003

NOTE: Per Directive #155, tests requiring real DB integration have been deleted.
Only tests with proper mocking are retained.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.base import EngineResult
from src.orchestration.flows.enrichment_flow import (
    enrich_lead_batch_task,
    get_leads_needing_enrichment_task,
)


# ============================================
# Tests: get_leads_needing_enrichment_task
# ============================================


@pytest.mark.asyncio
async def test_get_leads_needing_enrichment_success():
    """Test getting leads needing enrichment with JIT validation."""
    lead_ids = [uuid4(), uuid4(), uuid4()]
    client_id = uuid4()

    with patch("src.orchestration.flows.enrichment_flow.get_db_session") as mock_get_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()  # Sync mock - result.all() is not async
        # Mock query result: (lead_id, client_id, campaign_id, credits)
        mock_result.all.return_value = [
            (lead_ids[0], client_id, uuid4(), 1000),
            (lead_ids[1], client_id, uuid4(), 1000),
            (lead_ids[2], client_id, uuid4(), 1000),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await get_leads_needing_enrichment_task.fn(limit=100)

        assert result["total_leads"] == 3
        assert result["client_count"] == 1
        assert str(client_id) in result["leads_by_client"]


@pytest.mark.asyncio
async def test_get_leads_needing_enrichment_no_leads():
    """Test getting leads when none are available."""
    with patch("src.orchestration.flows.enrichment_flow.get_db_session") as mock_get_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()  # Sync mock - result.all() is not async
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await get_leads_needing_enrichment_task.fn(limit=100)

        assert result["total_leads"] == 0
        assert result["client_count"] == 0


# ============================================
# Tests: enrich_lead_batch_task
# ============================================


@pytest.mark.asyncio
async def test_enrich_lead_batch_success():
    """Test enriching a batch of leads."""
    lead_ids = [str(uuid4()), str(uuid4())]
    client_id = str(uuid4())

    with (
        patch("src.orchestration.flows.enrichment_flow.get_db_session") as mock_get_session,
        patch("src.orchestration.flows.enrichment_flow.get_scout_engine") as mock_get_scout,
    ):
        # Mock database
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        # Mock scout engine
        mock_scout = MagicMock()
        mock_scout.enrich_batch = AsyncMock(
            return_value=EngineResult.ok(
                data={
                    "total": 2,
                    "tier1_success": 2,
                    "tier2_success": 0,
                    "failures": 0,
                }
            )
        )
        mock_get_scout.return_value = mock_scout

        result = await enrich_lead_batch_task.fn(lead_ids, client_id)

        assert result["success"] is True
        assert result["total"] == 2
        assert result["data"]["tier1_success"] == 2


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Tests for get_leads_needing_enrichment_task
# [x] Tests for enrich_lead_batch_task
# [DELETED] Tests for score_lead_task - requires real DB
# [DELETED] Tests for allocate_channels_for_lead_task - requires real DB
# [DELETED] Tests for deduct_client_credits_task - requires real DB
# [DELETED] Tests for daily_enrichment_flow - requires real DB
# Per Directive #155: "If tests require real DB/integration: DELETE — do not skip"
