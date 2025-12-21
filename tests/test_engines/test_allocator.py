"""
FILE: tests/test_engines/test_allocator.py
PURPOSE: Unit tests for Allocator engine (channel + resource assignment)
PHASE: 4 (Engines)
TASK: ENG-004
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.allocator import (
    AllocatorEngine,
    RATE_LIMITS,
    get_allocator_engine,
)
from src.models.base import ChannelType


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_lead():
    """Create mock lead object."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.campaign_id = uuid4()
    lead.email = "john.doe@acme.com"
    lead.assigned_email_resource = None
    lead.assigned_linkedin_seat = None
    lead.assigned_phone_resource = None
    return lead


@pytest.fixture
def mock_campaign():
    """Create mock campaign object."""
    campaign = MagicMock()
    campaign.id = uuid4()
    campaign.client_id = uuid4()
    return campaign


@pytest.fixture
def mock_email_resource():
    """Create mock email resource."""
    resource = MagicMock()
    resource.id = uuid4()
    resource.campaign_id = uuid4()
    resource.channel = ChannelType.EMAIL
    resource.resource_name = "Sales Email"
    resource.resource_value = "sales@company.com"
    resource.is_active = True
    resource.last_used_at = None
    resource.usage_count = 0
    return resource


@pytest.fixture
def mock_linkedin_resource():
    """Create mock LinkedIn resource."""
    resource = MagicMock()
    resource.id = uuid4()
    resource.campaign_id = uuid4()
    resource.channel = ChannelType.LINKEDIN
    resource.resource_name = "Sales Seat 1"
    resource.resource_value = "seat_001"
    resource.is_active = True
    resource.last_used_at = None
    resource.usage_count = 0
    return resource


@pytest.fixture
def allocator_engine():
    """Create Allocator engine instance."""
    return AllocatorEngine()


# ============================================
# Engine Properties Tests
# ============================================


class TestAllocatorEngineProperties:
    """Test Allocator engine properties."""

    def test_engine_name(self, allocator_engine):
        """Test engine name property."""
        assert allocator_engine.name == "allocator"

    def test_singleton_instance(self):
        """Test singleton pattern."""
        engine1 = get_allocator_engine()
        engine2 = get_allocator_engine()
        assert engine1 is engine2


# ============================================
# Rate Limit Configuration Tests
# ============================================


class TestRateLimitConfiguration:
    """Test rate limit configuration."""

    def test_linkedin_rate_limit(self):
        """Test LinkedIn rate limit is 17/day."""
        assert RATE_LIMITS[ChannelType.LINKEDIN] == 17

    def test_email_rate_limit(self):
        """Test Email rate limit is 50/day."""
        assert RATE_LIMITS[ChannelType.EMAIL] == 50

    def test_sms_rate_limit(self):
        """Test SMS rate limit is 100/day."""
        assert RATE_LIMITS[ChannelType.SMS] == 100

    def test_voice_rate_limit(self):
        """Test Voice rate limit is 50/day."""
        assert RATE_LIMITS[ChannelType.VOICE] == 50

    def test_mail_rate_limit(self):
        """Test Mail rate limit is 1000/day."""
        assert RATE_LIMITS[ChannelType.MAIL] == 1000


# ============================================
# Resource Identifier Tests
# ============================================


class TestResourceIdentifier:
    """Test resource identifier extraction."""

    def test_email_resource_uses_domain(self, allocator_engine, mock_email_resource):
        """Test email resource uses domain as identifier."""
        resource_id = allocator_engine._get_resource_identifier(mock_email_resource)
        assert resource_id == "company.com"

    def test_linkedin_resource_uses_value(self, allocator_engine, mock_linkedin_resource):
        """Test LinkedIn resource uses value directly."""
        resource_id = allocator_engine._get_resource_identifier(mock_linkedin_resource)
        assert resource_id == "seat_001"


# ============================================
# Channel Allocation Tests
# ============================================


class TestChannelAllocation:
    """Test channel allocation logic."""

    @pytest.mark.asyncio
    async def test_allocate_single_channel(
        self, allocator_engine, mock_db_session, mock_lead, mock_campaign, mock_email_resource
    ):
        """Test allocating a single channel."""
        with patch.object(allocator_engine, "get_lead_by_id", return_value=mock_lead):
            with patch.object(allocator_engine, "get_campaign_by_id", return_value=mock_campaign):
                with patch.object(
                    allocator_engine,
                    "_get_campaign_resources",
                    return_value=[{
                        "resource": mock_email_resource,
                        "resource_id": "company.com",
                        "resource_name": "Sales Email",
                        "channel": ChannelType.EMAIL,
                        "remaining_quota": 50,
                        "daily_limit": 50,
                    }],
                ):
                    result = await allocator_engine.allocate_channels(
                        db=mock_db_session,
                        lead_id=mock_lead.id,
                        available_channels=[ChannelType.EMAIL],
                    )

                    assert result.success is True
                    assert "email" in result.data["channels"]

    @pytest.mark.asyncio
    async def test_allocate_multiple_channels(
        self, allocator_engine, mock_db_session, mock_lead, mock_campaign,
        mock_email_resource, mock_linkedin_resource
    ):
        """Test allocating multiple channels."""
        with patch.object(allocator_engine, "get_lead_by_id", return_value=mock_lead):
            with patch.object(allocator_engine, "get_campaign_by_id", return_value=mock_campaign):
                with patch.object(
                    allocator_engine,
                    "_get_campaign_resources",
                    return_value=[
                        {
                            "resource": mock_email_resource,
                            "resource_id": "company.com",
                            "resource_name": "Sales Email",
                            "channel": ChannelType.EMAIL,
                            "remaining_quota": 50,
                            "daily_limit": 50,
                        },
                        {
                            "resource": mock_linkedin_resource,
                            "resource_id": "seat_001",
                            "resource_name": "Sales Seat 1",
                            "channel": ChannelType.LINKEDIN,
                            "remaining_quota": 17,
                            "daily_limit": 17,
                        },
                    ],
                ):
                    result = await allocator_engine.allocate_channels(
                        db=mock_db_session,
                        lead_id=mock_lead.id,
                        available_channels=[ChannelType.EMAIL, ChannelType.LINKEDIN],
                    )

                    assert result.success is True
                    assert "email" in result.data["channels"]
                    assert "linkedin" in result.data["channels"]
                    assert len(result.data["channels"]) == 2

    @pytest.mark.asyncio
    async def test_allocation_fails_when_no_resources(
        self, allocator_engine, mock_db_session, mock_lead, mock_campaign
    ):
        """Test allocation fails when no resources available."""
        with patch.object(allocator_engine, "get_lead_by_id", return_value=mock_lead):
            with patch.object(allocator_engine, "get_campaign_by_id", return_value=mock_campaign):
                with patch.object(
                    allocator_engine,
                    "_get_campaign_resources",
                    return_value=[],  # No resources
                ):
                    result = await allocator_engine.allocate_channels(
                        db=mock_db_session,
                        lead_id=mock_lead.id,
                        available_channels=[ChannelType.EMAIL],
                    )

                    assert result.success is False
                    assert "exhausted" in result.error.lower()


# ============================================
# Rate Limit Tests
# ============================================


class TestRateLimitEnforcement:
    """Test rate limit enforcement."""

    @pytest.mark.asyncio
    async def test_quota_check_success(self, allocator_engine):
        """Test successful quota check and consumption."""
        with patch("src.engines.allocator.rate_limiter") as mock_limiter:
            mock_limiter.check_and_increment = AsyncMock(return_value=(True, 5))

            result = await allocator_engine.check_and_consume_quota(
                channel=ChannelType.EMAIL,
                resource_id="company.com",
            )

            assert result.success is True
            assert result.data["current_count"] == 5
            assert result.data["daily_limit"] == 50

    @pytest.mark.asyncio
    async def test_quota_check_exhausted(self, allocator_engine):
        """Test quota check fails when exhausted."""
        from src.exceptions import ResourceRateLimitError

        with patch("src.engines.allocator.rate_limiter") as mock_limiter:
            mock_limiter.check_and_increment = AsyncMock(
                side_effect=ResourceRateLimitError(
                    resource_type="email",
                    resource_id="company.com",
                    limit=50,
                    message="Rate limit exceeded",
                )
            )

            result = await allocator_engine.check_and_consume_quota(
                channel=ChannelType.EMAIL,
                resource_id="company.com",
            )

            assert result.success is False
            assert "limit" in result.error.lower()


# ============================================
# Resource Selection Tests
# ============================================


class TestResourceSelection:
    """Test resource selection (round-robin)."""

    @pytest.mark.asyncio
    async def test_get_next_resource_round_robin(
        self, allocator_engine, mock_db_session, mock_email_resource
    ):
        """Test round-robin resource selection."""
        # Create mock result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_email_resource]
        mock_db_session.execute.return_value = mock_result

        with patch("src.engines.allocator.rate_limiter") as mock_limiter:
            mock_limiter.get_remaining = AsyncMock(return_value=45)

            result = await allocator_engine.get_next_resource(
                db=mock_db_session,
                campaign_id=uuid4(),
                channel=ChannelType.EMAIL,
            )

            assert result.success is True
            assert result.data["remaining_quota"] == 45

    @pytest.mark.asyncio
    async def test_get_next_resource_skips_exhausted(
        self, allocator_engine, mock_db_session
    ):
        """Test resource selection skips exhausted resources."""
        # Create two mock resources
        exhausted_resource = MagicMock()
        exhausted_resource.id = uuid4()
        exhausted_resource.channel = ChannelType.EMAIL
        exhausted_resource.resource_name = "Exhausted Email"
        exhausted_resource.resource_value = "exhausted@company.com"
        exhausted_resource.is_active = True

        available_resource = MagicMock()
        available_resource.id = uuid4()
        available_resource.channel = ChannelType.EMAIL
        available_resource.resource_name = "Available Email"
        available_resource.resource_value = "available@company.com"
        available_resource.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            exhausted_resource,
            available_resource,
        ]
        mock_db_session.execute.return_value = mock_result

        with patch("src.engines.allocator.rate_limiter") as mock_limiter:
            # First resource exhausted, second has quota
            mock_limiter.get_remaining = AsyncMock(side_effect=[0, 30])

            result = await allocator_engine.get_next_resource(
                db=mock_db_session,
                campaign_id=uuid4(),
                channel=ChannelType.EMAIL,
            )

            assert result.success is True
            assert result.data["remaining_quota"] == 30


# ============================================
# Resource Status Tests
# ============================================


class TestResourceStatus:
    """Test resource status reporting."""

    @pytest.mark.asyncio
    async def test_get_resource_status(
        self, allocator_engine, mock_db_session, mock_email_resource
    ):
        """Test getting resource status for campaign."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_email_resource]
        mock_db_session.execute.return_value = mock_result

        with patch("src.engines.allocator.rate_limiter") as mock_limiter:
            mock_limiter.get_usage = AsyncMock(return_value=10)

            result = await allocator_engine.get_resource_status(
                db=mock_db_session,
                campaign_id=uuid4(),
            )

            assert result.success is True
            assert len(result.data["resources"]) == 1
            assert "email" in result.data["channels"]


# ============================================
# Batch Allocation Tests
# ============================================


class TestBatchAllocation:
    """Test batch allocation functionality."""

    @pytest.mark.asyncio
    async def test_batch_allocation_success(
        self, allocator_engine, mock_db_session, mock_lead
    ):
        """Test batch allocation returns summary."""
        lead_ids = [uuid4() for _ in range(3)]
        tier_channels = {
            str(lead_ids[0]): [ChannelType.EMAIL],
            str(lead_ids[1]): [ChannelType.EMAIL, ChannelType.LINKEDIN],
            str(lead_ids[2]): [ChannelType.EMAIL],
        }

        with patch.object(allocator_engine, "allocate_channels") as mock_allocate:
            from src.engines.base import EngineResult
            mock_allocate.return_value = EngineResult.ok(
                data={"channels": ["email"]},
            )

            result = await allocator_engine.allocate_batch(
                db=mock_db_session,
                lead_ids=lead_ids,
                tier_channels=tier_channels,
            )

            assert result.success is True
            assert result.data["total"] == 3

    @pytest.mark.asyncio
    async def test_batch_allocation_handles_failures(
        self, allocator_engine, mock_db_session
    ):
        """Test batch allocation handles individual failures."""
        lead_ids = [uuid4() for _ in range(2)]
        tier_channels = {
            str(lead_ids[0]): [ChannelType.EMAIL],
            str(lead_ids[1]): [],  # No channels - will fail
        }

        with patch.object(allocator_engine, "allocate_channels") as mock_allocate:
            from src.engines.base import EngineResult
            mock_allocate.return_value = EngineResult.ok(
                data={"channels": ["email"]},
            )

            result = await allocator_engine.allocate_batch(
                db=mock_db_session,
                lead_ids=lead_ids,
                tier_channels=tier_channels,
            )

            assert result.success is True
            assert result.data["failed"] == 1  # One failed due to no channels


# ============================================
# Helper Function Tests
# ============================================


class TestHelperFunctions:
    """Test helper functions."""

    @pytest.mark.asyncio
    async def test_find_available_resource(self, allocator_engine):
        """Test finding available resource for channel."""
        resources = [
            {
                "channel": ChannelType.EMAIL,
                "resource_id": "domain1.com",
                "remaining_quota": 0,  # Exhausted
            },
            {
                "channel": ChannelType.EMAIL,
                "resource_id": "domain2.com",
                "remaining_quota": 30,  # Available
            },
            {
                "channel": ChannelType.LINKEDIN,
                "resource_id": "seat_001",
                "remaining_quota": 10,
            },
        ]

        result = await allocator_engine._find_available_resource(
            resources=resources,
            channel=ChannelType.EMAIL,
        )

        assert result is not None
        assert result["resource_id"] == "domain2.com"

    @pytest.mark.asyncio
    async def test_find_available_resource_none_available(self, allocator_engine):
        """Test finding resource when none available."""
        resources = [
            {
                "channel": ChannelType.EMAIL,
                "resource_id": "domain1.com",
                "remaining_quota": 0,
            },
        ]

        result = await allocator_engine._find_available_resource(
            resources=resources,
            channel=ChannelType.EMAIL,
        )

        assert result is None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties
# [x] Test singleton pattern
# [x] Test rate limit configuration
# [x] Test resource identifier extraction
# [x] Test single channel allocation
# [x] Test multiple channel allocation
# [x] Test allocation fails when no resources
# [x] Test quota check success
# [x] Test quota check exhausted
# [x] Test round-robin resource selection
# [x] Test skipping exhausted resources
# [x] Test resource status reporting
# [x] Test batch allocation
# [x] Test batch allocation with failures
# [x] Test helper functions
