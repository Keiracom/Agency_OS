"""
FILE: tests/test_flows/test_campaign_flow.py
PURPOSE: Unit tests for campaign activation flow
PHASE: 5 (Orchestration)
TASK: ORC-002
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.base import CampaignStatus, LeadStatus, SubscriptionStatus
from src.orchestration.flows.campaign_flow import (
    activate_campaign_task,
    campaign_activation_flow,
    get_campaign_leads_task,
    trigger_enrichment_task,
    validate_campaign_task,
    validate_client_status_task,
)


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_client():
    """Create mock client object."""
    client = MagicMock()
    client.id = uuid4()
    client.subscription_status = SubscriptionStatus.ACTIVE
    client.credits_remaining = 1000
    client.tier = MagicMock(value="velocity")
    client.deleted_at = None
    return client


@pytest.fixture
def mock_campaign():
    """Create mock campaign object."""
    campaign = MagicMock()
    campaign.id = uuid4()
    campaign.client_id = uuid4()
    campaign.name = "Test Campaign"
    campaign.status = CampaignStatus.DRAFT
    campaign.permission_mode = MagicMock(value="co_pilot")
    campaign.deleted_at = None
    return campaign


@pytest.fixture
def mock_lead():
    """Create mock lead object."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.status = LeadStatus.NEW
    lead.deleted_at = None
    return lead


# ============================================
# Tests: validate_client_status_task
# ============================================


@pytest.mark.asyncio
async def test_validate_client_status_success(mock_client):
    """Test successful client validation."""
    with patch(
        "src.orchestration.flows.campaign_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=mock_client)
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await validate_client_status_task(mock_client.id)

        assert result["valid"] is True
        assert result["subscription_status"] == "active"
        assert result["credits_remaining"] == 1000


@pytest.mark.asyncio
async def test_validate_client_status_no_credits(mock_client):
    """Test client validation fails when no credits."""
    mock_client.credits_remaining = 0

    with patch(
        "src.orchestration.flows.campaign_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=mock_client)
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_db

        with pytest.raises(ValueError, match="must have credits"):
            await validate_client_status_task(mock_client.id)


@pytest.mark.asyncio
async def test_validate_client_status_not_found():
    """Test client validation fails when client not found."""
    with patch(
        "src.orchestration.flows.campaign_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_db

        with pytest.raises(ValueError, match="not found"):
            await validate_client_status_task(uuid4())


# ============================================
# Tests: validate_campaign_task
# ============================================


@pytest.mark.asyncio
async def test_validate_campaign_success(mock_campaign):
    """Test successful campaign validation."""
    with patch(
        "src.orchestration.flows.campaign_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=mock_campaign)
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await validate_campaign_task(mock_campaign.id)

        assert result["valid"] is True
        assert result["name"] == "Test Campaign"


@pytest.mark.asyncio
async def test_validate_campaign_not_found():
    """Test campaign validation fails when campaign not found."""
    with patch(
        "src.orchestration.flows.campaign_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_db

        with pytest.raises(ValueError, match="not found"):
            await validate_campaign_task(uuid4())


# ============================================
# Tests: activate_campaign_task
# ============================================


@pytest.mark.asyncio
async def test_activate_campaign_success():
    """Test successful campaign activation."""
    campaign_id = uuid4()

    with patch(
        "src.orchestration.flows.campaign_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=campaign_id)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await activate_campaign_task(campaign_id)

        assert result["status"] == "active"
        assert str(campaign_id) in result["campaign_id"]
        mock_db.commit.assert_called_once()


# ============================================
# Tests: get_campaign_leads_task
# ============================================


@pytest.mark.asyncio
async def test_get_campaign_leads_success():
    """Test getting campaign leads."""
    campaign_id = uuid4()
    lead_ids = [uuid4(), uuid4(), uuid4()]

    with patch(
        "src.orchestration.flows.campaign_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.all = AsyncMock(return_value=[(lid,) for lid in lead_ids])
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await get_campaign_leads_task(campaign_id)

        assert result["lead_count"] == 3
        assert len(result["lead_ids"]) == 3


# ============================================
# Tests: trigger_enrichment_task
# ============================================


@pytest.mark.asyncio
async def test_trigger_enrichment_success():
    """Test triggering enrichment for leads."""
    lead_ids = [str(uuid4()), str(uuid4())]
    campaign_id = str(uuid4())

    with patch(
        "src.orchestration.flows.campaign_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await trigger_enrichment_task(lead_ids, campaign_id)

        assert result["queued_count"] == 2
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_enrichment_empty_list():
    """Test triggering enrichment with no leads."""
    result = await trigger_enrichment_task([], str(uuid4()))

    assert result["queued_count"] == 0
    assert "No leads" in result["message"]


# ============================================
# Tests: campaign_activation_flow
# ============================================


@pytest.mark.asyncio
async def test_campaign_activation_flow_success(mock_campaign, mock_client):
    """Test full campaign activation flow."""
    campaign_id = uuid4()

    with patch(
        "src.orchestration.flows.campaign_flow.validate_campaign_task"
    ) as mock_validate_campaign, patch(
        "src.orchestration.flows.campaign_flow.validate_client_status_task"
    ) as mock_validate_client, patch(
        "src.orchestration.flows.campaign_flow.activate_campaign_task"
    ) as mock_activate, patch(
        "src.orchestration.flows.campaign_flow.get_campaign_leads_task"
    ) as mock_get_leads, patch(
        "src.orchestration.flows.campaign_flow.trigger_enrichment_task"
    ) as mock_trigger:

        # Setup mocks
        mock_validate_campaign.return_value = {
            "campaign_id": str(campaign_id),
            "client_id": str(mock_client.id),
            "name": "Test Campaign",
            "valid": True,
        }
        mock_validate_client.return_value = {
            "subscription_status": "active",
            "credits_remaining": 1000,
            "valid": True,
        }
        mock_activate.return_value = {
            "campaign_id": str(campaign_id),
            "status": "active",
            "activated_at": datetime.utcnow().isoformat(),
        }
        mock_get_leads.return_value = {
            "lead_count": 5,
            "lead_ids": [str(uuid4()) for _ in range(5)],
        }
        mock_trigger.return_value = {
            "queued_count": 5,
            "message": "Queued 5 leads",
        }

        result = await campaign_activation_flow(campaign_id)

        assert result["status"] == "activated"
        assert result["leads_count"] == 5
        assert result["leads_queued_for_enrichment"] == 5
        assert result["client_credits_remaining"] == 1000


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Tests for validate_client_status_task
# [x] Tests for validate_campaign_task
# [x] Tests for activate_campaign_task
# [x] Tests for get_campaign_leads_task
# [x] Tests for trigger_enrichment_task
# [x] Test for full campaign_activation_flow
# [x] Tests cover success and failure cases
# [x] Uses pytest fixtures for mocks
# [x] Uses AsyncMock for async functions
# [x] All tests have descriptive docstrings
