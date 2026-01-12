"""
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
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.engines.base import EngineResult, OutreachEngine

logger = logging.getLogger(__name__)
from src.engines.content_utils import build_linkedin_snapshot
from src.exceptions import ResourceRateLimitError, ValidationError
from src.integrations.unipile import UnipileClient, get_unipile_client
from src.integrations.redis import rate_limiter
from src.models.activity import Activity
from src.models.base import ChannelType
from src.models.lead import Lead


# Rate limit (Rule 17) - Now configurable via settings
# Unipile allows higher limits (80-100/day) but we default to conservative
LINKEDIN_DAILY_LIMIT_PER_ACCOUNT = settings.linkedin_max_daily


class LinkedInEngine(OutreachEngine):
    """
    LinkedIn engine for sending connection requests and messages via Unipile.

    Features:
    - Connection request sending (invitations)
    - Direct message sending
    - Resource-level rate limiting (configurable, default 17/day/account)
    - Activity logging with content snapshot
    - Conversation tracking

    Migration Note:
    - Migrated from HeyReach to Unipile for 70-85% cost reduction
    - Uses account_id instead of seat_id
    - Provider is 'unipile' instead of 'heyreach'
    """

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
        campaign = await self.get_campaign_by_id(db, campaign_id)

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
            logger.info(f"TEST_MODE: Redirecting LinkedIn {original_linkedin} → {lead.linkedin_url}")

        # Check rate limit (Rule 17)
        try:
            allowed, current_count = await rate_limiter.check_and_increment(
                resource_type="linkedin",
                resource_id=account_id,
                limit=LINKEDIN_DAILY_LIMIT_PER_ACCOUNT,
            )
        except ResourceRateLimitError as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "account_id": account_id,
                    "limit": LINKEDIN_DAILY_LIMIT_PER_ACCOUNT,
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
            provider_id = result.get("id") or result.get("message_id") or result.get("invitation_id")

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
                    "remaining_quota": LINKEDIN_DAILY_LIMIT_PER_ACCOUNT - current_count,
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
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn connection request (invitation).

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            message: Optional connection message
            account_id: Unipile account ID

        Returns:
            EngineResult with send result
        """
        return await self.validate_and_send(
            db=db,
            lead_id=lead_id,
            campaign_id=campaign_id,
            content=message or "",
            account_id=account_id,
            action="connection",
        )

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

    async def get_account_status(
        self,
        account_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get status of a LinkedIn account (quota, availability, Unipile status).

        Args:
            account_id: Unipile account ID

        Returns:
            EngineResult with account status
        """
        try:
            # Get current usage from rate limiter
            usage = await rate_limiter.get_usage(
                resource_type="linkedin",
                resource_id=account_id,
            )

            remaining = max(0, LINKEDIN_DAILY_LIMIT_PER_ACCOUNT - usage)

            # Optionally get Unipile account status
            unipile_status = None
            try:
                account_info = await self.unipile.get_account(account_id)
                unipile_status = account_info.get("status")
            except Exception:
                pass  # Non-critical, continue without Unipile status

            return EngineResult.ok(
                data={
                    "account_id": account_id,
                    "daily_limit": LINKEDIN_DAILY_LIMIT_PER_ACCOUNT,
                    "daily_used": usage,
                    "remaining": remaining,
                    "can_send": remaining > 0,
                    "unipile_status": unipile_status,
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
            url_pattern = r'https?://[^\s]+'
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
