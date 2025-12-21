# FIXED by fixer-agent: completed stub tests for HIGH-003
"""
FILE: tests/test_engines/test_closer.py
PURPOSE: Test suite for Closer engine (reply handling with AI intent classification)
PHASE: 4 (Engines)
TASK: ENG-010
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.engines.closer import CloserEngine, get_closer_engine, INTENT_MAP
from src.engines.base import EngineResult
from src.models.base import ChannelType, IntentType, LeadStatus


class MockAnthropicClient:
    """Mock Anthropic client for testing."""

    def __init__(self, intent_override: str | None = None, confidence_override: float | None = None):
        self.intent_override = intent_override
        self.confidence_override = confidence_override
        self.last_message = None
        self.last_context = None

    async def classify_intent(self, message, context=None):
        self.last_message = message
        self.last_context = context

        # Use overrides if set
        if self.intent_override:
            return {
                "intent": self.intent_override,
                "confidence": self.confidence_override or 0.95,
                "reasoning": f"Classified as {self.intent_override}",
                "cost_aud": 0.01,
            }

        # Simple mock classification based on keywords
        message_lower = message.lower()

        if "meeting" in message_lower or "schedule" in message_lower:
            intent = "meeting_request"
            confidence = 0.95
        elif "interested" in message_lower:
            intent = "interested"
            confidence = 0.90
        elif "question" in message_lower or "?" in message_lower:
            intent = "question"
            confidence = 0.85
        elif "not interested" in message_lower or "no thanks" in message_lower:
            intent = "not_interested"
            confidence = 0.90
        elif "unsubscribe" in message_lower or "stop" in message_lower:
            intent = "unsubscribe"
            confidence = 0.98
        elif "out of office" in message_lower or "ooo" in message_lower:
            intent = "out_of_office"
            confidence = 0.95
        elif "auto-reply" in message_lower or "automated" in message_lower:
            intent = "auto_reply"
            confidence = 0.92
        else:
            intent = "question"
            confidence = 0.70

        return {
            "intent": intent,
            "confidence": confidence,
            "reasoning": f"Classified as {intent}",
            "cost_aud": 0.01,
        }


class MockLead:
    """Mock lead for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.client_id = kwargs.get("client_id", uuid4())
        self.campaign_id = kwargs.get("campaign_id", uuid4())
        self.email = kwargs.get("email", "test@example.com")
        self.first_name = kwargs.get("first_name", "Test")
        self.last_name = kwargs.get("last_name", "Lead")
        self.title = kwargs.get("title", "CEO")
        self.company = kwargs.get("company", "Test Company")
        self.status = kwargs.get("status", LeadStatus.IN_SEQUENCE)
        self.als_score = kwargs.get("als_score", 75)
        self.last_replied_at = kwargs.get("last_replied_at", None)
        self.reply_count = kwargs.get("reply_count", 0)
        self.next_outreach_at = kwargs.get("next_outreach_at", None)
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
        self.lead_id = kwargs.get("lead_id", uuid4())
        self.channel = kwargs.get("channel", ChannelType.EMAIL)
        self.action = kwargs.get("action", "replied")
        self.intent = kwargs.get("intent", IntentType.INTERESTED)
        self.intent_confidence = kwargs.get("intent_confidence", 0.95)
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.metadata = kwargs.get("metadata", {})


class MockDB:
    """Mock database session."""

    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []
        self._lead = MockLead()
        self._campaign = MockCampaign()
        self._activities = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed.append(obj)
        # Assign an ID if not present
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = uuid4()

    async def execute(self, stmt):
        return MockResult(self._activities)


class MockResult:
    """Mock query result."""

    def __init__(self, activities):
        self._activities = activities

    def scalars(self):
        return self

    def all(self):
        return self._activities

    def scalar_one_or_none(self):
        return self._activities[0] if self._activities else None


@pytest.fixture
def closer_engine():
    """Create closer engine with mock client."""
    return CloserEngine(anthropic_client=MockAnthropicClient())


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MockDB()


# ============================================
# ENGINE PROPERTY TESTS
# ============================================

def test_engine_properties(closer_engine):
    """Test engine properties."""
    assert closer_engine.name == "closer"


def test_singleton():
    """Test singleton pattern."""
    engine1 = get_closer_engine()
    engine2 = get_closer_engine()
    assert engine1 is engine2


def test_intent_map():
    """Test intent mapping."""
    assert INTENT_MAP["meeting_request"] == IntentType.MEETING_REQUEST
    assert INTENT_MAP["interested"] == IntentType.INTERESTED
    assert INTENT_MAP["question"] == IntentType.QUESTION
    assert INTENT_MAP["not_interested"] == IntentType.NOT_INTERESTED
    assert INTENT_MAP["unsubscribe"] == IntentType.UNSUBSCRIBE
    assert INTENT_MAP["out_of_office"] == IntentType.OUT_OF_OFFICE
    assert INTENT_MAP["auto_reply"] == IntentType.AUTO_REPLY


# ============================================
# INTENT CLASSIFICATION TESTS
# ============================================

@pytest.mark.asyncio
async def test_classify_meeting_request(mock_db):
    """Test classification of meeting request."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("meeting_request", 0.95))

    result = await engine.classify_message(
        db=mock_db,
        message="Can we schedule a meeting to discuss?",
        context="Test context",
    )

    assert result.success
    assert result.data["intent"] == "meeting_request"
    assert result.data["intent_enum"] == IntentType.MEETING_REQUEST.value
    assert result.data["confidence"] == 0.95


@pytest.mark.asyncio
async def test_classify_interested(mock_db):
    """Test classification of interested response."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("interested", 0.90))

    result = await engine.classify_message(
        db=mock_db,
        message="This looks interesting, tell me more",
        context="Test context",
    )

    assert result.success
    assert result.data["intent"] == "interested"
    assert result.data["intent_enum"] == IntentType.INTERESTED.value


@pytest.mark.asyncio
async def test_classify_question(mock_db):
    """Test classification of question."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("question", 0.85))

    result = await engine.classify_message(
        db=mock_db,
        message="What is the pricing for this service?",
        context="Test context",
    )

    assert result.success
    assert result.data["intent"] == "question"
    assert result.data["intent_enum"] == IntentType.QUESTION.value


@pytest.mark.asyncio
async def test_classify_not_interested(mock_db):
    """Test classification of not interested response."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("not_interested", 0.90))

    result = await engine.classify_message(
        db=mock_db,
        message="No thanks, we are not interested at this time",
        context="Test context",
    )

    assert result.success
    assert result.data["intent"] == "not_interested"
    assert result.data["intent_enum"] == IntentType.NOT_INTERESTED.value


@pytest.mark.asyncio
async def test_classify_unsubscribe(mock_db):
    """Test classification of unsubscribe request."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("unsubscribe", 0.98))

    result = await engine.classify_message(
        db=mock_db,
        message="Please unsubscribe me from this list",
        context="Test context",
    )

    assert result.success
    assert result.data["intent"] == "unsubscribe"
    assert result.data["intent_enum"] == IntentType.UNSUBSCRIBE.value


@pytest.mark.asyncio
async def test_classify_out_of_office(mock_db):
    """Test classification of out of office reply."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("out_of_office", 0.95))

    result = await engine.classify_message(
        db=mock_db,
        message="I am out of office until Jan 1st",
        context="Test context",
    )

    assert result.success
    assert result.data["intent"] == "out_of_office"
    assert result.data["intent_enum"] == IntentType.OUT_OF_OFFICE.value


@pytest.mark.asyncio
async def test_classify_auto_reply(mock_db):
    """Test classification of auto reply."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("auto_reply", 0.92))

    result = await engine.classify_message(
        db=mock_db,
        message="This is an automated response",
        context="Test context",
    )

    assert result.success
    assert result.data["intent"] == "auto_reply"
    assert result.data["intent_enum"] == IntentType.AUTO_REPLY.value


# ============================================
# PROCESS REPLY TESTS
# ============================================

@pytest.mark.asyncio
async def test_process_reply_success():
    """Test successful reply processing."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("interested", 0.90))
    mock_db = MockDB()
    lead = MockLead()
    campaign = MockCampaign()

    # Patch the helper methods
    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="I'm interested in learning more!",
            channel=ChannelType.EMAIL,
            provider_message_id="msg_123",
        )

        assert result.success
        assert result.data["intent"] == "interested"
        assert result.data["confidence"] == 0.90
        assert "activity_id" in result.data
        assert mock_db.committed


# ============================================
# INTENT HANDLING TESTS
# ============================================

@pytest.mark.asyncio
async def test_handle_meeting_request_intent():
    """Test handling of meeting request intent."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("meeting_request", 0.95))
    mock_db = MockDB()
    lead = MockLead(status=LeadStatus.IN_SEQUENCE)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="Let's schedule a meeting",
            channel=ChannelType.EMAIL,
        )

        assert result.success
        assert lead.status == LeadStatus.CONVERTED
        assert "marked_as_converted" in result.data["actions"]
        assert "created_meeting_task" in result.data["actions"]


@pytest.mark.asyncio
async def test_handle_interested_intent():
    """Test handling of interested intent."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("interested", 0.90))
    mock_db = MockDB()
    lead = MockLead(status=LeadStatus.ENRICHED)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="This looks interesting!",
            channel=ChannelType.EMAIL,
        )

        assert result.success
        assert lead.status == LeadStatus.IN_SEQUENCE
        assert "moved_to_sequence" in result.data["actions"]
        assert "created_follow_up_task" in result.data["actions"]


@pytest.mark.asyncio
async def test_handle_unsubscribe_intent():
    """Test handling of unsubscribe intent."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("unsubscribe", 0.98))
    mock_db = MockDB()
    lead = MockLead(status=LeadStatus.IN_SEQUENCE)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="Please unsubscribe me",
            channel=ChannelType.EMAIL,
        )

        assert result.success
        assert lead.status == LeadStatus.UNSUBSCRIBED
        assert "unsubscribed" in result.data["actions"]


@pytest.mark.asyncio
async def test_handle_not_interested_intent():
    """Test handling of not interested intent."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("not_interested", 0.90))
    mock_db = MockDB()
    lead = MockLead(status=LeadStatus.IN_SEQUENCE)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="No thanks, we are not interested",
            channel=ChannelType.EMAIL,
        )

        assert result.success
        assert lead.status == LeadStatus.ENRICHED
        assert "paused_outreach" in result.data["actions"]


@pytest.mark.asyncio
async def test_handle_out_of_office_intent():
    """Test handling of out of office intent."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("out_of_office", 0.95))
    mock_db = MockDB()
    lead = MockLead(status=LeadStatus.IN_SEQUENCE)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="I am out of office until next week",
            channel=ChannelType.EMAIL,
        )

        assert result.success
        assert lead.next_outreach_at is not None
        assert "scheduled_follow_up_2_weeks" in result.data["actions"]


@pytest.mark.asyncio
async def test_handle_auto_reply_intent():
    """Test handling of auto reply intent."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("auto_reply", 0.92))
    mock_db = MockDB()
    lead = MockLead(status=LeadStatus.IN_SEQUENCE)
    original_status = lead.status
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="This is an automated response",
            channel=ChannelType.EMAIL,
        )

        assert result.success
        assert lead.status == original_status  # No status change
        assert "ignored_auto_reply" in result.data["actions"]


# ============================================
# REPLY HISTORY TESTS
# ============================================

@pytest.mark.asyncio
async def test_get_reply_history():
    """Test getting reply history for a lead."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient())
    mock_db = MockDB()
    lead = MockLead()

    # Add mock activities
    mock_db._activities = [
        MockActivity(lead_id=lead.id, intent=IntentType.INTERESTED),
        MockActivity(lead_id=lead.id, intent=IntentType.QUESTION),
    ]

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.get_lead_reply_history(
            db=mock_db,
            lead_id=lead.id,
            limit=10,
        )

        assert result.success
        assert len(result.data) == 2
        assert result.metadata["total_replies"] == 2


# ============================================
# ACTIVITY LOGGING TESTS
# ============================================

@pytest.mark.asyncio
async def test_activity_logging():
    """Test that activities are logged correctly."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("interested", 0.90))
    mock_db = MockDB()
    lead = MockLead()
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="Test message",
            channel=ChannelType.EMAIL,
            provider_message_id="msg_456",
        )

        assert result.success
        assert len(mock_db.added) == 1  # One activity added
        activity = mock_db.added[0]
        assert activity.action == "replied"
        assert activity.channel == ChannelType.EMAIL


# ============================================
# LEAD STATUS UPDATE TESTS
# ============================================

@pytest.mark.asyncio
async def test_lead_status_updates_on_reply():
    """Test that lead status is updated correctly after reply."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("interested", 0.90))
    mock_db = MockDB()
    lead = MockLead(reply_count=0)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="Test message",
            channel=ChannelType.EMAIL,
        )

        # Check reply tracking is updated
        assert lead.reply_count == 1
        assert lead.last_replied_at is not None


@pytest.mark.asyncio
async def test_question_intent_creates_response_task():
    """Test that question intent creates response task."""
    engine = CloserEngine(anthropic_client=MockAnthropicClient("question", 0.85))
    mock_db = MockDB()
    lead = MockLead(status=LeadStatus.IN_SEQUENCE)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.process_reply(
            db=mock_db,
            lead_id=lead.id,
            message="What is the pricing?",
            channel=ChannelType.EMAIL,
        )

        assert result.success
        assert "created_response_task" in result.data["actions"]


# ============================================
# TEST COVERAGE CHECKLIST
# ============================================
# [x] Basic engine properties
# [x] Singleton pattern
# [x] Intent mapping
# [x] Classify meeting request
# [x] Classify interested
# [x] Classify question
# [x] Classify not interested
# [x] Classify unsubscribe
# [x] Classify out of office
# [x] Classify auto reply
# [x] Process reply success
# [x] Handle meeting request intent
# [x] Handle interested intent
# [x] Handle unsubscribe intent
# [x] Get reply history
# [x] Activity logging
# [x] Lead status updates
