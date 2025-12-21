"""
FILE: tests/test_engines/test_linkedin.py
PURPOSE: Tests for LinkedIn engine
PHASE: 4 (Engines)
TASK: ENG-007
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.engines.linkedin import LinkedInEngine, get_linkedin_engine
from src.models.base import ChannelType, LeadStatus


@pytest.fixture
def mock_heyreach_client():
    """Mock HeyReach client."""
    class MockHeyReachClient:
        async def send_connection_request(self, seat_id, linkedin_url, message=None):
            return {
                "success": True,
                "request_id": f"req_{uuid4().hex[:16]}",
                "status": "pending",
                "provider": "heyreach",
            }

        async def send_message(self, seat_id, linkedin_url, message):
            return {
                "success": True,
                "message_id": f"msg_{uuid4().hex[:16]}",
                "status": "sent",
                "provider": "heyreach",
            }

        async def get_new_replies(self, seat_id):
            return [
                {
                    "message_id": "reply_1",
                    "profile_url": "https://linkedin.com/in/test",
                    "name": "Test User",
                    "message": "Thanks for reaching out!",
                    "received_at": datetime.utcnow().isoformat(),
                }
            ]

    return MockHeyReachClient()


@pytest.fixture
def linkedin_engine(mock_heyreach_client):
    """Create LinkedIn engine with mock client."""
    return LinkedInEngine(heyreach_client=mock_heyreach_client)


@pytest.fixture
def mock_db():
    """Mock database session."""
    class MockDB:
        def __init__(self):
            self.committed = False
            self.added = []

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            self.committed = True

        async def execute(self, stmt):
            class Result:
                def scalar_one_or_none(self):
                    return None
                def scalars(self):
                    class Scalars:
                        def all(self):
                            return []
                    return Scalars()
            return Result()

    return MockDB()


@pytest.fixture
def mock_lead():
    """Mock lead."""
    class MockLead:
        id = uuid4()
        client_id = uuid4()
        campaign_id = uuid4()
        email = "test@example.com"
        phone = "+61400000000"
        linkedin_url = "https://linkedin.com/in/test-user"
        first_name = "Test"
        last_name = "User"
        company = "Test Corp"
        status = LeadStatus.ENRICHED

    return MockLead()


@pytest.fixture
def mock_campaign():
    """Mock campaign."""
    class MockCampaign:
        id = uuid4()
        client_id = uuid4()
        name = "Test Campaign"
        status = "active"

    return MockCampaign()


class TestLinkedInEngine:
    """Test suite for LinkedIn engine."""

    def test_engine_properties(self, linkedin_engine):
        """Test engine properties."""
        assert linkedin_engine.name == "linkedin"
        assert linkedin_engine.channel == ChannelType.LINKEDIN

    def test_singleton(self):
        """Test singleton pattern."""
        engine1 = get_linkedin_engine()
        engine2 = get_linkedin_engine()
        assert engine1 is engine2

    @pytest.mark.asyncio
    async def test_send_missing_seat_id(self, linkedin_engine, mock_db, mock_lead, mock_campaign):
        """Test send fails without seat_id."""
        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        linkedin_engine.get_lead_by_id = mock_get_lead
        linkedin_engine.get_campaign_by_id = mock_get_campaign

        result = await linkedin_engine.send(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            content="Test LinkedIn message",
            # seat_id missing
        )

        assert not result.success
        assert "seat_id is required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_invalid_action(self, linkedin_engine, mock_db, mock_lead, mock_campaign):
        """Test send fails with invalid action."""
        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        linkedin_engine.get_lead_by_id = mock_get_lead
        linkedin_engine.get_campaign_by_id = mock_get_campaign

        result = await linkedin_engine.send(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            content="Test message",
            seat_id="seat_123",
            action="invalid",
        )

        assert not result.success
        assert "invalid action" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_lead_no_linkedin(self, linkedin_engine, mock_db, mock_lead, mock_campaign):
        """Test send fails if lead has no LinkedIn URL."""
        mock_lead.linkedin_url = None

        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        linkedin_engine.get_lead_by_id = mock_get_lead
        linkedin_engine.get_campaign_by_id = mock_get_campaign

        result = await linkedin_engine.send(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            content="Test message",
            seat_id="seat_123",
        )

        assert not result.success
        assert "no linkedin url" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_message_success(self, linkedin_engine, mock_db, mock_lead, mock_campaign):
        """Test successful LinkedIn message send."""
        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        linkedin_engine.get_lead_by_id = mock_get_lead
        linkedin_engine.get_campaign_by_id = mock_get_campaign

        # Mock rate limiter
        from src.integrations import redis
        original_check = redis.rate_limiter.check_and_increment

        async def mock_check(*args, **kwargs):
            return True, 1

        redis.rate_limiter.check_and_increment = mock_check

        try:
            result = await linkedin_engine.send(
                db=mock_db,
                lead_id=mock_lead.id,
                campaign_id=mock_campaign.id,
                content="Test LinkedIn message",
                seat_id="seat_123",
                action="message",
            )

            assert result.success
            assert result.data["provider_id"] is not None
            assert result.data["linkedin_url"] == mock_lead.linkedin_url
            assert result.data["seat_id"] == "seat_123"
            assert result.data["action"] == "message"
            assert mock_db.committed

        finally:
            redis.rate_limiter.check_and_increment = original_check

    @pytest.mark.asyncio
    async def test_send_connection_request_success(self, linkedin_engine, mock_db, mock_lead, mock_campaign):
        """Test successful LinkedIn connection request."""
        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        linkedin_engine.get_lead_by_id = mock_get_lead
        linkedin_engine.get_campaign_by_id = mock_get_campaign

        # Mock rate limiter
        from src.integrations import redis
        original_check = redis.rate_limiter.check_and_increment

        async def mock_check(*args, **kwargs):
            return True, 1

        redis.rate_limiter.check_and_increment = mock_check

        try:
            result = await linkedin_engine.send(
                db=mock_db,
                lead_id=mock_lead.id,
                campaign_id=mock_campaign.id,
                content="Nice to connect!",
                seat_id="seat_123",
                action="connection",
            )

            assert result.success
            assert result.data["provider_id"] is not None
            assert result.data["action"] == "connection"
            assert result.data["status"] == "pending"

        finally:
            redis.rate_limiter.check_and_increment = original_check

    @pytest.mark.asyncio
    async def test_send_connection_request_helper(self, linkedin_engine, mock_db, mock_lead, mock_campaign):
        """Test send_connection_request helper method."""
        async def mock_validate_and_send(*args, **kwargs):
            from src.engines.base import EngineResult
            return EngineResult.ok(
                data={
                    "provider_id": "req_123",
                    "action": "connection",
                    "status": "pending",
                }
            )

        linkedin_engine.validate_and_send = mock_validate_and_send

        result = await linkedin_engine.send_connection_request(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            message="Let's connect!",
            seat_id="seat_123",
        )

        assert result.success
        assert result.data["action"] == "connection"

    @pytest.mark.asyncio
    async def test_send_message_helper(self, linkedin_engine, mock_db, mock_lead, mock_campaign):
        """Test send_message helper method."""
        async def mock_validate_and_send(*args, **kwargs):
            from src.engines.base import EngineResult
            return EngineResult.ok(
                data={
                    "provider_id": "msg_123",
                    "action": "message",
                    "status": "sent",
                }
            )

        linkedin_engine.validate_and_send = mock_validate_and_send

        result = await linkedin_engine.send_message(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            message="Hello!",
            seat_id="seat_123",
        )

        assert result.success
        assert result.data["action"] == "message"

    @pytest.mark.asyncio
    async def test_get_seat_status(self, linkedin_engine):
        """Test get seat status."""
        # Mock rate limiter
        from src.integrations import redis
        original_usage = redis.rate_limiter.get_usage

        async def mock_usage(*args, **kwargs):
            return 5

        redis.rate_limiter.get_usage = mock_usage

        try:
            result = await linkedin_engine.get_seat_status("seat_123")

            assert result.success
            assert result.data["seat_id"] == "seat_123"
            assert result.data["daily_limit"] == 17
            assert result.data["daily_used"] == 5
            assert result.data["remaining"] == 12
            assert result.data["can_send"] is True

        finally:
            redis.rate_limiter.get_usage = original_usage

    @pytest.mark.asyncio
    async def test_get_new_replies(self, linkedin_engine, mock_db):
        """Test get new replies."""
        result = await linkedin_engine.get_new_replies(
            db=mock_db,
            seat_id="seat_123",
        )

        assert result.success
        assert result.data["seat_id"] == "seat_123"
        assert result.data["reply_count"] == 1
        assert len(result.data["replies"]) == 1
        assert result.data["replies"][0]["message"] == "Thanks for reaching out!"

    @pytest.mark.asyncio
    async def test_batch_send(self, linkedin_engine, mock_db):
        """Test batch LinkedIn actions."""
        send_count = 0

        async def mock_validate_and_send(db, lead_id, campaign_id, content, **kwargs):
            nonlocal send_count
            send_count += 1
            from src.engines.base import EngineResult
            if send_count <= 2:
                return EngineResult.ok(
                    data={
                        "provider_id": f"id_{send_count}",
                        "action": kwargs.get("action", "message"),
                    }
                )
            else:
                return EngineResult.fail(error="Rate limit exceeded")

        linkedin_engine.validate_and_send = mock_validate_and_send

        actions = [
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "Message 1",
                "seat_id": "seat_123",
                "action": "message",
            },
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "Connection request",
                "seat_id": "seat_123",
                "action": "connection",
            },
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "Message 3",
                "seat_id": "seat_123",
                "action": "message",
            },
        ]

        result = await linkedin_engine.send_batch(db=mock_db, actions=actions)

        assert result.success
        assert result.data["total"] == 3
        assert result.data["sent"] == 2
        assert result.data["rate_limited"] == 1


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties (name, channel)
# [x] Test singleton pattern
# [x] Test send validation (missing fields)
# [x] Test invalid action
# [x] Test send with no LinkedIn URL
# [x] Test successful message send
# [x] Test successful connection request
# [x] Test helper methods (send_connection_request, send_message)
# [x] Test get_seat_status
# [x] Test get_new_replies
# [x] Test batch sending
# [x] All tests use async/await
# [x] All tests have docstrings
