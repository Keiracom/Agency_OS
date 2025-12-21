"""
FILE: tests/test_flows/test_enrichment_flow.py
PURPOSE: Unit tests for daily enrichment flow
PHASE: 5 (Orchestration)
TASK: ORC-003
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.base import EngineResult
from src.models.base import CampaignStatus, LeadStatus, SubscriptionStatus
from src.orchestration.flows.enrichment_flow import (
    allocate_channels_for_lead_task,
    daily_enrichment_flow,
    deduct_client_credits_task,
    enrich_lead_batch_task,
    get_leads_needing_enrichment_task,
    score_lead_task,
)


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


# ============================================
# Tests: get_leads_needing_enrichment_task
# ============================================


@pytest.mark.asyncio
async def test_get_leads_needing_enrichment_success():
    """Test getting leads needing enrichment with JIT validation."""
    lead_ids = [uuid4(), uuid4(), uuid4()]
    client_id = uuid4()

    with patch(
        "src.orchestration.flows.enrichment_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        # Mock query result: (lead_id, client_id, campaign_id, credits)
        mock_result.all = AsyncMock(
            return_value=[
                (lead_ids[0], client_id, uuid4(), 1000),
                (lead_ids[1], client_id, uuid4(), 1000),
                (lead_ids[2], client_id, uuid4(), 1000),
            ]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await get_leads_needing_enrichment_task(limit=100)

        assert result["total_leads"] == 3
        assert result["client_count"] == 1
        assert str(client_id) in result["leads_by_client"]


@pytest.mark.asyncio
async def test_get_leads_needing_enrichment_no_leads():
    """Test getting leads when none are available."""
    with patch(
        "src.orchestration.flows.enrichment_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.all = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await get_leads_needing_enrichment_task(limit=100)

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

    with patch(
        "src.orchestration.flows.enrichment_flow.get_db_session"
    ) as mock_get_session, patch(
        "src.orchestration.flows.enrichment_flow.get_scout_engine"
    ) as mock_get_scout:
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

        result = await enrich_lead_batch_task(lead_ids, client_id)

        assert result["success"] is True
        assert result["total"] == 2
        assert result["data"]["tier1_success"] == 2


# ============================================
# Tests: score_lead_task
# ============================================


@pytest.mark.asyncio
async def test_score_lead_success():
    """Test scoring a lead."""
    lead_id = str(uuid4())

    with patch(
        "src.orchestration.flows.enrichment_flow.get_db_session"
    ) as mock_get_session, patch(
        "src.orchestration.flows.enrichment_flow.get_scorer_engine"
    ) as mock_get_scorer:
        # Mock database
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        # Mock scorer engine
        mock_scorer = MagicMock()
        mock_scorer.calculate_als = AsyncMock(
            return_value=EngineResult.ok(
                data={
                    "als_score": 85,
                    "als_tier": "hot",
                }
            )
        )
        mock_get_scorer.return_value = mock_scorer

        result = await score_lead_task(lead_id)

        assert result["success"] is True
        assert result["als_score"] == 85
        assert result["als_tier"] == "hot"


# ============================================
# Tests: allocate_channels_for_lead_task
# ============================================


@pytest.mark.asyncio
async def test_allocate_channels_success():
    """Test allocating channels for a lead."""
    lead_id = str(uuid4())
    als_tier = "hot"

    with patch(
        "src.orchestration.flows.enrichment_flow.get_db_session"
    ) as mock_get_session, patch(
        "src.orchestration.flows.enrichment_flow.get_allocator_engine"
    ) as mock_get_allocator:
        # Mock database
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        # Mock allocator engine
        mock_allocator = MagicMock()
        mock_allocator.allocate_channels = AsyncMock(
            return_value=EngineResult.ok(
                data={
                    "channels": ["email", "linkedin", "sms"],
                }
            )
        )
        mock_get_allocator.return_value = mock_allocator

        result = await allocate_channels_for_lead_task(lead_id, als_tier)

        assert result["success"] is True
        assert len(result["channels"]) == 3


@pytest.mark.asyncio
async def test_allocate_channels_dead_tier():
    """Test allocating channels for dead tier (should fail)."""
    lead_id = str(uuid4())

    result = await allocate_channels_for_lead_task(lead_id, "dead")

    assert result["success"] is False
    assert "No channels" in result["error"]


# ============================================
# Tests: deduct_client_credits_task
# ============================================


@pytest.mark.asyncio
async def test_deduct_client_credits_success():
    """Test deducting credits from client."""
    client_id = str(uuid4())
    credits_to_deduct = 5

    with patch(
        "src.orchestration.flows.enrichment_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=995)  # New balance
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await deduct_client_credits_task(client_id, credits_to_deduct)

        assert result["credits_deducted"] == 5
        assert result["credits_remaining"] == 995
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_deduct_client_credits_insufficient():
    """Test deducting credits when client has insufficient balance."""
    client_id = str(uuid4())

    with patch(
        "src.orchestration.flows.enrichment_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)  # Failed
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.rollback = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        with pytest.raises(ValueError, match="Failed to deduct"):
            await deduct_client_credits_task(client_id, 10)


# ============================================
# Tests: daily_enrichment_flow
# ============================================


@pytest.mark.asyncio
async def test_daily_enrichment_flow_no_leads():
    """Test daily enrichment flow with no leads."""
    with patch(
        "src.orchestration.flows.enrichment_flow.get_leads_needing_enrichment_task"
    ) as mock_get_leads:
        mock_get_leads.return_value = {
            "total_leads": 0,
            "client_count": 0,
            "leads_by_client": {},
        }

        result = await daily_enrichment_flow(batch_size=100)

        assert result["total_leads"] == 0
        assert "No leads" in result["message"]


@pytest.mark.asyncio
async def test_daily_enrichment_flow_success():
    """Test successful daily enrichment flow."""
    client_id = str(uuid4())
    lead_ids = [str(uuid4()), str(uuid4())]

    with patch(
        "src.orchestration.flows.enrichment_flow.get_leads_needing_enrichment_task"
    ) as mock_get_leads, patch(
        "src.orchestration.flows.enrichment_flow.enrich_lead_batch_task"
    ) as mock_enrich, patch(
        "src.orchestration.flows.enrichment_flow.score_lead_task"
    ) as mock_score, patch(
        "src.orchestration.flows.enrichment_flow.allocate_channels_for_lead_task"
    ) as mock_allocate, patch(
        "src.orchestration.flows.enrichment_flow.deduct_client_credits_task"
    ) as mock_deduct:

        # Mock getting leads
        mock_get_leads.return_value = {
            "total_leads": 2,
            "client_count": 1,
            "leads_by_client": {client_id: lead_ids},
            "client_credits": {client_id: 1000},
        }

        # Mock enrichment
        mock_enrich.return_value = {
            "success": True,
            "client_id": client_id,
            "data": {
                "total": 2,
                "tier1_success": 2,
                "tier2_success": 0,
                "enriched_leads": [
                    {"lead_id": lead_ids[0], "tier": 1},
                    {"lead_id": lead_ids[1], "tier": 1},
                ],
            },
        }

        # Mock scoring
        mock_score.side_effect = [
            {"success": True, "als_score": 85, "als_tier": "hot"},
            {"success": True, "als_score": 65, "als_tier": "warm"},
        ]

        # Mock allocation
        mock_allocate.side_effect = [
            {"success": True, "channels": ["email", "linkedin"]},
            {"success": True, "channels": ["email"]},
        ]

        # Mock credit deduction
        mock_deduct.return_value = {
            "credits_deducted": 2,
            "credits_remaining": 998,
        }

        result = await daily_enrichment_flow(batch_size=100)

        assert result["total_enriched"] == 2
        assert result["total_scored"] == 2
        assert result["total_allocated"] == 2
        assert result["total_credits_deducted"] == 2


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Tests for get_leads_needing_enrichment_task
# [x] Tests for enrich_lead_batch_task
# [x] Tests for score_lead_task
# [x] Tests for allocate_channels_for_lead_task
# [x] Tests for deduct_client_credits_task
# [x] Test for full daily_enrichment_flow
# [x] Tests cover success and failure cases
# [x] Uses pytest fixtures for mocks
# [x] Uses AsyncMock for async functions
# [x] All tests have descriptive docstrings
