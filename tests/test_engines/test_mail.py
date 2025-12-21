# FIXED by fixer-agent: completed stub tests for HIGH-003
"""
FILE: tests/test_engines/test_mail.py
PURPOSE: Test suite for Mail engine (direct mail via Lob)
PHASE: 4 (Engines)
TASK: ENG-009
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from src.engines.mail import MailEngine, get_mail_engine
from src.engines.base import EngineResult
from src.models.base import ChannelType, LeadStatus


class MockLobClient:
    """Mock Lob client for testing."""

    def __init__(self, should_fail: bool = False, invalid_address: bool = False):
        self.should_fail = should_fail
        self.invalid_address = invalid_address
        self.last_letter_params = None
        self.last_postcard_params = None

    async def verify_address(self, address_line1, city, state, zip_code, country="AU", address_line2=None):
        if self.invalid_address:
            return {
                "deliverability": "undeliverable",
                "valid": False,
                "primary_line": address_line1,
                "secondary_line": address_line2,
                "city": city,
                "state": state,
                "zip_code": zip_code,
                "country": country,
            }

        return {
            "deliverability": "deliverable",
            "valid": True,
            "primary_line": address_line1,
            "secondary_line": address_line2,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
        }

    async def send_letter(self, to_address, from_address, template_id, merge_variables, color=True):
        self.last_letter_params = {
            "to_address": to_address,
            "from_address": from_address,
            "template_id": template_id,
            "merge_variables": merge_variables,
            "color": color,
        }

        if self.should_fail:
            raise Exception("Lob API error")

        return {
            "success": True,
            "letter_id": "ltr_123",
            "url": "https://lob.com/letters/ltr_123",
            "expected_delivery_date": "2025-12-25",
            "tracking_number": "TRACK123",
            "carrier": "USPS",
            "provider": "lob",
        }

    async def send_postcard(self, to_address, from_address, front_template_id, back_template_id, merge_variables, size="4x6"):
        self.last_postcard_params = {
            "to_address": to_address,
            "from_address": from_address,
            "front_template_id": front_template_id,
            "back_template_id": back_template_id,
            "merge_variables": merge_variables,
            "size": size,
        }

        if self.should_fail:
            raise Exception("Lob API error")

        return {
            "success": True,
            "postcard_id": "psc_123",
            "url": "https://lob.com/postcards/psc_123",
            "expected_delivery_date": "2025-12-25",
            "provider": "lob",
        }

    async def get_letter(self, letter_id):
        return {
            "id": letter_id,
            "to": {"name": "Test Lead"},
            "from_": {"name": "Test Client"},
            "url": "https://lob.com/letters/ltr_123",
            "expected_delivery_date": "2025-12-25",
            "tracking_number": "TRACK123",
            "tracking_events": [],
        }

    def parse_webhook(self, payload):
        return {
            "event_id": payload.get("event_type", {}).get("id"),
            "resource_type": payload.get("body", {}).get("object"),
            "resource_id": payload.get("body", {}).get("id"),
            "tracking_number": payload.get("body", {}).get("tracking_number"),
            "tracking_events": payload.get("body", {}).get("tracking_events", []),
            "carrier": payload.get("body", {}).get("carrier"),
            "expected_delivery_date": payload.get("body", {}).get("expected_delivery_date"),
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
        self.als_score = kwargs.get("als_score", 90)  # Default high for mail
        self.last_contacted_at = kwargs.get("last_contacted_at", None)
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
        self.channel = kwargs.get("channel", ChannelType.MAIL)
        self.action = kwargs.get("action", "sent")
        self.provider_message_id = kwargs.get("provider_message_id", "ltr_123")
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
def mail_engine():
    """Create mail engine with mock client."""
    return MailEngine(lob_client=MockLobClient())


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MockDB()


@pytest.fixture
def valid_to_address():
    """Sample valid address."""
    return {
        "name": "Test Lead",
        "address_line1": "123 Main St",
        "city": "Sydney",
        "state": "NSW",
        "zip_code": "2000",
        "country": "AU",
    }


@pytest.fixture
def valid_from_address():
    """Sample valid sender address."""
    return {
        "name": "Test Company",
        "address_line1": "456 Business Ave",
        "city": "Melbourne",
        "state": "VIC",
        "zip_code": "3000",
        "country": "AU",
    }


# ============================================
# ENGINE PROPERTY TESTS
# ============================================

def test_engine_properties(mail_engine):
    """Test engine properties."""
    assert mail_engine.name == "mail"
    assert mail_engine.channel == ChannelType.MAIL


def test_singleton():
    """Test singleton pattern."""
    engine1 = get_mail_engine()
    engine2 = get_mail_engine()
    assert engine1 is engine2


# ============================================
# ADDRESS VERIFICATION TESTS
# ============================================

@pytest.mark.asyncio
async def test_verify_address_success():
    """Test successful address verification."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.verify_address(
            db=mock_db,
            lead_id=lead.id,
            address_data={
                "address_line1": "123 Main St",
                "city": "Sydney",
                "state": "NSW",
                "zip_code": "2000",
                "country": "AU",
            },
        )

        assert result.success
        assert result.data["valid"] is True
        assert result.data["deliverability"] == "deliverable"


@pytest.mark.asyncio
async def test_verify_address_invalid():
    """Test address verification with invalid address."""
    engine = MailEngine(lob_client=MockLobClient(invalid_address=True))
    mock_db = MockDB()
    lead = MockLead()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.verify_address(
            db=mock_db,
            lead_id=lead.id,
            address_data={
                "address_line1": "Invalid Address",
                "city": "Nowhere",
                "state": "XX",
                "zip_code": "0000",
            },
        )

        assert not result.success
        assert "not deliverable" in result.error.lower()


# ============================================
# SEND LETTER TESTS
# ============================================

@pytest.mark.asyncio
async def test_send_letter_success(valid_to_address, valid_from_address):
    """Test successful letter sending."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            to_address=valid_to_address,
            from_address=valid_from_address,
            merge_variables={"offer": "Special offer"},
        )

        assert result.success
        assert result.data["mail_id"] == "ltr_123"
        assert result.data["mail_type"] == "letter"
        assert result.data["tracking_number"] == "TRACK123"
        assert result.data["provider"] == "lob"
        assert mock_db.committed


@pytest.mark.asyncio
async def test_send_letter_missing_template(valid_to_address, valid_from_address):
    """Test letter fails without template_id."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="letter",
            to_address=valid_to_address,
            from_address=valid_from_address,
            # No template_id
        )

        assert not result.success
        assert "template_id is required" in result.error.lower()


# ============================================
# SEND POSTCARD TESTS
# ============================================

@pytest.mark.asyncio
async def test_send_postcard_success(valid_to_address, valid_from_address):
    """Test successful postcard sending."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="postcard",
            front_template_id="tmpl_front_123",
            back_template_id="tmpl_back_123",
            to_address=valid_to_address,
            from_address=valid_from_address,
            size="4x6",
        )

        assert result.success
        assert result.data["mail_id"] == "psc_123"
        assert result.data["mail_type"] == "postcard"


@pytest.mark.asyncio
async def test_send_postcard_missing_templates(valid_to_address, valid_from_address):
    """Test postcard fails without both template IDs."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="postcard",
            to_address=valid_to_address,
            from_address=valid_from_address,
            # Missing templates
        )

        assert not result.success
        assert "front_template_id" in result.error.lower() or "back_template_id" in result.error.lower()


# ============================================
# ALS VALIDATION TESTS
# ============================================

@pytest.mark.asyncio
async def test_send_mail_low_als(valid_to_address, valid_from_address):
    """Test mail fails when ALS score is below 85."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=80)  # Below 85 threshold

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=uuid4(),
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            to_address=valid_to_address,
            from_address=valid_from_address,
        )

        assert not result.success
        assert "als score too low" in result.error.lower()
        assert "minimum 85" in result.error.lower()


@pytest.mark.asyncio
async def test_send_mail_als_exactly_85(valid_to_address, valid_from_address):
    """Test mail succeeds when ALS score is exactly 85."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=85)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            to_address=valid_to_address,
            from_address=valid_from_address,
        )

        assert result.success


@pytest.mark.asyncio
async def test_send_mail_als_none(valid_to_address, valid_from_address):
    """Test mail fails when ALS score is None."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=None)

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead:
        mock_get_lead.return_value = lead

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=uuid4(),
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            to_address=valid_to_address,
            from_address=valid_from_address,
        )

        assert not result.success
        assert "als score too low" in result.error.lower()


# ============================================
# MISSING REQUIRED FIELDS TESTS
# ============================================

@pytest.mark.asyncio
async def test_send_mail_missing_to_address(valid_from_address):
    """Test mail fails without to_address."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            from_address=valid_from_address,
            # No to_address
        )

        assert not result.success
        assert "to_address is required" in result.error.lower()


@pytest.mark.asyncio
async def test_send_mail_missing_from_address(valid_to_address):
    """Test mail fails without from_address."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            to_address=valid_to_address,
            # No from_address
        )

        assert not result.success
        assert "from_address is required" in result.error.lower()


# ============================================
# GET MAIL STATUS TESTS
# ============================================

@pytest.mark.asyncio
async def test_get_mail_status(mock_db):
    """Test getting mail status."""
    engine = MailEngine(lob_client=MockLobClient())

    result = await engine.get_mail_status(
        db=mock_db,
        letter_id="ltr_123",
    )

    assert result.success
    assert result.data["id"] == "ltr_123"
    assert result.data["tracking_number"] == "TRACK123"
    assert result.data["expected_delivery_date"] == "2025-12-25"


# ============================================
# WEBHOOK PROCESSING TESTS
# ============================================

@pytest.mark.asyncio
async def test_process_tracking_webhook_delivered():
    """Test processing tracking webhook for delivered mail."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead()
    activity = MockActivity(lead_id=lead.id, provider_message_id="ltr_123")
    mock_db._activity = activity

    result = await engine.process_tracking_webhook(
        db=mock_db,
        payload={
            "body": {
                "id": "ltr_123",
                "object": "letter",
                "tracking_number": "TRACK123",
                "tracking_events": [
                    {"name": "In Transit", "time": "2025-12-22T10:00:00Z"},
                    {"name": "Delivered", "time": "2025-12-24T14:00:00Z"},
                ],
                "carrier": "USPS",
            },
        },
    )

    assert result.success
    assert result.data["resource_id"] == "ltr_123"
    assert result.data["delivered"] is True
    assert result.data["processed"]


@pytest.mark.asyncio
async def test_process_tracking_webhook_in_transit():
    """Test processing tracking webhook for in-transit mail."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead()
    activity = MockActivity(lead_id=lead.id, provider_message_id="ltr_123")
    mock_db._activity = activity

    result = await engine.process_tracking_webhook(
        db=mock_db,
        payload={
            "body": {
                "id": "ltr_123",
                "object": "letter",
                "tracking_events": [
                    {"name": "In Transit", "time": "2025-12-22T10:00:00Z"},
                ],
            },
        },
    )

    assert result.success
    assert result.data["delivered"] is False


@pytest.mark.asyncio
async def test_process_tracking_webhook_missing_resource_id(mock_db):
    """Test webhook processing with missing resource_id."""
    engine = MailEngine(lob_client=MockLobClient())

    result = await engine.process_tracking_webhook(
        db=mock_db,
        payload={
            "body": {
                # No id
                "tracking_events": [],
            },
        },
    )

    assert not result.success
    assert "missing resource_id" in result.error.lower()


@pytest.mark.asyncio
async def test_process_tracking_webhook_activity_not_found(mock_db):
    """Test webhook processing when activity not found."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db._activity = None  # No activity found

    result = await engine.process_tracking_webhook(
        db=mock_db,
        payload={
            "body": {
                "id": "ltr_unknown",
            },
        },
    )

    assert not result.success
    assert "activity not found" in result.error.lower()


# ============================================
# ACTIVITY LOGGING TESTS
# ============================================

@pytest.mark.asyncio
async def test_activity_logging(valid_to_address, valid_from_address):
    """Test that mail activities are logged correctly."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            to_address=valid_to_address,
            from_address=valid_from_address,
        )

        assert result.success
        assert len(mock_db.added) == 1
        activity = mock_db.added[0]
        assert activity.channel == ChannelType.MAIL
        assert activity.action == "sent"
        assert activity.provider_message_id == "ltr_123"


# ============================================
# LEAD UPDATE TESTS
# ============================================

@pytest.mark.asyncio
async def test_lead_update_on_success(valid_to_address, valid_from_address):
    """Test that lead is updated after successful mail send."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90, last_contacted_at=None)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            to_address=valid_to_address,
            from_address=valid_from_address,
        )

        assert lead.last_contacted_at is not None
        assert mock_db.committed


# ============================================
# INVALID MAIL TYPE TEST
# ============================================

@pytest.mark.asyncio
async def test_send_invalid_mail_type(valid_to_address, valid_from_address):
    """Test mail fails with invalid mail_type."""
    engine = MailEngine(lob_client=MockLobClient())
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="invalid_type",
            to_address=valid_to_address,
            from_address=valid_from_address,
        )

        assert not result.success
        assert "invalid mail_type" in result.error.lower()


# ============================================
# API ERROR HANDLING TEST
# ============================================

@pytest.mark.asyncio
async def test_send_mail_api_error(valid_to_address, valid_from_address):
    """Test mail handling when Lob API fails."""
    engine = MailEngine(lob_client=MockLobClient(should_fail=True))
    mock_db = MockDB()
    lead = MockLead(als_score=90)
    campaign = MockCampaign()

    with patch.object(engine, 'get_lead_by_id', new_callable=AsyncMock) as mock_get_lead, \
         patch.object(engine, 'get_campaign_by_id', new_callable=AsyncMock) as mock_get_campaign:

        mock_get_lead.return_value = lead
        mock_get_campaign.return_value = campaign

        result = await engine.send(
            db=mock_db,
            lead_id=lead.id,
            campaign_id=campaign.id,
            content="",
            mail_type="letter",
            template_id="tmpl_123",
            to_address=valid_to_address,
            from_address=valid_from_address,
        )

        assert not result.success
        assert "failed to send mail" in result.error.lower()


# ============================================
# TEST COVERAGE CHECKLIST
# ============================================
# [x] Basic engine properties
# [x] Singleton pattern
# [x] Verify address success
# [x] Verify address invalid
# [x] Send letter success
# [x] Send letter missing template
# [x] Send postcard success
# [x] Send postcard missing templates
# [x] Send mail validation (ALS < 85)
# [x] Send mail validation (ALS exactly 85)
# [x] Send mail validation (ALS None)
# [x] Send mail missing to_address
# [x] Send mail missing from_address
# [x] Get mail status
# [x] Process tracking webhook (delivered)
# [x] Process tracking webhook (in transit)
# [x] Process tracking webhook (missing resource_id)
# [x] Process tracking webhook (activity not found)
# [x] Activity logging
# [x] Lead update on success
# [x] Invalid mail type
# [x] API error handling
