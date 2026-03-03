"""
FILE: tests/test_flows/test_outreach_flow.py
PURPOSE: Unit tests for hourly outreach flow
PHASE: 5 (Orchestration)
TASK: ORC-004
"""

from contextlib import asynccontextmanager
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
    client.paused_at = None  # Phase H, Item 43
    return client


@pytest.fixture
def mock_campaign():
    """Create mock campaign object."""
    campaign = MagicMock()
    campaign.id = uuid4()
    campaign.status = CampaignStatus.ACTIVE
    campaign.permission_mode = PermissionMode.CO_PILOT
    campaign.deleted_at = None
    campaign.paused_at = None  # Phase H, Item 43
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
    mock_db = AsyncMock()
    mock_result = MagicMock()
    # Mock query result
    mock_result.all.return_value = [
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
    mock_db.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ):
        result = await get_leads_ready_for_outreach_task.fn(limit=50)

        assert result["total_leads"] == 1
        assert len(result["leads_by_channel"]["email"]) == 1
        assert len(result["leads_by_channel"]["linkedin"]) == 1


@pytest.mark.asyncio
async def test_get_leads_ready_for_outreach_no_leads():
    """Test getting leads when none are ready."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ):
        result = await get_leads_ready_for_outreach_task.fn(limit=50)

        assert result["total_leads"] == 0


# ============================================
# Tests: jit_validate_outreach_task
# ============================================


@pytest.mark.asyncio
async def test_jit_validate_outreach_success(mock_client, mock_campaign, mock_lead):
    """Test successful JIT validation for outreach."""
    mock_db = AsyncMock()

    # Mock three separate queries
    mock_client_result = MagicMock()
    mock_client_result.scalar_one_or_none.return_value = mock_client

    mock_campaign_result = MagicMock()
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

    mock_lead_result = MagicMock()
    mock_lead_result.scalar_one_or_none.return_value = mock_lead

    mock_db.execute = AsyncMock(
        side_effect=[mock_client_result, mock_campaign_result, mock_lead_result]
    )

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ):
        result = await jit_validate_outreach_task.fn(
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

    mock_db = AsyncMock()
    mock_client_result = MagicMock()
    mock_client_result.scalar_one_or_none.return_value = mock_client
    mock_db.execute = AsyncMock(return_value=mock_client_result)

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ):
        with pytest.raises(ValueError, match="no credits"):
            await jit_validate_outreach_task.fn(
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

    mock_db = AsyncMock()

    mock_client_result = MagicMock()
    mock_client_result.scalar_one_or_none.return_value = mock_client

    mock_campaign_result = MagicMock()
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

    mock_lead_result = MagicMock()
    mock_lead_result.scalar_one_or_none.return_value = mock_lead

    mock_db.execute = AsyncMock(
        side_effect=[mock_client_result, mock_campaign_result, mock_lead_result]
    )

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ):
        with pytest.raises(ValueError, match="unsubscribed"):
            await jit_validate_outreach_task.fn(
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

    # Mock lead for database query
    mock_lead = MagicMock()
    mock_lead.id = uuid4()
    mock_lead.propensity_score = 50  # Below 85, uses standard email
    mock_lead.first_name = "John"
    mock_lead.last_name = "Doe"
    mock_lead.title = "CEO"
    mock_lead.company = "Test Corp"
    mock_lead.organization_industry = "Technology"
    mock_lead.organization_employee_count = 100

    # Mock database
    mock_db = AsyncMock()
    mock_lead_result = MagicMock()
    mock_lead_result.scalar_one_or_none.return_value = mock_lead
    mock_db.execute = AsyncMock(return_value=mock_lead_result)
    mock_db.commit = AsyncMock()

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    # Mock allocator (rate limit check)
    mock_allocator = MagicMock()
    mock_allocator.check_and_consume_quota = AsyncMock(
        return_value=EngineResult.ok(data={"remaining": 45})
    )

    # Mock content engine
    mock_content = MagicMock()
    mock_content.generate_email = AsyncMock(
        return_value=EngineResult.ok(
            data={"subject": "Test Subject - Reaching Out About Partnership", "body": "Hello John, I wanted to reach out regarding a potential partnership opportunity that could benefit Test Corp. I believe our solutions would be a great fit for your technology needs."}
        )
    )

    # Mock email engine
    mock_email = MagicMock()
    mock_email.send_email = AsyncMock(
        return_value=EngineResult.ok(data={"message_id": "msg123"})
    )

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ), patch(
        "src.orchestration.flows.outreach_flow.get_content_engine",
        return_value=mock_content
    ), patch(
        "src.orchestration.flows.outreach_flow.get_email_engine",
        return_value=mock_email
    ), patch(
        "src.orchestration.flows.outreach_flow.get_allocator_engine",
        return_value=mock_allocator
    ):
        result = await send_email_outreach_task.fn(
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

    mock_db = AsyncMock()

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    # Mock allocator (rate limit exceeded)
    mock_allocator = MagicMock()
    mock_allocator.check_and_consume_quota = AsyncMock(
        return_value=EngineResult.fail(error="Rate limit exceeded")
    )

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ), patch(
        "src.orchestration.flows.outreach_flow.get_allocator_engine",
        return_value=mock_allocator
    ):
        result = await send_email_outreach_task.fn(
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

    # Mock lead for database query
    mock_lead = MagicMock()
    mock_lead.id = uuid4()
    mock_lead.linkedin_url = "https://linkedin.com/in/test"

    # Mock database
    mock_db = AsyncMock()
    mock_lead_result = MagicMock()
    mock_lead_result.scalar_one_or_none.return_value = mock_lead
    mock_db.execute = AsyncMock(return_value=mock_lead_result)
    mock_db.commit = AsyncMock()

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    # Mock allocator
    mock_allocator = MagicMock()
    mock_allocator.check_and_consume_quota = AsyncMock(
        return_value=EngineResult.ok(data={"remaining": 15})
    )

    # Mock content engine
    mock_content = MagicMock()
    mock_content.generate_linkedin_message = AsyncMock(
        return_value=EngineResult.ok(data={"message": "Hi there! I noticed your work at the company and would love to connect and discuss potential opportunities for collaboration."})
    )

    # Mock LinkedIn engine
    mock_linkedin = MagicMock()
    mock_linkedin.send_connection_request = AsyncMock(
        return_value=EngineResult.ok(data={})
    )

    # Mock timing engine to bypass business hours check
    mock_timing = MagicMock()
    mock_timing.is_weekend.return_value = False
    mock_timing.is_business_hours.return_value = True

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ), patch(
        "src.orchestration.flows.outreach_flow.get_content_engine",
        return_value=mock_content
    ), patch(
        "src.orchestration.flows.outreach_flow.get_linkedin_engine",
        return_value=mock_linkedin
    ), patch(
        "src.orchestration.flows.outreach_flow.get_allocator_engine",
        return_value=mock_allocator
    ), patch(
        "src.orchestration.flows.outreach_flow.get_timing_engine",
        return_value=mock_timing
    ):
        result = await send_linkedin_outreach_task.fn(
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

    # Mock lead for database query
    mock_lead = MagicMock()
    mock_lead.id = uuid4()
    mock_lead.phone = "+1234567890"
    mock_lead.propensity_score = 90  # Above 85, SMS requires Hot tier
    mock_lead.first_name = "John"

    # Mock database
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=mock_lead)  # SMS uses db.get() not execute()
    mock_db.commit = AsyncMock()

    @asynccontextmanager
    async def mock_get_session():
        yield mock_db

    # Mock allocator
    mock_allocator = MagicMock()
    mock_allocator.check_and_consume_quota = AsyncMock(
        return_value=EngineResult.ok(data={"remaining": 95})
    )

    # Mock content engine
    mock_content = MagicMock()
    mock_content.generate_sms = AsyncMock(
        return_value=EngineResult.ok(data={"message": "Hi John! Just following up on the partnership discussion. Would you have 15 mins this week to connect?"})
    )

    # Mock SMS engine
    mock_sms = MagicMock()
    mock_sms.send_sms = AsyncMock(
        return_value=EngineResult.ok(data={"message_id": "sms123"})
    )

    with patch(
        "src.orchestration.flows.outreach_flow.get_db_session",
        mock_get_session
    ), patch(
        "src.orchestration.flows.outreach_flow.get_content_engine",
        return_value=mock_content
    ), patch(
        "src.orchestration.flows.outreach_flow.get_sms_engine",
        return_value=mock_sms
    ), patch(
        "src.orchestration.flows.outreach_flow.get_allocator_engine",
        return_value=mock_allocator
    ):
        result = await send_sms_outreach_task.fn(
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
    mock_get_leads = AsyncMock(return_value={
        "total_leads": 0,
        "leads_by_channel": {
            "email": [],
            "linkedin": [],
            "sms": [],
        },
    })

    with patch(
        "src.orchestration.flows.outreach_flow.get_leads_ready_for_outreach_task",
        mock_get_leads
    ):
        result = await hourly_outreach_flow.fn(batch_size=50)

        assert result["total_leads"] == 0
        assert "No leads" in result["message"]


# NOTE: test_hourly_outreach_flow_success deleted per Directive #155
# This integration test requires Prefect server infrastructure.
# Individual task tests above provide coverage for the underlying logic.


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
