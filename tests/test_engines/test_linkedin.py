"""
FILE: tests/test_engines/test_linkedin.py
PURPOSE: Tests for LinkedIn engine
PHASE: 4 (Engines)
TASK: ENG-007

NOTE: Per Directive #155, tests requiring Redis connection have been deleted.
Only unit tests with proper mocking are retained.
"""

from datetime import datetime, UTC
from uuid import uuid4

import pytest

from src.engines.linkedin import LinkedInEngine, get_linkedin_engine
from src.models.base import ChannelType, LeadStatus


@pytest.fixture
def mock_unipile_client():
    """Mock Unipile client."""
    class MockUnipileClient:
        async def send_connection_request(self, account_id, linkedin_url, message=None):
            return {
                "success": True,
                "request_id": f"req_{uuid4().hex[:16]}",
                "status": "pending",
                "provider": "unipile",
            }

        async def send_message(self, account_id, linkedin_url, message):
            return {
                "success": True,
                "message_id": f"msg_{uuid4().hex[:16]}",
                "status": "sent",
                "provider": "unipile",
            }

        async def get_new_replies(self, account_id):
            return [
                {
                    "message_id": "reply_1",
                    "profile_url": "https://linkedin.com/in/test",
                    "name": "Test User",
                    "message": "Thanks for reaching out!",
                    "received_at": datetime.now(UTC).isoformat(),
                }
            ]

    return MockUnipileClient()


@pytest.fixture
def linkedin_engine(mock_unipile_client):
    """Create LinkedIn engine with mock client."""
    return LinkedInEngine(unipile_client=mock_unipile_client)


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
        organization_country = "Australia"
        state = None

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
    async def test_send_missing_account_id(self, linkedin_engine, mock_db, mock_lead, mock_campaign):
        """Test send fails without account_id."""
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
            # account_id missing
        )

        assert not result.success
        assert "account_id is required" in result.error.lower()

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
            account_id="seat_123",
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
            account_id="seat_123",
        )

        assert not result.success
        assert "no linkedin url" in result.error.lower()

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
            account_id="seat_123",
        )

        assert result.success
        assert result.data["action"] == "message"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties (name, channel)
# [x] Test singleton pattern
# [x] Test send validation (missing fields)
# [x] Test invalid action
# [x] Test send with no LinkedIn URL
# [x] Test helper methods (send_message)
# [DELETED] Tests requiring Redis connection (per Directive #155)
