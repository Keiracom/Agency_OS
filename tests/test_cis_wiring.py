"""
Tests for CIS (Conversion Intelligence System) wiring to outreach handlers.

Directive #166: Verify that email/linkedin/sms engines call record_outreach_outcome()
when logging "sent" activities.

All tests use mocks — no live API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC

from src.engines.email import EmailEngine
from src.engines.linkedin import LinkedInEngine
from src.engines.sms import SMSEngine


@pytest.fixture
def mock_lead():
    """Create a mock lead with required attributes."""
    # Use spec=[] to avoid auto-creating MagicMock for unset attributes
    lead = MagicMock(spec=[])
    lead.id = uuid4()
    lead.client_id = uuid4()
    lead.propensity_score = 75
    lead.propensity_tier = "warm"
    lead.email = "test@example.com"
    lead.phone = "+61412345678"
    lead.linkedin_url = "https://linkedin.com/in/testuser"
    # String attributes needed by content_utils.py
    lead.company = "Test Company"
    lead.company_name = "Test Company"
    lead.first_name = "John"
    lead.last_name = "Doe"
    lead.industry = "Technology"
    lead.organization_industry = "Technology"
    lead.title = "CEO"
    return lead


@pytest.fixture
def mock_db():
    """Create a mock async database session.
    
    Uses MagicMock base with async commit() to avoid RuntimeWarnings
    from sync methods like db.add() returning unawaited coroutines.
    """
    db = MagicMock()
    db.commit = AsyncMock()  # Only commit is async in SQLAlchemy
    return db


@pytest.fixture
def mock_activity():
    """Create a mock activity with an id."""
    activity = MagicMock()
    activity.id = uuid4()
    return activity


class TestEmailCISWiring:
    """Test CIS wiring in email engine."""

    @pytest.mark.asyncio
    async def test_email_sent_calls_record_outreach_outcome(self, mock_lead, mock_db, mock_activity):
        """Test: email send calls record_outreach_outcome with correct channel + fields."""
        campaign_id = uuid4()
        subject = "Test Subject"
        sequence_step = 1
        
        with patch("src.engines.email.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_get_cis.return_value = mock_cis_service
                
                engine = EmailEngine()
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=campaign_id,
                    action="sent",
                    provider_message_id="msg-123",
                    thread_id="thread-456",
                    sequence_step=sequence_step,
                    subject=subject,
                    content_preview="Test content",
                    html_content="<p>Test content</p>",
                )
                
                # Verify CIS service was called
                mock_cis_service.record_outreach_outcome.assert_called_once()
                call_args = mock_cis_service.record_outreach_outcome.call_args
                
                # Verify correct arguments
                assert call_args.kwargs["activity_id"] == mock_activity.id
                assert call_args.kwargs["lead_id"] == mock_lead.id
                assert call_args.kwargs["client_id"] == mock_lead.client_id
                assert call_args.kwargs["campaign_id"] == campaign_id
                assert call_args.kwargs["channel"] == "email"
                assert call_args.kwargs["sequence_step"] == sequence_step
                assert call_args.kwargs["propensity_score_at_send"] == mock_lead.propensity_score
                assert call_args.kwargs["propensity_tier_at_send"] == mock_lead.propensity_tier
                assert call_args.kwargs["subject_line"] == subject
                assert call_args.kwargs["session"] == mock_db

    @pytest.mark.asyncio
    async def test_email_non_sent_action_skips_cis(self, mock_lead, mock_db, mock_activity):
        """Test: non-sent actions (e.g., 'bounced') don't call record_outreach_outcome."""
        with patch("src.engines.email.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_get_cis.return_value = mock_cis_service
                
                engine = EmailEngine()
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=uuid4(),
                    action="bounced",  # Not "sent"
                )
                
                # CIS should NOT be called for non-sent actions
                mock_cis_service.record_outreach_outcome.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_cis_failure_is_non_blocking(self, mock_lead, mock_db, mock_activity):
        """Test: CIS failures don't block email logging."""
        with patch("src.engines.email.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_cis_service.record_outreach_outcome.side_effect = Exception("CIS DB error")
                mock_get_cis.return_value = mock_cis_service
                
                engine = EmailEngine()
                # Should NOT raise even though CIS fails
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=uuid4(),
                    action="sent",
                )
                
                # Verify activity was still committed
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()


class TestLinkedInCISWiring:
    """Test CIS wiring in LinkedIn engine."""

    @pytest.mark.asyncio
    async def test_linkedin_sent_calls_record_outreach_outcome(self, mock_lead, mock_db, mock_activity):
        """Test: linkedin send calls record_outreach_outcome with channel=linkedin."""
        campaign_id = uuid4()
        sequence_step = 2
        
        with patch("src.engines.linkedin.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_get_cis.return_value = mock_cis_service
                
                engine = LinkedInEngine()
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=campaign_id,
                    action="sent",
                    provider_message_id="li-msg-123",
                    content_preview="Test LinkedIn message",
                    message_content="Test LinkedIn message",
                    sequence_step=sequence_step,
                )
                
                # Verify CIS service was called
                mock_cis_service.record_outreach_outcome.assert_called_once()
                call_args = mock_cis_service.record_outreach_outcome.call_args
                
                # Verify correct arguments
                assert call_args.kwargs["activity_id"] == mock_activity.id
                assert call_args.kwargs["lead_id"] == mock_lead.id
                assert call_args.kwargs["client_id"] == mock_lead.client_id
                assert call_args.kwargs["campaign_id"] == campaign_id
                assert call_args.kwargs["channel"] == "linkedin"
                assert call_args.kwargs["sequence_step"] == sequence_step
                assert call_args.kwargs["propensity_score_at_send"] == mock_lead.propensity_score
                assert call_args.kwargs["propensity_tier_at_send"] == mock_lead.propensity_tier
                assert call_args.kwargs["subject_line"] is None  # LinkedIn has no subject
                assert call_args.kwargs["session"] == mock_db

    @pytest.mark.asyncio
    async def test_linkedin_non_sent_action_skips_cis(self, mock_lead, mock_db, mock_activity):
        """Test: non-sent LinkedIn actions don't call record_outreach_outcome."""
        with patch("src.engines.linkedin.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_get_cis.return_value = mock_cis_service
                
                engine = LinkedInEngine()
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=uuid4(),
                    action="connection_request",  # Not "sent"
                )
                
                # CIS should NOT be called for non-sent actions
                mock_cis_service.record_outreach_outcome.assert_not_called()

    @pytest.mark.asyncio
    async def test_linkedin_cis_failure_is_non_blocking(self, mock_lead, mock_db, mock_activity):
        """Test: CIS failures don't block LinkedIn logging."""
        with patch("src.engines.linkedin.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_cis_service.record_outreach_outcome.side_effect = Exception("CIS DB error")
                mock_get_cis.return_value = mock_cis_service
                
                engine = LinkedInEngine()
                # Should NOT raise even though CIS fails
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=uuid4(),
                    action="sent",
                )
                
                # Verify activity was still committed
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()


class TestSMSCISWiring:
    """Test CIS wiring in SMS engine."""

    @pytest.mark.asyncio
    async def test_sms_sent_calls_record_outreach_outcome(self, mock_lead, mock_db, mock_activity):
        """Test: sms send calls record_outreach_outcome with channel=sms."""
        campaign_id = uuid4()
        sequence_step = 1
        
        with patch("src.engines.sms.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_get_cis.return_value = mock_cis_service
                
                engine = SMSEngine()
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=campaign_id,
                    action="sent",
                    provider_message_id="sms-msg-123",
                    content_preview="Test SMS",
                    message_content="Test SMS message content",
                    sequence_step=sequence_step,
                    from_number="+61400000000",
                )
                
                # Verify CIS service was called
                mock_cis_service.record_outreach_outcome.assert_called_once()
                call_args = mock_cis_service.record_outreach_outcome.call_args
                
                # Verify correct arguments
                assert call_args.kwargs["activity_id"] == mock_activity.id
                assert call_args.kwargs["lead_id"] == mock_lead.id
                assert call_args.kwargs["client_id"] == mock_lead.client_id
                assert call_args.kwargs["campaign_id"] == campaign_id
                assert call_args.kwargs["channel"] == "sms"
                assert call_args.kwargs["sequence_step"] == sequence_step
                assert call_args.kwargs["propensity_score_at_send"] == mock_lead.propensity_score
                assert call_args.kwargs["propensity_tier_at_send"] == mock_lead.propensity_tier
                assert call_args.kwargs["subject_line"] is None  # SMS has no subject
                assert call_args.kwargs["session"] == mock_db

    @pytest.mark.asyncio
    async def test_sms_non_sent_action_skips_cis(self, mock_lead, mock_db, mock_activity):
        """Test: non-sent SMS actions don't call record_outreach_outcome."""
        with patch("src.engines.sms.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_get_cis.return_value = mock_cis_service
                
                engine = SMSEngine()
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=uuid4(),
                    action="delivered",  # Not "sent"
                )
                
                # CIS should NOT be called for non-sent actions
                mock_cis_service.record_outreach_outcome.assert_not_called()

    @pytest.mark.asyncio
    async def test_sms_cis_failure_is_non_blocking(self, mock_lead, mock_db, mock_activity):
        """Test: CIS failures don't block SMS logging."""
        with patch("src.engines.sms.Activity", return_value=mock_activity):
            with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                mock_cis_service = AsyncMock()
                mock_cis_service.record_outreach_outcome.side_effect = Exception("CIS DB error")
                mock_get_cis.return_value = mock_cis_service
                
                engine = SMSEngine()
                # Should NOT raise even though CIS fails
                await engine._log_activity(
                    db=mock_db,
                    lead=mock_lead,
                    campaign_id=uuid4(),
                    action="sent",
                )
                
                # Verify activity was still committed
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()


class TestCISWiringIntegration:
    """Cross-channel integration tests."""

    @pytest.mark.asyncio
    async def test_all_channels_use_same_cis_service_method(self, mock_lead, mock_db, mock_activity):
        """Verify all channels call the same record_outreach_outcome method."""
        engines = [
            ("email", EmailEngine(), "src.engines.email"),
            ("linkedin", LinkedInEngine(), "src.engines.linkedin"),
            ("sms", SMSEngine(), "src.engines.sms"),
        ]
        
        for channel, engine, module_path in engines:
            with patch(f"{module_path}.Activity", return_value=mock_activity):
                with patch("src.services.cis_service.get_cis_service") as mock_get_cis:
                    mock_cis_service = AsyncMock()
                    mock_get_cis.return_value = mock_cis_service
                    
                    await engine._log_activity(
                        db=mock_db,
                        lead=mock_lead,
                        campaign_id=uuid4(),
                        action="sent",
                    )
                    
                    # Verify record_outreach_outcome was called (not some other method)
                    assert mock_cis_service.record_outreach_outcome.called, \
                        f"{channel} engine did not call record_outreach_outcome"
                    
                    # Verify the channel parameter matches
                    call_args = mock_cis_service.record_outreach_outcome.call_args
                    assert call_args.kwargs["channel"] == channel, \
                        f"{channel} engine passed wrong channel: {call_args.kwargs['channel']}"
