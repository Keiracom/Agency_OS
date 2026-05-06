"""
FILE: tests/test_engines/test_email.py
PURPOSE: Tests for Email engine
PHASE: 4 (Engines)
TASK: ENG-005
"""

from uuid import uuid4

import pytest

from src.engines.email import EmailEngine, get_email_engine
from src.models.base import ChannelType, LeadStatus


@pytest.fixture
def mock_salesforge_client():
    """Mock Salesforge client."""

    class MockSalesforgeClient:
        async def send_email(self, **kwargs):
            return {
                "success": True,
                "message_id": f"msg_{uuid4().hex[:16]}",
                "provider": "salesforge",
            }

    return MockSalesforgeClient()


@pytest.fixture
def email_engine(mock_salesforge_client):
    """Create email engine with mock client."""
    return EmailEngine(salesforge_client=mock_salesforge_client)


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

                def all(self):
                    return []

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
        linkedin_url = "https://linkedin.com/in/test"
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


class TestEmailEngine:
    """Test suite for Email engine."""

    def test_engine_properties(self, email_engine):
        """Test engine properties."""
        assert email_engine.name == "email"
        assert email_engine.channel == ChannelType.EMAIL

    def test_singleton(self):
        """Test singleton pattern."""
        engine1 = get_email_engine()
        engine2 = get_email_engine()
        assert engine1 is engine2

    def test_extract_domain(self, email_engine):
        """Test domain extraction from email."""
        # Simple email
        assert email_engine._extract_domain("test@example.com") == "example.com"

        # Email with name
        assert email_engine._extract_domain("John Doe <test@example.com>") == "example.com"

        # Invalid email
        assert email_engine._extract_domain("invalid") is None
        assert email_engine._extract_domain(None) is None

    def test_get_content_preview(self, email_engine):
        """Test content preview generation."""
        # HTML content
        html = "<html><body><p>Hello <strong>world</strong>!</p></body></html>"
        preview = email_engine._get_content_preview(html)
        assert "Hello world!" in preview
        assert "<" not in preview  # HTML stripped

        # Long content
        long_html = "<p>" + ("A" * 300) + "</p>"
        preview = email_engine._get_content_preview(long_html, max_length=50)
        assert len(preview) <= 53  # 50 + "..."
        assert preview.endswith("...")

    @pytest.mark.asyncio
    async def test_send_email_missing_subject(
        self, email_engine, mock_db, mock_lead, mock_campaign
    ):
        """Test send fails without subject."""

        # Mock validation methods
        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        email_engine.get_lead_by_id = mock_get_lead
        email_engine.get_campaign_by_id = mock_get_campaign

        result = await email_engine.send(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            content="<p>Test email</p>",
            from_email="sender@example.com",
            # subject missing
        )

        assert not result.success
        assert "subject is required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_email_missing_from_email(
        self, email_engine, mock_db, mock_lead, mock_campaign
    ):
        """Test send fails without from_email."""

        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        email_engine.get_lead_by_id = mock_get_lead
        email_engine.get_campaign_by_id = mock_get_campaign

        result = await email_engine.send(
            db=mock_db,
            lead_id=mock_lead.id,
            campaign_id=mock_campaign.id,
            content="<p>Test email</p>",
            subject="Test Subject",
            # from_email missing
        )

        assert not result.success
        assert "from email is required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_email_success(self, email_engine, mock_db, mock_lead, mock_campaign):
        """Test successful email send."""
        from unittest.mock import AsyncMock, patch

        # Mock validation methods
        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        async def mock_validate_address(db, client_id):
            return {"valid": True, "address": "123 Test St"}

        email_engine.get_lead_by_id = mock_get_lead
        email_engine.get_campaign_by_id = mock_get_campaign
        email_engine._validate_physical_address = mock_validate_address

        # Mock rate limiter and salesforge
        with patch("src.engines.email.rate_limiter") as mock_rate_limiter:
            mock_rate_limiter.check_and_increment = AsyncMock(return_value=(True, 1))

            # Mock salesforge send
            email_engine._salesforge = AsyncMock()
            email_engine._salesforge.send_email = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": "msg_test123",
                }
            )

            # Mock activity logging
            email_engine._log_activity = AsyncMock()

            result = await email_engine.send(
                db=mock_db,
                lead_id=mock_lead.id,
                campaign_id=mock_campaign.id,
                content="<p>Test email content</p>",
                subject="Test Subject",
                from_email="sender@example.com",
                from_name="Test Sender",
                include_signature=False,  # Skip signature generation
            )

            assert result.success
            assert result.data["message_id"] == "msg_test123"
            assert result.data["to_email"] == mock_lead.email
            assert result.data["from_email"] == "sender@example.com"
            assert result.data["subject"] == "Test Subject"

    @pytest.mark.asyncio
    async def test_send_with_threading(self, email_engine, mock_db, mock_lead, mock_campaign):
        """Test email send with threading (follow-up)."""
        from unittest.mock import AsyncMock, patch

        async def mock_get_lead(db, lead_id):
            return mock_lead

        async def mock_get_campaign(db, campaign_id):
            return mock_campaign

        async def mock_get_thread_info(db, lead_id, campaign_id):
            return {
                "in_reply_to": "previous_message_id",
                "references": ["msg1", "msg2"],
                "thread_id": "thread_123",
            }

        async def mock_validate_address(db, client_id):
            return {"valid": True, "address": "123 Test St"}

        email_engine.get_lead_by_id = mock_get_lead
        email_engine.get_campaign_by_id = mock_get_campaign
        email_engine._get_thread_info = mock_get_thread_info
        email_engine._validate_physical_address = mock_validate_address

        # Mock rate limiter and salesforge
        with patch("src.engines.email.rate_limiter") as mock_rate_limiter:
            mock_rate_limiter.check_and_increment = AsyncMock(return_value=(True, 1))

            # Mock salesforge send
            email_engine._salesforge = AsyncMock()
            email_engine._salesforge.send_email = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": "msg_followup123",
                }
            )

            # Mock activity logging
            email_engine._log_activity = AsyncMock()

            result = await email_engine.send(
                db=mock_db,
                lead_id=mock_lead.id,
                campaign_id=mock_campaign.id,
                content="<p>Follow-up email</p>",
                subject="Re: Test Subject",
                from_email="sender@example.com",
                is_followup=True,
                include_signature=False,  # Skip signature generation
            )

            assert result.success
            assert result.data["is_followup"] is True
            assert result.data["thread_id"] == "thread_123"

    @pytest.mark.asyncio
    async def test_batch_send(self, email_engine, mock_db):
        """Test batch email sending with mocked send_batch internals."""
        from src.engines.base import EngineResult
        from unittest.mock import AsyncMock

        # Create mock responses: 2 success, 1 rate limited
        send_count = {"value": 0}

        async def mock_send_effect(*args, **kwargs):
            send_count["value"] += 1
            if send_count["value"] <= 2:
                return EngineResult.ok(
                    data={
                        "message_id": f"msg_{send_count['value']}",
                        "to_email": "test@example.com",
                        "from_email": "sender@example.com",
                        "subject": f"Subject {send_count['value']}",
                    }
                )
            else:
                return EngineResult.fail(error="Rate limit exceeded")

        # Mock validate_and_send with AsyncMock that handles any call signature
        mock_validate = AsyncMock(side_effect=mock_send_effect)
        email_engine.validate_and_send = mock_validate

        emails = [
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "<p>Email 1</p>",
                "subject": "Subject 1",
                "from_email": "sender@example.com",
            },
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "<p>Email 2</p>",
                "subject": "Subject 2",
                "from_email": "sender@example.com",
            },
            {
                "lead_id": uuid4(),
                "campaign_id": uuid4(),
                "content": "<p>Email 3</p>",
                "subject": "Subject 3",
                "from_email": "sender@example.com",
            },
        ]

        result = await email_engine.send_batch(db=mock_db, emails=emails)

        assert result.success
        assert result.data["total"] == 3
        assert result.data["sent"] == 2
        assert result.data["rate_limited"] == 1


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties (name, channel)
# [x] Test singleton pattern
# [x] Test domain extraction
# [x] Test content preview
# [x] Test send validation (missing fields)
# [x] Test successful send
# [x] Test threading support
# [x] Test batch sending
# [x] All tests use async/await
# [x] All tests have docstrings
