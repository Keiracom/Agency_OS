"""
FILE: src/engines/linkedin.py
PURPOSE: LinkedIn engine using HeyReach integration
PHASE: 4 (Engines), modified Phase 16 for Conversion Intelligence
TASK: ENG-007, 16E-003
DEPENDENCIES:
  - src/engines/base.py
  - src/engines/content_utils.py (Phase 16)
  - src/integrations/heyreach.py
  - src/integrations/redis.py
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines (content_utils is utilities, not engine)
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits (17/day/seat)
PHASE 16 CHANGES:
  - Added content_snapshot capture for WHAT Detector learning
  - Tracks touch_number, sequence context, and message_type
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import EngineResult, OutreachEngine
from src.engines.content_utils import build_linkedin_snapshot
from src.exceptions import ResourceRateLimitError, ValidationError
from src.integrations.heyreach import HeyReachClient, get_heyreach_client
from src.integrations.redis import rate_limiter
from src.models.activity import Activity
from src.models.base import ChannelType
from src.models.lead import Lead


# Rate limit (Rule 17)
LINKEDIN_DAILY_LIMIT_PER_SEAT = 17


class LinkedInEngine(OutreachEngine):
    """
    LinkedIn engine for sending connection requests and messages via HeyReach.

    Features:
    - Connection request sending
    - Direct message sending
    - Resource-level rate limiting (17/day/seat - Rule 17)
    - Activity logging
    - Conversation tracking
    """

    def __init__(self, heyreach_client: HeyReachClient | None = None):
        """
        Initialize LinkedIn engine.

        Args:
            heyreach_client: Optional HeyReach client (uses singleton if not provided)
        """
        self._heyreach = heyreach_client

    @property
    def name(self) -> str:
        return "linkedin"

    @property
    def channel(self) -> ChannelType:
        return ChannelType.LINKEDIN

    @property
    def heyreach(self) -> HeyReachClient:
        if self._heyreach is None:
            self._heyreach = get_heyreach_client()
        return self._heyreach

    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs: Any,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn message or connection request.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            content: Message content
            **kwargs: Additional options:
                - seat_id: HeyReach seat ID (required)
                - action: 'connection' or 'message' (default: 'message')

        Returns:
            EngineResult with send result
        """
        # Validate required fields
        seat_id = kwargs.get("seat_id")
        if not seat_id:
            return EngineResult.fail(
                error="HeyReach seat_id is required",
                metadata={"lead_id": str(lead_id)},
            )

        action = kwargs.get("action", "message")
        if action not in ("connection", "message"):
            return EngineResult.fail(
                error="Invalid action. Must be 'connection' or 'message'",
                metadata={"action": action},
            )

        # Get lead
        lead = await self.get_lead_by_id(db, lead_id)
        campaign = await self.get_campaign_by_id(db, campaign_id)

        # Validate LinkedIn URL
        if not lead.linkedin_url:
            return EngineResult.fail(
                error="Lead has no LinkedIn URL",
                metadata={"lead_id": str(lead_id)},
            )

        # Check rate limit (Rule 17)
        try:
            allowed, current_count = await rate_limiter.check_and_increment(
                resource_type="linkedin",
                resource_id=seat_id,
                limit=LINKEDIN_DAILY_LIMIT_PER_SEAT,
            )
        except ResourceRateLimitError as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "seat_id": seat_id,
                    "limit": LINKEDIN_DAILY_LIMIT_PER_SEAT,
                },
            )

        try:
            # Send connection request or message
            if action == "connection":
                result = await self.heyreach.send_connection_request(
                    seat_id=seat_id,
                    linkedin_url=lead.linkedin_url,
                    message=content if content else None,
                )
                activity_action = "connection_sent"
            else:
                result = await self.heyreach.send_message(
                    seat_id=seat_id,
                    linkedin_url=lead.linkedin_url,
                    message=content,
                )
                activity_action = "message_sent"

            # Get message/request ID
            provider_id = result.get("message_id") or result.get("request_id")

            # Log activity with content snapshot (Phase 16)
            await self._log_activity(
                db=db,
                lead=lead,
                campaign_id=campaign_id,
                action=activity_action,
                provider_message_id=provider_id,
                content_preview=content[:200] if len(content) > 200 else content,
                message_content=content,  # Phase 16: Pass full content for snapshot
                message_type="connection" if action == "connection" else "message",
                connection_note=content if action == "connection" else None,
                sequence_step=kwargs.get("sequence_step"),
                sequence_id=kwargs.get("sequence_id"),
                provider_response=result,
                seat_id=seat_id,
            )

            return EngineResult.ok(
                data={
                    "provider_id": provider_id,
                    "linkedin_url": lead.linkedin_url,
                    "seat_id": seat_id,
                    "action": action,
                    "status": result.get("status"),
                    "remaining_quota": LINKEDIN_DAILY_LIMIT_PER_SEAT - current_count,
                },
                metadata={
                    "engine": self.name,
                    "channel": self.channel.value,
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"LinkedIn {action} failed: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                    "seat_id": seat_id,
                    "action": action,
                },
            )

    async def send_connection_request(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        message: str | None = None,
        seat_id: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn connection request.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            message: Optional connection message
            seat_id: HeyReach seat ID

        Returns:
            EngineResult with send result
        """
        return await self.validate_and_send(
            db=db,
            lead_id=lead_id,
            campaign_id=campaign_id,
            content=message or "",
            seat_id=seat_id,
            action="connection",
        )

    async def send_message(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        message: str,
        seat_id: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn direct message.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            message: Message content
            seat_id: HeyReach seat ID

        Returns:
            EngineResult with send result
        """
        return await self.validate_and_send(
            db=db,
            lead_id=lead_id,
            campaign_id=campaign_id,
            content=message,
            seat_id=seat_id,
            action="message",
        )

    async def send_batch(
        self,
        db: AsyncSession,
        actions: list[dict[str, Any]],
    ) -> EngineResult[dict[str, Any]]:
        """
        Send multiple LinkedIn actions (connections or messages).

        Args:
            db: Database session (passed by caller)
            actions: List of action configs with lead_id, campaign_id, content, etc.

        Returns:
            EngineResult with batch send summary
        """
        results = {
            "total": len(actions),
            "sent": 0,
            "failed": 0,
            "rate_limited": 0,
            "actions": [],
        }

        for action_config in actions:
            lead_id = action_config.get("lead_id")
            campaign_id = action_config.get("campaign_id")
            content = action_config.get("content", "")

            if not all([lead_id, campaign_id]):
                results["failed"] += 1
                results["actions"].append({
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
                **action_config,
            )

            if result.success:
                results["sent"] += 1
                results["actions"].append({
                    "lead_id": str(lead_id),
                    "status": "sent",
                    "provider_id": result.data.get("provider_id"),
                    "action": result.data.get("action"),
                })
            else:
                # Check if rate limited
                if "rate limit" in result.error.lower():
                    results["rate_limited"] += 1
                else:
                    results["failed"] += 1

                results["actions"].append({
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

    async def get_seat_status(
        self,
        seat_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get status of a LinkedIn seat (quota, availability).

        Args:
            seat_id: HeyReach seat ID

        Returns:
            EngineResult with seat status
        """
        try:
            # Get current usage from rate limiter
            usage = await rate_limiter.get_usage(
                resource_type="linkedin",
                resource_id=seat_id,
            )

            remaining = max(0, LINKEDIN_DAILY_LIMIT_PER_SEAT - usage)

            return EngineResult.ok(
                data={
                    "seat_id": seat_id,
                    "daily_limit": LINKEDIN_DAILY_LIMIT_PER_SEAT,
                    "daily_used": usage,
                    "remaining": remaining,
                    "can_send": remaining > 0,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to get seat status: {str(e)}",
                metadata={"seat_id": seat_id},
            )

    async def get_new_replies(
        self,
        db: AsyncSession,
        seat_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get new LinkedIn replies for a seat.

        Args:
            db: Database session (passed by caller)
            seat_id: HeyReach seat ID

        Returns:
            EngineResult with new replies
        """
        try:
            replies = await self.heyreach.get_new_replies(seat_id)

            return EngineResult.ok(
                data={
                    "seat_id": seat_id,
                    "reply_count": len(replies),
                    "replies": replies,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to get replies: {str(e)}",
                metadata={"seat_id": seat_id},
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
        message_type: str = "message",
        connection_note: str | None = None,
        sequence_step: int | None = None,
        sequence_id: str | None = None,
        provider_response: dict | None = None,
        seat_id: str | None = None,
    ) -> None:
        """
        Log LinkedIn activity to database.

        Phase 16: Now captures content_snapshot for WHAT Detector learning.
        """
        metadata = {}
        if seat_id:
            metadata["seat_id"] = seat_id

        # Build content snapshot for Conversion Intelligence (Phase 16)
        snapshot = None
        if message_content or connection_note:
            snapshot = build_linkedin_snapshot(
                message=message_content or "",
                lead=lead,
                message_type=message_type,
                connection_note=connection_note,
                touch_number=sequence_step or 1,
                sequence_id=sequence_id,
            )

        activity = Activity(
            client_id=lead.client_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            channel=ChannelType.LINKEDIN,
            action=action,
            provider_message_id=provider_message_id,
            sequence_step=sequence_step,
            content_preview=content_preview,
            content_snapshot=snapshot,  # Phase 16: Store content snapshot
            provider="heyreach",
            provider_status=action,
            provider_response=provider_response,
            metadata=metadata,
            created_at=datetime.utcnow(),
        )

        db.add(activity)
        await db.commit()


# Singleton instance
_linkedin_engine: LinkedInEngine | None = None


def get_linkedin_engine() -> LinkedInEngine:
    """Get or create LinkedIn engine instance."""
    global _linkedin_engine
    if _linkedin_engine is None:
        _linkedin_engine = LinkedInEngine()
    return _linkedin_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete check inherited from BaseEngine
# [x] Resource-level rate limits (17/day/seat - Rule 17)
# [x] Connection request support
# [x] Direct message support
# [x] Activity logging after send
# [x] Batch sending support
# [x] Seat status checking
# [x] New replies retrieval
# [x] Extends OutreachEngine from base.py
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Phase 16: content_snapshot captured for WHAT Detector
# [x] Phase 16: touch_number, sequence_id, and message_type tracked
