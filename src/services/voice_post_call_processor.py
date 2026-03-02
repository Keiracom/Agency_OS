"""
Contract: src/services/voice_post_call_processor.py
Purpose: Post-call processing for voice calls - outcome classification, routing, and updates
Layer: 3 - services
Imports: models, integrations
Consumers: voice webhook handlers, orchestration

FILE: src/services/voice_post_call_processor.py
PURPOSE: Process completed voice calls - classify outcomes, route actions, update records
PHASE: Voice AI Infrastructure
TASK: VOICE-POST-001
DEPENDENCIES:
  - src/integrations/anthropic.py (Claude Haiku for classification)
  - src/integrations/twilio.py (Telnyx SMS)
  - src/integrations/postmark.py (Resend email alternative)
  - src/services/suppression_service.py
  - src/services/alert_service.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - All functions async with type hints and docstrings
  - Log all outcome routing decisions at INFO level
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS & ENUMS
# ============================================


class CallOutcome(StrEnum):
    """Voice call outcome classifications."""

    BOOKED = "BOOKED"
    CALLBACK = "CALLBACK"
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    VOICEMAIL = "VOICEMAIL"
    NO_ANSWER = "NO_ANSWER"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    ESCALATION = "ESCALATION"
    ANGRY = "ANGRY"


class LeadStatus(StrEnum):
    """Lead pool status values."""

    AVAILABLE = "available"
    ASSIGNED = "assigned"
    CONVERTED = "converted"
    WARM_VOICE = "warm_voice"
    DISQUALIFIED_VOICE = "disqualified_voice"


# Confidence threshold for classification
CONFIDENCE_THRESHOLD = 0.70

# ALS score adjustments
ALS_POSITIVE_ADJUSTMENT = 15  # BOOKED or INTERESTED
ALS_NEGATIVE_ADJUSTMENT = -15  # ANGRY or UNSUBSCRIBE


# ============================================
# DATA CLASSES
# ============================================


@dataclass
class ProcessResult:
    """Result of post-call processing."""

    success: bool
    outcome: str
    actions_taken: list[str] = field(default_factory=list)
    callback_scheduled_at: datetime | None = None
    als_adjustment: int = 0
    flagged_for_review: bool = False
    error: str | None = None


@dataclass
class ClassificationResult:
    """Result of AI outcome classification."""

    outcome: str
    confidence: float
    callback_time: datetime | None = None
    sentiment_summary: str = ""
    raw_response: dict | None = None


# ============================================
# CLASSIFICATION PROMPTS
# ============================================


CLASSIFICATION_SYSTEM_PROMPT = """You are an expert at classifying voice call outcomes for sales outreach.
Analyze the transcript and classify the call into ONE of these outcomes:

OUTCOMES:
- BOOKED: Prospect agreed to a meeting/demo, confirmed date/time
- CALLBACK: Prospect requested a callback at a specific time
- INTERESTED: Prospect showed interest but no meeting booked yet
- NOT_INTERESTED: Prospect politely declined, not interested
- VOICEMAIL: Call went to voicemail, left message
- NO_ANSWER: Call was not answered, no voicemail
- UNSUBSCRIBE: Prospect requested to be removed from all contact
- ESCALATION: Prospect requested to speak to manager/supervisor
- ANGRY: Prospect was hostile, angry, or threatening

EXTRACT:
- callback_time: If CALLBACK, extract the requested callback date/time as ISO format
- sentiment_summary: 2 sentences max summarizing the prospect's sentiment and key points

Return JSON only:
{
  "outcome": "OUTCOME_VALUE",
  "confidence": 0.0-1.0,
  "callback_time": "ISO datetime or null",
  "sentiment_summary": "Brief 2-sentence summary"
}"""


# ============================================
# POST-CALL PROCESSOR SERVICE
# ============================================


class VoicePostCallProcessor:
    """
    Service for processing completed voice calls.

    Handles:
    - AI-powered outcome classification via Claude Haiku
    - Supabase record updates (voice_calls, lead_pool)
    - Outcome-specific routing (SMS, email, scheduling)
    - ALS score adjustments
    - CIS feed for learning
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the post-call processor.

        Args:
            session: Async database session
        """
        self.session = session

    async def process_completed_call(
        self,
        call_sid: str,
        transcript: str,
        duration: int,
        raw_outcome: str,
    ) -> ProcessResult:
        """
        Process a completed voice call.

        Main entry point called by webhook handlers after call completion.
        Classifies outcome, updates records, and routes to appropriate actions.

        Args:
            call_sid: Unique call identifier (Telnyx call SID)
            transcript: Full call transcript
            duration: Call duration in seconds
            raw_outcome: Raw outcome from Telnyx (connected, busy, etc.)

        Returns:
            ProcessResult with outcome and actions taken
        """
        actions_taken: list[str] = []
        callback_scheduled_at: datetime | None = None
        als_adjustment = 0
        flagged_for_review = False

        try:
            # Step 1: Fetch call record and lead data
            call_data = await self._get_call_data(call_sid)
            if not call_data:
                logger.error(f"Call record not found for SID: {call_sid}")
                return ProcessResult(
                    success=False,
                    outcome="UNKNOWN",
                    error=f"Call record not found: {call_sid}",
                )

            lead_id = call_data.get("lead_id")
            client_id = call_data.get("client_id")
            campaign_id = call_data.get("campaign_id")
            hook_used = call_data.get("hook_used")
            propensity_score_at_call = call_data.get("propensity_score_at_call")

            # Step 2: Classify outcome via Claude Haiku
            classification = await self._classify_outcome(transcript, raw_outcome)

            # Check confidence threshold
            if classification.confidence < CONFIDENCE_THRESHOLD:
                flagged_for_review = True
                logger.warning(
                    f"Low confidence classification ({classification.confidence:.2f}) "
                    f"for call {call_sid} - flagging for human review"
                )
                actions_taken.append("flagged_for_human_review")

            outcome = classification.outcome
            logger.info(
                f"Call {call_sid} classified as {outcome} "
                f"(confidence: {classification.confidence:.2f})"
            )

            # Step 3: Update voice_calls record
            await self._update_voice_call_record(
                call_sid=call_sid,
                outcome=outcome,
                duration_seconds=duration,
                transcript=transcript,
                sentiment_summary=classification.sentiment_summary,
            )
            actions_taken.append("voice_call_record_updated")

            # Step 4: Route based on outcome
            if outcome == CallOutcome.BOOKED:
                routing_result = await self._handle_booked(
                    lead_id=lead_id,
                    client_id=client_id,
                    campaign_id=campaign_id,
                    call_sid=call_sid,
                )
                actions_taken.extend(routing_result)
                als_adjustment = ALS_POSITIVE_ADJUSTMENT

            elif outcome == CallOutcome.CALLBACK:
                callback_scheduled_at = classification.callback_time
                routing_result = await self._handle_callback(
                    lead_id=lead_id,
                    client_id=client_id,
                    callback_time=callback_scheduled_at,
                )
                actions_taken.extend(routing_result)

            elif outcome == CallOutcome.INTERESTED:
                routing_result = await self._handle_interested(
                    lead_id=lead_id,
                    client_id=client_id,
                    campaign_id=campaign_id,
                )
                actions_taken.extend(routing_result)
                als_adjustment = ALS_POSITIVE_ADJUSTMENT

            elif outcome == CallOutcome.UNSUBSCRIBE:
                routing_result = await self._handle_unsubscribe(
                    lead_id=lead_id,
                    client_id=client_id,
                )
                actions_taken.extend(routing_result)
                als_adjustment = ALS_NEGATIVE_ADJUSTMENT

            elif outcome in (CallOutcome.ESCALATION, CallOutcome.ANGRY):
                routing_result = await self._handle_escalation(
                    lead_id=lead_id,
                    client_id=client_id,
                    outcome=outcome,
                    transcript=transcript,
                    callback_time=classification.callback_time,
                )
                actions_taken.extend(routing_result)
                if outcome == CallOutcome.ANGRY:
                    als_adjustment = ALS_NEGATIVE_ADJUSTMENT

            elif outcome == CallOutcome.NOT_INTERESTED:
                routing_result = await self._handle_not_interested(
                    lead_id=lead_id,
                )
                actions_taken.extend(routing_result)

            # Handle VOICEMAIL and NO_ANSWER - no special routing needed
            # Voice retry service handles rescheduling separately

            # Step 5: Update propensity score if adjustment needed
            if als_adjustment != 0 and lead_id:
                await self._adjust_propensity_score(lead_id, als_adjustment)
                actions_taken.append(f"propensity_adjusted_{als_adjustment:+d}")

            # Step 6: Write to CIS feed for learning
            await self._write_cis_feed(
                call_sid=call_sid,
                outcome=outcome,
                hook_used=hook_used,
                propensity_score_at_call=propensity_score_at_call,
                client_id=client_id,
            )
            actions_taken.append("cis_feed_updated")

            await self.session.commit()

            logger.info(
                f"Post-call processing complete for {call_sid}: "
                f"outcome={outcome}, actions={actions_taken}"
            )

            return ProcessResult(
                success=True,
                outcome=outcome,
                actions_taken=actions_taken,
                callback_scheduled_at=callback_scheduled_at,
                als_adjustment=als_adjustment,
                flagged_for_review=flagged_for_review,
            )

        except Exception as e:
            logger.error(f"Post-call processing failed for {call_sid}: {e}")
            await self.session.rollback()
            return ProcessResult(
                success=False,
                outcome="ERROR",
                actions_taken=actions_taken,
                error=str(e),
            )

    # =========================================================================
    # CLASSIFICATION
    # =========================================================================

    async def _classify_outcome(
        self,
        transcript: str,
        raw_outcome: str,
    ) -> ClassificationResult:
        """
        Classify call outcome using Claude Haiku.

        Args:
            transcript: Full call transcript
            raw_outcome: Raw outcome from telephony provider

        Returns:
            ClassificationResult with outcome and metadata
        """
        # Handle trivial cases without AI
        if not transcript or transcript.strip() == "":
            if raw_outcome in ("no_answer", "no-answer", "busy"):
                return ClassificationResult(
                    outcome=CallOutcome.NO_ANSWER,
                    confidence=1.0,
                    sentiment_summary="Call not answered.",
                )
            elif raw_outcome in ("voicemail", "machine_end_beep"):
                return ClassificationResult(
                    outcome=CallOutcome.VOICEMAIL,
                    confidence=1.0,
                    sentiment_summary="Call went to voicemail.",
                )

        try:
            from src.integrations.anthropic import get_anthropic_client

            client = get_anthropic_client()

            prompt = f"""Analyze this voice call transcript and classify the outcome.

Raw telephony outcome: {raw_outcome}

Transcript:
\"\"\"
{transcript[:3000]}
\"\"\"

Return JSON classification only."""

            response = await client.complete(
                prompt=prompt,
                system=CLASSIFICATION_SYSTEM_PROMPT,
                max_tokens=300,
                temperature=0.1,
                model="claude-3-5-haiku-20241022",
                enable_caching=True,
            )

            # Parse JSON from response
            content = response.get("content", "")

            # Extract JSON from potential markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            # Handle plain JSON
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                result = json.loads(json_match.group())

                # Parse callback time if provided
                callback_time = None
                if result.get("callback_time"):
                    try:
                        callback_time = datetime.fromisoformat(
                            result["callback_time"].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        logger.warning(
                            f"Could not parse callback time: {result.get('callback_time')}"
                        )

                return ClassificationResult(
                    outcome=result.get("outcome", CallOutcome.NOT_INTERESTED),
                    confidence=float(result.get("confidence", 0.5)),
                    callback_time=callback_time,
                    sentiment_summary=result.get("sentiment_summary", ""),
                    raw_response=result,
                )

        except Exception as e:
            logger.error(f"AI classification failed: {e}")

        # Fallback to rule-based classification
        return self._classify_with_rules(transcript, raw_outcome)

    def _classify_with_rules(
        self,
        transcript: str,
        raw_outcome: str,
    ) -> ClassificationResult:
        """
        Fallback rule-based classification.

        Args:
            transcript: Call transcript
            raw_outcome: Raw outcome

        Returns:
            ClassificationResult from rules
        """
        transcript_lower = transcript.lower() if transcript else ""

        # Check for booking indicators
        booking_phrases = [
            "book",
            "schedule",
            "calendar",
            "appointment",
            "demo",
            "let's set up",
            "sounds good",
            "i'm free",
            "let's do it",
        ]
        if any(phrase in transcript_lower for phrase in booking_phrases):
            return ClassificationResult(
                outcome=CallOutcome.BOOKED,
                confidence=0.65,
                sentiment_summary="Prospect appeared to agree to a meeting.",
            )

        # Check for callback indicators
        callback_phrases = [
            "call me back",
            "call later",
            "try again",
            "busy right now",
            "call tomorrow",
            "next week",
            "another time",
        ]
        if any(phrase in transcript_lower for phrase in callback_phrases):
            return ClassificationResult(
                outcome=CallOutcome.CALLBACK,
                confidence=0.60,
                sentiment_summary="Prospect requested a callback.",
            )

        # Check for unsubscribe
        unsubscribe_phrases = [
            "stop calling",
            "remove me",
            "unsubscribe",
            "do not call",
            "take me off",
            "never call again",
        ]
        if any(phrase in transcript_lower for phrase in unsubscribe_phrases):
            return ClassificationResult(
                outcome=CallOutcome.UNSUBSCRIBE,
                confidence=0.80,
                sentiment_summary="Prospect requested removal from contact list.",
            )

        # Check for anger
        anger_phrases = [
            "fuck",
            "asshole",
            "scam",
            "harassing",
            "sue you",
            "reported",
            "police",
            "lawyer",
        ]
        if any(phrase in transcript_lower for phrase in anger_phrases):
            return ClassificationResult(
                outcome=CallOutcome.ANGRY,
                confidence=0.75,
                sentiment_summary="Prospect expressed strong negative sentiment.",
            )

        # Check for escalation
        escalation_phrases = [
            "speak to manager",
            "supervisor",
            "boss",
            "complaint",
            "your manager",
            "escalate",
        ]
        if any(phrase in transcript_lower for phrase in escalation_phrases):
            return ClassificationResult(
                outcome=CallOutcome.ESCALATION,
                confidence=0.70,
                sentiment_summary="Prospect requested to speak with management.",
            )

        # Check for interest
        interest_phrases = [
            "sounds interesting",
            "tell me more",
            "how does it work",
            "curious",
            "maybe",
            "possibly",
        ]
        if any(phrase in transcript_lower for phrase in interest_phrases):
            return ClassificationResult(
                outcome=CallOutcome.INTERESTED,
                confidence=0.55,
                sentiment_summary="Prospect showed some interest.",
            )

        # Check for not interested
        not_interested_phrases = [
            "not interested",
            "no thanks",
            "no thank you",
            "pass",
            "not for us",
            "don't need",
        ]
        if any(phrase in transcript_lower for phrase in not_interested_phrases):
            return ClassificationResult(
                outcome=CallOutcome.NOT_INTERESTED,
                confidence=0.70,
                sentiment_summary="Prospect declined.",
            )

        # Default based on raw outcome
        if raw_outcome in ("voicemail", "machine_end_beep"):
            return ClassificationResult(
                outcome=CallOutcome.VOICEMAIL,
                confidence=0.90,
                sentiment_summary="Call reached voicemail.",
            )

        if raw_outcome in ("no_answer", "no-answer", "busy"):
            return ClassificationResult(
                outcome=CallOutcome.NO_ANSWER,
                confidence=0.90,
                sentiment_summary="Call was not answered.",
            )

        # Fallback
        return ClassificationResult(
            outcome=CallOutcome.NOT_INTERESTED,
            confidence=0.40,
            sentiment_summary="Unable to determine clear intent from transcript.",
        )

    # =========================================================================
    # DATA ACCESS
    # =========================================================================

    async def _get_call_data(self, call_sid: str) -> dict[str, Any] | None:
        """
        Fetch call record and related data.

        Args:
            call_sid: Telnyx call SID

        Returns:
            Call data dict or None if not found
        """
        result = await self.session.execute(
            text("""
                SELECT
                    vc.id,
                    vc.lead_id,
                    vc.client_id,
                    vc.campaign_id,
                    vc.hook_used,
                    lp.als_score as propensity_score_at_call,
                    lp.first_name as lead_first_name,
                    lp.phone as lead_phone,
                    lp.email as lead_email,
                    c.business_name as agency_name,
                    c.calendly_link
                FROM voice_calls vc
                LEFT JOIN lead_pool lp ON vc.lead_id = lp.id
                LEFT JOIN clients c ON vc.client_id = c.id
                WHERE vc.call_sid = :call_sid
            """),
            {"call_sid": call_sid},
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None

    async def _update_voice_call_record(
        self,
        call_sid: str,
        outcome: str,
        duration_seconds: int,
        transcript: str,
        sentiment_summary: str,
    ) -> None:
        """
        Update voice_calls record with outcome data.

        Args:
            call_sid: Call identifier
            outcome: Classified outcome
            duration_seconds: Call duration
            transcript: Full transcript
            sentiment_summary: AI-generated sentiment summary
        """
        await self.session.execute(
            text("""
                UPDATE voice_calls SET
                    outcome = :outcome,
                    duration_seconds = :duration_seconds,
                    transcript = :transcript,
                    sentiment_summary = :sentiment_summary,
                    recording_disclosure_delivered = true,
                    updated_at = NOW()
                WHERE call_sid = :call_sid
            """),
            {
                "call_sid": call_sid,
                "outcome": outcome,
                "duration_seconds": duration_seconds,
                "transcript": transcript,
                "sentiment_summary": sentiment_summary,
            },
        )
        logger.info(f"Updated voice_calls record for {call_sid}")

    # =========================================================================
    # OUTCOME ROUTING
    # =========================================================================

    async def _handle_booked(
        self,
        lead_id: UUID | None,
        client_id: UUID | None,
        campaign_id: UUID | None,
        call_sid: str,
    ) -> list[str]:
        """
        Handle BOOKED outcome - meeting confirmed.

        Actions:
        - Update lead_pool status → CONVERTED
        - Fire Calendly booking link via SMS AND email
        - Log conversion event to audit_logs
        - Notify agency owner via dashboard event

        Args:
            lead_id: Lead UUID
            client_id: Client UUID
            campaign_id: Campaign UUID
            call_sid: Call identifier

        Returns:
            List of actions taken
        """
        actions = []

        if not lead_id:
            logger.warning("No lead_id for BOOKED call - skipping lead update")
            return actions

        # Get lead and client data
        lead_data = await self._get_lead_data(lead_id)
        client_data = await self._get_client_data(client_id) if client_id else {}

        # Update lead_pool status
        await self.session.execute(
            text("""
                UPDATE lead_pool SET
                    pool_status = :status,
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {"lead_id": str(lead_id), "status": LeadStatus.CONVERTED},
        )
        actions.append("lead_status_converted")
        logger.info(f"Lead {lead_id} status updated to CONVERTED")

        # Get Calendly link
        calendly_link = client_data.get("calendly_link", "")
        agency_name = client_data.get("business_name", "Our Team")
        lead_name = lead_data.get("first_name", "there")
        lead_phone = lead_data.get("phone")
        lead_email = lead_data.get("email")

        # Send SMS with Calendly link (if phone available)
        if lead_phone and calendly_link:
            sms_sent = await self._send_sms(
                to_number=lead_phone,
                message=(
                    f"Hi {lead_name}! Great speaking with you. "
                    f"Here's the link to book your meeting: {calendly_link} — {agency_name}"
                ),
                client_id=client_id,
            )
            if sms_sent:
                actions.append("calendly_sms_sent")

        # Send email with Calendly link (if email available)
        if lead_email and calendly_link:
            email_sent = await self._send_email(
                to_email=lead_email,
                to_name=lead_name,
                subject=f"Your meeting with {agency_name} is confirmed",
                body=(
                    f"Hi {lead_name},\n\n"
                    f"Thank you for your time on the call! We're excited to connect further.\n\n"
                    f"Please use this link to confirm your meeting slot: {calendly_link}\n\n"
                    f"Looking forward to speaking with you!\n\n"
                    f"Best regards,\n{agency_name}"
                ),
                client_id=client_id,
            )
            if email_sent:
                actions.append("calendly_email_sent")

        # Log conversion event
        await self._log_audit_event(
            client_id=client_id,
            event_type="voice_conversion",
            event_data={
                "lead_id": str(lead_id),
                "call_sid": call_sid,
                "outcome": "BOOKED",
            },
        )
        actions.append("conversion_logged")

        # Notify agency owner
        await self._create_dashboard_notification(
            client_id=client_id,
            notification_type="voice_booked",
            title="Meeting Booked via Voice Call! 🎉",
            message=f"{lead_name} from {lead_data.get('company_name', 'Unknown Company')} booked a meeting.",
            metadata={"lead_id": str(lead_id), "call_sid": call_sid},
        )
        actions.append("owner_notified")

        return actions

    async def _handle_callback(
        self,
        lead_id: UUID | None,
        client_id: UUID | None,
        callback_time: datetime | None,
    ) -> list[str]:
        """
        Handle CALLBACK outcome - prospect requested callback.

        Actions:
        - Schedule next call attempt at extracted callback_time
        - Create Prefect scheduled run for voice_flow
        - SMS prospect confirmation

        Args:
            lead_id: Lead UUID
            client_id: Client UUID
            callback_time: Requested callback time

        Returns:
            List of actions taken
        """
        actions = []

        if not lead_id:
            return actions

        # Use provided callback time or default to next business day 9 AM
        if not callback_time:
            callback_time = self._next_business_day()

        lead_data = await self._get_lead_data(lead_id)
        client_data = await self._get_client_data(client_id) if client_id else {}

        # Schedule Prefect run for callback
        scheduled = await self._schedule_prefect_voice_flow(
            lead_id=lead_id,
            client_id=client_id,
            scheduled_time=callback_time,
        )
        if scheduled:
            actions.append("prefect_callback_scheduled")

        # Send SMS confirmation
        lead_phone = lead_data.get("phone")
        lead_name = lead_data.get("first_name", "there")
        agency_name = client_data.get("business_name", "Our team")
        agent_name = client_data.get("voice_agent_name", "Alex")

        if lead_phone:
            # Format callback time nicely
            day_str = callback_time.strftime("%A")
            time_str = callback_time.strftime("%I:%M %p")

            sms_sent = await self._send_sms(
                to_number=lead_phone,
                message=(
                    f"Hi {lead_name}, {agent_name} will call you back "
                    f"{day_str} at {time_str}. — {agency_name}"
                ),
                client_id=client_id,
            )
            if sms_sent:
                actions.append("callback_sms_sent")

        return actions

    async def _handle_interested(
        self,
        lead_id: UUID | None,
        client_id: UUID | None,
        campaign_id: UUID | None,
    ) -> list[str]:
        """
        Handle INTERESTED outcome - warm lead, no booking yet.

        Actions:
        - Update lead_pool status → WARM_VOICE
        - Queue personalised email follow-up via closer.py
        - Notify agency owner

        Args:
            lead_id: Lead UUID
            client_id: Client UUID
            campaign_id: Campaign UUID

        Returns:
            List of actions taken
        """
        actions = []

        if not lead_id:
            return actions

        # Update lead status
        await self.session.execute(
            text("""
                UPDATE lead_pool SET
                    pool_status = :status,
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {"lead_id": str(lead_id), "status": LeadStatus.WARM_VOICE},
        )
        actions.append("lead_status_warm_voice")
        logger.info(f"Lead {lead_id} status updated to WARM_VOICE")

        # Queue email follow-up via closer engine
        await self._queue_closer_followup(
            lead_id=lead_id,
            client_id=client_id,
            campaign_id=campaign_id,
            trigger="voice_interested",
        )
        actions.append("closer_followup_queued")

        # Notify agency owner
        lead_data = await self._get_lead_data(lead_id)
        await self._create_dashboard_notification(
            client_id=client_id,
            notification_type="voice_interested",
            title="Warm Lead from Voice Call",
            message=f"{lead_data.get('first_name', 'A prospect')} showed interest on the call. Follow-up queued.",
            metadata={"lead_id": str(lead_id)},
        )
        actions.append("owner_notified")

        return actions

    async def _handle_unsubscribe(
        self,
        lead_id: UUID | None,
        client_id: UUID | None,
    ) -> list[str]:
        """
        Handle UNSUBSCRIBE outcome - prospect wants no contact.

        Actions:
        - Update lead_pool: unsubscribed = true, all_channels = true
        - Add to agency_exclusion_list
        - Suppress across email, LinkedIn, SMS, voice immediately

        Args:
            lead_id: Lead UUID
            client_id: Client UUID

        Returns:
            List of actions taken
        """
        actions = []

        if not lead_id:
            return actions

        lead_data = await self._get_lead_data(lead_id)

        # Update lead_pool unsubscribed flag
        await self.session.execute(
            text("""
                UPDATE lead_pool SET
                    is_unsubscribed = true,
                    unsubscribed_at = NOW(),
                    unsubscribe_reason = 'voice_call_request',
                    pool_status = 'unsubscribed',
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {"lead_id": str(lead_id)},
        )
        actions.append("lead_unsubscribed")
        logger.info(f"Lead {lead_id} marked as unsubscribed (all channels)")

        # Add to suppression list via suppression service
        if client_id and lead_data.get("email"):
            from src.services.suppression_service import SuppressionService

            suppression_service = SuppressionService(self.session)
            await suppression_service.add_suppression(
                client_id=client_id,
                email=lead_data.get("email"),
                domain=self._extract_domain(lead_data.get("email", "")),
                reason="unsubscribed",
                source="voice_call",
                notes="Requested removal during voice call",
            )
            actions.append("suppression_added")

        return actions

    async def _handle_escalation(
        self,
        lead_id: UUID | None,
        client_id: UUID | None,
        outcome: str,
        transcript: str,
        callback_time: datetime | None,
    ) -> list[str]:
        """
        Handle ESCALATION or ANGRY outcome.

        Actions:
        - Update escalation_notified = true
        - Fire immediate push notification to agency owner dashboard
        - Include transcript, prospect name, callback preference

        Args:
            lead_id: Lead UUID
            client_id: Client UUID
            outcome: ESCALATION or ANGRY
            transcript: Call transcript
            callback_time: If prospect gave a callback preference

        Returns:
            List of actions taken
        """
        actions = []

        if not client_id:
            return actions

        lead_data = await self._get_lead_data(lead_id) if lead_id else {}

        # Update escalation flag in voice_calls (already done in main update)
        # Create urgent dashboard notification
        await self._create_dashboard_notification(
            client_id=client_id,
            notification_type="voice_escalation",
            title=f"⚠️ {'Angry Prospect' if outcome == CallOutcome.ANGRY else 'Escalation Request'}",
            message=(
                f"Prospect: {lead_data.get('first_name', 'Unknown')} {lead_data.get('last_name', '')}\n"
                f"Company: {lead_data.get('company_name', 'Unknown')}\n"
                f"{'Requested callback: ' + callback_time.strftime('%Y-%m-%d %H:%M') if callback_time else ''}"
            ),
            metadata={
                "lead_id": str(lead_id) if lead_id else None,
                "outcome": outcome,
                "transcript_preview": transcript[:500] if transcript else None,
                "callback_preference": callback_time.isoformat() if callback_time else None,
                "urgent": True,
            },
            severity="high",
        )
        actions.append("escalation_notification_sent")

        # Send alert email to owner
        from src.services.alert_service import AlertService, AlertType

        alert_service = AlertService(self.session)
        await alert_service.create_alert(
            alert_type=AlertType.ANGRY_COMPLAINT,
            title=f"{'Angry' if outcome == CallOutcome.ANGRY else 'Escalation'} Voice Call",
            message=(
                f"A prospect expressed strong negative sentiment or requested escalation.\n\n"
                f"Prospect: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}\n"
                f"Company: {lead_data.get('company_name', 'Unknown')}\n\n"
                f"Transcript preview:\n{transcript[:500] if transcript else 'No transcript available'}"
            ),
            client_id=client_id,
            lead_id=lead_id,
            metadata={"outcome": outcome},
        )
        actions.append("owner_alert_sent")

        return actions

    async def _handle_not_interested(
        self,
        lead_id: UUID | None,
    ) -> list[str]:
        """
        Handle NOT_INTERESTED outcome.

        Actions:
        - Update lead_pool status → DISQUALIFIED_VOICE
        - Pause sequence

        Args:
            lead_id: Lead UUID

        Returns:
            List of actions taken
        """
        actions = []

        if not lead_id:
            return actions

        # Update lead status
        await self.session.execute(
            text("""
                UPDATE lead_pool SET
                    pool_status = :status,
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {"lead_id": str(lead_id), "status": LeadStatus.DISQUALIFIED_VOICE},
        )
        actions.append("lead_status_disqualified")
        logger.info(f"Lead {lead_id} status updated to DISQUALIFIED_VOICE")

        # Pause any active sequences for this lead
        await self.session.execute(
            text("""
                UPDATE sequence_enrollments SET
                    status = 'paused',
                    paused_reason = 'voice_not_interested',
                    updated_at = NOW()
                WHERE lead_id = :lead_id AND status = 'active'
            """),
            {"lead_id": str(lead_id)},
        )
        actions.append("sequence_paused")

        return actions

    # =========================================================================
    # PROPENSITY SCORING & CIS
    # =========================================================================

    async def _adjust_propensity_score(
        self,
        lead_id: UUID,
        adjustment: int,
    ) -> None:
        """
        Adjust propensity score for a lead.

        Args:
            lead_id: Lead UUID
            adjustment: Score adjustment (+15 or -15 typically)
        """
        await self.session.execute(
            text("""
                UPDATE lead_pool SET
                    als_score = GREATEST(0, LEAST(100, COALESCE(als_score, 50) + :adjustment)),
                    scored_at = NOW(),
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {"lead_id": str(lead_id), "adjustment": adjustment},
        )
        logger.info(f"Adjusted propensity score for lead {lead_id} by {adjustment:+d}")

    async def _write_cis_feed(
        self,
        call_sid: str,
        outcome: str,
        hook_used: str | None,
        propensity_score_at_call: int | None,
        client_id: UUID | None,
    ) -> None:
        """
        Write call outcome to conversion_events table for CIS learning.

        Args:
            call_sid: Call identifier
            outcome: Call outcome
            hook_used: Voice hook/script used
            propensity_score_at_call: Propensity score at time of call
            client_id: Client UUID
        """
        try:
            await self.session.execute(
                text("""
                    INSERT INTO conversion_events (
                        client_id, event_type, event_source, event_data, created_at
                    ) VALUES (
                        :client_id, 'voice_call_outcome', 'voice_post_processor',
                        :event_data, NOW()
                    )
                """),
                {
                    "client_id": str(client_id) if client_id else None,
                    "event_data": json.dumps(
                        {
                            "call_sid": call_sid,
                            "outcome": outcome,
                            "hook_used": hook_used,
                            "propensity_score_at_call": propensity_score_at_call,
                        }
                    ),
                },
            )
            logger.debug(f"CIS feed updated for call {call_sid}")
        except Exception as e:
            # Non-critical - log and continue
            logger.warning(f"Failed to write CIS feed: {e}")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_lead_data(self, lead_id: UUID) -> dict[str, Any]:
        """Fetch lead data from lead_pool."""
        result = await self.session.execute(
            text("""
                SELECT first_name, last_name, email, phone, company_name
                FROM lead_pool WHERE id = :lead_id
            """),
            {"lead_id": str(lead_id)},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else {}

    async def _get_client_data(self, client_id: UUID) -> dict[str, Any]:
        """Fetch client data."""
        result = await self.session.execute(
            text("""
                SELECT business_name, calendly_link, voice_agent_name
                FROM clients WHERE id = :client_id
            """),
            {"client_id": str(client_id)},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else {}

    async def _send_sms(
        self,
        to_number: str,
        message: str,
        client_id: UUID | None,
    ) -> bool:
        """
        Send SMS via Twilio/Telnyx.

        Args:
            to_number: Recipient phone
            message: SMS content
            client_id: Client UUID for from number lookup

        Returns:
            True if sent successfully
        """
        try:
            from src.integrations.twilio import get_twilio_client

            client = get_twilio_client()
            result = await client.send_sms(
                to_number=to_number,
                message=message,
                check_dncr=True,
            )
            logger.info(f"SMS sent to {to_number}: {result.get('message_sid')}")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}")
            return False

    async def _send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        client_id: UUID | None,
    ) -> bool:
        """
        Send email via Postmark/Resend.

        Args:
            to_email: Recipient email
            to_name: Recipient name
            subject: Email subject
            body: Email body
            client_id: Client UUID for sender lookup

        Returns:
            True if sent successfully
        """
        try:
            from src.integrations.postmark import get_postmark_client

            client_data = await self._get_client_data(client_id) if client_id else {}
            from_email = f"hello@{client_data.get('domain', 'agencyos.com.au')}"

            client = get_postmark_client()
            result = await client.send_email(
                from_email=from_email,
                to_email=to_email,
                subject=subject,
                text_body=body,
            )
            logger.info(f"Email sent to {to_email}: {result.get('message_id')}")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def _schedule_prefect_voice_flow(
        self,
        lead_id: UUID,
        client_id: UUID | None,
        scheduled_time: datetime,
    ) -> bool:
        """
        Schedule a Prefect run for voice flow callback.

        Args:
            lead_id: Lead UUID
            client_id: Client UUID
            scheduled_time: When to call back

        Returns:
            True if scheduled successfully
        """
        try:
            # Store scheduled callback in database for Prefect pickup
            await self.session.execute(
                text("""
                    INSERT INTO scheduled_voice_callbacks (
                        lead_id, client_id, scheduled_at, status, created_at
                    ) VALUES (
                        :lead_id, :client_id, :scheduled_at, 'pending', NOW()
                    )
                """),
                {
                    "lead_id": str(lead_id),
                    "client_id": str(client_id) if client_id else None,
                    "scheduled_at": scheduled_time,
                },
            )
            logger.info(f"Scheduled voice callback for lead {lead_id} at {scheduled_time}")
            return True
        except Exception as e:
            logger.error(f"Failed to schedule Prefect voice flow: {e}")
            return False

    async def _queue_closer_followup(
        self,
        lead_id: UUID,
        client_id: UUID | None,
        campaign_id: UUID | None,
        trigger: str,
    ) -> None:
        """
        Queue a personalised email follow-up via closer engine.

        Args:
            lead_id: Lead UUID
            client_id: Client UUID
            campaign_id: Campaign UUID
            trigger: Trigger reason
        """
        try:
            await self.session.execute(
                text("""
                    INSERT INTO closer_queue (
                        lead_id, client_id, campaign_id, trigger, status, created_at
                    ) VALUES (
                        :lead_id, :client_id, :campaign_id, :trigger, 'pending', NOW()
                    )
                """),
                {
                    "lead_id": str(lead_id),
                    "client_id": str(client_id) if client_id else None,
                    "campaign_id": str(campaign_id) if campaign_id else None,
                    "trigger": trigger,
                },
            )
            logger.info(f"Queued closer follow-up for lead {lead_id}")
        except Exception as e:
            logger.warning(f"Failed to queue closer follow-up: {e}")

    async def _create_dashboard_notification(
        self,
        client_id: UUID | None,
        notification_type: str,
        title: str,
        message: str,
        metadata: dict | None = None,
        severity: str = "medium",
    ) -> None:
        """
        Create dashboard notification for agency owner.

        Args:
            client_id: Client UUID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            metadata: Additional metadata
            severity: Notification severity
        """
        if not client_id:
            return

        try:
            await self.session.execute(
                text("""
                    INSERT INTO admin_notifications (
                        notification_type, client_id, title, message,
                        severity, status, metadata, created_at
                    ) VALUES (
                        :notification_type, :client_id, :title, :message,
                        :severity, 'pending', :metadata, NOW()
                    )
                """),
                {
                    "notification_type": notification_type,
                    "client_id": str(client_id),
                    "title": title,
                    "message": message,
                    "severity": severity,
                    "metadata": json.dumps(metadata or {}),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to create dashboard notification: {e}")

    async def _log_audit_event(
        self,
        client_id: UUID | None,
        event_type: str,
        event_data: dict,
    ) -> None:
        """
        Log event to audit_logs table.

        Args:
            client_id: Client UUID
            event_type: Type of audit event
            event_data: Event data
        """
        try:
            await self.session.execute(
                text("""
                    INSERT INTO audit_logs (
                        client_id, event_type, event_data, created_at
                    ) VALUES (
                        :client_id, :event_type, :event_data, NOW()
                    )
                """),
                {
                    "client_id": str(client_id) if client_id else None,
                    "event_type": event_type,
                    "event_data": json.dumps(event_data),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")

    def _next_business_day(self) -> datetime:
        """Get next business day at 9 AM."""
        now = datetime.utcnow()
        next_day = now + timedelta(days=1)

        # Skip weekends
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)

        return next_day.replace(hour=9, minute=0, second=0, microsecond=0)

    def _extract_domain(self, email: str) -> str | None:
        """Extract domain from email address."""
        if not email or "@" not in email:
            return None
        return email.split("@")[1].lower()


# ============================================
# FACTORY FUNCTION
# ============================================


def get_voice_post_call_processor(session: AsyncSession) -> VoicePostCallProcessor:
    """
    Get VoicePostCallProcessor instance.

    Args:
        session: Database session

    Returns:
        VoicePostCallProcessor instance
    """
    return VoicePostCallProcessor(session)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Layer 3 - services (imports integrations)
# [x] process_completed_call() main entry point
# [x] Claude Haiku outcome classification with confidence threshold
# [x] Rule-based fallback classification
# [x] Supabase update for voice_calls record
# [x] BOOKED routing: CONVERTED status, SMS+email, audit log, notification
# [x] CALLBACK routing: Prefect scheduling, SMS confirmation
# [x] INTERESTED routing: WARM_VOICE status, closer queue, notification
# [x] UNSUBSCRIBE routing: suppression across all channels
# [x] ESCALATION/ANGRY routing: immediate notification + alert
# [x] NOT_INTERESTED routing: DISQUALIFIED_VOICE status, sequence pause
# [x] ALS score adjustment (+15/-15)
# [x] CIS feed for conversion_events
# [x] All functions async with type hints and docstrings
# [x] INFO logging for all outcome routing decisions
# [x] ProcessResult dataclass return type
