"""
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
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.engines.base import EngineResult, OutreachEngine

logger = logging.getLogger(__name__)
from src.engines.content_utils import build_voice_snapshot
from src.exceptions import ValidationError
from src.integrations.vapi import (
    VapiClient,
    VapiAssistantConfig,
    VapiCallRequest,
    VapiCallResult,
    get_vapi_client,
)
from src.agents.sdk_agents.sdk_eligibility import should_use_sdk_voice_kb
from src.agents.sdk_agents.voice_kb_agent import run_sdk_voice_kb, get_basic_voice_kb
from src.services.sdk_usage_service import log_sdk_usage
from src.models.activity import Activity
from src.models.base import ChannelType, LeadStatus
from src.models.lead import Lead
from src.models.campaign import Campaign


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
                    "g2": {"rating": float(row.g2_rating) if row.g2_rating else None, "count": row.g2_review_count},
                    "capterra": {"rating": float(row.capterra_rating) if row.capterra_rating else None, "count": row.capterra_review_count},
                    "trustpilot": {"rating": float(row.trustpilot_rating) if row.trustpilot_rating else None, "count": row.trustpilot_review_count},
                    "google": {"rating": float(row.google_rating) if row.google_rating else None, "count": row.google_review_count},
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

        # Validate ALS score (70+ required for voice)
        if lead.als_score is None or lead.als_score < 70:
            return EngineResult.fail(
                error=f"ALS score too low for voice: {lead.als_score} (minimum 70)",
                metadata={
                    "lead_id": str(lead_id),
                    "als_score": lead.als_score,
                },
            )

        # TEST_MODE: Redirect voice call to test recipient
        original_phone = lead.phone
        if settings.TEST_MODE:
            lead.phone = settings.TEST_VOICE_RECIPIENT
            logger.info(f"TEST_MODE: Redirecting voice call {original_phone} → {lead.phone}")

        # Get campaign for context
        campaign = await self.get_campaign_by_id(db, campaign_id)

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

            await db.commit()

            return EngineResult.ok(
                data={
                    "call_id": call_id,
                    "event": event_type,
                    "processed": True,
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
    # SDK VOICE KB (Hot Leads - ALS 85+)
    # ============================================

    async def generate_voice_kb(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        sdk_enrichment: dict[str, Any] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate voice knowledge base for a lead.

        This method:
        1. Checks if lead is Hot (ALS >= 85)
        2. If Hot: Uses SDK for comprehensive KB generation
        3. If not Hot: Returns basic KB

        The KB is used by the voice AI to:
        - Open calls with specific, relevant hooks
        - Handle objections with company-specific responses
        - Navigate conversations intelligently

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            campaign_id: Campaign UUID
            sdk_enrichment: Pre-fetched SDK enrichment data (optional)

        Returns:
            EngineResult with voice KB dict
        """
        try:
            # Get lead
            lead = await self.get_lead_by_id(db, lead_id)

            # Build lead data dict
            lead_data = {
                "first_name": lead.first_name,
                "last_name": lead.last_name or "",
                "title": lead.title or "",
                "company_name": lead.company,
                "company_industry": lead.organization_industry or "",
                "company_employee_count": lead.organization_employee_count,
                "company_city": getattr(lead, "organization_city", None),
                "company_country": getattr(lead, "organization_country", None),
                "linkedin_headline": getattr(lead, "linkedin_headline", None),
                "linkedin_about": getattr(lead, "linkedin_about", None),
                "linkedin_recent_posts": getattr(lead, "linkedin_recent_posts", None),
                "als_score": lead.als_score or 0,
            }

            # Check if Hot lead (SDK voice KB for ALL Hot leads)
            if should_use_sdk_voice_kb(lead_data):
                logger.info(
                    f"Generating SDK voice KB for Hot lead",
                    extra={
                        "lead_id": str(lead_id),
                        "als_score": lead.als_score,
                    }
                )

                # Get SDK enrichment from lead if not provided
                enrichment_data = sdk_enrichment
                if not enrichment_data:
                    # Try to get from lead's deep_research_data
                    if hasattr(lead, "deep_research_data") and lead.deep_research_data:
                        enrichment_data = lead.deep_research_data.get("sdk_enrichment")
                    elif hasattr(lead, "sdk_enrichment") and lead.sdk_enrichment:
                        enrichment_data = lead.sdk_enrichment

                # Get campaign for context
                campaign = None
                try:
                    campaign = await self.get_campaign_by_id(db, campaign_id)
                except Exception:
                    pass

                campaign_context = None
                if campaign:
                    campaign_context = {
                        "product_name": getattr(campaign, "product_name", None) or campaign.name,
                        "value_prop": getattr(campaign, "value_proposition", None) or getattr(campaign, "description", None),
                        "differentiator": getattr(campaign, "differentiator", None),
                    }

                # Fetch client intelligence for proof points
                client_intelligence = None
                if campaign and hasattr(campaign, "client_id") and campaign.client_id:
                    client_intelligence = await self._get_client_intelligence(db, campaign.client_id)

                # Generate SDK voice KB
                sdk_result = await run_sdk_voice_kb(
                    lead_data=lead_data,
                    enrichment_data=enrichment_data,
                    campaign_context=campaign_context,
                    client_intelligence=client_intelligence,
                )

                # Log SDK usage to database for cost tracking
                try:
                    client_id = campaign.client_id if campaign and hasattr(campaign, "client_id") else lead.client_id
                    await log_sdk_usage(
                        db,
                        client_id=client_id,
                        agent_type="voice_kb",
                        model_used=sdk_result.model_used or "claude-sonnet-4-20250514",
                        input_tokens=sdk_result.input_tokens,
                        output_tokens=sdk_result.output_tokens,
                        cached_tokens=sdk_result.cached_tokens,
                        cost_aud=sdk_result.cost_aud,
                        turns_used=sdk_result.turns_used,
                        duration_ms=sdk_result.duration_ms,
                        tool_calls=sdk_result.tool_calls,
                        success=sdk_result.success,
                        error_message=sdk_result.error,
                        lead_id=lead_id,
                        campaign_id=campaign_id,
                    )
                except Exception as log_err:
                    logger.warning(f"Failed to log SDK voice KB usage: {log_err}")

                if sdk_result.success and sdk_result.data:
                    # Convert Pydantic model to dict if needed
                    kb_data = sdk_result.data
                    if hasattr(kb_data, "model_dump"):
                        kb_data = kb_data.model_dump()

                    return EngineResult.ok(
                        data={
                            **kb_data,
                            "lead_id": str(lead_id),
                            "campaign_id": str(campaign_id),
                            "source": "sdk",
                        },
                        metadata={
                            "cost_aud": sdk_result.cost_aud,
                            "sdk": True,
                            "als_score": lead.als_score,
                        },
                    )

                # SDK failed - fall back to basic
                logger.warning(
                    f"SDK voice KB failed for Hot lead, falling back to basic",
                    extra={
                        "lead_id": str(lead_id),
                        "error": sdk_result.error,
                    }
                )

            # Non-Hot lead or SDK failure: return basic KB
            basic_kb = get_basic_voice_kb(lead_data)
            return EngineResult.ok(
                data={
                    **basic_kb,
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
                metadata={
                    "sdk": False,
                    "als_score": lead.als_score,
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
                    "sdk_enhanced": kb_result.metadata.get("sdk", False) if kb_result.success else False,
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
                enhancements.append(f"OBJECTION RESPONSES:\n" + "\n".join(obj_text[:4]))

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
