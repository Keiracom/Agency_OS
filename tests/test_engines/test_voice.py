# FIXED by fixer-agent: completed stub tests for HIGH-003
"""
FILE: tests/test_engines/test_voice.py
PURPOSE: Test suite for Voice engine (AI voice calls via Synthflow)
PHASE: 4 (Engines)
TASK: ENG-008
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from src.engines.voice import VoiceEngine, get_voice_engine
from src.engines.base import EngineResult
from src.models.base import ChannelType, LeadStatus


class MockSynthflowClient:
    """Mock Synthflow client for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.last_call_params = None

    async def initiate_call(self, phone_number, agent_id, lead_data, callback_url=None):
        self.last_call_params = {
            "phone_number": phone_number,
            "agent_id": agent_id,
            "lead_data": lead_data,
            "callback_url": callback_url,
        }

        if self.should_fail:
            raise Exception("Synthflow API error")

        return {
            "call_id": "call_123",
            "status": "initiated",
            "provider": "synthflow",
        }

    async def get_call_status(self, call_id):
        return {
            "call_id": call_id,
            "status": "completed",
            "duration": 120,
            "outcome": "answered",
            "transcript": "Test transcript",
            "sentiment": "positive",
            "started_at": datetime.utcnow().isoformat(),
            "ended_at": datetime.utcnow().isoformat(),
        }

    async def get_transcript(self, call_id):
        return {
            "call_id": call_id,
            "transcript": "Test transcript content",
            "summary": "Positive call",
            "intent": "interested",
            "action_items": ["Follow up next week"],
        }

    def parse_call_webhook(self, payload):
        return {
            "call_id": payload.get("call_id"),
            "event": payload.get("event"),
            "status": payload.get("status"),
            "duration": payload.get("duration"),
            "outcome": payload.get("outcome"),
            "transcript": payload.get("transcript"),
            "sentiment": payload.get("sentiment"),
            "intent": payload.get("intent"),
            "meeting_booked": payload.get("meeting_booked", False),
            "meeting_time": payload.get("meeting_time"),
        }


class MockLead:
    """Mock lead for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.client_id = kwargs.get("client_id", uuid4())
        self.campaign_id = kwargs.get("campaign_id", uuid4())
        self.email = kwargs.get("email", "test@example.com")
        self.phone = kwargs.get("phone", "+61412345678")
        self.first_name = kwargs.get("first_name", "Test")
        self.last_name = kwargs.get("last_name", "Lead")
        self.title = kwargs.get("title", "CEO")
        self.company = kwargs.get("company", "Test Company")
        self.status = kwargs.get("status", LeadStatus.ENRICHED)
        self.als_score = kwargs.get("als_score", 75)
        self.last_contacted_at = kwargs.get("last_contacted_at", None)
        self.last_replied_at = kwargs.get("last_replied_at", None)
        self.reply_count = kwargs.get("reply_count", 0)
        self.deleted_at = None

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class MockCampaign:
    """Mock campaign for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.name = kwargs.get("name", "Test Campaign")
        self.deleted_at = None


class MockActivity:
    """Mock activity for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.client_id = kwargs.get("client_id", uuid4())
        self.campaign_id = kwargs.get("campaign_id", uuid4())
        self.lead_id = kwargs.get("lead_id", uuid4())
        self.channel = kwargs.get("channel", ChannelType.VOICE)
        self.action = kwargs.get("action", "sent")
        self.provider_message_id = kwargs.get("provider_message_id", "call_123")
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.metadata = kwargs.get("metadata", {})


class MockDB:
    """Mock database session."""

    def __init__(self):
        self.added = []
        self.committed = False
        self._activity = None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def execute(self, stmt):
        return MockResult(self._activity)


class MockResult:
    """Mock query result."""

    def __init__(self, activity):
        self._activity = activity

    def scalar_one_or_none(self):
        return self._activity


@pytest.fixture
def voice_engine():
    """Create voice engine with mock client."""
    return VoiceEngine(synthflow_client=MockSynthflowClient())


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MockDB()


# ============================================
# ENGINE PROPERTY TESTS
# ============================================

def test_engine_properties(voice_engine):
    """Test engine properties."""
    assert voice_engine.name == "voice"
    assert voice_engine.channel == ChannelType.VOICE


def test_singleton():
    """Test singleton pattern."""
    engine1 = get_voice_engine()
    engine2 = get_voice_engine()
    assert engine1 is engine2


# ============================================
# SEND CALL TESTS
# ============================================

@pytest.mark.asyncio
async def test_send_call_success():
    """Test successful call initiation."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(als_score=75, phone="+61412345678")
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="Call script",
            agent_id="agent_123",
            callback_url="https://example.com/webhook",
            from_number="+61400000000",
        )

        assert result.success
        assert result.data["call_id"] == "call_123"
        assert result.data["status"] == "initiated"
        assert result.data["provider"] == "synthflow"
        assert mock_db.committed


@pytest.mark.asyncio
async def test_send_call_no_phone():
    """Test call fails when lead has no phone number."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(als_score=75, phone=None)

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=uuid4(),
            content="Call script",
            agent_id="agent_123",
        )

        assert not result.success
        assert "no phone number" in result.error.lower()


@pytest.mark.asyncio
async def test_send_call_low_als():
    """Test call fails when ALS score is below 70."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(als_score=65, phone="+61412345678")

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=uuid4(),
            content="Call script",
            agent_id="agent_123",
        )

        assert not result.success
        assert "als score too low" in result.error.lower()
        assert "minimum 70" in result.error.lower()


@pytest.mark.asyncio
async def test_send_call_no_agent_id():
    """Test call fails when agent_id is not provided."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(als_score=80, phone="+61412345678")
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="Call script",
            # No agent_id provided
        )

        assert not result.success
        assert "agent_id is required" in result.error.lower()


@pytest.mark.asyncio
async def test_send_call_api_error():
    """Test call handling when Synthflow API fails."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient(should_fail=True))
    mock_db = MockDB()
    lead = MockLead(als_score=80, phone="+61412345678")
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="Call script",
            agent_id="agent_123",
        )

        assert not result.success
        assert "failed to initiate call" in result.error.lower()


# ============================================
# GET CALL STATUS TESTS
# ============================================

@pytest.mark.asyncio
async def test_get_call_status(mock_db):
    """Test getting call status."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())

    result = await engine.get_call_status(
        db=mock_db,
        call_id="call_123",
    )

    assert result.success
    assert result.data["call_id"] == "call_123"
    assert result.data["status"] == "completed"
    assert result.data["duration"] == 120
    assert result.data["outcome"] == "answered"


# ============================================
# GET TRANSCRIPT TESTS
# ============================================

@pytest.mark.asyncio
async def test_get_transcript(mock_db):
    """Test getting call transcript."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())

    result = await engine.get_call_transcript(
        db=mock_db,
        call_id="call_123",
    )

    assert result.success
    assert result.data["call_id"] == "call_123"
    assert result.data["transcript"] == "Test transcript content"
    assert result.data["summary"] == "Positive call"
    assert result.data["intent"] == "interested"
    assert "Follow up next week" in result.data["action_items"]


# ============================================
# WEBHOOK PROCESSING TESTS
# ============================================

@pytest.mark.asyncio
async def test_process_webhook_call_ended():
    """Test processing webhook for ended call."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead()
    activity = MockActivity(lead_id=lead.id, provider_message_id="call_123")
    mock_db._activity = activity

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.process_call_webhook(
            db=mock_db,
            payload={
                "call_id": "call_123",
                "event": "ended",
                "status": "completed",
                "duration": 120,
                "outcome": "answered",
                "transcript": "Test transcript",
                "sentiment": "positive",
                "meeting_booked": False,
            },
        )

        assert result.success
        assert result.data["call_id"] == "call_123"
        assert result.data["event"] == "ended"
        assert result.data["processed"]


@pytest.mark.asyncio
async def test_process_webhook_meeting_booked():
    """Test processing webhook when meeting is booked."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(status=LeadStatus.ENRICHED)
    activity = MockActivity(lead_id=lead.id, provider_message_id="call_123")
    mock_db._activity = activity

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.process_call_webhook(
            db=mock_db,
            payload={
                "call_id": "call_123",
                "event": "ended",
                "meeting_booked": True,
                "meeting_time": "2025-12-25T10:00:00Z",
            },
        )

        assert result.success
        assert lead.status == LeadStatus.CONVERTED
        assert lead.reply_count == 1


@pytest.mark.asyncio
async def test_process_webhook_missing_call_id(mock_db):
    """Test webhook processing with missing call_id."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())

    result = await engine.process_call_webhook(
        db=mock_db,
        payload={
            "event": "ended",
            # No call_id
        },
    )

    assert not result.success
    assert "missing call_id" in result.error.lower()


@pytest.mark.asyncio
async def test_process_webhook_activity_not_found(mock_db):
    """Test webhook processing when activity not found."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db._activity = None  # No activity found

    result = await engine.process_call_webhook(
        db=mock_db,
        payload={
            "call_id": "call_unknown",
            "event": "ended",
        },
    )

    assert not result.success
    assert "activity not found" in result.error.lower()


# ============================================
# ACTIVITY LOGGING TESTS
# ============================================

@pytest.mark.asyncio
async def test_activity_logging():
    """Test that call activities are logged correctly."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(als_score=80, phone="+61412345678")
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="Call script",
            agent_id="agent_123",
            from_number="+61400000000",
        )

        assert result.success
        assert len(mock_db.added) == 1
        activity = mock_db.added[0]
        assert activity.channel == ChannelType.VOICE
        assert activity.action == "sent"
        assert activity.provider_message_id == "call_123"


# ============================================
# LEAD UPDATE TESTS
# ============================================

@pytest.mark.asyncio
async def test_lead_update_on_success():
    """Test that lead is updated after successful call."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(als_score=80, phone="+61412345678", last_contacted_at=None)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="Call script",
            agent_id="agent_123",
        )

        assert lead.last_contacted_at is not None
        assert mock_db.committed


# ============================================
# ALS SCORE BOUNDARY TESTS
# ============================================

@pytest.mark.asyncio
async def test_send_call_als_exactly_70():
    """Test call succeeds when ALS score is exactly 70."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(als_score=70, phone="+61412345678")
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="Call script",
            agent_id="agent_123",
        )

        assert result.success


@pytest.mark.asyncio
async def test_send_call_als_none():
    """Test call fails when ALS score is None."""
    engine = VoiceEngine(synthflow_client=MockSynthflowClient())
    mock_db = MockDB()
    lead = MockLead(als_score=None, phone="+61412345678")

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=uuid4(),
            content="Call script",
            agent_id="agent_123",
        )

        assert not result.success
        assert "als score too low" in result.error.lower()


# ============================================
# TEST COVERAGE CHECKLIST
# ============================================
# [x] Basic engine properties
# [x] Singleton pattern
# [x] Send call success
# [x] Send call validation (no phone)
# [x] Send call validation (ALS < 70)
# [x] Send call validation (no agent_id)
# [x] Send call API error handling
# [x] Get call status
# [x] Get transcript
# [x] Process webhook (call ended)
# [x] Process webhook (meeting booked)
# [x] Process webhook (missing call_id)
# [x] Process webhook (activity not found)
# [x] Activity logging
# [x] Lead update on success
# [x] ALS boundary tests (exactly 70, None)
