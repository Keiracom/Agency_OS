"""
Contract: src/services/alert_service.py
Purpose: Centralized alert service for system-wide failure notifications
Layer: 3 - services
Imports: integrations
Consumers: orchestration, engines, integrations

FILE: src/services/alert_service.py
PURPOSE: Centralized alerting for silent failures across Agency OS
PHASE: Directive 048 (Part F)
TASK: ALERT-001
DEPENDENCIES:
  - src/integrations/supabase.py
  - src/integrations/resend.py (for email delivery)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - No silent failures
  - All alerts create Supabase record + dashboard flag
  - Campaign-level issues email agency owner

ALERT TYPES:
1. Angry complaint → immediate notification + email
2. Bright Data API timeout/error after 2 retries
3. Hunter rate limit hit (with estimated recovery time)
4. LinkedIn daily rate limit per seat
5. Email warmup health score below threshold
6. Hot+Warm ratio drops below 20% in active campaign
7. Batch quota shortfall after 3 replacement loops
8. Reply confidence <60% → human review queue (not alert)
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# =============================================================================
# ALERT TYPES & SEVERITY MAPPING
# =============================================================================

class AlertType:
    """Alert type constants."""
    ANGRY_COMPLAINT = "angry_complaint"
    BRIGHT_DATA_ERROR = "bright_data_error"
    HUNTER_RATE_LIMIT = "hunter_rate_limit"
    LINKEDIN_RATE_LIMIT = "linkedin_rate_limit"
    WARMUP_HEALTH_LOW = "warmup_health_low"
    HOT_WARM_RATIO_LOW = "hot_warm_ratio_low"
    QUOTA_SHORTFALL = "quota_shortfall"
    REPLY_LOW_CONFIDENCE = "reply_low_confidence"  # Human review, not alert
    CAMPAIGN_HALT = "campaign_halt"
    ENRICHMENT_FAILURE = "enrichment_failure"
    WEBHOOK_FAILURE = "webhook_failure"


ALERT_SEVERITY = {
    AlertType.ANGRY_COMPLAINT: "high",
    AlertType.BRIGHT_DATA_ERROR: "high",
    AlertType.HUNTER_RATE_LIMIT: "medium",
    AlertType.LINKEDIN_RATE_LIMIT: "medium",
    AlertType.WARMUP_HEALTH_LOW: "high",
    AlertType.HOT_WARM_RATIO_LOW: "medium",
    AlertType.QUOTA_SHORTFALL: "high",
    AlertType.REPLY_LOW_CONFIDENCE: "low",
    AlertType.CAMPAIGN_HALT: "high",
    AlertType.ENRICHMENT_FAILURE: "medium",
    AlertType.WEBHOOK_FAILURE: "high",
}

# Alerts that should email agency owner
EMAIL_ALERT_TYPES = {
    AlertType.ANGRY_COMPLAINT,
    AlertType.WARMUP_HEALTH_LOW,
    AlertType.HOT_WARM_RATIO_LOW,
    AlertType.QUOTA_SHORTFALL,
    AlertType.CAMPAIGN_HALT,
}


# =============================================================================
# ALERT SERVICE
# =============================================================================

class AlertService:
    """
    Centralized alert service for Agency OS.

    Creates Supabase notification records with dashboard flags.
    Sends emails to agency owners for campaign-level issues.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize Alert Service.

        Args:
            session: Async database session
        """
        self.session = session

    async def create_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        client_id: UUID | None = None,
        campaign_id: UUID | None = None,
        lead_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        send_email: bool | None = None,
    ) -> UUID | None:
        """
        Create an alert notification.

        Args:
            alert_type: Type of alert (from AlertType)
            title: Alert title
            message: Alert message with details
            client_id: Related client UUID
            campaign_id: Related campaign UUID
            lead_id: Related lead UUID
            metadata: Additional context data
            send_email: Override email sending (None = auto based on type)

        Returns:
            Alert UUID or None on failure
        """
        severity = ALERT_SEVERITY.get(alert_type, "medium")
        should_email = send_email if send_email is not None else (alert_type in EMAIL_ALERT_TYPES)

        try:
            # Create Supabase notification record
            result = await self.session.execute(
                text("""
                    INSERT INTO admin_notifications (
                        notification_type, client_id, campaign_id, lead_id,
                        title, message, severity, status, metadata
                    ) VALUES (
                        :notification_type, :client_id, :campaign_id, :lead_id,
                        :title, :message, :severity, 'pending', :metadata
                    )
                    RETURNING id
                """),
                {
                    "notification_type": alert_type,
                    "client_id": str(client_id) if client_id else None,
                    "campaign_id": str(campaign_id) if campaign_id else None,
                    "lead_id": str(lead_id) if lead_id else None,
                    "title": title,
                    "message": message,
                    "severity": severity,
                    "metadata": json.dumps(metadata or {}),
                },
            )
            row = result.fetchone()
            alert_id = row.id if row else None
            await self.session.commit()

            # Set dashboard flag
            if client_id:
                await self._set_dashboard_flag(client_id, alert_type, alert_id)

            # Send email if required
            if should_email and client_id:
                await self._send_alert_email(client_id, title, message, alert_type, metadata)

            logger.info(f"Created alert {alert_id}: {alert_type} - {title}")
            return alert_id

        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None

    async def _set_dashboard_flag(
        self,
        client_id: UUID,
        alert_type: str,
        alert_id: UUID | None,
    ) -> None:
        """Set dashboard alert flag for client."""
        try:
            await self.session.execute(
                text("""
                    INSERT INTO client_dashboard_flags (
                        client_id, flag_type, flag_value, alert_id, created_at
                    ) VALUES (
                        :client_id, :flag_type, TRUE, :alert_id, NOW()
                    )
                    ON CONFLICT (client_id, flag_type) DO UPDATE
                    SET flag_value = TRUE,
                        alert_id = :alert_id,
                        updated_at = NOW()
                """),
                {
                    "client_id": str(client_id),
                    "flag_type": f"alert_{alert_type}",
                    "alert_id": str(alert_id) if alert_id else None,
                },
            )
            await self.session.commit()
        except Exception as e:
            # Table might not exist yet, log and continue
            logger.warning(f"Could not set dashboard flag: {e}")

    async def _send_alert_email(
        self,
        client_id: UUID,
        title: str,
        message: str,
        alert_type: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        """Send alert email to agency owner."""
        try:
            # Get agency owner email
            result = await self.session.execute(
                text("""
                    SELECT u.email, u.first_name, c.business_name
                    FROM clients c
                    JOIN users u ON c.owner_id = u.id
                    WHERE c.id = :client_id
                """),
                {"client_id": str(client_id)},
            )
            row = result.fetchone()

            if not row or not row.email:
                logger.warning(f"No owner email found for client {client_id}")
                return

            # Send via Resend
            from src.integrations.resend import send_alert_email
            
            await send_alert_email(
                to_email=row.email,
                to_name=row.first_name or "Agency Owner",
                subject=f"[Agency OS Alert] {title}",
                body=message,
                business_name=row.business_name,
                alert_type=alert_type,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")

    # =========================================================================
    # SPECIFIC ALERT METHODS
    # =========================================================================

    async def alert_bright_data_error(
        self,
        error_message: str,
        retry_count: int,
        client_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Alert: Bright Data API timeout/error after 2 retries.

        Args:
            error_message: Error details
            retry_count: Number of retries attempted
            client_id: Related client
            metadata: Additional context

        Returns:
            Alert UUID
        """
        return await self.create_alert(
            alert_type=AlertType.BRIGHT_DATA_ERROR,
            title="🔴 Bright Data API Error",
            message=f"Bright Data API failed after {retry_count} retries. "
                   f"Error: {error_message}. Enrichment pipeline may be blocked.",
            client_id=client_id,
            metadata={**(metadata or {}), "retry_count": retry_count, "error": error_message},
        )

    async def alert_hunter_rate_limit(
        self,
        client_id: UUID | None = None,
        requests_remaining: int = 0,
        reset_time: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Alert: Hunter rate limit hit with estimated recovery time.

        Args:
            client_id: Related client
            requests_remaining: Remaining requests
            reset_time: When rate limit resets
            metadata: Additional context

        Returns:
            Alert UUID
        """
        recovery_msg = ""
        if reset_time:
            recovery_msg = f" Estimated recovery: {reset_time.strftime('%Y-%m-%d %H:%M UTC')}"
        
        return await self.create_alert(
            alert_type=AlertType.HUNTER_RATE_LIMIT,
            title="⚠️ Hunter Rate Limit Hit",
            message=f"Hunter API rate limit reached. Remaining requests: {requests_remaining}.{recovery_msg}",
            client_id=client_id,
            metadata={
                **(metadata or {}),
                "requests_remaining": requests_remaining,
                "reset_time": reset_time.isoformat() if reset_time else None,
            },
        )

    async def alert_linkedin_rate_limit(
        self,
        client_id: UUID,
        seat_id: str,
        daily_limit: int,
        actions_today: int,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Alert: LinkedIn daily rate limit reached per seat.

        Args:
            client_id: Client UUID
            seat_id: LinkedIn seat/account ID
            daily_limit: Daily action limit
            actions_today: Actions performed today
            metadata: Additional context

        Returns:
            Alert UUID
        """
        return await self.create_alert(
            alert_type=AlertType.LINKEDIN_RATE_LIMIT,
            title="⚠️ LinkedIn Daily Limit Reached",
            message=f"LinkedIn seat {seat_id} has reached daily limit. "
                   f"Actions: {actions_today}/{daily_limit}. Will resume tomorrow.",
            client_id=client_id,
            metadata={
                **(metadata or {}),
                "seat_id": seat_id,
                "daily_limit": daily_limit,
                "actions_today": actions_today,
            },
        )

    async def alert_warmup_health_low(
        self,
        client_id: UUID,
        domain: str,
        health_score: float,
        threshold: float,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Alert: Email warmup health score dropped below threshold.

        Args:
            client_id: Client UUID
            domain: Email domain
            health_score: Current health score
            threshold: Required threshold
            metadata: Additional context

        Returns:
            Alert UUID
        """
        return await self.create_alert(
            alert_type=AlertType.WARMUP_HEALTH_LOW,
            title="🔴 Email Warmup Health Critical",
            message=f"Domain {domain} health score dropped to {health_score:.1f}% "
                   f"(threshold: {threshold:.1f}%). Outreach may be paused to protect reputation.",
            client_id=client_id,
            metadata={
                **(metadata or {}),
                "domain": domain,
                "health_score": health_score,
                "threshold": threshold,
            },
            send_email=True,  # Always email for warmup issues
        )

    async def alert_hot_warm_ratio_low(
        self,
        client_id: UUID,
        campaign_id: UUID,
        hot_warm_ratio: float,
        threshold: float = 20.0,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Alert: Hot+Warm ratio dropped below 20% in active campaign.

        Args:
            client_id: Client UUID
            campaign_id: Campaign UUID
            hot_warm_ratio: Current Hot+Warm percentage
            threshold: Required threshold (default 20%)
            metadata: Additional context

        Returns:
            Alert UUID
        """
        return await self.create_alert(
            alert_type=AlertType.HOT_WARM_RATIO_LOW,
            title="⚠️ Lead Quality Declining",
            message=f"Campaign Hot+Warm ratio dropped to {hot_warm_ratio:.1f}% "
                   f"(below {threshold:.1f}% threshold). Consider pausing for discovery.",
            client_id=client_id,
            campaign_id=campaign_id,
            metadata={
                **(metadata or {}),
                "hot_warm_ratio": hot_warm_ratio,
                "threshold": threshold,
            },
            send_email=True,
        )

    async def alert_quota_shortfall(
        self,
        client_id: UUID,
        campaign_id: UUID,
        shortfall: int,
        loops_run: int,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Alert: Batch quota shortfall after 3 replacement loops.

        Args:
            client_id: Client UUID
            campaign_id: Campaign UUID
            shortfall: Number of leads still needed
            loops_run: Discovery loops attempted
            metadata: Additional context

        Returns:
            Alert UUID
        """
        return await self.create_alert(
            alert_type=AlertType.QUOTA_SHORTFALL,
            title="🔴 Lead Quota Shortfall",
            message=f"Campaign is {shortfall} leads short after {loops_run} discovery attempts. "
                   f"Manual intervention required to meet quota.",
            client_id=client_id,
            campaign_id=campaign_id,
            metadata={
                **(metadata or {}),
                "shortfall": shortfall,
                "discovery_loops_run": loops_run,
            },
            send_email=True,
        )

    async def alert_angry_complaint(
        self,
        client_id: UUID,
        lead_id: UUID,
        lead_name: str,
        lead_company: str,
        message_preview: str,
        campaign_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Alert: Angry/complaint reply requiring immediate attention.

        Args:
            client_id: Client UUID
            lead_id: Lead UUID
            lead_name: Lead's full name
            lead_company: Lead's company
            message_preview: Preview of the angry message
            campaign_id: Related campaign UUID
            metadata: Additional context

        Returns:
            Alert UUID
        """
        return await self.create_alert(
            alert_type=AlertType.ANGRY_COMPLAINT,
            title="🔴 Angry/Complaint Reply",
            message=f"Angry or complaint reply received from {lead_name} ({lead_company}). "
                   f"Preview: {message_preview[:100]}... Requires immediate attention.",
            client_id=client_id,
            campaign_id=campaign_id,
            lead_id=lead_id,
            metadata={
                **(metadata or {}),
                "lead_name": lead_name,
                "lead_company": lead_company,
                "message_preview": message_preview,
            },
            send_email=True,
        )

    async def flag_reply_for_review(
        self,
        lead_id: UUID,
        confidence: float,
        intent: str,
        message_preview: str,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Flag reply for human review (confidence <60%).

        This creates a review queue entry, NOT an alert.

        Args:
            lead_id: Lead UUID
            confidence: Classification confidence
            intent: Detected intent
            message_preview: First 200 chars of message
            metadata: Additional context

        Returns:
            Review queue entry UUID
        """
        try:
            result = await self.session.execute(
                text("""
                    INSERT INTO human_review_queue (
                        lead_id, review_type, priority, status,
                        data, created_at
                    ) VALUES (
                        :lead_id, 'reply_classification', 
                        CASE WHEN :confidence < 0.4 THEN 'high' ELSE 'medium' END,
                        'pending',
                        :data, NOW()
                    )
                    RETURNING id
                """),
                {
                    "lead_id": str(lead_id),
                    "confidence": confidence,
                    "data": json.dumps({
                        "confidence": confidence,
                        "intent": intent,
                        "message_preview": message_preview,
                        **(metadata or {}),
                    }),
                },
            )
            row = result.fetchone()
            await self.session.commit()

            logger.info(f"Flagged reply for human review: lead {lead_id}, confidence {confidence:.1%}")
            return row.id if row else None

        except Exception as e:
            logger.error(f"Failed to flag reply for review: {e}")
            return None


# =============================================================================
# SINGLETON & HELPERS
# =============================================================================

_alert_service: AlertService | None = None


def get_alert_service(session: AsyncSession) -> AlertService:
    """Get alert service instance for the given session."""
    return AlertService(session)


async def create_alert(
    session: AsyncSession,
    alert_type: str,
    title: str,
    message: str,
    **kwargs,
) -> UUID | None:
    """Convenience function to create an alert."""
    service = get_alert_service(session)
    return await service.create_alert(alert_type, title, message, **kwargs)


# =============================================================================
# VERIFICATION CHECKLIST
# =============================================================================
# [x] Contract comment at top
# [x] AlertType constants for all specified types (including angry_complaint)
# [x] Severity mapping per alert type
# [x] create_alert creates Supabase notification record
# [x] Dashboard flag set for client
# [x] Email sent to agency owner for campaign-level issues
# [x] alert_angry_complaint (immediate + email)
# [x] alert_bright_data_error (after 2 retries)
# [x] alert_hunter_rate_limit (with estimated recovery time)
# [x] alert_linkedin_rate_limit (per seat)
# [x] alert_warmup_health_low (below threshold)
# [x] alert_hot_warm_ratio_low (below 20%)
# [x] alert_quota_shortfall (after 3 loops)
# [x] flag_reply_for_review (confidence <60%, human review queue)
# [x] All methods async with type hints
# [x] All methods have docstrings
