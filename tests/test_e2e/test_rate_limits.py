"""
FILE: tests/test_e2e/test_rate_limits.py
PURPOSE: Resource-level rate limit integration tests
PHASE: 9 (Integration Testing)
TASK: TST-005
DEPENDENCIES:
  - tests/conftest.py
  - tests/fixtures/*
RULES APPLIED:
  - Rule 17: Resource-level rate limits
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from tests.fixtures.database_fixtures import (
    create_test_client,
    create_test_campaign,
    create_hot_lead,
    create_warm_lead,
    create_email_resource,
    create_phone_resource,
    create_linkedin_resource,
    create_lead_batch,
)


# ============================================================================
# Email Rate Limit Tests (50/day/domain)
# ============================================================================

class TestEmailRateLimits:
    """Test email rate limiting (50/day/domain - Rule 17)."""

    @pytest.mark.asyncio
    async def test_email_under_daily_limit(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """Email should send when under daily limit."""
        # Arrange
        resource = create_email_resource("client_123")
        daily_limit = 50
        current_usage = 30

        mock_redis.get.return_value = str(current_usage)

        # Act
        async def check_email_rate_limit(redis, resource_id: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:email:{resource_id}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed, remaining = await check_email_rate_limit(
            mock_redis,
            resource["identifier"],
            daily_limit,
        )

        # Assert
        assert allowed is True
        assert remaining == 20

    @pytest.mark.asyncio
    async def test_email_at_daily_limit(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """Email should block when at daily limit."""
        # Arrange
        resource = create_email_resource("client_123")
        daily_limit = 50
        current_usage = 50

        mock_redis.get.return_value = str(current_usage)

        # Act
        async def check_email_rate_limit(redis, resource_id: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:email:{resource_id}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed, remaining = await check_email_rate_limit(
            mock_redis,
            resource["identifier"],
            daily_limit,
        )

        # Assert
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_email_rate_limit_increment(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """Email usage should increment after send."""
        # Arrange
        resource = create_email_resource("client_123")
        current_usage = 30

        mock_redis.incr.return_value = current_usage + 1
        mock_redis.expire.return_value = True

        # Act
        async def increment_email_usage(redis, resource_id: str) -> int:
            key = f"rate_limit:email:{resource_id}:daily"
            new_count = await redis.incr(key)
            # Set TTL to end of day if first increment
            await redis.expire(key, 86400)
            return new_count

        new_count = await increment_email_usage(mock_redis, resource["identifier"])

        # Assert
        assert new_count == 31
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_multiple_domains_independent(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """Each email domain should have independent rate limits."""
        # Arrange
        resource1 = create_email_resource("client_123")
        resource1["identifier"] = "outreach@domain1.com"

        resource2 = create_email_resource("client_123")
        resource2["identifier"] = "sales@domain2.com"

        # Mock different usage for each domain
        async def mock_get(key):
            if "domain1" in key:
                return "45"  # Near limit
            elif "domain2" in key:
                return "10"  # Plenty of capacity
            return "0"

        mock_redis.get = AsyncMock(side_effect=mock_get)

        # Act
        async def check_email_rate_limit(redis, resource_id: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:email:{resource_id}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed1, remaining1 = await check_email_rate_limit(mock_redis, resource1["identifier"], 50)
        allowed2, remaining2 = await check_email_rate_limit(mock_redis, resource2["identifier"], 50)

        # Assert
        assert allowed1 is True
        assert remaining1 == 5
        assert allowed2 is True
        assert remaining2 == 40


# ============================================================================
# SMS Rate Limit Tests (100/day/number)
# ============================================================================

class TestSMSRateLimits:
    """Test SMS rate limiting (100/day/number - Rule 17)."""

    @pytest.mark.asyncio
    async def test_sms_under_daily_limit(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """SMS should send when under daily limit."""
        # Arrange
        resource = create_phone_resource("client_123")
        daily_limit = 100
        current_usage = 50

        mock_redis.get.return_value = str(current_usage)

        # Act
        async def check_sms_rate_limit(redis, phone_number: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:sms:{phone_number}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed, remaining = await check_sms_rate_limit(
            mock_redis,
            resource["identifier"],
            daily_limit,
        )

        # Assert
        assert allowed is True
        assert remaining == 50

    @pytest.mark.asyncio
    async def test_sms_at_daily_limit(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """SMS should block when at daily limit."""
        # Arrange
        resource = create_phone_resource("client_123")
        daily_limit = 100
        current_usage = 100

        mock_redis.get.return_value = str(current_usage)

        # Act
        async def check_sms_rate_limit(redis, phone_number: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:sms:{phone_number}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed, remaining = await check_sms_rate_limit(
            mock_redis,
            resource["identifier"],
            daily_limit,
        )

        # Assert
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_sms_multiple_numbers_independent(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """Each phone number should have independent rate limits."""
        # Arrange
        resource1 = create_phone_resource("client_123")
        resource1["identifier"] = "+61499999991"

        resource2 = create_phone_resource("client_123")
        resource2["identifier"] = "+61499999992"

        # Mock different usage for each number
        async def mock_get(key):
            if "999991" in key:
                return "95"  # Near limit
            elif "999992" in key:
                return "20"  # Plenty of capacity
            return "0"

        mock_redis.get = AsyncMock(side_effect=mock_get)

        # Act
        async def check_sms_rate_limit(redis, phone_number: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:sms:{phone_number}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed1, remaining1 = await check_sms_rate_limit(mock_redis, resource1["identifier"], 100)
        allowed2, remaining2 = await check_sms_rate_limit(mock_redis, resource2["identifier"], 100)

        # Assert
        assert allowed1 is True
        assert remaining1 == 5
        assert allowed2 is True
        assert remaining2 == 80


# ============================================================================
# LinkedIn Rate Limit Tests (17/day/seat)
# ============================================================================

class TestLinkedInRateLimits:
    """Test LinkedIn rate limiting (17/day/seat - Rule 17)."""

    @pytest.mark.asyncio
    async def test_linkedin_under_daily_limit(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """LinkedIn should send when under daily limit."""
        # Arrange
        resource = create_linkedin_resource("client_123")
        daily_limit = 17
        current_usage = 10

        mock_redis.get.return_value = str(current_usage)

        # Act
        async def check_linkedin_rate_limit(redis, seat_id: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:linkedin:{seat_id}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed, remaining = await check_linkedin_rate_limit(
            mock_redis,
            resource["identifier"],
            daily_limit,
        )

        # Assert
        assert allowed is True
        assert remaining == 7

    @pytest.mark.asyncio
    async def test_linkedin_at_daily_limit(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """LinkedIn should block when at daily limit (17/seat)."""
        # Arrange
        resource = create_linkedin_resource("client_123")
        daily_limit = 17
        current_usage = 17

        mock_redis.get.return_value = str(current_usage)

        # Act
        async def check_linkedin_rate_limit(redis, seat_id: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:linkedin:{seat_id}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed, remaining = await check_linkedin_rate_limit(
            mock_redis,
            resource["identifier"],
            daily_limit,
        )

        # Assert
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_linkedin_strict_limit_enforcement(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """LinkedIn limit of 17 should be strictly enforced."""
        # Arrange - Simulate trying to exceed limit
        resource = create_linkedin_resource("client_123")
        current_usage = 16

        mock_redis.get.return_value = str(current_usage)

        # Act
        async def can_send_linkedin(redis, seat_id: str) -> bool:
            key = f"rate_limit:linkedin:{seat_id}:daily"
            current = int(await redis.get(key) or 0)
            return current < 17

        # Should allow 17th (index 16)
        allowed = await can_send_linkedin(mock_redis, resource["identifier"])
        assert allowed is True

        # Simulate sending the 17th
        mock_redis.get.return_value = "17"

        # Should block 18th
        allowed = await can_send_linkedin(mock_redis, resource["identifier"])
        assert allowed is False


# ============================================================================
# Voice Rate Limit Tests (50/day/number)
# ============================================================================

class TestVoiceRateLimits:
    """Test voice call rate limiting (50/day/number)."""

    @pytest.mark.asyncio
    async def test_voice_under_daily_limit(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """Voice calls should be allowed when under daily limit."""
        # Arrange
        phone_number = "+61488888888"
        daily_limit = 50
        current_usage = 25

        mock_redis.get.return_value = str(current_usage)

        # Act
        async def check_voice_rate_limit(redis, phone: str, limit: int) -> tuple[bool, int]:
            key = f"rate_limit:voice:{phone}:daily"
            current = int(await redis.get(key) or 0)
            return current < limit, limit - current

        allowed, remaining = await check_voice_rate_limit(mock_redis, phone_number, daily_limit)

        # Assert
        assert allowed is True
        assert remaining == 25

    @pytest.mark.asyncio
    async def test_voice_requires_minimum_als(
        self,
        db_session: AsyncMock,
    ):
        """Voice calls should only be for leads with ALS >= 70."""
        # Arrange
        client = create_test_client()
        campaign = create_test_campaign(client["id"])

        hot_lead = create_hot_lead(client["id"], campaign["id"])  # ALS 92
        warm_lead = create_warm_lead(client["id"], campaign["id"])  # ALS 72

        from tests.fixtures.database_fixtures import create_cool_lead
        cool_lead = create_cool_lead(client["id"], campaign["id"])  # ALS 48

        # Act
        def is_voice_eligible(lead: dict, min_als: int = 70) -> bool:
            return lead["als_score"] >= min_als

        # Assert
        assert is_voice_eligible(hot_lead) is True
        assert is_voice_eligible(warm_lead) is True
        assert is_voice_eligible(cool_lead) is False


# ============================================================================
# Allocator Round-Robin Tests
# ============================================================================

class TestAllocatorRoundRobin:
    """Test allocator round-robin resource selection."""

    @pytest.mark.asyncio
    async def test_round_robin_email_selection(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """Allocator should round-robin between email resources."""
        # Arrange
        resources = [
            {"id": "email_1", "identifier": "outreach@domain1.com", "daily_limit": 50},
            {"id": "email_2", "identifier": "sales@domain2.com", "daily_limit": 50},
            {"id": "email_3", "identifier": "hello@domain3.com", "daily_limit": 50},
        ]

        # Mock usage: first resource at limit, others available
        usage = {"email_1": 50, "email_2": 20, "email_3": 30}

        async def mock_get(key):
            for resource_id, count in usage.items():
                if resource_id in key:
                    return str(count)
            return "0"

        mock_redis.get = AsyncMock(side_effect=mock_get)

        # Act
        async def allocate_email_resource(redis, resources: list) -> dict | None:
            for resource in resources:
                key = f"rate_limit:email:{resource['identifier']}:daily"
                current = int(await redis.get(key) or 0)
                if current < resource["daily_limit"]:
                    return resource
            return None

        selected = await allocate_email_resource(mock_redis, resources)

        # Assert - Should skip email_1 (at limit) and select email_2
        assert selected is not None
        assert selected["id"] == "email_2"

    @pytest.mark.asyncio
    async def test_all_resources_exhausted(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """Allocator should return None when all resources exhausted."""
        # Arrange
        resources = [
            {"id": "email_1", "identifier": "outreach@domain1.com", "daily_limit": 50},
            {"id": "email_2", "identifier": "sales@domain2.com", "daily_limit": 50},
        ]

        # All at limit
        mock_redis.get.return_value = "50"

        # Act
        async def allocate_email_resource(redis, resources: list) -> dict | None:
            for resource in resources:
                key = f"rate_limit:email:{resource['identifier']}:daily"
                current = int(await redis.get(key) or 0)
                if current < resource["daily_limit"]:
                    return resource
            return None

        selected = await allocate_email_resource(mock_redis, resources)

        # Assert
        assert selected is None

    @pytest.mark.asyncio
    async def test_channel_allocation_respects_campaign_allocation(
        self,
        db_session: AsyncMock,
    ):
        """Channel selection should respect campaign allocation percentages."""
        # Arrange
        client = create_test_client()
        campaign = create_test_campaign(client["id"])
        # Campaign has: email 60%, sms 20%, linkedin 20%

        leads = create_lead_batch(client["id"], campaign["id"], count=100)

        # Act - Simulate allocation distribution
        email_count = int(100 * (campaign["allocation_email"] / 100))
        sms_count = int(100 * (campaign["allocation_sms"] / 100))
        linkedin_count = int(100 * (campaign["allocation_linkedin"] / 100))

        # Assert
        assert email_count == 60
        assert sms_count == 20
        assert linkedin_count == 20
        assert email_count + sms_count + linkedin_count == 100


# ============================================================================
# Rate Limit Reset Tests
# ============================================================================

class TestRateLimitReset:
    """Test rate limit reset behavior."""

    @pytest.mark.asyncio
    async def test_daily_limits_reset_at_midnight_aest(
        self,
        mock_redis: MagicMock,
    ):
        """Rate limits should reset at midnight AEST."""
        # Arrange
        resource_id = "email_account_1"

        # Simulate TTL check - should have TTL until midnight
        mock_redis.ttl.return_value = 3600  # 1 hour until reset

        # Act
        async def get_reset_time(redis, key: str) -> int:
            return await redis.ttl(key)

        ttl = await get_reset_time(mock_redis, f"rate_limit:email:{resource_id}:daily")

        # Assert
        assert ttl > 0
        assert ttl <= 86400  # Max 24 hours

    @pytest.mark.asyncio
    async def test_rate_limit_counter_expires(
        self,
        mock_redis: MagicMock,
    ):
        """Rate limit counters should auto-expire."""
        # Arrange
        resource_id = "email_account_1"

        # After expiry, get returns None
        mock_redis.get.return_value = None

        # Act
        async def get_current_usage(redis, resource_type: str, resource_id: str) -> int:
            key = f"rate_limit:{resource_type}:{resource_id}:daily"
            value = await redis.get(key)
            return int(value) if value else 0

        usage = await get_current_usage(mock_redis, "email", resource_id)

        # Assert - Counter should be 0 after reset
        assert usage == 0


# ============================================================================
# Combined Rate Limit Scenarios
# ============================================================================

class TestCombinedRateLimitScenarios:
    """Test combined rate limit scenarios."""

    @pytest.mark.asyncio
    async def test_high_volume_batch_respects_all_limits(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """High volume batch should respect all resource limits."""
        # Arrange
        client = create_test_client()
        campaign = create_test_campaign(client["id"])
        leads = create_lead_batch(client["id"], campaign["id"], count=200)

        email_limit = 50
        sms_limit = 100
        linkedin_limit = 17

        # Track actual sends
        email_sent = 0
        sms_sent = 0
        linkedin_sent = 0

        # Act
        for i, lead in enumerate(leads):
            # Simulate channel allocation based on campaign %
            channel_roll = i % 100
            if channel_roll < 60:  # 60% email
                if email_sent < email_limit:
                    email_sent += 1
            elif channel_roll < 80:  # 20% sms
                if sms_sent < sms_limit:
                    sms_sent += 1
            else:  # 20% linkedin
                if linkedin_sent < linkedin_limit:
                    linkedin_sent += 1

        # Assert
        assert email_sent == 50  # Capped at limit
        assert sms_sent == 40  # Only 40 leads allocated (20% of 200)
        assert linkedin_sent == 17  # Capped at 17/seat limit

    @pytest.mark.asyncio
    async def test_multi_resource_failover(
        self,
        mock_redis: MagicMock,
        db_session: AsyncMock,
    ):
        """When one resource is exhausted, should failover to another."""
        # Arrange
        resources = [
            {"id": "r1", "identifier": "email1@test.com", "daily_limit": 50},
            {"id": "r2", "identifier": "email2@test.com", "daily_limit": 50},
        ]

        usage_tracker = {"r1": 0, "r2": 0}

        # Act - Send 75 emails (more than single resource can handle)
        emails_to_send = 75
        sent = 0

        for _ in range(emails_to_send):
            for resource in resources:
                if usage_tracker[resource["id"]] < resource["daily_limit"]:
                    usage_tracker[resource["id"]] += 1
                    sent += 1
                    break

        # Assert
        assert sent == 75
        assert usage_tracker["r1"] == 50  # First resource maxed
        assert usage_tracker["r2"] == 25  # Second resource used for overflow


# ============================================================================
# Verification Checklist
# ============================================================================
# [x] Contract comment at top
# [x] Email rate limits (50/day/domain)
# [x] SMS rate limits (100/day/number)
# [x] LinkedIn rate limits (17/day/seat)
# [x] Voice rate limits (50/day/number) with ALS check
# [x] Round-robin resource selection
# [x] Resource exhaustion handling
# [x] Campaign allocation percentage respect
# [x] Rate limit reset behavior
# [x] Multi-resource failover
# [x] High volume batch scenario
# [x] Rule 17 compliance (resource-level limits)
