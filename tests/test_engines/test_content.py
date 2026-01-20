"""
FILE: tests/test_engines/test_content.py
PURPOSE: Unit tests for Content engine (AI content generation)
PHASE: 4 (Engines), updated Phase 2 (Smart Prompt System)
TASK: ENG-011
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.content import ContentEngine, get_content_engine
from src.exceptions import AISpendLimitError, ValidationError
from src.models.base import LeadStatus


# Smart prompt module path for patching
SMART_PROMPTS_MODULE = "src.engines.content"


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client."""
    client = AsyncMock()
    client.complete = AsyncMock()
    client.get_spend_status = AsyncMock()
    return client


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
    lead.email = "john.doe@acme.com"
    lead.first_name = "John"
    lead.last_name = "Doe"
    lead.title = "CEO"
    lead.company = "Acme Inc"
    lead.organization_industry = "Technology"
    lead.organization_employee_count = 50
    lead.status = LeadStatus.ENRICHED
    return lead


@pytest.fixture
def mock_campaign():
    """Create mock campaign object."""
    campaign = MagicMock()
    campaign.id = uuid4()
    campaign.name = "Q1 Outreach"
    campaign.client_id = uuid4()
    campaign.product_name = "Agency OS"
    campaign.value_proposition = "Automate your sales outreach"
    return campaign


@pytest.fixture
def mock_lead_context():
    """Create mock lead context from smart prompt system."""
    return {
        "person": {
            "first_name": "John",
            "last_name": "Doe",
            "full_name": "John Doe",
            "title": "CEO",
            "seniority": "c_suite",
        },
        "company": {
            "name": "Acme Inc",
            "industry": "Technology",
            "employee_count": 50,
        },
        "signals": {
            "is_hiring": True,
            "recently_funded": False,
        },
        "score": {
            "als_score": 75,
            "als_tier": "warm",
        },
    }


@pytest.fixture
def mock_proof_points():
    """Create mock proof points from client intelligence."""
    return {
        "available": True,
        "metrics": [{"metric": "50% increase in meetings", "context": "average for clients"}],
        "named_clients": ["TechCorp", "StartupXYZ"],
        "differentiators": ["AI-powered personalization"],
    }


@pytest.fixture
def content_engine(mock_anthropic_client):
    """Create Content engine with mock client."""
    return ContentEngine(anthropic_client=mock_anthropic_client)


# ============================================
# Engine Properties Tests
# ============================================


class TestContentEngineProperties:
    """Test Content engine properties."""

    def test_engine_name(self, content_engine):
        """Test engine name property."""
        assert content_engine.name == "content"

    def test_singleton_instance(self):
        """Test singleton pattern."""
        engine1 = get_content_engine()
        engine2 = get_content_engine()
        assert engine1 is engine2


# ============================================
# Email Generation Tests
# ============================================


class TestEmailGeneration:
    """Test email content generation with Smart Prompt system."""

    @pytest.mark.asyncio
    async def test_generate_email_success(
        self, content_engine, mock_db_session, mock_lead, mock_campaign,
        mock_lead_context, mock_proof_points
    ):
        """Test successful email generation with smart prompt."""
        with patch.object(content_engine, "get_campaign_by_id", new_callable=AsyncMock, return_value=mock_campaign):
            with patch(f"{SMART_PROMPTS_MODULE}.build_full_lead_context", new_callable=AsyncMock, return_value=mock_lead_context):
                with patch(f"{SMART_PROMPTS_MODULE}.build_client_proof_points", new_callable=AsyncMock, return_value=mock_proof_points):
                    # Mock AI response
                    content_engine.anthropic.complete.return_value = {
                        "content": '{"subject": "Test Subject", "body": "Test Body"}',
                        "cost_aud": 0.05,
                        "input_tokens": 100,
                        "output_tokens": 50,
                    }

                    result = await content_engine.generate_email(
                        db=mock_db_session,
                        lead_id=mock_lead.id,
                        campaign_id=mock_campaign.id,
                    )

                    assert result.success is True
                    assert result.data["subject"] == "Test Subject"
                    assert result.data["body"] == "Test Body"
                    assert result.metadata["cost_aud"] == 0.05
                    assert result.metadata.get("smart_prompt") is True

    @pytest.mark.asyncio
    async def test_generate_email_with_template(
        self, content_engine, mock_db_session, mock_lead, mock_campaign,
        mock_lead_context, mock_proof_points
    ):
        """Test email generation with template."""
        with patch.object(content_engine, "get_campaign_by_id", new_callable=AsyncMock, return_value=mock_campaign):
            with patch(f"{SMART_PROMPTS_MODULE}.build_full_lead_context", new_callable=AsyncMock, return_value=mock_lead_context):
                with patch(f"{SMART_PROMPTS_MODULE}.build_client_proof_points", new_callable=AsyncMock, return_value=mock_proof_points):
                    content_engine.anthropic.complete.return_value = {
                        "content": '{"subject": "Custom Subject", "body": "Custom Body"}',
                        "cost_aud": 0.05,
                        "input_tokens": 150,
                        "output_tokens": 60,
                    }

                    result = await content_engine.generate_email(
                        db=mock_db_session,
                        lead_id=mock_lead.id,
                        campaign_id=mock_campaign.id,
                        template="Hi {{first_name}}, from {{company}}",
                    )

                    assert result.success is True
                    # Verify AI was called
                    content_engine.anthropic.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_email_missing_lead_data(
        self, content_engine, mock_db_session, mock_campaign
    ):
        """Test email generation fails with insufficient lead data."""
        incomplete_lead = MagicMock()
        incomplete_lead.id = uuid4()
        incomplete_lead.first_name = None  # Missing
        incomplete_lead.full_name = ""
        incomplete_lead.title = None
        incomplete_lead.company = None  # Missing
        incomplete_lead.organization_industry = None

        # Empty context simulates missing lead data
        empty_context = {}

        with patch.object(content_engine, "get_campaign_by_id", new_callable=AsyncMock, return_value=mock_campaign):
            with patch(f"{SMART_PROMPTS_MODULE}.build_full_lead_context", new_callable=AsyncMock, return_value=empty_context):
                with patch.object(content_engine, "get_lead_by_id", new_callable=AsyncMock, return_value=incomplete_lead):
                    result = await content_engine.generate_email(
                        db=mock_db_session,
                        lead_id=incomplete_lead.id,
                        campaign_id=mock_campaign.id,
                    )

                    assert result.success is False
                    assert "first_name" in result.error or "company" in result.error

    @pytest.mark.asyncio
    async def test_generate_email_json_fallback(
        self, content_engine, mock_db_session, mock_lead, mock_campaign,
        mock_lead_context, mock_proof_points
    ):
        """Test email generation with JSON parsing fallback."""
        with patch.object(content_engine, "get_campaign_by_id", new_callable=AsyncMock, return_value=mock_campaign):
            with patch(f"{SMART_PROMPTS_MODULE}.build_full_lead_context", new_callable=AsyncMock, return_value=mock_lead_context):
                with patch(f"{SMART_PROMPTS_MODULE}.build_client_proof_points", new_callable=AsyncMock, return_value=mock_proof_points):
                    # Mock AI response with invalid JSON
                    content_engine.anthropic.complete.return_value = {
                        "content": "This is not valid JSON",
                        "cost_aud": 0.05,
                        "input_tokens": 100,
                        "output_tokens": 50,
                    }

                    result = await content_engine.generate_email(
                        db=mock_db_session,
                        lead_id=mock_lead.id,
                        campaign_id=mock_campaign.id,
                    )

                    assert result.success is True
                    assert result.data["body"] == "This is not valid JSON"
                    assert result.metadata.get("fallback") is True

    @pytest.mark.asyncio
    async def test_generate_email_spend_limit(
        self, content_engine, mock_db_session, mock_lead, mock_campaign,
        mock_lead_context, mock_proof_points
    ):
        """Test email generation respects spend limit."""
        with patch.object(content_engine, "get_campaign_by_id", new_callable=AsyncMock, return_value=mock_campaign):
            with patch(f"{SMART_PROMPTS_MODULE}.build_full_lead_context", new_callable=AsyncMock, return_value=mock_lead_context):
                with patch(f"{SMART_PROMPTS_MODULE}.build_client_proof_points", new_callable=AsyncMock, return_value=mock_proof_points):
                    # Mock AI spend limit error
                    content_engine.anthropic.complete.side_effect = AISpendLimitError(
                        spent=100.0, limit=100.0
                    )

                    result = await content_engine.generate_email(
                        db=mock_db_session,
                        lead_id=mock_lead.id,
                        campaign_id=mock_campaign.id,
                    )

                    assert result.success is False
                    assert "spend limit" in result.error.lower()


# ============================================
# SMS Generation Tests
# ============================================


class TestSMSGeneration:
    """Test SMS content generation."""

    @pytest.mark.asyncio
    async def test_generate_sms_success(
        self, content_engine, mock_db_session, mock_lead, mock_campaign
    ):
        """Test successful SMS generation."""
        with patch.object(content_engine, "get_lead_by_id", return_value=mock_lead):
            with patch.object(content_engine, "get_campaign_by_id", return_value=mock_campaign):
                content_engine.anthropic.complete.return_value = {
                    "content": "Hi John, quick question about Acme Inc. Can we chat? - Alex",
                    "cost_aud": 0.02,
                    "input_tokens": 50,
                    "output_tokens": 20,
                }

                result = await content_engine.generate_sms(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                    campaign_id=mock_campaign.id,
                )

                assert result.success is True
                assert len(result.data["message"]) <= 160
                assert result.metadata["length"] <= 160

    @pytest.mark.asyncio
    async def test_generate_sms_truncation(
        self, content_engine, mock_db_session, mock_lead, mock_campaign
    ):
        """Test SMS truncation to 160 characters."""
        with patch.object(content_engine, "get_lead_by_id", return_value=mock_lead):
            with patch.object(content_engine, "get_campaign_by_id", return_value=mock_campaign):
                # Mock long message
                long_message = "A" * 200
                content_engine.anthropic.complete.return_value = {
                    "content": long_message,
                    "cost_aud": 0.02,
                    "input_tokens": 50,
                    "output_tokens": 40,
                }

                result = await content_engine.generate_sms(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                    campaign_id=mock_campaign.id,
                )

                assert result.success is True
                assert len(result.data["message"]) == 160
                assert result.data["message"].endswith("...")


# ============================================
# LinkedIn Generation Tests
# ============================================


class TestLinkedInGeneration:
    """Test LinkedIn message generation."""

    @pytest.mark.asyncio
    async def test_generate_linkedin_connection(
        self, content_engine, mock_db_session, mock_lead, mock_campaign
    ):
        """Test LinkedIn connection request generation."""
        with patch.object(content_engine, "get_lead_by_id", return_value=mock_lead):
            with patch.object(content_engine, "get_campaign_by_id", return_value=mock_campaign):
                content_engine.anthropic.complete.return_value = {
                    "content": "Hi John, impressed by Acme's work in tech. Would love to connect!",
                    "cost_aud": 0.03,
                    "input_tokens": 80,
                    "output_tokens": 25,
                }

                result = await content_engine.generate_linkedin(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                    campaign_id=mock_campaign.id,
                    message_type="connection",
                )

                assert result.success is True
                assert len(result.data["message"]) <= 300
                assert result.data["message_type"] == "connection"

    @pytest.mark.asyncio
    async def test_generate_linkedin_inmail(
        self, content_engine, mock_db_session, mock_lead, mock_campaign
    ):
        """Test LinkedIn InMail generation."""
        with patch.object(content_engine, "get_lead_by_id", return_value=mock_lead):
            with patch.object(content_engine, "get_campaign_by_id", return_value=mock_campaign):
                content_engine.anthropic.complete.return_value = {
                    "content": "Hi John, saw your recent post about AI. Great insights! Would love to discuss...",
                    "cost_aud": 0.04,
                    "input_tokens": 120,
                    "output_tokens": 35,
                }

                result = await content_engine.generate_linkedin(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                    campaign_id=mock_campaign.id,
                    message_type="inmail",
                )

                assert result.success is True
                assert len(result.data["message"]) <= 1000
                assert result.data["message_type"] == "inmail"


# ============================================
# Voice Script Generation Tests
# ============================================


class TestVoiceScriptGeneration:
    """Test voice call script generation."""

    @pytest.mark.asyncio
    async def test_generate_voice_script_success(
        self, content_engine, mock_db_session, mock_lead, mock_campaign
    ):
        """Test successful voice script generation."""
        with patch.object(content_engine, "get_lead_by_id", return_value=mock_lead):
            with patch.object(content_engine, "get_campaign_by_id", return_value=mock_campaign):
                content_engine.anthropic.complete.return_value = {
                    "content": '{"opening": "Hi John", "value_prop": "We help tech companies...", "cta": "Can we schedule a call?"}',
                    "cost_aud": 0.06,
                    "input_tokens": 150,
                    "output_tokens": 60,
                }

                result = await content_engine.generate_voice_script(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                    campaign_id=mock_campaign.id,
                )

                assert result.success is True
                assert "opening" in result.data
                assert "value_prop" in result.data
                assert "cta" in result.data

    @pytest.mark.asyncio
    async def test_generate_voice_script_missing_data(
        self, content_engine, mock_db_session, mock_campaign
    ):
        """Test voice script generation fails with insufficient data."""
        incomplete_lead = MagicMock()
        incomplete_lead.id = uuid4()
        incomplete_lead.first_name = "John"
        incomplete_lead.company = None  # Missing

        with patch.object(content_engine, "get_lead_by_id", return_value=incomplete_lead):
            with patch.object(content_engine, "get_campaign_by_id", return_value=mock_campaign):
                result = await content_engine.generate_voice_script(
                    db=mock_db_session,
                    lead_id=incomplete_lead.id,
                    campaign_id=mock_campaign.id,
                )

                assert result.success is False
                assert "company" in result.error.lower()


# ============================================
# Spend Status Tests
# ============================================


class TestSpendStatus:
    """Test AI spend status reporting."""

    @pytest.mark.asyncio
    async def test_get_spend_status(self, content_engine):
        """Test spend status retrieval."""
        content_engine.anthropic.get_spend_status.return_value = {
            "daily_limit": 100.0,
            "spent": 45.5,
            "remaining": 54.5,
            "percentage_used": 45.5,
        }

        result = await content_engine.get_spend_status()

        assert result.success is True
        assert result.data["spent"] == 45.5
        assert result.data["remaining"] == 54.5
        assert result.metadata["engine"] == "content"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties
# [x] Test singleton pattern
# [x] Test email generation success
# [x] Test email generation with template
# [x] Test email generation with missing lead data
# [x] Test email generation JSON fallback
# [x] Test email generation respects spend limit
# [x] Test SMS generation success
# [x] Test SMS truncation to 160 characters
# [x] Test LinkedIn connection request generation
# [x] Test LinkedIn InMail generation
# [x] Test voice script generation success
# [x] Test voice script generation with missing data
# [x] Test spend status retrieval
