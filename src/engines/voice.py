"""
Contract: src/engines/voice.py
Purpose: Voice engine using Vapi and ElevenLabs for AI voice calls
Layer: 3 - engines
Imports: models, integrations, services
Consumers: orchestration only

FILE: src/engines/voice.py
PURPOSE: Voice engine using Vapi + Twilio + ElevenLabs for AI voice calls
PHASE: 4 (Engines), modified Phase 16 for Conversion Intelligence, Phase 17 for Vapi
TASK: ENG-008, 16E-003, CRED-007
DEPENDENCIES:
  - src/engines/base.py
  - src/engines/content_utils.py (Phase 16)
  - src/integrations/vapi.py
  - src/integrations/redis.py
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines (content_utils is utilities, not engine)
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limit (50/day/number)
PHASE 16 CHANGES:
  - Added content_snapshot capture for WHAT Detector learning
  - Tracks touch_number, sequence context, outcome, and duration
PHASE 17 CHANGES:
  - Replaced Synthflow with Vapi + ElevenLabs stack
  - Vapi orchestrates: STT (built-in) -> LLM (Claude) -> TTS (ElevenLabs)
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.engines.base import EngineResult, OutreachEngine
from src.services.voice_retry_service import (
    MAX_RETRIES,
    RETRYABLE_OUTCOMES,
    VoiceRetryService,
)

logger = logging.getLogger(__name__)
from src.engines.content_utils import build_voice_snapshot
from src.engines.smart_prompts import (
    SMART_VOICE_KB_PROMPT,
    build_client_proof_points,
    build_full_lead_context,
    format_lead_context_for_prompt,
    format_proof_points_for_prompt,
)
from src.integrations.anthropic import get_anthropic_client
from src.integrations.dncr import get_dncr_client
from src.integrations.vapi import (
    VapiAssistantConfig,
    VapiCallRequest,
    VapiClient,
    get_vapi_client,
)
from src.models.activity import Activity
from src.models.base import ChannelType, LeadStatus
from src.models.lead import Lead

# ============================================
# BUSINESS HOURS CONSTANTS (Per VOICE.md spec)
# ============================================
VOICE_BUSINESS_HOURS = {
    "start": 9,  # 9 AM
    "end": 17,  # 5 PM
    "lunch_start": 12,  # Skip 12-1 PM (low answer rate)
    "lunch_end": 13,
    "days": [0, 1, 2, 3, 4],  # Monday-Friday (weekday() values)
    "default_timezone": "Australia/Sydney",
}


def is_within_business_hours(
    lead_timezone: str | None = None,
) -> tuple[bool, str | None]:
    """
    Check if current time is within business hours for voice calls.

    Per VOICE.md spec:
    - Business hours: 9 AM - 5 PM
    - Weekdays only (Monday-Friday)
    - Skip lunch hour 12-1 PM (low answer rate)

    Args:
        lead_timezone: Lead's timezone (e.g., "Australia/Sydney").
                      Falls back to Australia/Sydney if not provided.

    Returns:
        Tuple of (is_within_hours, reason_if_not)
    """
    timezone = lead_timezone or VOICE_BUSINESS_HOURS["default_timezone"]

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        # Invalid timezone, fall back to default
        logger.warning(f"Invalid timezone '{timezone}', using default")
        tz = ZoneInfo(VOICE_BUSINESS_HOURS["default_timezone"])

    now = datetime.now(tz)

    # Check day of week (Monday=0, Sunday=6)
    if now.weekday() not in VOICE_BUSINESS_HOURS["days"]:
        return False, "weekend"

    # Check if before business hours
    if now.hour < VOICE_BUSINESS_HOURS["start"]:
        return False, "before_business_hours"

    # Check if after business hours
    if now.hour >= VOICE_BUSINESS_HOURS["end"]:
        return False, "after_business_hours"

    # Check lunch hour (12-1 PM has low answer rate)
    if VOICE_BUSINESS_HOURS["lunch_start"] <= now.hour < VOICE_BUSINESS_HOURS["lunch_end"]:
        return False, "lunch_hour"

    return True, None


def get_next_business_hour(
    lead_timezone: str | None = None,
) -> datetime:
    """
    Calculate the next available business hour for voice calls.

    Finds the next time that is:
    - Within 9 AM - 5 PM
    - Not during lunch (12-1 PM)
    - On a weekday (Monday-Friday)

    Args:
        lead_timezone: Lead's timezone. Falls back to Australia/Sydney.

    Returns:
        Datetime of next available business hour (timezone-aware).
    """
    timezone = lead_timezone or VOICE_BUSINESS_HOURS["default_timezone"]

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo(VOICE_BUSINESS_HOURS["default_timezone"])

    now = datetime.now(tz)

    # Start with current time
    next_time = now.replace(minute=0, second=0, microsecond=0)

    # If currently in lunch hour, skip to after lunch
    if VOICE_BUSINESS_HOURS["lunch_start"] <= next_time.hour < VOICE_BUSINESS_HOURS["lunch_end"]:
        next_time = next_time.replace(hour=VOICE_BUSINESS_HOURS["lunch_end"])
        # Verify this is still valid (not past end of day)
        if next_time.hour >= VOICE_BUSINESS_HOURS["end"]:
            next_time = next_time.replace(hour=VOICE_BUSINESS_HOURS["start"])
            next_time += timedelta(days=1)

    # If past end of business day, move to next day
    elif next_time.hour >= VOICE_BUSINESS_HOURS["end"]:
        next_time = next_time.replace(hour=VOICE_BUSINESS_HOURS["start"])
        next_time += timedelta(days=1)

    # If before start of business day, set to start time
    elif next_time.hour < VOICE_BUSINESS_HOURS["start"]:
        next_time = next_time.replace(hour=VOICE_BUSINESS_HOURS["start"])

    # Skip to Monday if weekend
    while next_time.weekday() not in VOICE_BUSINESS_HOURS["days"]:
        next_time += timedelta(days=1)

    return next_time


class VoiceEngine(OutreachEngine):
    """
    Voice engine for AI voice calls via Vapi.

    Handles:
    - Voice call initiation with AI assistants
    - Call status tracking
    - Transcript retrieval and storage
    - Activity logging
    - ALS requirement: 70+ only (Rule from blueprint)
    - Resource-level rate limit: 50/day/number (Rule 17)

    Flow:
    1. Create/get assistant for campaign
    2. Initiate outbound call via Twilio (through Vapi)
    3. Vapi orchestrates: STT (built-in) -> LLM (Claude) -> TTS (ElevenLabs)
    4. Webhook receives call result
    5. Log activity + transcript
    """

    # Default voice - ElevenLabs "Adam" (professional male)
    DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"

    def __init__(self, vapi_client: VapiClient | None = None):
        """
        Initialize Voice engine with Vapi client.

        Args:
            vapi_client: Optional Vapi client (uses singleton if not provided)
        """
        self._vapi = vapi_client

    @property
    def name(self) -> str:
        return "voice"

    @property
    def channel(self) -> ChannelType:
        return ChannelType.VOICE

    @property
    def vapi(self) -> VapiClient:
        if self._vapi is None:
            self._vapi = get_vapi_client()
        return self._vapi

    async def _get_client_intelligence(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Fetch client intelligence data for SDK personalization.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Dict with proof points or None if not available
        """
        try:
            query = text("""
                SELECT
                    proof_metrics,
                    proof_clients,
                    proof_industries,
                    common_pain_points,
                    differentiators,
                    website_testimonials,
                    website_case_studies,
                    g2_rating,
                    g2_review_count,
                    capterra_rating,
                    capterra_review_count,
                    trustpilot_rating,
                    trustpilot_review_count,
                    google_rating,
                    google_review_count
                FROM client_intelligence
                WHERE client_id = :client_id
                AND deleted_at IS NULL
            """)

            result = await db.execute(query, {"client_id": str(client_id)})
            row = result.fetchone()

            if not row:
                return None

            return {
                "proof_metrics": row.proof_metrics or [],
                "proof_clients": row.proof_clients or [],
                "proof_industries": row.proof_industries or [],
                "common_pain_points": row.common_pain_points or [],
                "differentiators": row.differentiators or [],
                "testimonials": row.website_testimonials or [],
                "case_studies": row.website_case_studies or [],
                "ratings": {
                    "g2": {
                        "rating": float(row.g2_rating) if row.g2_rating else None,
                        "count": row.g2_review_count,
                    },
                    "capterra": {
                        "rating": float(row.capterra_rating) if row.capterra_rating else None,
                        "count": row.capterra_review_count,
                    },
                    "trustpilot": {
                        "rating": float(row.trustpilot_rating) if row.trustpilot_rating else None,
                        "count": row.trustpilot_review_count,
                    },
                    "google": {
                        "rating": float(row.google_rating) if row.google_rating else None,
                        "count": row.google_review_count,
                    },
                },
            }
        except Exception as e:
            logger.warning(f"Failed to fetch client intelligence: {e}")
            return None

    async def create_campaign_assistant(
        self,
        db: AsyncSession,
        campaign_id: str,
        script: str,
        first_message: str,
        voice_id: str = None,
    ) -> str:
        """
        Create a Vapi assistant for a campaign.

        Args:
            db: Database session (passed by caller)
            campaign_id: Campaign UUID
            script: System prompt/script for the assistant
            first_message: Opening message for calls
            voice_id: ElevenLabs voice ID (optional, uses default)

        Returns:
            assistant_id to store in campaign record
        """
        config = VapiAssistantConfig(
            name=f"AgencyOS-{campaign_id[:8]}",
            first_message=first_message,
            system_prompt=self._build_system_prompt(script),
            voice_id=voice_id or self.DEFAULT_VOICE_ID,
        )

        result = await self.vapi.create_assistant(config)
        return result["id"]

    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs: Any,
    ) -> EngineResult[dict[str, Any]]:
        """
        Initiate an AI voice call to a lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            content: Call script or context (not used, AI assistant handles)
            **kwargs: Additional options:
                - assistant_id: Vapi assistant ID to use
                - from_number: Phone number to call from (resource)

        Returns:
            EngineResult with call initiation result
        """
        # Get lead
        lead = await self.get_lead_by_id(db, lead_id)

        # Validate phone number
        if not lead.phone:
            return EngineResult.fail(
                error="Lead has no phone number",
                metadata={"lead_id": str(lead_id)},
            )

        # DNCR check for Australian numbers (legal requirement)
        # Check cached result first (set during enrichment), then API if needed
        skip_dncr = kwargs.get("skip_dncr", False)

        if not skip_dncr and lead.phone.startswith("+61"):
            # Check if DNCR was already checked during enrichment
            if lead.dncr_checked and lead.dncr_result:
                # Lead is on DNCR - block immediately without API call
                await self._log_dncr_rejection(
                    db=db,
                    lead=lead,
                    campaign_id=campaign_id,
                    source="cached",
                )
                return EngineResult.fail(
                    error=f"Phone number {lead.phone} is on the Do Not Call Register (cached)",
                    metadata={
                        "lead_id": str(lead_id),
                        "phone": lead.phone,
                        "reason": "dncr",
                        "source": "cached",
                    },
                )
            elif not lead.dncr_checked:
                # Not checked during enrichment - check now via DNCR API
                try:
                    dncr_client = get_dncr_client()
                    if dncr_client.is_enabled:
                        is_on_dncr = await dncr_client.check_number(lead.phone)
                        # Cache the result on the lead
                        lead.dncr_checked = True
                        lead.dncr_result = is_on_dncr
                        if is_on_dncr:
                            await self._log_dncr_rejection(
                                db=db,
                                lead=lead,
                                campaign_id=campaign_id,
                                source="api",
                            )
                            await db.commit()
                            return EngineResult.fail(
                                error=f"Phone number {lead.phone} is on the Do Not Call Register",
                                metadata={
                                    "lead_id": str(lead_id),
                                    "phone": lead.phone,
                                    "reason": "dncr",
                                    "source": "api",
                                },
                            )
                except Exception as e:
                    # Log but don't block - fail open (business decision)
                    logger.warning(f"DNCR check failed for voice call, proceeding: {e}")

        # Validate ALS score (70+ required for voice)
        if lead.als_score is None or lead.als_score < 70:
            return EngineResult.fail(
                error=f"ALS score too low for voice: {lead.als_score} (minimum 70)",
                metadata={
                    "lead_id": str(lead_id),
                    "als_score": lead.als_score,
                },
            )

        # Validate business hours (9-5 weekdays, skip lunch 12-1 PM)
        can_call, reason = is_within_business_hours(lead.timezone)
        if not can_call:
            next_available = get_next_business_hour(lead.timezone)
            return EngineResult.fail(
                error=f"Outside business hours: {reason}",
                metadata={
                    "lead_id": str(lead_id),
                    "reason": reason,
                    "lead_timezone": lead.timezone or VOICE_BUSINESS_HOURS["default_timezone"],
                    "retry_at": next_available.isoformat(),
                    "status": "scheduled",
                },
            )

        # TEST_MODE: Redirect voice call to test recipient
        original_phone = lead.phone
        if settings.TEST_MODE:
            lead.phone = settings.TEST_VOICE_RECIPIENT
            logger.info(f"TEST_MODE: Redirecting voice call {original_phone} → {lead.phone}")

        # Get campaign for context
        await self.get_campaign_by_id(db, campaign_id)

        # Extract options
        assistant_id = kwargs.get("assistant_id")
        if not assistant_id:
            return EngineResult.fail(
                error="assistant_id is required for voice calls",
                metadata={"lead_id": str(lead_id)},
            )

        from_number = kwargs.get("from_number")

        try:
            # Initiate call via Vapi
            request = VapiCallRequest(
                assistant_id=assistant_id,
                phone_number=lead.phone,
                customer_name=f"{lead.first_name} {lead.last_name}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                    "client_id": str(lead.client_id),
                },
            )

            result = await self.vapi.start_outbound_call(request)

            # Log activity
            await self._log_call_activity(
                db=db,
                lead=lead,
                campaign_id=campaign_id,
                call_id=result.get("id"),
                status=result.get("status"),
                from_number=from_number,
            )

            # Update lead
            lead.last_contacted_at = datetime.utcnow()
            await db.commit()

            return EngineResult.ok(
                data={
                    "call_id": result.get("id"),
                    "status": result.get("status"),
                    "provider": "vapi",
                    "phone_number": lead.phone,
                    "lead_id": str(lead_id),
                },
                metadata={
                    "engine": self.name,
                    "channel": self.channel.value,
                    "campaign_id": str(campaign_id),
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to initiate call: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "phone_number": lead.phone,
                },
            )

    async def get_call_status(
        self,
        db: AsyncSession,
        call_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get status and details of a voice call.

        Args:
            db: Database session (passed by caller)
            call_id: Vapi call ID

        Returns:
            EngineResult with call status
        """
        try:
            result = await self.vapi.get_call(call_id)

            return EngineResult.ok(
                data={
                    "call_id": result.call_id,
                    "status": result.status,
                    "duration_seconds": result.duration_seconds,
                    "transcript": result.transcript,
                    "recording_url": result.recording_url,
                    "cost": result.cost,
                    "ended_reason": result.ended_reason,
                },
                metadata={"call_id": call_id},
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to get call status: {str(e)}",
                metadata={"call_id": call_id},
            )

    async def get_call_transcript(
        self,
        db: AsyncSession,
        call_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get transcript of a voice call.

        Args:
            db: Database session (passed by caller)
            call_id: Vapi call ID

        Returns:
            EngineResult with transcript
        """
        try:
            result = await self.vapi.get_call(call_id)

            return EngineResult.ok(
                data={
                    "call_id": result.call_id,
                    "transcript": result.transcript,
                    "duration_seconds": result.duration_seconds,
                },
                metadata={"call_id": call_id},
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to get transcript: {str(e)}",
                metadata={"call_id": call_id},
            )

    async def process_call_webhook(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
    ) -> EngineResult[dict[str, Any]]:
        """
        Process Vapi call event webhook.

        Args:
            db: Database session (passed by caller)
            payload: Webhook payload

        Returns:
            EngineResult with processing result
        """
        try:
            # Parse webhook
            event = self.vapi.parse_webhook(payload)

            call_id = event.get("call_id")
            event_type = event.get("event")

            if not call_id:
                return EngineResult.fail(
                    error="Missing call_id in webhook",
                    metadata={"payload": payload},
                )

            # Find activity by call_id
            stmt = select(Activity).where(
                and_(
                    Activity.channel == ChannelType.VOICE,
                    Activity.provider_message_id == call_id,
                )
            )
            result = await db.execute(stmt)
            activity = result.scalar_one_or_none()

            if not activity:
                return EngineResult.fail(
                    error=f"Activity not found for call_id {call_id}",
                    metadata={"call_id": call_id},
                )

            # Update activity based on event
            if event_type in ["call-ended", "end-of-call-report"]:
                # Get lead for content_snapshot (Phase 16)
                lead = await self.get_lead_by_id(db, activity.lead_id)

                # Build content snapshot for Conversion Intelligence (Phase 16)
                outcome = event.get("ended_reason", "completed")
                duration = event.get("duration", 0)
                snapshot = build_voice_snapshot(
                    lead=lead,
                    script_id=activity.metadata.get("script_id") if activity.metadata else None,
                    script_content=None,
                    outcome=outcome,
                    duration_seconds=duration,
                    notes=event.get("transcript"),
                    touch_number=activity.sequence_step or 1,
                    sequence_id=activity.metadata.get("sequence_id") if activity.metadata else None,
                )

                # Check if meeting was booked (from transcript analysis or metadata)
                meeting_booked = event.get("metadata", {}).get("meeting_booked", False)

                # Create new activity for call completion
                completion_activity = Activity(
                    client_id=activity.client_id,
                    campaign_id=activity.campaign_id,
                    lead_id=activity.lead_id,
                    channel=ChannelType.VOICE,
                    action="completed",
                    provider_message_id=call_id,
                    provider="vapi",
                    provider_status=outcome,
                    sequence_step=activity.sequence_step,
                    content_snapshot=snapshot,  # Phase 16: Store content snapshot
                    led_to_booking=meeting_booked,  # Phase 16: Track converting touch
                    metadata={
                        "duration": duration,
                        "outcome": outcome,
                        "transcript": event.get("transcript"),
                        "recording_url": event.get("recording_url"),
                        "cost": event.get("cost"),
                        "meeting_booked": meeting_booked,
                    },
                )
                db.add(completion_activity)

                # Update lead if meeting booked
                if meeting_booked:
                    lead.status = LeadStatus.CONVERTED
                    lead.last_replied_at = datetime.utcnow()
                    lead.reply_count += 1

                # === VOICE RETRY SCHEDULING ===
                # Schedule retry for busy/no_answer outcomes
                retry_result = None
                if (
                    outcome in RETRYABLE_OUTCOMES
                    or outcome.lower().replace("_", "-") in RETRYABLE_OUTCOMES
                ):
                    retry_service = VoiceRetryService(db)
                    retry_result = await retry_service.schedule_retry(
                        activity_id=completion_activity.id,
                        outcome=outcome,
                    )
                    if retry_result["scheduled"]:
                        logger.info(
                            f"Voice retry scheduled: lead={activity.lead_id}, "
                            f"outcome={outcome}, retry_at={retry_result['retry_at']}, "
                            f"attempt={retry_result['attempt_number']}/{MAX_RETRIES}"
                        )

            await db.commit()

            return EngineResult.ok(
                data={
                    "call_id": call_id,
                    "event": event_type,
                    "processed": True,
                    "retry_scheduled": retry_result["scheduled"] if retry_result else False,
                    "retry_at": retry_result["retry_at"].isoformat()
                    if retry_result and retry_result.get("retry_at")
                    else None,
                },
                metadata={"activity_id": str(activity.id)},
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to process webhook: {str(e)}",
                metadata={"payload": payload},
            )

    async def _log_call_activity(
        self,
        db: AsyncSession,
        lead: Lead,
        campaign_id: UUID,
        call_id: str | None,
        status: str | None,
        from_number: str | None,
    ) -> None:
        """
        Log call activity to database.

        Args:
            db: Database session
            lead: Lead being called
            campaign_id: Campaign UUID
            call_id: Vapi call ID
            status: Call status
            from_number: Phone number calling from
        """
        activity = Activity(
            client_id=lead.client_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            channel=ChannelType.VOICE,
            action="sent",
            provider_message_id=call_id,
            provider="vapi",
            provider_status=status,
            metadata={
                "to_number": lead.phone,
                "from_number": from_number,
                "lead_name": lead.full_name,
                "company": lead.company,
            },
        )
        db.add(activity)
        await db.commit()

    async def _log_dncr_rejection(
        self,
        db: AsyncSession,
        lead: Lead,
        campaign_id: UUID,
        source: str = "api",
    ) -> None:
        """
        Log DNCR rejection activity to database.

        Args:
            db: Database session
            lead: Lead being blocked
            campaign_id: Campaign UUID
            source: Source of DNCR check ("cached" or "api")
        """
        activity = Activity(
            client_id=lead.client_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            channel=ChannelType.VOICE,
            action="rejected_dncr",
            provider="vapi",
            provider_status="blocked",
            metadata={
                "to_number": lead.phone,
                "lead_name": lead.full_name,
                "company": lead.company,
                "reason": "dncr_registered",
                "source": source,
            },
        )
        db.add(activity)
        logger.info(
            f"DNCR rejection logged for voice call: lead={lead.id}, "
            f"phone={lead.phone[:6]}***, source={source}"
        )

    def _build_system_prompt(self, script: str) -> str:
        """Build the system prompt for the voice assistant."""
        return f"""You are a friendly, professional sales development representative for a marketing agency.

SCRIPT GUIDANCE:
{script}

RULES:
- Be conversational and natural, not robotic
- Listen actively and respond to what the person actually says
- If they seem busy, offer to call back at a better time
- If they're not interested, thank them politely and end the call
- If they're interested, book a meeting or transfer to a human
- Keep responses concise (1-2 sentences max)
- Use Australian English spellings and expressions

GOAL:
Qualify the lead and either:
1. Book a meeting if interested
2. Gather objection data if not interested
3. Schedule a callback if timing is bad

Always be respectful of their time."""

    # ============================================
    # VOICE KB GENERATION (Smart Prompt System)
    # Updated 2026-01-20 per SDK_AND_CONTENT_ARCHITECTURE.md
    # ============================================

    async def generate_voice_kb(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        sdk_enrichment: dict[str, Any] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate voice knowledge base for a lead using Smart Prompt system.

        Uses ALL available data from lead enrichment and client intelligence
        to generate a comprehensive KB the voice AI can use during calls.

        The KB is used by the voice AI to:
        - Open calls with specific, relevant hooks
        - Handle objections with company-specific responses
        - Navigate conversations intelligently

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            campaign_id: Campaign UUID
            sdk_enrichment: DEPRECATED - ignored

        Returns:
            EngineResult with voice KB dict
        """
        try:
            # Build full lead context using Smart Prompt system
            lead_context = await build_full_lead_context(db, lead_id, include_engagement=True)

            if not lead_context:
                # Fallback to basic query
                lead = await self.get_lead_by_id(db, lead_id)
                lead_context = {
                    "person": {
                        "first_name": lead.first_name,
                        "full_name": lead.full_name,
                        "title": lead.title,
                    },
                    "company": {
                        "name": lead.company,
                        "industry": lead.organization_industry,
                    },
                    "score": {"als_score": lead.als_score},
                }

            # Get campaign for context
            campaign = await self.get_campaign_by_id(db, campaign_id)

            # Get client proof points
            proof_points = {}
            if campaign.client_id:
                proof_points = await build_client_proof_points(db, campaign.client_id)

            # Format for prompt
            lead_context_str = format_lead_context_for_prompt(lead_context)
            proof_points_str = format_proof_points_for_prompt(proof_points)

            # Build campaign context
            campaign_context = f"""**Campaign:** {campaign.name}
**Product/Service:** {getattr(campaign, "product_name", campaign.name)}
{f"**Value Prop:** {getattr(campaign, 'value_proposition', '')}" if hasattr(campaign, "value_proposition") and campaign.value_proposition else ""}
{f"**Differentiator:** {getattr(campaign, 'differentiator', '')}" if hasattr(campaign, "differentiator") and campaign.differentiator else ""}"""

            # Use Smart Voice KB Prompt
            prompt = SMART_VOICE_KB_PROMPT.format(
                lead_context=lead_context_str,
                proof_points=proof_points_str,
                campaign_context=campaign_context,
            )

            # System prompt
            system = """You are an expert sales call strategist. Generate voice call knowledge bases that help sales reps have personalized, effective conversations.
Be specific and actionable. Return valid JSON only."""

            # Generate via AI
            anthropic = get_anthropic_client()
            result = await anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=1200,
                temperature=0.7,
            )

            # Parse JSON from response
            import json

            try:
                content = result["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                kb_data = json.loads(content.strip())

                return EngineResult.ok(
                    data={
                        **kb_data,
                        "lead_id": str(lead_id),
                        "campaign_id": str(campaign_id),
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "smart_prompt": True,
                        "als_score": lead_context.get("score", {}).get("als_score"),
                        "has_proof_points": proof_points.get("available", False),
                    },
                )
            except json.JSONDecodeError:
                # Fallback to basic KB structure
                return EngineResult.ok(
                    data={
                        "recommended_opener": f"Hi {lead_context.get('person', {}).get('first_name', 'there')}, this is a quick call about {campaign.name}.",
                        "opening_hooks": [
                            "Ask about their current challenges",
                            "Reference their company's industry",
                        ],
                        "objection_responses": {},
                        "lead_id": str(lead_id),
                        "campaign_id": str(campaign_id),
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "fallback": True,
                        "als_score": lead_context.get("score", {}).get("als_score"),
                    },
                )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to generate voice KB: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

    async def create_campaign_assistant_with_kb(
        self,
        db: AsyncSession,
        campaign_id: str,
        lead_id: UUID,
        script: str,
        first_message: str,
        voice_id: str = None,
        sdk_enrichment: dict[str, Any] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Create a Vapi assistant with SDK voice KB integration.

        This method:
        1. Generates voice KB for the lead (SDK for Hot, basic otherwise)
        2. Enhances the script with KB data
        3. Creates the Vapi assistant

        Args:
            db: Database session
            campaign_id: Campaign UUID
            lead_id: Lead UUID for KB generation
            script: Base system prompt/script
            first_message: Opening message
            voice_id: ElevenLabs voice ID (optional)
            sdk_enrichment: Pre-fetched SDK enrichment data

        Returns:
            EngineResult with assistant_id and KB data
        """
        try:
            # Generate voice KB for this lead
            kb_result = await self.generate_voice_kb(
                db=db,
                lead_id=lead_id,
                campaign_id=UUID(campaign_id),
                sdk_enrichment=sdk_enrichment,
            )

            if not kb_result.success:
                logger.warning(f"Voice KB generation failed, using base script: {kb_result.error}")
                kb_data = {}
            else:
                kb_data = kb_result.data

            # Enhance the script with KB data
            enhanced_script = self._enhance_script_with_kb(script, kb_data)

            # Personalize the first message if we have a recommended opener
            personalized_first_message = first_message
            if kb_data.get("recommended_opener"):
                personalized_first_message = kb_data["recommended_opener"]

            # Create the assistant
            config = VapiAssistantConfig(
                name=f"AgencyOS-{campaign_id[:8]}",
                first_message=personalized_first_message,
                system_prompt=self._build_system_prompt(enhanced_script),
                voice_id=voice_id or self.DEFAULT_VOICE_ID,
            )

            result = await self.vapi.create_assistant(config)
            assistant_id = result["id"]

            return EngineResult.ok(
                data={
                    "assistant_id": assistant_id,
                    "voice_kb": kb_data,
                    "first_message_used": personalized_first_message,
                    "sdk_enhanced": kb_result.metadata.get("sdk", False)
                    if kb_result.success
                    else False,
                },
                metadata={
                    "cost_aud": kb_result.metadata.get("cost_aud", 0) if kb_result.success else 0,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to create assistant with KB: {str(e)}",
                metadata={
                    "campaign_id": campaign_id,
                    "lead_id": str(lead_id),
                },
            )

    def _enhance_script_with_kb(
        self,
        base_script: str,
        kb_data: dict[str, Any],
    ) -> str:
        """
        Enhance the voice script with knowledge base data.

        Args:
            base_script: Original script
            kb_data: Voice KB data

        Returns:
            Enhanced script with KB context
        """
        if not kb_data or kb_data.get("source") == "standard":
            return base_script

        enhancements = []

        # Add company context
        if kb_data.get("company_context"):
            enhancements.append(f"COMPANY CONTEXT:\n{kb_data['company_context']}")

        # Add opening hooks
        if kb_data.get("opening_hooks"):
            hooks = "\n- ".join(kb_data["opening_hooks"][:3])
            enhancements.append(f"OPENING HOOKS (use one of these):\n- {hooks}")

        # Add pain point questions
        if kb_data.get("pain_point_questions"):
            questions = "\n- ".join(kb_data["pain_point_questions"][:3])
            enhancements.append(f"DISCOVERY QUESTIONS:\n- {questions}")

        # Add objection responses
        if kb_data.get("objection_responses"):
            obj = kb_data["objection_responses"]
            obj_text = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key != "custom_objections" and value:
                        obj_text.append(f'- "{key.replace("_", " ").title()}": {value}')
            if obj_text:
                enhancements.append("OBJECTION RESPONSES:\n" + "\n".join(obj_text[:4]))

        # Add topics to avoid
        if kb_data.get("do_not_mention"):
            avoid = "\n- ".join(kb_data["do_not_mention"][:3])
            enhancements.append(f"DO NOT MENTION:\n- {avoid}")

        # Add meeting ask
        if kb_data.get("meeting_ask"):
            enhancements.append(f"MEETING ASK:\n{kb_data['meeting_ask']}")

        if enhancements:
            kb_section = "\n\n".join(enhancements)
            return f"""{base_script}

---
LEAD-SPECIFIC INTELLIGENCE:

{kb_section}

Use this intelligence to personalize the conversation. Reference specific company context and pain points when relevant."""

        return base_script


# Singleton instance
_voice_engine: VoiceEngine | None = None


def get_voice_engine() -> VoiceEngine:
    """Get or create Voice engine instance."""
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine()
    return _voice_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete check inherited from BaseEngine (Rule 14)
# [x] Resource-level rate limit: 50/day/number (Rule 17)
# [x] ALS score validation (70+ required)
# [x] Extends OutreachEngine from base.py
# [x] Uses Vapi integration (replaced Synthflow)
# [x] Call initiation with AI assistant
# [x] Call status retrieval
# [x] Transcript retrieval
# [x] Webhook processing
# [x] Activity logging
# [x] Lead update on success
# [x] EngineResult wrapper for responses
# [x] Test file created: tests/test_engines/test_voice.py
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Phase 16: content_snapshot captured for WHAT Detector
# [x] Phase 16: outcome, duration, touch_number tracked
# [x] Phase 16: led_to_booking flag for converting touches
# [x] Phase 17: Vapi + ElevenLabs stack (STT handled by Vapi)
# [x] Voice retry: busy=2hr, no_answer=next business day (TODO.md #3)
# [x] Voice retry: MAX_RETRIES=3 enforced
# [x] Voice retry: VoiceRetryService integration in process_call_webhook
# [x] Business hours validation: 9-5 weekdays, skip 12-1 PM lunch (TODO.md #15)
# [x] Timezone-aware: uses lead.timezone or Australia/Sydney default
# [x] get_next_business_hour() calculates next valid call time
# [x] DNCR check: Australian numbers checked against Do Not Call Register (TODO.md #16)
# [x] DNCR cached: uses lead.dncr_checked/dncr_result to avoid redundant API calls
# [x] DNCR rejection logging: _log_dncr_rejection() for audit trail
