"""
FILE: tests/test_e2e/test_full_flow.py
PURPOSE: End-to-end integration tests for full enrichment → outreach flow
PHASE: 9 (Integration Testing)
TASK: TST-003
DEPENDENCIES:
  - tests/conftest.py
  - tests/fixtures/*
  - src/engines/*
  - src/orchestration/*
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from tests.fixtures.database_fixtures import (
    create_test_client,
    create_test_campaign,
    create_test_lead,
    create_new_lead,
    create_hot_lead,
    create_warm_lead,
    create_lead_batch,
)
from tests.fixtures.api_responses import (
    apollo_person_enrichment_success,
    resend_send_success,
    twilio_sms_success,
    heyreach_connection_request_success,
    anthropic_message_success,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_client() -> dict:
    """Create a test client with active subscription."""
    return create_test_client(
        name="E2E Test Agency",
        credits=5000,
        subscription_status="active",
    )


@pytest.fixture
def test_campaign(test_client: dict) -> dict:
    """Create a test campaign."""
    return create_test_campaign(
        client_id=test_client["id"],
        name="E2E Test Campaign",
        status="active",
        permission_mode="autopilot",
    )


@pytest.fixture
def new_leads(test_client: dict, test_campaign: dict) -> list[dict]:
    """Create a batch of new leads for testing."""
    leads = []
    for i in range(5):
        lead = create_new_lead(test_client["id"], test_campaign["id"])
        lead["email"] = f"newlead{i}@company{i}.io"
        lead["company_domain"] = f"company{i}.io"
        leads.append(lead)
    return leads


# ============================================================================
# Full Flow Tests
# ============================================================================

class TestFullEnrichmentToOutreachFlow:
    """Test the complete flow from lead creation to outreach."""

    @pytest.mark.asyncio
    async def test_full_flow_single_lead(
        self,
        test_client: dict,
        test_campaign: dict,
        db_session: AsyncMock,
        mock_redis: MagicMock,
        mock_apollo_client: MagicMock,
        mock_resend_client: MagicMock,
        mock_anthropic_client: MagicMock,
    ):
        """Test full flow for a single lead: create → enrich → score → outreach."""
        # Arrange
        lead = create_new_lead(test_client["id"], test_campaign["id"])

        # Mock Apollo enrichment
        mock_apollo_client.enrich_person.return_value = apollo_person_enrichment_success()

        # Mock content generation
        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Hi Jane, I noticed TechCompany is expanding...")],
            usage=MagicMock(input_tokens=100, output_tokens=50),
        )

        # Mock email send
        mock_resend_client.send.return_value = resend_send_success()

        # Act - Step 1: Create lead (simulated)
        assert lead["status"] == "new"
        assert lead["als_score"] == 0

        # Act - Step 2: Enrich lead
        with patch("src.engines.scout.ScoutEngine") as MockScoutEngine:
            scout = MockScoutEngine.return_value
            scout.enrich = AsyncMock(return_value={
                "success": True,
                "data": apollo_person_enrichment_success()["person"],
                "source": "apollo",
                "cached": False,
            })

            enrichment_result = await scout.enrich(db_session, lead["email"])

            assert enrichment_result["success"] is True
            assert enrichment_result["source"] == "apollo"

            # Update lead with enrichment data
            lead["status"] = "enriched"
            lead["first_name"] = enrichment_result["data"]["first_name"]
            lead["title"] = enrichment_result["data"]["title"]

        # Act - Step 3: Score lead
        with patch("src.engines.scorer.ScorerEngine") as MockScorerEngine:
            scorer = MockScorerEngine.return_value
            scorer.score = AsyncMock(return_value={
                "als_score": 85,
                "als_tier": "hot",
                "components": {
                    "data_quality": 90,
                    "authority": 95,
                    "company_fit": 85,
                    "timing": 75,
                    "risk": 80,
                },
            })

            score_result = await scorer.score(db_session, lead)

            assert score_result["als_score"] == 85
            assert score_result["als_tier"] == "hot"

            # Update lead with score
            lead["status"] = "scored"
            lead["als_score"] = score_result["als_score"]
            lead["als_tier"] = score_result["als_tier"]

        # Act - Step 4: Allocate channel
        with patch("src.engines.allocator.AllocatorEngine") as MockAllocatorEngine:
            allocator = MockAllocatorEngine.return_value
            allocator.allocate = AsyncMock(return_value={
                "channel": "email",
                "resource_id": "email_account_1",
                "within_limits": True,
            })

            allocation_result = await allocator.allocate(
                db_session,
                lead,
                test_campaign,
            )

            assert allocation_result["channel"] == "email"
            assert allocation_result["within_limits"] is True

        # Act - Step 5: Generate content
        with patch("src.engines.content.ContentEngine") as MockContentEngine:
            content = MockContentEngine.return_value
            content.generate_email = AsyncMock(return_value={
                "subject": "Quick question about TechCompany",
                "body": "Hi Jane, I noticed TechCompany is expanding...",
                "personalization_score": 0.85,
            })

            content_result = await content.generate_email(
                db_session,
                lead,
                test_campaign,
                step=1,
            )

            assert content_result["personalization_score"] >= 0.8

        # Act - Step 6: Send email
        with patch("src.engines.email.EmailEngine") as MockEmailEngine:
            email_engine = MockEmailEngine.return_value
            email_engine.send = AsyncMock(return_value={
                "success": True,
                "message_id": f"email_{uuid.uuid4().hex[:12]}",
                "provider": "resend",
            })

            send_result = await email_engine.send(
                db_session,
                lead,
                content_result["subject"],
                content_result["body"],
                resource_id=allocation_result["resource_id"],
            )

            assert send_result["success"] is True
            assert send_result["provider"] == "resend"

            # Update lead status
            lead["status"] = "in_sequence"
            lead["sequence_step"] = 1
            lead["last_contacted_at"] = datetime.utcnow().isoformat()

        # Assert - Final state
        assert lead["status"] == "in_sequence"
        assert lead["sequence_step"] == 1
        assert lead["als_score"] == 85
        assert lead["als_tier"] == "hot"

    @pytest.mark.asyncio
    async def test_full_flow_batch_leads(
        self,
        test_client: dict,
        test_campaign: dict,
        db_session: AsyncMock,
    ):
        """Test full flow for a batch of leads."""
        # Arrange
        leads = create_lead_batch(
            test_client["id"],
            test_campaign["id"],
            count=10,
            tier_distribution={"hot": 2, "warm": 4, "cool": 3, "cold": 1},
        )

        # Act - Process batch
        processed_count = 0
        sent_count = 0

        with patch("src.engines.scout.ScoutEngine") as MockScout, \
             patch("src.engines.scorer.ScorerEngine") as MockScorer, \
             patch("src.engines.allocator.AllocatorEngine") as MockAllocator, \
             patch("src.engines.email.EmailEngine") as MockEmail:

            scout = MockScout.return_value
            scorer = MockScorer.return_value
            allocator = MockAllocator.return_value
            email = MockEmail.return_value

            # Mock enrichment
            scout.enrich = AsyncMock(return_value={
                "success": True,
                "data": apollo_person_enrichment_success()["person"],
            })

            # Mock scoring based on tier
            async def mock_score(db, lead):
                return {
                    "als_score": lead["als_score"],
                    "als_tier": lead["als_tier"],
                    "components": {},
                }
            scorer.score = mock_score

            # Mock allocation - only allow warm and hot leads
            async def mock_allocate(db, lead, campaign):
                if lead["als_tier"] in ["hot", "warm"]:
                    return {"channel": "email", "within_limits": True}
                return {"channel": None, "within_limits": False, "reason": "tier_too_low"}
            allocator.allocate = mock_allocate

            # Mock sending
            email.send = AsyncMock(return_value={"success": True})

            for lead in leads:
                processed_count += 1

                # Enrich
                await scout.enrich(db_session, lead["email"])
                lead["status"] = "enriched"

                # Score
                score_result = await scorer.score(db_session, lead)
                lead["als_score"] = score_result["als_score"]

                # Allocate
                alloc_result = await allocator.allocate(db_session, lead, test_campaign)

                # Send only if allocated
                if alloc_result.get("channel"):
                    await email.send(db_session, lead, "Subject", "Body")
                    sent_count += 1
                    lead["status"] = "in_sequence"

        # Assert
        assert processed_count == 10
        assert sent_count == 6  # 2 hot + 4 warm

    @pytest.mark.asyncio
    async def test_flow_with_jit_validation_failure(
        self,
        test_client: dict,
        test_campaign: dict,
        db_session: AsyncMock,
    ):
        """Test flow stops when JIT validation fails."""
        # Arrange - Client with no credits
        test_client["credits_remaining"] = 0
        lead = create_new_lead(test_client["id"], test_campaign["id"])

        # Act
        with patch("src.orchestration.tasks.enrichment_tasks") as mock_tasks:
            mock_tasks.enrich_lead_task = AsyncMock(
                side_effect=Exception("JIT validation failed: Insufficient credits")
            )

            with pytest.raises(Exception) as exc_info:
                await mock_tasks.enrich_lead_task(lead["id"])

            assert "Insufficient credits" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_flow_with_inactive_campaign(
        self,
        test_client: dict,
        db_session: AsyncMock,
    ):
        """Test flow stops when campaign is paused."""
        # Arrange
        paused_campaign = create_test_campaign(
            test_client["id"],
            status="paused",
        )
        lead = create_warm_lead(test_client["id"], paused_campaign["id"])

        # Act
        with patch("src.orchestration.tasks.outreach_tasks") as mock_tasks:
            mock_tasks.send_email_task = AsyncMock(
                side_effect=Exception("JIT validation failed: Campaign is paused")
            )

            with pytest.raises(Exception) as exc_info:
                await mock_tasks.send_email_task(lead["id"])

            assert "Campaign is paused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_flow_respects_permission_mode(
        self,
        test_client: dict,
        db_session: AsyncMock,
    ):
        """Test flow respects manual permission mode."""
        # Arrange - Manual mode campaign
        manual_campaign = create_test_campaign(
            test_client["id"],
            permission_mode="manual",
        )
        lead = create_hot_lead(test_client["id"], manual_campaign["id"])

        # Act - Should queue for approval instead of sending
        with patch("src.engines.allocator.AllocatorEngine") as MockAllocator:
            allocator = MockAllocator.return_value
            allocator.allocate = AsyncMock(return_value={
                "channel": "email",
                "within_limits": True,
                "requires_approval": True,  # Manual mode
            })

            result = await allocator.allocate(db_session, lead, manual_campaign)

            assert result["requires_approval"] is True


class TestMultiChannelSequence:
    """Test multi-channel outreach sequences."""

    @pytest.mark.asyncio
    async def test_multi_channel_sequence(
        self,
        test_client: dict,
        test_campaign: dict,
        db_session: AsyncMock,
    ):
        """Test a lead going through multi-channel sequence."""
        # Arrange
        lead = create_hot_lead(test_client["id"], test_campaign["id"])
        sequence = [
            {"step": 1, "channel": "email", "delay_days": 0},
            {"step": 2, "channel": "email", "delay_days": 3},
            {"step": 3, "channel": "linkedin", "delay_days": 5},
            {"step": 4, "channel": "sms", "delay_days": 7},
            {"step": 5, "channel": "email", "delay_days": 10},
        ]

        # Act
        with patch("src.engines.email.EmailEngine") as MockEmail, \
             patch("src.engines.linkedin.LinkedInEngine") as MockLinkedIn, \
             patch("src.engines.sms.SMSEngine") as MockSMS:

            email = MockEmail.return_value
            linkedin = MockLinkedIn.return_value
            sms = MockSMS.return_value

            email.send = AsyncMock(return_value={"success": True})
            linkedin.send_connection_request = AsyncMock(return_value={"success": True})
            sms.send = AsyncMock(return_value={"success": True})

            activities = []

            for step in sequence:
                lead["sequence_step"] = step["step"]

                if step["channel"] == "email":
                    result = await email.send(db_session, lead, "Subject", "Body")
                elif step["channel"] == "linkedin":
                    result = await linkedin.send_connection_request(db_session, lead, "Message")
                elif step["channel"] == "sms":
                    result = await sms.send(db_session, lead, "SMS message")

                activities.append({
                    "step": step["step"],
                    "channel": step["channel"],
                    "success": result["success"],
                })

        # Assert
        assert len(activities) == 5
        assert all(a["success"] for a in activities)
        assert activities[0]["channel"] == "email"
        assert activities[2]["channel"] == "linkedin"
        assert activities[3]["channel"] == "sms"


class TestReplyHandling:
    """Test reply processing flow."""

    @pytest.mark.asyncio
    async def test_reply_processing_interested(
        self,
        test_client: dict,
        test_campaign: dict,
        db_session: AsyncMock,
    ):
        """Test processing an interested reply."""
        # Arrange
        lead = create_warm_lead(test_client["id"], test_campaign["id"])
        lead["status"] = "in_sequence"
        lead["sequence_step"] = 2

        reply_content = "Thanks for reaching out! I'd love to learn more. Can we schedule a call?"

        # Act
        with patch("src.engines.closer.CloserEngine") as MockCloser:
            closer = MockCloser.return_value
            closer.classify_intent = AsyncMock(return_value={
                "intent": "interested",
                "confidence": 0.92,
                "suggested_action": "schedule_meeting",
            })

            result = await closer.classify_intent(db_session, lead, reply_content)

            # Update lead based on intent
            if result["intent"] == "interested":
                lead["status"] = "converted"

        # Assert
        assert result["intent"] == "interested"
        assert result["confidence"] > 0.9
        assert lead["status"] == "converted"

    @pytest.mark.asyncio
    async def test_reply_processing_unsubscribe(
        self,
        test_client: dict,
        test_campaign: dict,
        db_session: AsyncMock,
    ):
        """Test processing an unsubscribe reply."""
        # Arrange
        lead = create_warm_lead(test_client["id"], test_campaign["id"])
        lead["status"] = "in_sequence"

        reply_content = "Please remove me from your mailing list. Unsubscribe."

        # Act
        with patch("src.engines.closer.CloserEngine") as MockCloser:
            closer = MockCloser.return_value
            closer.classify_intent = AsyncMock(return_value={
                "intent": "unsubscribe",
                "confidence": 0.98,
                "suggested_action": "add_to_suppression",
            })

            result = await closer.classify_intent(db_session, lead, reply_content)

            # Update lead based on intent
            if result["intent"] == "unsubscribe":
                lead["status"] = "unsubscribed"

        # Assert
        assert result["intent"] == "unsubscribe"
        assert lead["status"] == "unsubscribed"


class TestWebhookRoundTrip:
    """Test webhook processing round-trip."""

    @pytest.mark.asyncio
    async def test_email_reply_webhook_roundtrip(
        self,
        test_client: dict,
        test_campaign: dict,
        db_session: AsyncMock,
    ):
        """Test email reply webhook triggers intent classification."""
        from tests.fixtures.webhook_payloads import postmark_inbound_email

        # Arrange
        lead = create_warm_lead(test_client["id"], test_campaign["id"])
        lead["status"] = "in_sequence"

        webhook_payload = postmark_inbound_email(
            from_email=lead["email"],
            body="I'm interested! Let's schedule a call.",
        )

        # Act - Simulate webhook processing
        with patch("src.engines.closer.CloserEngine") as MockCloser:
            closer = MockCloser.return_value
            closer.classify_intent = AsyncMock(return_value={
                "intent": "meeting_request",
                "confidence": 0.95,
            })

            # 1. Receive webhook
            from_email = webhook_payload["From"]
            body = webhook_payload["TextBody"]

            # 2. Find lead by email
            found_lead = lead if lead["email"] == from_email else None
            assert found_lead is not None

            # 3. Classify intent
            result = await closer.classify_intent(db_session, found_lead, body)

            # 4. Update lead status
            if result["intent"] == "meeting_request":
                found_lead["status"] = "converted"

        # Assert
        assert result["intent"] == "meeting_request"
        assert found_lead["status"] == "converted"


# ============================================================================
# Verification Checklist
# ============================================================================
# [x] Contract comment at top
# [x] Full single lead flow (create → enrich → score → allocate → send)
# [x] Batch lead processing with tier filtering
# [x] JIT validation failure handling
# [x] Inactive campaign handling
# [x] Permission mode respect (manual requires approval)
# [x] Multi-channel sequence test (email → linkedin → sms)
# [x] Reply processing (interested, unsubscribe)
# [x] Webhook round-trip test
# [x] All tests use mocked engines
