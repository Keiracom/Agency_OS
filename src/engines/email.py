"""
FILE: src/engines/email.py
PURPOSE: Email engine using Resend integration with threading support
PHASE: 4 (Engines), modified Phase 16/24B for Conversion Intelligence
TASK: ENG-005, 16E-002, CONTENT-002
DEPENDENCIES:
  - src/engines/base.py
  - src/engines/content_utils.py (Phase 16)
  - src/integrations/resend.py
  - src/integrations/redis.py
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines (content_utils is utilities, not engine)
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits (50/day/domain)
  - Rule 18: Email threading via In-Reply-To headers
PHASE 16 CHANGES:
  - Added content_snapshot capture for WHAT Detector learning
  - Tracks touch_number and sequence context
PHASE 24B CHANGES:
  - Store full_message_body for complete content analysis
  - Link to template_id for template tracking
  - Track ab_test_id and ab_variant for A/B testing
  - Store links_included and personalization_fields_used
  - Track ai_model_used and prompt_version
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import EngineResult, OutreachEngine
from src.engines.content_utils import build_content_snapshot
from src.exceptions import ResourceRateLimitError, ValidationError
from src.integrations.redis import rate_limiter
from src.integrations.resend import ResendClient, get_resend_client
from src.models.activity import Activity
from src.models.base import ChannelType
from src.models.lead import Lead


# Rate limit (Rule 17)
EMAIL_DAILY_LIMIT_PER_DOMAIN = 50


class EmailEngine(OutreachEngine):
    """
    Email engine for sending emails via Resend.

    Features:
    - Email threading support (Rule 18)
    - Resource-level rate limiting (50/day/domain - Rule 17)
    - Activity logging
    - Follow-up sequence support
    """

    def __init__(self, resend_client: ResendClient | None = None):
        """
        Initialize Email engine.

        Args:
            resend_client: Optional Resend client (uses singleton if not provided)
        """
        self._resend = resend_client

    @property
    def name(self) -> str:
        return "email"

    @property
    def channel(self) -> ChannelType:
        return ChannelType.EMAIL

    @property
    def resend(self) -> ResendClient:
        if self._resend is None:
            self._resend = get_resend_client()
        return self._resend

    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs: Any,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send an email to a lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            content: Email HTML content
            **kwargs: Additional options:
                - subject: Email subject (required)
                - text_content: Plain text version
                - from_email: Sender email (required)
                - from_name: Sender name
                - reply_to: Reply-to address
                - sequence_step: Step number in sequence
                - is_followup: Whether this is a follow-up
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
        subject = kwargs.get("subject")
        from_email = kwargs.get("from_email")

        if not subject:
            return EngineResult.fail(
                error="Email subject is required",
                metadata={"lead_id": str(lead_id)},
            )
        if not from_email:
            return EngineResult.fail(
                error="From email is required",
                metadata={"lead_id": str(lead_id)},
            )

        # Get lead
        lead = await self.get_lead_by_id(db, lead_id)
        campaign = await self.get_campaign_by_id(db, campaign_id)

        # Extract domain for rate limiting (Rule 17)
        domain = self._extract_domain(from_email)
        if not domain:
            return EngineResult.fail(
                error="Invalid from_email address",
                metadata={"from_email": from_email},
            )

        # Check rate limit
        try:
            allowed, current_count = await rate_limiter.check_and_increment(
                resource_type="email",
                resource_id=domain,
                limit=EMAIL_DAILY_LIMIT_PER_DOMAIN,
            )
        except ResourceRateLimitError as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "domain": domain,
                    "limit": EMAIL_DAILY_LIMIT_PER_DOMAIN,
                },
            )

        # Get threading info if this is a follow-up (Rule 18)
        in_reply_to = None
        references = []
        thread_id = None

        if kwargs.get("is_followup"):
            thread_info = await self._get_thread_info(db, lead_id, campaign_id)
            in_reply_to = thread_info.get("in_reply_to")
            references = thread_info.get("references", [])
            thread_id = thread_info.get("thread_id")

        # Build sender
        from_name = kwargs.get("from_name")
        sender = f"{from_name} <{from_email}>" if from_name else from_email

        try:
            # Send via Resend
            result = await self.resend.send_email(
                from_email=sender,
                to_email=lead.email,
                subject=subject,
                html_body=content,
                text_body=kwargs.get("text_content"),
                reply_to=kwargs.get("reply_to"),
                in_reply_to=in_reply_to,
                references=references,
                tags={
                    "campaign_id": str(campaign_id),
                    "lead_id": str(lead_id),
                    "client_id": str(campaign.client_id),
                },
            )

            message_id = result.get("message_id")

            # Log activity with content snapshot (Phase 16) and template tracking (Phase 24B)
            await self._log_activity(
                db=db,
                lead=lead,
                campaign_id=campaign_id,
                action="sent",
                provider_message_id=message_id,
                thread_id=thread_id or message_id,  # Start new thread if not a follow-up
                in_reply_to=in_reply_to,
                sequence_step=kwargs.get("sequence_step"),
                subject=subject,
                content_preview=self._get_content_preview(content),
                html_content=content,  # Phase 16: Pass full content for snapshot
                sequence_id=kwargs.get("sequence_id"),  # Phase 16: Sequence context
                provider_response=result,
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
                    "message_id": message_id,
                    "to_email": lead.email,
                    "from_email": from_email,
                    "subject": subject,
                    "thread_id": thread_id or message_id,
                    "is_followup": bool(in_reply_to),
                    "domain": domain,
                    "remaining_quota": EMAIL_DAILY_LIMIT_PER_DOMAIN - current_count,
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
                error=f"Email send failed: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                    "from_email": from_email,
                    "domain": domain,
                },
            )

    async def send_batch(
        self,
        db: AsyncSession,
        emails: list[dict[str, Any]],
    ) -> EngineResult[dict[str, Any]]:
        """
        Send multiple emails in batch.

        Args:
            db: Database session (passed by caller)
            emails: List of email configs with lead_id, campaign_id, content, etc.

        Returns:
            EngineResult with batch send summary
        """
        results = {
            "total": len(emails),
            "sent": 0,
            "failed": 0,
            "rate_limited": 0,
            "emails": [],
        }

        for email_config in emails:
            lead_id = email_config.get("lead_id")
            campaign_id = email_config.get("campaign_id")
            content = email_config.get("content")

            if not all([lead_id, campaign_id, content]):
                results["failed"] += 1
                results["emails"].append({
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
                **email_config,
            )

            if result.success:
                results["sent"] += 1
                results["emails"].append({
                    "lead_id": str(lead_id),
                    "status": "sent",
                    "message_id": result.data.get("message_id"),
                })
            else:
                # Check if rate limited
                if "rate limit" in result.error.lower():
                    results["rate_limited"] += 1
                else:
                    results["failed"] += 1

                results["emails"].append({
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

    async def _get_thread_info(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
    ) -> dict[str, Any]:
        """
        Get email thread information for follow-ups.

        Finds the most recent sent email to build threading headers.
        """
        stmt = (
            select(Activity)
            .where(
                and_(
                    Activity.lead_id == lead_id,
                    Activity.campaign_id == campaign_id,
                    Activity.channel == ChannelType.EMAIL,
                    Activity.action == "sent",
                    Activity.provider_message_id.is_not(None),
                )
            )
            .order_by(desc(Activity.created_at))
            .limit(1)
        )

        result = await db.execute(stmt)
        last_activity = result.scalar_one_or_none()

        if not last_activity:
            return {}

        # Get all message IDs in this thread for References header
        thread_stmt = (
            select(Activity.provider_message_id)
            .where(
                and_(
                    Activity.lead_id == lead_id,
                    Activity.campaign_id == campaign_id,
                    Activity.channel == ChannelType.EMAIL,
                    Activity.action == "sent",
                    Activity.provider_message_id.is_not(None),
                )
            )
            .order_by(Activity.created_at)
        )

        thread_result = await db.execute(thread_stmt)
        all_message_ids = [row[0] for row in thread_result.all() if row[0]]

        return {
            "in_reply_to": last_activity.provider_message_id,
            "references": all_message_ids,
            "thread_id": last_activity.thread_id,
        }

    async def _log_activity(
        self,
        db: AsyncSession,
        lead: Lead,
        campaign_id: UUID,
        action: str,
        provider_message_id: str | None = None,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        sequence_step: int | None = None,
        subject: str | None = None,
        content_preview: str | None = None,
        html_content: str | None = None,
        sequence_id: str | None = None,
        provider_response: dict | None = None,
        # Phase 24B: Content tracking fields
        template_id: UUID | None = None,
        ab_test_id: UUID | None = None,
        ab_variant: str | None = None,
        ai_model_used: str | None = None,
        prompt_version: str | None = None,
        personalization_fields_used: list[str] | None = None,
    ) -> None:
        """
        Log email activity to database.

        Phase 16: Now captures content_snapshot for WHAT Detector learning.
        Phase 24B: Now stores template_id, A/B test info, and full message body.
        """
        # Build content snapshot for Conversion Intelligence (Phase 16)
        snapshot = None
        if html_content:
            # Strip HTML for analysis
            import re
            text_content = re.sub(r'<[^>]+>', '', html_content).strip()
            snapshot = build_content_snapshot(
                body=text_content,
                lead=lead,
                subject=subject,
                touch_number=sequence_step or 1,
                sequence_id=sequence_id,
                channel="email",
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

        # Phase 24B: Extract links from HTML content
        links_included = None
        if html_content:
            import re
            # Extract URLs from href attributes
            href_pattern = r'href=["\']([^"\']+)["\']'
            links_included = list(set(re.findall(href_pattern, html_content)))

        activity = Activity(
            client_id=lead.client_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            channel=ChannelType.EMAIL,
            action=action,
            provider_message_id=provider_message_id,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            sequence_step=sequence_step,
            subject=subject,
            content_preview=content_preview,
            content_snapshot=snapshot,  # Phase 16: Store content snapshot
            # Phase 24B: Content tracking fields
            template_id=template_id,
            ab_test_id=ab_test_id,
            ab_variant=ab_variant,
            full_message_body=html_content,  # Store complete content
            links_included=links_included,
            personalization_fields_used=personalization_fields_used,
            ai_model_used=ai_model_used,
            prompt_version=prompt_version,
            provider="resend",
            provider_status="sent",
            provider_response=provider_response,
            created_at=datetime.utcnow(),
        )

        db.add(activity)
        await db.commit()

    def _extract_domain(self, email: str) -> str | None:
        """Extract domain from email address."""
        if not email or "@" not in email:
            return None
        # Handle "Name <email@domain.com>" format
        if "<" in email and ">" in email:
            email = email.split("<")[1].split(">")[0]
        return email.split("@")[1].lower()

    def _get_content_preview(self, html_content: str, max_length: int = 200) -> str:
        """Get preview of email content (strip HTML)."""
        # Simple HTML stripping - in production, use a proper HTML parser
        import re
        text = re.sub(r'<[^>]+>', '', html_content)
        text = text.strip()
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text


# Singleton instance
_email_engine: EmailEngine | None = None


def get_email_engine() -> EmailEngine:
    """Get or create Email engine instance."""
    global _email_engine
    if _email_engine is None:
        _email_engine = EmailEngine()
    return _email_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete check inherited from BaseEngine
# [x] Resource-level rate limits (50/day/domain - Rule 17)
# [x] Email threading via In-Reply-To (Rule 18)
# [x] References header for multi-message threads
# [x] Activity logging after send
# [x] Batch sending support
# [x] Thread info retrieval for follow-ups
# [x] Extends OutreachEngine from base.py
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Phase 16: content_snapshot captured for WHAT Detector
# [x] Phase 16: touch_number and sequence_id tracked
# [x] Phase 24B: template_id stored for template tracking
# [x] Phase 24B: ab_test_id and ab_variant for A/B testing
# [x] Phase 24B: full_message_body stored for complete content analysis
# [x] Phase 24B: links_included extracted from HTML
# [x] Phase 24B: personalization_fields_used tracked
# [x] Phase 24B: ai_model_used and prompt_version stored
