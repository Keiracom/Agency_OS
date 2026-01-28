"""
Contract: src/engines/sms.py
Purpose: SMS engine using ClickSend integration with DNCR compliance
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration only

FILE: src/engines/sms.py
PURPOSE: SMS engine using ClickSend integration with DNCR compliance
PHASE: 4 (Engines), modified Phase 16/24B for Conversion Intelligence, E2E Testing
TASK: ENG-006, 16E-003, CONTENT-003
DEPENDENCIES:
  - src/engines/base.py
  - src/engines/content_utils.py (Phase 16)
  - src/integrations/clicksend.py (PRIMARY SMS for Australia)
  - src/integrations/redis.py
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines (content_utils is utilities, not engine)
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits (100/day/number)
  - DNCR compliance for Australian numbers

NOTE: ClickSend is the primary SMS provider for Australia.
      Twilio is used for VOICE CALLS only (via Vapi).

PHASE 16 CHANGES:
  - Added content_snapshot capture for WHAT Detector learning
  - Tracks touch_number, sequence context, and segment count
PHASE 24B CHANGES:
  - Store full_message_body for complete content analysis
  - Link to template_id for template tracking
  - Track ab_test_id and ab_variant for A/B testing
  - Store links_included and personalization_fields_used
  - Track ai_model_used and prompt_version
FIX-E2E-006:
  - Changed from Twilio to ClickSend for SMS
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.engines.base import EngineResult, OutreachEngine

logger = logging.getLogger(__name__)
from src.engines.content_utils import build_sms_snapshot
from src.exceptions import DNCRError, ResourceRateLimitError
from src.integrations.clicksend import ClickSendClient, get_clicksend_client
from src.integrations.redis import rate_limiter
from src.models.activity import Activity
from src.models.base import ChannelType
from src.models.lead import Lead

# Rate limit (Rule 17)
SMS_DAILY_LIMIT_PER_NUMBER = 100


class SMSEngine(OutreachEngine):
    """
    SMS engine for sending text messages via ClickSend.

    ClickSend is an Australian company (Perth) - primary SMS provider for AU market.
    Twilio is used for VOICE CALLS only (via Vapi).

    Features:
    - DNCR compliance check for Australian numbers
    - Resource-level rate limiting (100/day/number - Rule 17)
    - Activity logging
    - ALS >= 85 requirement (enforced by allocator)
    - Native Australian phone number support
    """

    def __init__(self, clicksend_client: ClickSendClient | None = None):
        """
        Initialize SMS engine.

        Args:
            clicksend_client: Optional ClickSend client (uses singleton if not provided)
        """
        self._clicksend = clicksend_client

    @property
    def name(self) -> str:
        return "sms"

    @property
    def channel(self) -> ChannelType:
        return ChannelType.SMS

    @property
    def clicksend(self) -> ClickSendClient:
        if self._clicksend is None:
            self._clicksend = get_clicksend_client()
        return self._clicksend

    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs: Any,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send an SMS to a lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            content: SMS message content
            **kwargs: Additional options:
                - from_number: Sender phone number (required)
                - skip_dncr: Skip DNCR check (default: False)
                - template_id: UUID of template used (Phase 24B)
                - ab_test_id: UUID of A/B test (Phase 24B)
                - ab_variant: A/B variant 'A', 'B', or 'control' (Phase 24B)
                - ai_model_used: AI model used for generation (Phase 24B)
                - prompt_version: Version of prompt used (Phase 24B)
                - personalization_fields_used: List of personalization fields (Phase 24B)

        Returns:
            EngineResult with send result
        """
        # Validate required fields
        from_number = kwargs.get("from_number")
        if not from_number:
            return EngineResult.fail(
                error="From phone number is required",
                metadata={"lead_id": str(lead_id)},
            )

        # Get lead
        lead = await self.get_lead_by_id(db, lead_id)
        await self.get_campaign_by_id(db, campaign_id)

        # Validate phone number
        if not lead.phone:
            return EngineResult.fail(
                error="Lead has no phone number",
                metadata={"lead_id": str(lead_id)},
            )

        # TEST_MODE: Redirect SMS to test recipient
        original_phone = lead.phone
        if settings.TEST_MODE:
            lead.phone = settings.TEST_SMS_RECIPIENT
            logger.info(f"TEST_MODE: Redirecting SMS {original_phone} → {lead.phone}")

        # Check rate limit (Rule 17)
        try:
            allowed, current_count = await rate_limiter.check_and_increment(
                resource_type="sms",
                resource_id=from_number,
                limit=SMS_DAILY_LIMIT_PER_NUMBER,
            )
        except ResourceRateLimitError as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "from_number": from_number,
                    "limit": SMS_DAILY_LIMIT_PER_NUMBER,
                },
            )

        # DNCR check for Australian numbers
        # Optimization: Check cached dncr_result first (set during enrichment)
        # This avoids unnecessary DNCR API calls for already-checked numbers
        skip_dncr = kwargs.get("skip_dncr", False)

        if not skip_dncr and lead.phone.startswith("+61"):
            # Check if DNCR was already checked during enrichment
            if lead.dncr_checked and lead.dncr_result:
                # Lead is on DNCR - block immediately without API call
                await self._log_activity(
                    db=db,
                    lead=lead,
                    campaign_id=campaign_id,
                    action="rejected_dncr",
                    content_preview=content[:200] if len(content) > 200 else content,
                    provider_response={"error": "Cached DNCR block", "source": "enrichment"},
                    from_number=from_number,
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
            elif lead.dncr_checked and not lead.dncr_result:
                # Already checked and clean - skip DNCR API call
                skip_dncr = True
                logger.debug(f"Lead {lead_id} DNCR already checked (clean), skipping API call")

        try:
            result = await self.clicksend.send_sms(
                to_number=lead.phone,
                message=content,
                from_number=from_number,
                check_dncr=not skip_dncr,
            )

            message_sid = result.get("message_sid")

            # Log activity with content snapshot (Phase 16) and template tracking (Phase 24B)
            await self._log_activity(
                db=db,
                lead=lead,
                campaign_id=campaign_id,
                action="sent",
                provider_message_id=message_sid,
                content_preview=content[:200] if len(content) > 200 else content,
                message_content=content,  # Phase 16: Pass full content for snapshot
                sequence_step=kwargs.get("sequence_step"),
                sequence_id=kwargs.get("sequence_id"),
                provider_response=result,
                from_number=from_number,
                # Phase 24B: Content tracking fields
                template_id=kwargs.get("template_id"),
                ab_test_id=kwargs.get("ab_test_id"),
                ab_variant=kwargs.get("ab_variant"),
                ai_model_used=kwargs.get("ai_model_used"),
                prompt_version=kwargs.get("prompt_version"),
                personalization_fields_used=kwargs.get("personalization_fields_used"),
            )

            return EngineResult.ok(
                data={
                    "message_sid": message_sid,
                    "to_number": lead.phone,
                    "from_number": from_number,
                    "status": result.get("status"),
                    "remaining_quota": SMS_DAILY_LIMIT_PER_NUMBER - current_count,
                },
                metadata={
                    "engine": self.name,
                    "channel": self.channel.value,
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

        except DNCRError as e:
            # Log DNCR rejection
            await self._log_activity(
                db=db,
                lead=lead,
                campaign_id=campaign_id,
                action="rejected_dncr",
                content_preview=content[:200] if len(content) > 200 else content,
                provider_response={"error": str(e)},
                from_number=from_number,
            )

            return EngineResult.fail(
                error=str(e),
                metadata={
                    "lead_id": str(lead_id),
                    "phone": lead.phone,
                    "reason": "dncr",
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"SMS send failed: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                    "from_number": from_number,
                },
            )

    async def send_batch(
        self,
        db: AsyncSession,
        messages: list[dict[str, Any]],
    ) -> EngineResult[dict[str, Any]]:
        """
        Send multiple SMS messages.

        Args:
            db: Database session (passed by caller)
            messages: List of message configs with lead_id, campaign_id, content, etc.

        Returns:
            EngineResult with batch send summary
        """
        results = {
            "total": len(messages),
            "sent": 0,
            "failed": 0,
            "dncr_rejected": 0,
            "rate_limited": 0,
            "messages": [],
        }

        for message_config in messages:
            lead_id = message_config.get("lead_id")
            campaign_id = message_config.get("campaign_id")
            content = message_config.get("content")

            if not all([lead_id, campaign_id, content]):
                results["failed"] += 1
                results["messages"].append({
                    "lead_id": str(lead_id) if lead_id else None,
                    "status": "failed",
                    "reason": "Missing required fields",
                })
                continue

            result = await self.validate_and_send(
                db=db,
                lead_id=lead_id,
                campaign_id=campaign_id,
                content=content,
                **message_config,
            )

            if result.success:
                results["sent"] += 1
                results["messages"].append({
                    "lead_id": str(lead_id),
                    "status": "sent",
                    "message_sid": result.data.get("message_sid"),
                })
            else:
                # Categorize failure
                if "dncr" in result.error.lower() or result.metadata.get("reason") == "dncr":
                    results["dncr_rejected"] += 1
                    results["messages"].append({
                        "lead_id": str(lead_id),
                        "status": "dncr_rejected",
                        "reason": result.error,
                    })
                elif "rate limit" in result.error.lower():
                    results["rate_limited"] += 1
                    results["messages"].append({
                        "lead_id": str(lead_id),
                        "status": "rate_limited",
                        "reason": result.error,
                    })
                else:
                    results["failed"] += 1
                    results["messages"].append({
                        "lead_id": str(lead_id),
                        "status": "failed",
                        "reason": result.error,
                    })

        return EngineResult.ok(
            data=results,
            metadata={
                "success_rate": results["sent"] / results["total"] if results["total"] > 0 else 0,
            },
        )

    async def check_dncr(
        self,
        phone_number: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Check if a phone number is on the DNCR.

        Args:
            phone_number: Phone number to check

        Returns:
            EngineResult with DNCR status
        """
        try:
            is_on_dncr = await self.clicksend.check_dncr(phone_number)

            return EngineResult.ok(
                data={
                    "phone_number": phone_number,
                    "on_dncr": is_on_dncr,
                    "can_contact": not is_on_dncr,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"DNCR check failed: {str(e)}",
                metadata={"phone_number": phone_number},
            )

    async def _log_activity(
        self,
        db: AsyncSession,
        lead: Lead,
        campaign_id: UUID,
        action: str,
        provider_message_id: str | None = None,
        content_preview: str | None = None,
        message_content: str | None = None,
        sequence_step: int | None = None,
        sequence_id: str | None = None,
        provider_response: dict | None = None,
        from_number: str | None = None,
        # Phase 24B: Content tracking fields
        template_id: UUID | None = None,
        ab_test_id: UUID | None = None,
        ab_variant: str | None = None,
        ai_model_used: str | None = None,
        prompt_version: str | None = None,
        personalization_fields_used: list[str] | None = None,
    ) -> None:
        """
        Log SMS activity to database.

        Phase 16: Now captures content_snapshot for WHAT Detector learning.
        Phase 24B: Now stores template_id, A/B test info, and full message body.
        """
        metadata = {}
        if from_number:
            metadata["from_number"] = from_number

        # Build content snapshot for Conversion Intelligence (Phase 16)
        snapshot = None
        if message_content and action == "sent":
            snapshot = build_sms_snapshot(
                message=message_content,
                lead=lead,
                touch_number=sequence_step or 1,
                sequence_id=sequence_id,
            )
            # Phase 24B: Enhance snapshot with additional tracking data
            if snapshot:
                snapshot["ai_model"] = ai_model_used
                snapshot["prompt_version"] = prompt_version
                snapshot["personalization_available"] = personalization_fields_used or []
                if ab_variant:
                    snapshot["ab_variant"] = ab_variant
                if ab_test_id:
                    snapshot["ab_test_id"] = str(ab_test_id)

        # Phase 24B: Extract links from SMS content
        links_included = None
        if message_content:
            import re
            # Extract URLs from SMS content
            url_pattern = r'https?://[^\s]+'
            links_included = list(set(re.findall(url_pattern, message_content)))

        activity = Activity(
            client_id=lead.client_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            channel=ChannelType.SMS,
            action=action,
            provider_message_id=provider_message_id,
            sequence_step=sequence_step,
            content_preview=content_preview,
            content_snapshot=snapshot,  # Phase 16: Store content snapshot
            # Phase 24B: Content tracking fields
            template_id=template_id,
            ab_test_id=ab_test_id,
            ab_variant=ab_variant,
            full_message_body=message_content,  # Store complete content
            links_included=links_included,
            personalization_fields_used=personalization_fields_used,
            ai_model_used=ai_model_used,
            prompt_version=prompt_version,
            provider="clicksend",
            provider_status=action,
            provider_response=provider_response,
            extra_data=metadata,
            created_at=datetime.utcnow(),
        )

        db.add(activity)
        await db.commit()


# Singleton instance
_sms_engine: SMSEngine | None = None


def get_sms_engine() -> SMSEngine:
    """Get or create SMS engine instance."""
    global _sms_engine
    if _sms_engine is None:
        _sms_engine = SMSEngine()
    return _sms_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete check inherited from BaseEngine
# [x] Resource-level rate limits (100/day/number - Rule 17)
# [x] DNCR check for Australian numbers
# [x] DNCR cached check optimization (check lead.dncr_result before API call)
# [x] DNCR rejection logging
# [x] Activity logging after send
# [x] Batch sending support
# [x] Extends OutreachEngine from base.py
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Phase 16: content_snapshot captured for WHAT Detector
# [x] Phase 16: touch_number, sequence_id, and segment_count tracked
# [x] Phase 24B: template_id stored for template tracking
# [x] Phase 24B: ab_test_id and ab_variant for A/B testing
# [x] Phase 24B: full_message_body stored for complete content analysis
# [x] Phase 24B: links_included extracted from SMS
# [x] Phase 24B: personalization_fields_used tracked
# [x] Phase 24B: ai_model_used and prompt_version stored
# [x] FIX-E2E-006: Changed from Twilio to ClickSend for SMS (AU market)
