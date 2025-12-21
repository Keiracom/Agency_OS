"""
FILE: tests/test_engines/test_sms.py
PURPOSE: Tests for SMS engine
PHASE: 4 (Engines)
TASK: ENG-006
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.engines.sms import SMSEngine, get_sms_engine
from src.models.base import ChannelType, LeadStatus
from src.exceptions import DNCRError


@pytest.fixture
def mock_twilio_client():
    """Mock Twilio client."""
    class MockTwilioClient:
        def __init__(self):
            self.dncr_numbers = set()

        async def send_sms(self, to_number, message, from_number, check_dncr=True):
            if check_dncr and to_number in self.dncr_numbers:
                raise DNCRError(
                    phone=to_number,
                    message=f"Phone number {to_number} is on the Do Not Call Register",
                )

            return {
                "success": True,
                "message_sid": f"SM{uuid4().hex[:32]}",
                "status": "queued",
                "provider": "twilio",
            }

        async def check_dncr(self, phone_number):
            return phone_number in self.dncr_numbers

    return MockTwilioClient()


@pytest.fixture
def sms_engine(mock_twilio_client):
    """Create SMS engine with mock client."""
    return SMSEngine(twilio_client=mock_twilio_client)


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


class TestSMSEngine:
    """Test suite for SMS engine."""

    def test_engine_properties(self, sms_engine):
        """Test engine properties."""
        assert sms_engine.name == "sms"
        assert sms_engine.channel == ChannelType.SMS

    def test_singleton(self):
        """Test singleton pattern."""
        engine1 = get_sms_engine()
        engine2 = get_sms_engine()
        assert engine1 is engine2

    @pytest.mark.asyncio
    async def test_send_missing_from_number(self, sms_engine, mock_db, mock_lead, mock_campaign):
        """Test send fails without from_number."""
        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        sms_engine.get_lead_by_id = mock_get_lead
        sms_engine.get_campaign_by_id = mock_get_campaign

        result = await sms_engine.send(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            content="Test SMS message",
            # from_number missing
        )

        assert not result.success
        assert "phone number is required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_lead_no_phone(self, sms_engine, mock_db, mock_lead, mock_campaign):
        """Test send fails if lead has no phone."""
        mock_lead.phone = None

        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        sms_engine.get_lead_by_id = mock_get_lead
        sms_engine.get_campaign_by_id = mock_get_campaign

        result = await sms_engine.send(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            content="Test SMS message",
            from_number="+61400111222",
        )

        assert not result.success
        assert "no phone number" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_success(self, sms_engine, mock_db, mock_lead, mock_campaign):
        """Test successful SMS send."""
        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        sms_engine.get_lead_by_id = mock_get_lead
        sms_engine.get_campaign_by_id = mock_get_campaign

        # Mock rate limiter
        from src.integrations import redis
        original_check = redis.rate_limiter.check_and_increment

        async def mock_check(*args, **kwargs):
            return True, 1

        redis.rate_limiter.check_and_increment = mock_check

        try:
            result = await sms_engine.send(
                db=mock_db,
                lead_id=mock_lead.id,
                campaign_id=mock_campaign.id,
                content="Test SMS message",
                from_number="+61400111222",
            )

            assert result.success
            assert result.data["message_sid"] is not None
            assert result.data["to_number"] == mock_lead.phone
            assert result.data["from_number"] == "+61400111222"
            assert result.data["status"] == "queued"
            assert mock_db.committed

        finally:
            redis.rate_limiter.check_and_increment = original_check

    @pytest.mark.asyncio
    async def test_send_dncr_rejection(self, sms_engine, mock_db, mock_lead, mock_campaign, mock_twilio_client):
        """Test SMS rejected by DNCR check."""
        # Add lead's phone to DNCR list
        mock_twilio_client.dncr_numbers.add(mock_lead.phone)

        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        sms_engine.get_lead_by_id = mock_get_lead
        sms_engine.get_campaign_by_id = mock_get_campaign

        # Mock rate limiter
        from src.integrations import redis
        original_check = redis.rate_limiter.check_and_increment

        async def mock_check(*args, **kwargs):
            return True, 1

        redis.rate_limiter.check_and_increment = mock_check

        try:
            result = await sms_engine.send(
                db=mock_db,
                lead_id=mock_lead.id,
                campaign_id=mock_campaign.id,
                content="Test SMS message",
                from_number="+61400111222",
            )

            assert not result.success
            assert "do not call register" in result.error.lower()
            assert result.metadata.get("reason") == "dncr"
            assert mock_db.committed  # Activity logged

        finally:
            redis.rate_limiter.check_and_increment = original_check

    @pytest.mark.asyncio
    async def test_send_skip_dncr(self, sms_engine, mock_db, mock_lead, mock_campaign, mock_twilio_client):
        """Test SMS send with DNCR check skipped."""
        # Add lead's phone to DNCR list
        mock_twilio_client.dncr_numbers.add(mock_lead.phone)

        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        sms_engine.get_lead_by_id = mock_get_lead
        sms_engine.get_campaign_by_id = mock_get_campaign

        # Mock rate limiter
        from src.integrations import redis
        original_check = redis.rate_limiter.check_and_increment

        async def mock_check(*args, **kwargs):
            return True, 1

        redis.rate_limiter.check_and_increment = mock_check

        try:
            # Should succeed because we skip DNCR check
            result = await sms_engine.send(
                db=mock_db,
                lead_id=mock_lead.id,
                campaign_id=mock_campaign.id,
                content="Test SMS message",
                from_number="+61400111222",
                skip_dncr=True,
            )

            assert result.success

        finally:
            redis.rate_limiter.check_and_increment = original_check

    @pytest.mark.asyncio
    async def test_check_dncr(self, sms_engine, mock_twilio_client):
        """Test DNCR check method."""
        # Not on DNCR
        result = await sms_engine.check_dncr("+61400000000")
        assert result.success
        assert result.data["on_dncr"] is False
        assert result.data["can_contact"] is True

        # On DNCR
        mock_twilio_client.dncr_numbers.add("+61400999999")
        result = await sms_engine.check_dncr("+61400999999")
        assert result.success
        assert result.data["on_dncr"] is True
        assert result.data["can_contact"] is False

    @pytest.mark.asyncio
    async def test_batch_send(self, sms_engine, mock_db):
        """Test batch SMS sending."""
        send_count = 0

        async def mock_validate_and_send(db, lead_id, campaign_id, content, **kwargs):
            nonlocal send_count
            send_count += 1
            if send_count == 1:
                # Success
                return await sms_engine.send(db, lead_id, campaign_id, content, **kwargs)
            elif send_count == 2:
                # DNCR rejection
                from src.engines.base import EngineResult
                return EngineResult.fail(
                    error="Phone number is on Do Not Call Register",
                    metadata={"reason": "dncr"},
                )
            else:
                # Rate limited
                from src.engines.base import EngineResult
                return EngineResult.fail(error="Rate limit exceeded")

        sms_engine.validate_and_send = mock_validate_and_send

        messages = [
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "SMS 1",
                "from_number": "+61400111222",
            },
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "SMS 2",
                "from_number": "+61400111222",
            },
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "SMS 3",
                "from_number": "+61400111222",
            },
        ]

        result = await sms_engine.send_batch(db=mock_db, messages=messages)

        assert result.success
        assert result.data["total"] == 3
        assert result.data["sent"] == 1
        assert result.data["dncr_rejected"] == 1
        assert result.data["rate_limited"] == 1


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties (name, channel)
# [x] Test singleton pattern
# [x] Test send validation (missing fields)
# [x] Test send with no phone number
# [x] Test successful send
# [x] Test DNCR rejection
# [x] Test skip DNCR
# [x] Test check_dncr method
# [x] Test batch sending
# [x] All tests use async/await
# [x] All tests have docstrings
