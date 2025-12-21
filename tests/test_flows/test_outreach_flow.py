"""
FILE: tests/test_flows/test_outreach_flow.py
PURPOSE: Unit tests for hourly outreach flow
PHASE: 5 (Orchestration)
TASK: ORC-004
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.base import EngineResult
from src.models.base import (
    CampaignStatus,
    LeadStatus,
    PermissionMode,
    SubscriptionStatus,
)
from src.orchestration.flows.outreach_flow import (
    get_leads_ready_for_outreach_task,
    hourly_outreach_flow,
    jit_validate_outreach_task,
    send_email_outreach_task,
    send_linkedin_outreach_task,
    send_sms_outreach_task,
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
    client.deleted_at = None
    return client


@pytest.fixture
def mock_campaign():
    """Create mock campaign object."""
    campaign = MagicMock()
    campaign.id = uuid4()
    campaign.status = CampaignStatus.ACTIVE
    campaign.permission_mode = PermissionMode.CO_PILOT
    campaign.deleted_at = None
    return campaign


@pytest.fixture
def mock_lead():
    """Create mock lead object."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.status = LeadStatus.IN_SEQUENCE
    lead.deleted_at = None
    return lead


# ============================================
# Tests: get_leads_ready_for_outreach_task
# ============================================


@pytest.mark.asyncio
async def test_get_leads_ready_for_outreach_success():
    """Test getting leads ready for outreach with JIT validation."""
    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        # Mock query result
        mock_result.all = AsyncMock(
            return_value=[
                (
                    uuid4(),  # lead_id
                    uuid4(),  # client_id
                    uuid4(),  # campaign_id
                    "domain.com",  # email_resource
                    "seat123",  # linkedin_seat
                    "+1234567890",  # phone_resource
                    PermissionMode.CO_PILOT,  # permission_mode
                    SubscriptionStatus.ACTIVE,  # subscription_status
                    1000,  # credits_remaining
                ),
            ]
        )
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await get_leads_ready_for_outreach_task(limit=50)

        assert result["total_leads"] == 1
        assert len(result["leads_by_channel"]["email"]) == 1
        assert len(result["leads_by_channel"]["linkedin"]) == 1


@pytest.mark.asyncio
async def test_get_leads_ready_for_outreach_no_leads():
    """Test getting leads when none are ready."""
    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.all = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await get_leads_ready_for_outreach_task(limit=50)

        assert result["total_leads"] == 0


# ============================================
# Tests: jit_validate_outreach_task
# ============================================


@pytest.mark.asyncio
async def test_jit_validate_outreach_success(mock_client, mock_campaign, mock_lead):
    """Test successful JIT validation for outreach."""
    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()

        # Mock three separate queries
        mock_client_result = AsyncMock()
        mock_client_result.scalar_one_or_none = AsyncMock(return_value=mock_client)

        mock_campaign_result = AsyncMock()
        mock_campaign_result.scalar_one_or_none = AsyncMock(return_value=mock_campaign)

        mock_lead_result = AsyncMock()
        mock_lead_result.scalar_one_or_none = AsyncMock(return_value=mock_lead)

        mock_db.execute = AsyncMock(
            side_effect=[mock_client_result, mock_campaign_result, mock_lead_result]
        )
        mock_get_session.return_value.__aenter__.return_value = mock_db

        result = await jit_validate_outreach_task(
            lead_id=str(mock_lead.id),
            campaign_id=str(mock_campaign.id),
            client_id=str(mock_client.id),
        )

        assert result["valid"] is True
        assert result["permission_mode"] == "co_pilot"


@pytest.mark.asyncio
async def test_jit_validate_outreach_no_credits(mock_client, mock_campaign, mock_lead):
    """Test JIT validation fails when client has no credits."""
    mock_client.credits_remaining = 0

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()
        mock_client_result = AsyncMock()
        mock_client_result.scalar_one_or_none = AsyncMock(return_value=mock_client)
        mock_db.execute = AsyncMock(return_value=mock_client_result)
        mock_get_session.return_value.__aenter__.return_value = mock_db

        with pytest.raises(ValueError, match="no credits"):
            await jit_validate_outreach_task(
                lead_id=str(mock_lead.id),
                campaign_id=str(mock_campaign.id),
                client_id=str(mock_client.id),
            )


@pytest.mark.asyncio
async def test_jit_validate_outreach_lead_unsubscribed(
    mock_client, mock_campaign, mock_lead
):
    """Test JIT validation fails when lead is unsubscribed."""
    mock_lead.status = LeadStatus.UNSUBSCRIBED

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session:
        mock_db = AsyncMock()

        mock_client_result = AsyncMock()
        mock_client_result.scalar_one_or_none = AsyncMock(return_value=mock_client)

        mock_campaign_result = AsyncMock()
        mock_campaign_result.scalar_one_or_none = AsyncMock(return_value=mock_campaign)

        mock_lead_result = AsyncMock()
        mock_lead_result.scalar_one_or_none = AsyncMock(return_value=mock_lead)

        mock_db.execute = AsyncMock(
            side_effect=[mock_client_result, mock_campaign_result, mock_lead_result]
        )
        mock_get_session.return_value.__aenter__.return_value = mock_db

        with pytest.raises(ValueError, match="unsubscribed"):
            await jit_validate_outreach_task(
                lead_id=str(mock_lead.id),
                campaign_id=str(mock_campaign.id),
                client_id=str(mock_client.id),
            )


# ============================================
# Tests: send_email_outreach_task
# ============================================


@pytest.mark.asyncio
async def test_send_email_outreach_success():
    """Test successful email outreach."""
    lead_id = str(uuid4())
    campaign_id = str(uuid4())
    resource = "domain.com"

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session, patch(
        "src.orchestration.flows.outreach_flow.get_content_engine"
    ) as mock_get_content, patch(
        "src.orchestration.flows.outreach_flow.get_email_engine"
    ) as mock_get_email, patch(
        "src.orchestration.flows.outreach_flow.get_allocator_engine"
    ) as mock_get_allocator:

        # Mock database
        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        # Mock allocator (rate limit check)
        mock_allocator = MagicMock()
        mock_allocator.check_and_consume_quota = AsyncMock(
            return_value=EngineResult.ok(data={"remaining": 45})
        )
        mock_get_allocator.return_value = mock_allocator

        # Mock content engine
        mock_content = MagicMock()
        mock_content.generate_email = AsyncMock(
            return_value=EngineResult.ok(
                data={"subject": "Test Subject", "body": "Test Body"}
            )
        )
        mock_get_content.return_value = mock_content

        # Mock email engine
        mock_email = MagicMock()
        mock_email.send_email = AsyncMock(
            return_value=EngineResult.ok(data={"message_id": "msg123"})
        )
        mock_get_email.return_value = mock_email

        result = await send_email_outreach_task(
            lead_id, campaign_id, resource, "autopilot"
        )

        assert result["success"] is True
        assert result["channel"] == "email"
        assert result["message_id"] == "msg123"


@pytest.mark.asyncio
async def test_send_email_outreach_rate_limit_exceeded():
    """Test email outreach when rate limit is exceeded."""
    lead_id = str(uuid4())
    campaign_id = str(uuid4())
    resource = "domain.com"

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session, patch(
        "src.orchestration.flows.outreach_flow.get_allocator_engine"
    ) as mock_get_allocator:

        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        # Mock allocator (rate limit exceeded)
        mock_allocator = MagicMock()
        mock_allocator.check_and_consume_quota = AsyncMock(
            return_value=EngineResult.fail(error="Rate limit exceeded")
        )
        mock_get_allocator.return_value = mock_allocator

        result = await send_email_outreach_task(
            lead_id, campaign_id, resource, "autopilot"
        )

        assert result["success"] is False
        assert "Rate limit" in result["error"]


# ============================================
# Tests: send_linkedin_outreach_task
# ============================================


@pytest.mark.asyncio
async def test_send_linkedin_outreach_success():
    """Test successful LinkedIn outreach."""
    lead_id = str(uuid4())
    campaign_id = str(uuid4())
    resource = "seat123"

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session, patch(
        "src.orchestration.flows.outreach_flow.get_content_engine"
    ) as mock_get_content, patch(
        "src.orchestration.flows.outreach_flow.get_linkedin_engine"
    ) as mock_get_linkedin, patch(
        "src.orchestration.flows.outreach_flow.get_allocator_engine"
    ) as mock_get_allocator:

        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        # Mock allocator
        mock_allocator = MagicMock()
        mock_allocator.check_and_consume_quota = AsyncMock(
            return_value=EngineResult.ok(data={"remaining": 15})
        )
        mock_get_allocator.return_value = mock_allocator

        # Mock content engine
        mock_content = MagicMock()
        mock_content.generate_linkedin_message = AsyncMock(
            return_value=EngineResult.ok(data={"message": "Test Message"})
        )
        mock_get_content.return_value = mock_content

        # Mock LinkedIn engine
        mock_linkedin = MagicMock()
        mock_linkedin.send_connection_request = AsyncMock(
            return_value=EngineResult.ok(data={})
        )
        mock_get_linkedin.return_value = mock_linkedin

        result = await send_linkedin_outreach_task(
            lead_id, campaign_id, resource, "autopilot"
        )

        assert result["success"] is True
        assert result["channel"] == "linkedin"


# ============================================
# Tests: send_sms_outreach_task
# ============================================


@pytest.mark.asyncio
async def test_send_sms_outreach_success():
    """Test successful SMS outreach."""
    lead_id = str(uuid4())
    campaign_id = str(uuid4())
    resource = "+1234567890"

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session"
    ) as mock_get_session, patch(
        "src.orchestration.flows.outreach_flow.get_content_engine"
    ) as mock_get_content, patch(
        "src.orchestration.flows.outreach_flow.get_sms_engine"
    ) as mock_get_sms, patch(
        "src.orchestration.flows.outreach_flow.get_allocator_engine"
    ) as mock_get_allocator:

        mock_db = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_db

        # Mock allocator
        mock_allocator = MagicMock()
        mock_allocator.check_and_consume_quota = AsyncMock(
            return_value=EngineResult.ok(data={"remaining": 95})
        )
        mock_get_allocator.return_value = mock_allocator

        # Mock content engine
        mock_content = MagicMock()
        mock_content.generate_sms = AsyncMock(
            return_value=EngineResult.ok(data={"message": "Test SMS"})
        )
        mock_get_content.return_value = mock_content

        # Mock SMS engine
        mock_sms = MagicMock()
        mock_sms.send_sms = AsyncMock(
            return_value=EngineResult.ok(data={"message_id": "sms123"})
        )
        mock_get_sms.return_value = mock_sms

        result = await send_sms_outreach_task(
            lead_id, campaign_id, resource, "autopilot"
        )

        assert result["success"] is True
        assert result["channel"] == "sms"
        assert result["message_id"] == "sms123"


# ============================================
# Tests: hourly_outreach_flow
# ============================================


@pytest.mark.asyncio
async def test_hourly_outreach_flow_no_leads():
    """Test hourly outreach flow with no leads."""
    with patch(
        "src.orchestration.flows.outreach_flow.get_leads_ready_for_outreach_task"
    ) as mock_get_leads:
        mock_get_leads.return_value = {
            "total_leads": 0,
            "leads_by_channel": {
                "email": [],
                "linkedin": [],
                "sms": [],
            },
        }

        result = await hourly_outreach_flow(batch_size=50)

        assert result["total_leads"] == 0
        assert "No leads" in result["message"]


@pytest.mark.asyncio
async def test_hourly_outreach_flow_success():
    """Test successful hourly outreach flow."""
    lead_id = str(uuid4())
    campaign_id = str(uuid4())
    client_id = str(uuid4())

    with patch(
        "src.orchestration.flows.outreach_flow.get_leads_ready_for_outreach_task"
    ) as mock_get_leads, patch(
        "src.orchestration.flows.outreach_flow.jit_validate_outreach_task"
    ) as mock_validate, patch(
        "src.orchestration.flows.outreach_flow.send_email_outreach_task"
    ) as mock_send_email:

        # Mock getting leads
        mock_get_leads.return_value = {
            "total_leads": 1,
            "leads_by_channel": {
                "email": [
                    {
                        "lead_id": lead_id,
                        "campaign_id": campaign_id,
                        "client_id": client_id,
                        "resource": "domain.com",
                    }
                ],
                "linkedin": [],
                "sms": [],
            },
        }

        # Mock JIT validation
        mock_validate.return_value = {
            "valid": True,
            "permission_mode": "autopilot",
        }

        # Mock sending email
        mock_send_email.return_value = {
            "lead_id": lead_id,
            "channel": "email",
            "success": True,
            "message_id": "msg123",
        }

        result = await hourly_outreach_flow(batch_size=50)

        assert result["emails_sent"] == 1
        assert result["total_sent"] == 1


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Tests for get_leads_ready_for_outreach_task
# [x] Tests for jit_validate_outreach_task
# [x] Tests for send_email_outreach_task
# [x] Tests for send_linkedin_outreach_task
# [x] Tests for send_sms_outreach_task
# [x] Test for full hourly_outreach_flow
# [x] Tests cover success and failure cases
# [x] Tests cover JIT validation failures
# [x] Tests cover rate limit scenarios
# [x] Uses pytest fixtures for mocks
# [x] Uses AsyncMock for async functions
# [x] All tests have descriptive docstrings
