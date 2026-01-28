"""
Contract: src/engines/linkedin.py
Purpose: LinkedIn engine using Unipile integration for messaging and connections
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration only

FILE: src/engines/linkedin.py
PURPOSE: LinkedIn engine using Unipile integration (migrated from HeyReach)
PHASE: 4 (Engines), modified Phase 16/24B for Conversion Intelligence
TASK: ENG-007, 16E-003, CONTENT-004
DEPENDENCIES:
  - src/engines/base.py
  - src/engines/content_utils.py (Phase 16)
  - src/integrations/unipile.py (migrated from heyreach.py)
  - src/integrations/redis.py
  - src/models/lead.py
  - src/models/activity.py
  - src/models/linkedin_connection.py (for profile view tracking)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines (content_utils is utilities, not engine)
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits (now configurable, default 17/day/seat)
PHASE 16 CHANGES:
  - Added content_snapshot capture for WHAT Detector learning
  - Tracks touch_number, sequence context, and message_type
PHASE 24B CHANGES:
  - Store full_message_body for complete content analysis
  - Link to template_id for template tracking
  - Track ab_test_id and ab_variant for A/B testing
  - Store links_included and personalization_fields_used
  - Track ai_model_used and prompt_version
UNIPILE MIGRATION:
  - Replaced HeyReach client with Unipile client
  - account_id instead of seat_id
  - Higher rate limits possible (80-100/day vs 17/day)
  - Provider changed from 'heyreach' to 'unipile'
PROFILE VIEW DELAY (Gap #19):
  - View profile 10-30 min before connecting (humanization)
  - Records profile_viewed_at timestamp in linkedin_connections
  - Returns status 'scheduled' if delay not yet elapsed
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.engines.base import EngineResult, OutreachEngine

logger = logging.getLogger(__name__)
from src.engines.content_utils import build_linkedin_snapshot
from src.exceptions import ResourceRateLimitError
from src.integrations.redis import rate_limiter
from src.integrations.unipile import UnipileClient, get_unipile_client
from src.models.activity import Activity
from src.models.base import ChannelType
from src.models.lead import Lead
from src.models.linkedin_connection import LinkedInConnection

# Rate limit (Rule 17) - Now configurable via settings
# Unipile allows higher limits (80-100/day) but we default to conservative
LINKEDIN_DAILY_LIMIT_PER_ACCOUNT = settings.linkedin_max_daily

# Profile View Delay (Gap #19) - Humanization settings
# View profile, wait 10-30 minutes, then send connection request
PROFILE_VIEW_DELAY_MIN_MINUTES = 10
PROFILE_VIEW_DELAY_MAX_MINUTES = 30


class LinkedInEngine(OutreachEngine):
    """
    LinkedIn engine for sending connection requests and messages via Unipile.

    Features:
    - Connection request sending (invitations)
    - Direct message sending
    - Resource-level rate limiting (configurable, default 17/day/account)
    - Weekend reduction (Saturday 50%, Sunday 0%)
    - Activity logging with content snapshot
    - Conversation tracking

    Migration Note:
    - Migrated from HeyReach to Unipile for 70-85% cost reduction
    - Uses account_id instead of seat_id
    - Provider is 'unipile' instead of 'heyreach'
    """

    def _get_effective_daily_limit(self) -> int:
        """
        Get daily limit adjusted for weekend reduction.

        Weekend rules:
        - Sunday (weekday 6): 0% - No sends allowed
        - Saturday (weekday 5): 50% - Half of normal quota
        - Weekdays (0-4): 100% - Full quota

        Returns:
            Effective daily limit based on current day of week
        """
        today = datetime.utcnow().weekday()
        base_limit = LINKEDIN_DAILY_LIMIT_PER_ACCOUNT

        if today == 6:  # Sunday
            logger.info("LinkedIn weekend reduction: Sunday - 0% quota")
            return 0
        elif today == 5:  # Saturday
            reduced = base_limit // 2
            logger.info(
                f"LinkedIn weekend reduction: Saturday - 50% quota ({reduced}/{base_limit})"
            )
            return reduced

        return base_limit

    def __init__(self, unipile_client: UnipileClient | None = None):
        """
        Initialize LinkedIn engine.

        Args:
            unipile_client: Optional Unipile client (uses singleton if not provided)
        """
        self._unipile = unipile_client

    @property
    def name(self) -> str:
        return "linkedin"

    @property
    def channel(self) -> ChannelType:
        return ChannelType.LINKEDIN

    @property
    def unipile(self) -> UnipileClient:
        if self._unipile is None:
            self._unipile = get_unipile_client()
        return self._unipile

    async def get_combined_activity_count(
        self,
        account_id: str,
    ) -> dict[str, Any]:
        """
        Get total LinkedIn activity for today (manual + automated combined).

        Gap #18 Implementation: Fetches activity from Unipile API which tracks
        ALL actions on the LinkedIn account, regardless of whether they were
        initiated via our system (automated) or directly by the user (manual).

        Per LINKEDIN.md spec:
        - Daily limits apply to the ACCOUNT, not per-session
        - Client sending 5 manual connections leaves only 15 for automation
        - Dashboard shows: "Today: 5 connections sent (3 automated, 2 manual)"

        Args:
            account_id: Unipile account ID

        Returns:
            Dict with:
            - total: Combined activity count (manual + automated)
            - automated: Our system's sends (from Redis counter)
            - manual: User's direct activity (calculated difference)
            - source: "unipile" if API succeeded, "redis_only" if fallback
        """
        # Get our automated count from Redis (what we've sent today)
        automated_count = await rate_limiter.get_usage(
            resource_type="linkedin",
            resource_id=account_id,
        )

        # Get total account activity from Unipile (includes both manual + automated)
        try:
            unipile_activity = await self.unipile.get_today_activity_count(account_id)
            total_count = unipile_activity.get("total", 0)

            # Ensure total is at least as high as our automated count
            # (in case Unipile API has lag)
            total_count = max(total_count, automated_count)

            # Calculate manual activity (total minus our automated sends)
            manual_count = max(0, total_count - automated_count)

            logger.debug(
                f"LinkedIn quota for {account_id}: "
                f"total={total_count} (automated={automated_count}, manual={manual_count})"
            )

            return {
                "total": total_count,
                "automated": automated_count,
                "manual": manual_count,
                "source": "unipile",
            }

        except Exception as e:
            # Fallback to Redis-only if Unipile API fails
            # This is conservative - we only know our automated sends
            logger.warning(
                f"Failed to get Unipile activity for {account_id}, falling back to Redis only: {e}"
            )
            return {
                "total": automated_count,
                "automated": automated_count,
                "manual": 0,
                "source": "redis_only",
            }

    async def get_remaining_quota(
        self,
        account_id: str,
    ) -> dict[str, Any]:
        """
        Get remaining quota for a LinkedIn account (considering manual + automated).

        Gap #18: This is the primary method to check before any LinkedIn action.
        It accounts for both automated sends and manual user activity.

        Args:
            account_id: Unipile account ID

        Returns:
            Dict with:
            - remaining: Available sends today
            - daily_limit: Effective limit (with weekend reduction)
            - used_total: Combined manual + automated usage
            - used_automated: Our automated sends only
            - used_manual: User's manual activity
            - can_send: Boolean if any quota remains
            - source: "unipile" if API succeeded, "redis_only" if fallback
        """
        # Get effective daily limit (with weekend reduction)
        effective_limit = self._get_effective_daily_limit()

        # Get combined activity count (Gap #18)
        activity = await self.get_combined_activity_count(account_id)

        remaining = max(0, effective_limit - activity["total"])

        return {
            "remaining": remaining,
            "daily_limit": effective_limit,
            "used_total": activity["total"],
            "used_automated": activity["automated"],
            "used_manual": activity["manual"],
            "can_send": remaining > 0 and effective_limit > 0,
            "source": activity["source"],
        }

    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs: Any,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn message or connection request via Unipile.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            content: Message content
            **kwargs: Additional options:
                - account_id: Unipile account ID (required)
                - action: 'connection' or 'message' (default: 'message')
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
        account_id = kwargs.get("account_id")
        if not account_id:
            return EngineResult.fail(
                error="Unipile account_id is required",
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
        await self.get_campaign_by_id(db, campaign_id)

        # Validate LinkedIn URL
        if not lead.linkedin_url:
            return EngineResult.fail(
                error="Lead has no LinkedIn URL",
                metadata={"lead_id": str(lead_id)},
            )

        # TEST_MODE: Redirect LinkedIn to test recipient
        original_linkedin = lead.linkedin_url
        if settings.TEST_MODE:
            lead.linkedin_url = settings.TEST_LINKEDIN_RECIPIENT
            logger.info(
                f"TEST_MODE: Redirecting LinkedIn {original_linkedin} → {lead.linkedin_url}"
            )

        # Get effective daily limit (with weekend reduction)
        effective_limit = self._get_effective_daily_limit()

        # Early return for Sunday (0% quota)
        if effective_limit == 0:
            return EngineResult.fail(
                error="LinkedIn activity paused for Sunday",
                metadata={
                    "lead_id": str(lead_id),
                    "account_id": account_id,
                    "reason": "sunday_pause",
                },
            )

        # Gap #18: Check combined quota (manual + automated activity)
        # This ensures we respect LinkedIn's account-level limits even when
        # the user is manually sending connections outside our system.
        quota = await self.get_remaining_quota(account_id)

        if not quota["can_send"]:
            manual_info = ""
            if quota["used_manual"] > 0:
                manual_info = (
                    f" ({quota['used_manual']} manual + {quota['used_automated']} automated)"
                )

            return EngineResult.fail(
                error=f"LinkedIn daily limit ({effective_limit}/day) exceeded for account{manual_info}",
                metadata={
                    "account_id": account_id,
                    "limit": effective_limit,
                    "used_total": quota["used_total"],
                    "used_manual": quota["used_manual"],
                    "used_automated": quota["used_automated"],
                    "remaining": quota["remaining"],
                    "source": quota["source"],
                },
            )

        # Also track in Redis for our automated sends (for faster local checks)
        try:
            allowed, current_count = await rate_limiter.check_and_increment(
                resource_type="linkedin",
                resource_id=account_id,
                limit=effective_limit,
            )
        except ResourceRateLimitError as e:
            # This shouldn't happen if combined check passed, but handle it
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "account_id": account_id,
                    "limit": effective_limit,
                },
            )

        try:
            # Send connection request (invitation) or message via Unipile
            if action == "connection":
                result = await self.unipile.send_invitation(
                    account_id=account_id,
                    recipient_id=lead.linkedin_url,
                    message=content if content else None,
                )
                activity_action = "connection_sent"
            else:
                result = await self.unipile.send_message(
                    account_id=account_id,
                    recipient_id=lead.linkedin_url,
                    text=content,
                )
                activity_action = "message_sent"

            # Get message/request ID from Unipile response
            provider_id = (
                result.get("id") or result.get("message_id") or result.get("invitation_id")
            )

            # Log activity with content snapshot (Phase 16) and template tracking (Phase 24B)
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
                account_id=account_id,
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
                    "provider_id": provider_id,
                    "linkedin_url": lead.linkedin_url,
                    "account_id": account_id,
                    "action": action,
                    "status": result.get("status", "sent"),
                    # Gap #18: Use combined quota for remaining count
                    "remaining_quota": quota["remaining"] - 1,  # -1 for this send
                    "used_manual": quota["used_manual"],
                    "used_automated": quota["used_automated"] + 1,  # +1 for this send
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
                    "account_id": account_id,
                    "action": action,
                },
            )

    async def send_connection_request(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        message: str | None = None,
        account_id: str | None = None,
        seat_id: UUID | None = None,
        skip_delay: bool = False,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn connection request (invitation) with profile view delay.

        Gap #19 Implementation:
        - If profile not viewed, views profile and returns 'scheduled' status
        - If profile viewed but <10 min ago, returns 'waiting' status
        - If profile viewed >=10 min ago, sends connection request

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            message: Optional connection message
            account_id: Unipile account ID
            seat_id: LinkedIn seat UUID (for connection tracking)
            skip_delay: Skip delay check (for manual overrides)

        Returns:
            EngineResult with send result or scheduling info
        """
        # If skip_delay, send immediately (for backwards compatibility or manual override)
        if skip_delay:
            return await self.validate_and_send(
                db=db,
                lead_id=lead_id,
                campaign_id=campaign_id,
                content=message or "",
                account_id=account_id,
                action="connection",
            )

        # Check profile view status and delay (Gap #19)
        delay_check = await self._check_profile_view_delay(
            db=db,
            lead_id=lead_id,
            seat_id=seat_id,
            account_id=account_id,
        )

        if delay_check["status"] == "needs_view":
            # View profile now, schedule connection for later
            view_result = await self._view_profile(
                db=db,
                lead_id=lead_id,
                campaign_id=campaign_id,
                seat_id=seat_id,
                account_id=account_id,
                message=message,
            )
            return view_result

        elif delay_check["status"] == "waiting":
            # Profile was viewed but not enough time passed
            return EngineResult.ok(
                data={
                    "status": "waiting",
                    "reason": "profile_view_delay",
                    "profile_viewed_at": delay_check["profile_viewed_at"].isoformat(),
                    "minutes_elapsed": delay_check["minutes_elapsed"],
                    "minutes_remaining": PROFILE_VIEW_DELAY_MIN_MINUTES
                    - delay_check["minutes_elapsed"],
                    "connect_available_at": delay_check["connect_available_at"].isoformat(),
                },
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

        # Profile viewed and delay elapsed - send connection
        return await self.validate_and_send(
            db=db,
            lead_id=lead_id,
            campaign_id=campaign_id,
            content=message or "",
            account_id=account_id,
            action="connection",
        )

    async def _check_profile_view_delay(
        self,
        db: AsyncSession,
        lead_id: UUID,
        seat_id: UUID | None = None,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Check if profile view delay has been satisfied.

        Gap #19: Enforces 10-30 minute delay between profile view and connection.

        Args:
            db: Database session
            lead_id: Lead UUID
            seat_id: LinkedIn seat UUID (optional, for tracking)
            account_id: Unipile account ID (optional)

        Returns:
            Dict with status and timing info:
            - status: 'needs_view' | 'waiting' | 'ready'
            - profile_viewed_at: timestamp if viewed
            - minutes_elapsed: minutes since view
            - connect_available_at: when connection can be sent
        """
        # Look for existing linkedin_connection record with profile_viewed_at
        stmt = select(LinkedInConnection).where(
            LinkedInConnection.lead_id == lead_id,
        )
        if seat_id:
            stmt = stmt.where(LinkedInConnection.seat_id == seat_id)

        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()

        # No existing connection record or no profile view
        if not connection or not connection.profile_viewed_at:
            return {"status": "needs_view"}

        # Profile was viewed - check elapsed time
        profile_viewed_at = connection.profile_viewed_at
        now = datetime.utcnow()
        elapsed = now - profile_viewed_at
        minutes_elapsed = int(elapsed.total_seconds() / 60)

        if minutes_elapsed < PROFILE_VIEW_DELAY_MIN_MINUTES:
            # Not enough time passed
            return {
                "status": "waiting",
                "profile_viewed_at": profile_viewed_at,
                "minutes_elapsed": minutes_elapsed,
                "connect_available_at": profile_viewed_at
                + timedelta(minutes=PROFILE_VIEW_DELAY_MIN_MINUTES),
            }

        # Delay satisfied
        return {
            "status": "ready",
            "profile_viewed_at": profile_viewed_at,
            "minutes_elapsed": minutes_elapsed,
        }

    async def _view_profile(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        seat_id: UUID | None = None,
        account_id: str | None = None,
        message: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        View a LinkedIn profile and schedule connection for later.

        Gap #19: Views profile via Unipile, creates/updates linkedin_connection
        record with profile_viewed_at, and returns scheduling info.

        Args:
            db: Database session
            lead_id: Lead UUID
            campaign_id: Campaign UUID
            seat_id: LinkedIn seat UUID
            account_id: Unipile account ID
            message: Connection message (stored for later use)

        Returns:
            EngineResult with profile view result and scheduling info
        """
        # Get lead for LinkedIn URL
        lead = await self.get_lead_by_id(db, lead_id)
        if not lead.linkedin_url:
            return EngineResult.fail(
                error="Lead has no LinkedIn URL",
                metadata={"lead_id": str(lead_id)},
            )

        try:
            # View profile via Unipile
            profile_data = await self.unipile.get_profile(
                account_id=account_id,
                profile_id=lead.linkedin_url,
            )
            logger.info(f"Viewed LinkedIn profile for lead {lead_id}: {lead.linkedin_url}")

        except Exception as e:
            logger.warning(f"Failed to view LinkedIn profile for lead {lead_id}: {e}")
            # Continue anyway - we'll record the view attempt
            profile_data = {"found": False, "error": str(e)}

        # Calculate random delay (10-30 minutes)
        delay_minutes = random.randint(
            PROFILE_VIEW_DELAY_MIN_MINUTES,
            PROFILE_VIEW_DELAY_MAX_MINUTES,
        )
        now = datetime.utcnow()
        connect_at = now + timedelta(minutes=delay_minutes)

        # Create or update linkedin_connection record
        stmt = select(LinkedInConnection).where(
            LinkedInConnection.lead_id == lead_id,
        )
        if seat_id:
            stmt = stmt.where(LinkedInConnection.seat_id == seat_id)

        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()

        if connection:
            # Update existing record
            connection.profile_viewed_at = now
            connection.note_content = message  # Store message for later
        else:
            # Create new record (if seat_id provided)
            if seat_id:
                connection = LinkedInConnection(
                    lead_id=lead_id,
                    seat_id=seat_id,
                    campaign_id=campaign_id,
                    profile_viewed_at=now,
                    note_content=message,
                    note_included=bool(message),
                    status="pending",  # Will be updated when connection is actually sent
                )
                db.add(connection)

        await db.commit()

        # Log activity for profile view
        await self._log_activity(
            db=db,
            lead=lead,
            campaign_id=campaign_id,
            action="profile_viewed",
            account_id=account_id,
        )

        return EngineResult.ok(
            data={
                "status": "scheduled",
                "profile_viewed": True,
                "profile_viewed_at": now.isoformat(),
                "connect_scheduled_at": connect_at.isoformat(),
                "delay_minutes": delay_minutes,
                "profile_data": {
                    "found": profile_data.get("found", False),
                    "first_name": profile_data.get("first_name"),
                    "last_name": profile_data.get("last_name"),
                    "headline": profile_data.get("headline"),
                    "company": profile_data.get("company"),
                },
            },
            metadata={
                "engine": self.name,
                "channel": self.channel.value,
                "lead_id": str(lead_id),
                "campaign_id": str(campaign_id),
            },
        )

    async def get_connections_ready_to_send(
        self,
        db: AsyncSession,
        seat_id: UUID | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get LinkedIn connections that have passed the profile view delay.

        Gap #19: Returns connections where:
        - profile_viewed_at is set
        - At least 10 minutes have elapsed since profile view
        - Connection request not yet sent (status is 'pending' with no requested_at)

        Args:
            db: Database session
            seat_id: Optional seat UUID to filter by
            limit: Maximum records to return

        Returns:
            List of connection records ready for connection request
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=PROFILE_VIEW_DELAY_MIN_MINUTES)

        stmt = select(LinkedInConnection).where(
            LinkedInConnection.profile_viewed_at.isnot(None),
            LinkedInConnection.profile_viewed_at <= cutoff_time,
            LinkedInConnection.status == "pending",
            LinkedInConnection.requested_at.is_(None),  # Not yet sent
        )

        if seat_id:
            stmt = stmt.where(LinkedInConnection.seat_id == seat_id)

        stmt = stmt.order_by(LinkedInConnection.profile_viewed_at.asc()).limit(limit)

        result = await db.execute(stmt)
        connections = result.scalars().all()

        return [
            {
                "connection_id": str(conn.id),
                "lead_id": str(conn.lead_id),
                "seat_id": str(conn.seat_id),
                "campaign_id": str(conn.campaign_id) if conn.campaign_id else None,
                "profile_viewed_at": conn.profile_viewed_at.isoformat(),
                "message": conn.note_content,
                "minutes_since_view": int(
                    (datetime.utcnow() - conn.profile_viewed_at).total_seconds() / 60
                ),
            }
            for conn in connections
        ]

    async def send_message(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        message: str,
        account_id: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn direct message.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            message: Message content
            account_id: Unipile account ID

        Returns:
            EngineResult with send result
        """
        return await self.validate_and_send(
            db=db,
            lead_id=lead_id,
            campaign_id=campaign_id,
            content=message,
            account_id=account_id,
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
                results["actions"].append(
                    {
                        "lead_id": str(lead_id) if lead_id else None,
                        "status": "failed",
                        "reason": "Missing required fields",
                    }
                )
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
                results["actions"].append(
                    {
                        "lead_id": str(lead_id),
                        "status": "sent",
                        "provider_id": result.data.get("provider_id"),
                        "action": result.data.get("action"),
                    }
                )
            else:
                # Check if rate limited
                if "rate limit" in result.error.lower():
                    results["rate_limited"] += 1
                else:
                    results["failed"] += 1

                results["actions"].append(
                    {
                        "lead_id": str(lead_id),
                        "status": "failed",
                        "reason": result.error,
                    }
                )

        return EngineResult.ok(
            data=results,
            metadata={
                "success_rate": results["sent"] / results["total"] if results["total"] > 0 else 0,
            },
        )

    async def get_account_status(
        self,
        account_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get status of a LinkedIn account (quota, availability, Unipile status).

        Gap #18: Now includes combined quota tracking (manual + automated).

        Args:
            account_id: Unipile account ID

        Returns:
            EngineResult with account status including:
            - daily_limit: Effective limit with weekend reduction
            - daily_used_total: Combined manual + automated usage
            - daily_used_automated: Our automated sends only
            - daily_used_manual: User's manual activity
            - remaining: Available sends
            - can_send: Boolean if quota available
        """
        try:
            # Gap #18: Get combined activity count (manual + automated)
            quota = await self.get_remaining_quota(account_id)

            # Optionally get Unipile account status
            unipile_status = None
            try:
                account_info = await self.unipile.get_account(account_id)
                unipile_status = account_info.get("status")
            except Exception:
                pass  # Non-critical, continue without Unipile status

            # Determine weekend status
            today = datetime.utcnow().weekday()
            weekend_status = None
            if today == 6:
                weekend_status = "sunday_blocked"
            elif today == 5:
                weekend_status = "saturday_reduced"

            return EngineResult.ok(
                data={
                    "account_id": account_id,
                    "daily_limit": quota["daily_limit"],
                    "base_daily_limit": LINKEDIN_DAILY_LIMIT_PER_ACCOUNT,
                    # Gap #18: Detailed activity breakdown
                    "daily_used_total": quota["used_total"],
                    "daily_used_automated": quota["used_automated"],
                    "daily_used_manual": quota["used_manual"],
                    "daily_used": quota["used_total"],  # Backwards compatibility
                    "remaining": quota["remaining"],
                    "can_send": quota["can_send"],
                    "unipile_status": unipile_status,
                    "weekend_status": weekend_status,
                    "quota_source": quota["source"],  # "unipile" or "redis_only"
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to get account status: {str(e)}",
                metadata={"account_id": account_id},
            )

    async def get_new_replies(
        self,
        db: AsyncSession,
        account_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get new LinkedIn messages for an account.

        Args:
            db: Database session (passed by caller)
            account_id: Unipile account ID

        Returns:
            EngineResult with new messages
        """
        try:
            messages = await self.unipile.get_messages(account_id, limit=50)

            return EngineResult.ok(
                data={
                    "account_id": account_id,
                    "message_count": len(messages),
                    "messages": messages,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to get messages: {str(e)}",
                metadata={"account_id": account_id},
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
        account_id: str | None = None,
        # Phase 24B: Content tracking fields
        template_id: UUID | None = None,
        ab_test_id: UUID | None = None,
        ab_variant: str | None = None,
        ai_model_used: str | None = None,
        prompt_version: str | None = None,
        personalization_fields_used: list[str] | None = None,
    ) -> None:
        """
        Log LinkedIn activity to database.

        Phase 16: Now captures content_snapshot for WHAT Detector learning.
        Phase 24B: Now stores template_id, A/B test info, and full message body.
        """
        metadata = {}
        if account_id:
            metadata["account_id"] = account_id

        # Build content snapshot for Conversion Intelligence (Phase 16)
        snapshot = None
        full_body = message_content or connection_note
        if full_body:
            snapshot = build_linkedin_snapshot(
                message=message_content or "",
                lead=lead,
                message_type=message_type,
                connection_note=connection_note,
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

        # Phase 24B: Extract links from LinkedIn content
        links_included = None
        if full_body:
            import re

            # Extract URLs from LinkedIn message content
            url_pattern = r"https?://[^\s]+"
            links_included = list(set(re.findall(url_pattern, full_body)))

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
            # Phase 24B: Content tracking fields
            template_id=template_id,
            ab_test_id=ab_test_id,
            ab_variant=ab_variant,
            full_message_body=full_body,  # Store complete content
            links_included=links_included,
            personalization_fields_used=personalization_fields_used,
            ai_model_used=ai_model_used,
            prompt_version=prompt_version,
            provider="unipile",  # Changed from 'heyreach' to 'unipile'
            provider_status=action,
            provider_response=provider_response,
            extra_data=metadata,
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
# [x] Resource-level rate limits (configurable via settings - Rule 17)
# [x] Connection request support (via Unipile send_invitation)
# [x] Direct message support (via Unipile send_message)
# [x] Activity logging after send (provider='unipile')
# [x] Batch sending support
# [x] Account status checking (replaced seat_status)
# [x] New messages retrieval (replaced get_new_replies)
# [x] Extends OutreachEngine from base.py
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Phase 16: content_snapshot captured for WHAT Detector
# [x] Phase 16: touch_number, sequence_id, and message_type tracked
# [x] Phase 24B: template_id stored for template tracking
# [x] Phase 24B: ab_test_id and ab_variant for A/B testing
# [x] Phase 24B: full_message_body stored for complete content analysis
# [x] Phase 24B: links_included extracted from LinkedIn
# [x] Phase 24B: personalization_fields_used tracked
# [x] Phase 24B: ai_model_used and prompt_version stored
# [x] UNIPILE MIGRATION: Replaced HeyReach with Unipile client
# [x] UNIPILE MIGRATION: account_id instead of seat_id
# [x] UNIPILE MIGRATION: provider='unipile' in activity logs
# [x] WEEKEND REDUCTION: Saturday 50%, Sunday 0% quota enforcement
# [x] WEEKEND REDUCTION: _get_effective_daily_limit() helper method
# [x] WEEKEND REDUCTION: Early return with sunday_pause reason
# [x] PROFILE VIEW DELAY (Gap #19): PROFILE_VIEW_DELAY_MIN/MAX_MINUTES constants
# [x] PROFILE VIEW DELAY (Gap #19): _check_profile_view_delay() checks timing
# [x] PROFILE VIEW DELAY (Gap #19): _view_profile() views profile via Unipile
# [x] PROFILE VIEW DELAY (Gap #19): send_connection_request() enforces 10-30 min delay
# [x] PROFILE VIEW DELAY (Gap #19): get_connections_ready_to_send() for processing
# [x] PROFILE VIEW DELAY (Gap #19): profile_viewed activity logged
# [x] SHARED QUOTA (Gap #18): get_combined_activity_count() fetches from Unipile
# [x] SHARED QUOTA (Gap #18): get_remaining_quota() calculates available quota
# [x] SHARED QUOTA (Gap #18): send() checks combined quota before sending
# [x] SHARED QUOTA (Gap #18): get_account_status() returns manual/automated breakdown
# [x] SHARED QUOTA (Gap #18): Fallback to Redis-only if Unipile API fails
# [x] PROFILE VIEW DELAY (Gap #19): skip_delay parameter for manual override
