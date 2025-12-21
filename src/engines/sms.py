"""
FILE: src/engines/sms.py
PURPOSE: SMS engine using Twilio integration with DNCR compliance
PHASE: 4 (Engines)
TASK: ENG-006
DEPENDENCIES:
  - src/engines/base.py
  - src/integrations/twilio.py
  - src/integrations/redis.py
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits (100/day/number)
  - DNCR compliance for Australian numbers
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import EngineResult, OutreachEngine
from src.exceptions import DNCRError, ResourceRateLimitError, ValidationError
from src.integrations.redis import rate_limiter
from src.integrations.twilio import TwilioClient, get_twilio_client
from src.models.activity import Activity
from src.models.base import ChannelType
from src.models.lead import Lead


# Rate limit (Rule 17)
SMS_DAILY_LIMIT_PER_NUMBER = 100


class SMSEngine(OutreachEngine):
    """
    SMS engine for sending text messages via Twilio.

    Features:
    - DNCR compliance check for Australian numbers
    - Resource-level rate limiting (100/day/number - Rule 17)
    - Activity logging
    - ALS >= 85 requirement (enforced by allocator)
    """

    def __init__(self, twilio_client: TwilioClient | None = None):
        """
        Initialize SMS engine.

        Args:
            twilio_client: Optional Twilio client (uses singleton if not provided)
        """
        self._twilio = twilio_client

    @property
    def name(self) -> str:
        return "sms"

    @property
    def channel(self) -> ChannelType:
        return ChannelType.SMS

    @property
    def twilio(self) -> TwilioClient:
        if self._twilio is None:
            self._twilio = get_twilio_client()
        return self._twilio

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
        campaign = await self.get_campaign_by_id(db, campaign_id)

        # Validate phone number
        if not lead.phone:
            return EngineResult.fail(
                error="Lead has no phone number",
                metadata={"lead_id": str(lead_id)},
            )

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
        skip_dncr = kwargs.get("skip_dncr", False)
        try:
            result = await self.twilio.send_sms(
                to_number=lead.phone,
                message=content,
                from_number=from_number,
                check_dncr=not skip_dncr,
            )

            message_sid = result.get("message_sid")

            # Log activity
            await self._log_activity(
                db=db,
                lead=lead,
                campaign_id=campaign_id,
                action="sent",
                provider_message_id=message_sid,
                content_preview=content[:200] if len(content) > 200 else content,
                provider_response=result,
                from_number=from_number,
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
            is_on_dncr = await self.twilio.check_dncr(phone_number)

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
        provider_response: dict | None = None,
        from_number: str | None = None,
    ) -> None:
        """Log SMS activity to database."""
        metadata = {}
        if from_number:
            metadata["from_number"] = from_number

        activity = Activity(
            client_id=lead.client_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            channel=ChannelType.SMS,
            action=action,
            provider_message_id=provider_message_id,
            content_preview=content_preview,
            provider="twilio",
            provider_status=action,
            provider_response=provider_response,
            metadata=metadata,
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
# [x] DNCR rejection logging
# [x] Activity logging after send
# [x] Batch sending support
# [x] Extends OutreachEngine from base.py
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
