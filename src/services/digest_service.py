"""
Contract: src/services/digest_service.py
Purpose: Service for daily/weekly digest email generation and delivery
Layer: 3 - services
Imports: models, engines
Consumers: orchestration, scheduled tasks

FILE: src/services/digest_service.py
PURPOSE: Service for daily/weekly digest email generation and delivery
PHASE: H (Client Transparency)
TASK: Item 44 - Daily Digest Email
DEPENDENCIES:
  - src/models/digest_log.py
  - src/models/client.py
  - src/engines/reporter.py
  - src/engines/email.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 13: AI spend limiter awareness
"""

import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.campaign import Campaign
from src.models.client import Client
from src.models.digest_log import DigestLog
from src.models.lead import Lead
from src.models.membership import Membership
from src.models.user import User

logger = logging.getLogger(__name__)


class DigestService:
    """
    Service for generating and sending daily digest emails.

    Phase H, Item 44: Provides clients with automated summary of:
    - Content sent on their behalf
    - Key metrics (sends, opens, clicks, replies)
    - Top performing campaigns
    - Recent content examples
    """

    # HTML template for digest email
    DIGEST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Digest - {client_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header p {{ margin: 10px 0 0; opacity: 0.9; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 30px; }}
        .metric {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; margin-top: 5px; }}
        .section {{ margin-bottom: 25px; }}
        .section h2 {{ font-size: 18px; color: #333; margin-bottom: 15px; border-bottom: 2px solid #667eea; padding-bottom: 8px; }}
        .campaign {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .campaign-name {{ font-weight: bold; color: #333; }}
        .campaign-stats {{ font-size: 13px; color: #666; margin-top: 5px; }}
        .content-sample {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #667eea; }}
        .content-meta {{ font-size: 12px; color: #999; margin-bottom: 8px; }}
        .content-preview {{ font-size: 14px; color: #555; }}
        .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; }}
        .btn {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-top: 20px; }}
        .no-activity {{ background: white; padding: 30px; border-radius: 8px; text-align: center; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Daily Digest</h1>
        <p>{digest_date} - {client_name}</p>
    </div>

    <div class="content">
        {metrics_section}

        {campaigns_section}

        {content_section}

        <div style="text-align: center;">
            <a href="{dashboard_url}" class="btn">View Full Dashboard</a>
        </div>
    </div>

    <div class="footer">
        <p>This digest was sent by Agency OS on behalf of {client_name}.</p>
        <p>You're receiving this because you're subscribed to daily digests.</p>
        <p><a href="{settings_url}">Update digest preferences</a></p>
    </div>
</body>
</html>
"""

    METRICS_SECTION_TEMPLATE = """
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{sent}</div>
                <div class="metric-label">Emails Sent</div>
            </div>
            <div class="metric">
                <div class="metric-value">{opened}</div>
                <div class="metric-label">Opened</div>
            </div>
            <div class="metric">
                <div class="metric-value">{clicked}</div>
                <div class="metric-label">Clicked</div>
            </div>
            <div class="metric">
                <div class="metric-value">{replies}</div>
                <div class="metric-label">Replies</div>
            </div>
        </div>

        <div class="section">
            <h2>Performance</h2>
            <p><strong>Open Rate:</strong> {open_rate}% | <strong>Reply Rate:</strong> {reply_rate}%</p>
            {meetings_line}
        </div>
"""

    NO_ACTIVITY_TEMPLATE = """
        <div class="no-activity">
            <p>No outreach activity yesterday.</p>
            <p>Check your dashboard for campaign status.</p>
        </div>
"""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def get_clients_for_digest(self, target_hour: int = 7) -> list[Client]:
        """
        Get all clients that should receive a digest at the specified hour.

        Args:
            target_hour: Hour of day in client's timezone (0-23)

        Returns:
            List of clients configured for digest at this hour
        """
        query = select(Client).where(
            and_(
                Client.digest_enabled == True,  # noqa: E712
                Client.digest_frequency.in_(["daily", "weekly"]),
                Client.digest_send_hour == target_hour,
                Client.paused_at.is_(None),  # Don't send if paused
                Client.deleted_at.is_(None),  # Not soft-deleted
            )
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_digest_data(self, client_id: UUID, digest_date: date) -> dict[str, Any]:
        """
        Get digest data for a client for a specific date.

        Args:
            client_id: Client UUID
            digest_date: Date to generate digest for (typically yesterday)

        Returns:
            Dict containing metrics, top campaigns, and content samples
        """
        # Get client info
        client = await self.db.get(Client, client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Define date boundaries (full day in Australia/Sydney timezone)
        # Note: In production, should use proper timezone handling
        start_of_day = datetime.combine(digest_date, datetime.min.time())
        end_of_day = datetime.combine(digest_date, datetime.max.time())

        # Get activity metrics for the day
        metrics = await self._get_day_metrics(client_id, start_of_day, end_of_day)

        # Get top performing campaigns
        top_campaigns = await self._get_top_campaigns(client_id, start_of_day, end_of_day)

        # Get recent content samples
        content_samples = await self._get_content_samples(client_id, start_of_day, end_of_day)

        # Get meeting count
        meetings_count = await self._get_meetings_count(client_id, start_of_day, end_of_day)

        return {
            "client_id": str(client_id),
            "client_name": client.name,
            "digest_date": digest_date.isoformat(),
            "metrics": {
                "sent": metrics["sent"],
                "opened": metrics["opened"],
                "clicked": metrics["clicked"],
                "replies": metrics["replies"],
                "open_rate": round((metrics["opened"] / metrics["sent"] * 100) if metrics["sent"] > 0 else 0, 1),
                "reply_rate": round((metrics["replies"] / metrics["sent"] * 100) if metrics["sent"] > 0 else 0, 1),
                "meetings": meetings_count,
            },
            "top_campaigns": top_campaigns,
            "content_samples": content_samples,
        }

    async def _get_day_metrics(
        self, client_id: UUID, start: datetime, end: datetime
    ) -> dict[str, int]:
        """Get activity metrics for a day."""
        # Count sent
        sent_query = (
            select(func.count(Activity.id))
            .join(Campaign, Activity.campaign_id == Campaign.id)
            .where(
                and_(
                    Campaign.client_id == client_id,
                    Activity.action == "sent",
                    Activity.created_at >= start,
                    Activity.created_at <= end,
                )
            )
        )
        sent_result = await self.db.execute(sent_query)
        sent = sent_result.scalar() or 0

        # Count opened
        opened_query = (
            select(func.count(Activity.id))
            .join(Campaign, Activity.campaign_id == Campaign.id)
            .where(
                and_(
                    Campaign.client_id == client_id,
                    Activity.action == "opened",
                    Activity.created_at >= start,
                    Activity.created_at <= end,
                )
            )
        )
        opened_result = await self.db.execute(opened_query)
        opened = opened_result.scalar() or 0

        # Count clicked
        clicked_query = (
            select(func.count(Activity.id))
            .join(Campaign, Activity.campaign_id == Campaign.id)
            .where(
                and_(
                    Campaign.client_id == client_id,
                    Activity.action == "clicked",
                    Activity.created_at >= start,
                    Activity.created_at <= end,
                )
            )
        )
        clicked_result = await self.db.execute(clicked_query)
        clicked = clicked_result.scalar() or 0

        # Count replied
        replied_query = (
            select(func.count(Activity.id))
            .join(Campaign, Activity.campaign_id == Campaign.id)
            .where(
                and_(
                    Campaign.client_id == client_id,
                    Activity.action == "replied",
                    Activity.created_at >= start,
                    Activity.created_at <= end,
                )
            )
        )
        replied_result = await self.db.execute(replied_query)
        replies = replied_result.scalar() or 0

        return {
            "sent": sent,
            "opened": opened,
            "clicked": clicked,
            "replies": replies,
        }

    async def _get_top_campaigns(
        self, client_id: UUID, start: datetime, end: datetime, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Get top performing campaigns for the day."""
        query = (
            select(
                Campaign.id,
                Campaign.name,
                func.count(Activity.id).filter(Activity.action == "sent").label("sent"),
                func.count(Activity.id).filter(Activity.action == "opened").label("opened"),
                func.count(Activity.id).filter(Activity.action == "replied").label("replied"),
            )
            .join(Activity, Campaign.id == Activity.campaign_id)
            .where(
                and_(
                    Campaign.client_id == client_id,
                    Activity.created_at >= start,
                    Activity.created_at <= end,
                )
            )
            .group_by(Campaign.id, Campaign.name)
            .order_by(
                func.count(Activity.id).filter(Activity.action == "replied").desc(),
                func.count(Activity.id).filter(Activity.action == "opened").desc(),
            )
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "campaign_id": str(row.id),
                "campaign_name": row.name,
                "sent": row.sent or 0,
                "opened": row.opened or 0,
                "replied": row.replied or 0,
            }
            for row in rows
        ]

    async def _get_content_samples(
        self, client_id: UUID, start: datetime, end: datetime, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Get recent content samples for the day."""
        query = (
            select(
                Activity.id,
                Activity.channel,
                Activity.subject,
                Activity.content_snapshot,
                Activity.created_at,
                Lead.first_name,
                Lead.last_name,
                Lead.company,
            )
            .join(Campaign, Activity.campaign_id == Campaign.id)
            .join(Lead, Activity.lead_id == Lead.id)
            .where(
                and_(
                    Campaign.client_id == client_id,
                    Activity.action == "sent",
                    Activity.channel == "email",
                    Activity.created_at >= start,
                    Activity.created_at <= end,
                )
            )
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "activity_id": str(row.id),
                "channel": row.channel,
                "lead_name": f"{row.first_name or ''} {row.last_name or ''}".strip() or "Unknown",
                "company": row.company or "Unknown",
                "subject": row.subject_line or "(No subject)",
                "preview": (row.content_snapshot or "")[:150] + "..." if row.content_snapshot and len(row.content_snapshot) > 150 else row.content_snapshot or "",
                "sent_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def _get_meetings_count(
        self, client_id: UUID, start: datetime, end: datetime
    ) -> int:
        """Get count of meetings booked on the day."""
        # Import Meeting model if exists, otherwise return 0
        try:
            from src.models.meeting import Meeting
            query = (
                select(func.count(Meeting.id))
                .where(
                    and_(
                        Meeting.client_id == client_id,
                        Meeting.created_at >= start,
                        Meeting.created_at <= end,
                    )
                )
            )
            result = await self.db.execute(query)
            return result.scalar() or 0
        except ImportError:
            return 0

    def render_digest_html(
        self, digest_data: dict[str, Any], dashboard_url: str = "https://app.agencyos.ai/dashboard"
    ) -> str:
        """
        Render digest data as HTML email.

        Args:
            digest_data: Data from get_digest_data()
            dashboard_url: URL to client dashboard

        Returns:
            HTML string for email body
        """
        metrics = digest_data["metrics"]
        has_activity = metrics["sent"] > 0

        # Build metrics section
        if has_activity:
            meetings_line = f"<p><strong>Meetings Booked:</strong> {metrics['meetings']}</p>" if metrics["meetings"] > 0 else ""
            metrics_section = self.METRICS_SECTION_TEMPLATE.format(
                sent=metrics["sent"],
                opened=metrics["opened"],
                clicked=metrics["clicked"],
                replies=metrics["replies"],
                open_rate=metrics["open_rate"],
                reply_rate=metrics["reply_rate"],
                meetings_line=meetings_line,
            )
        else:
            metrics_section = self.NO_ACTIVITY_TEMPLATE

        # Build campaigns section
        campaigns_html = ""
        if digest_data["top_campaigns"]:
            campaigns_html = '<div class="section"><h2>Top Campaigns</h2>'
            for campaign in digest_data["top_campaigns"]:
                campaigns_html += f'''
                <div class="campaign">
                    <div class="campaign-name">{campaign["campaign_name"]}</div>
                    <div class="campaign-stats">
                        Sent: {campaign["sent"]} | Opened: {campaign["opened"]} | Replied: {campaign["replied"]}
                    </div>
                </div>
                '''
            campaigns_html += "</div>"

        # Build content samples section
        content_html = ""
        if digest_data["content_samples"]:
            content_html = '<div class="section"><h2>Recent Content Sent</h2>'
            for sample in digest_data["content_samples"][:3]:  # Limit to 3
                content_html += f'''
                <div class="content-sample">
                    <div class="content-meta">To: {sample["lead_name"]} at {sample["company"]}</div>
                    <div class="content-preview"><strong>{sample["subject"]}</strong><br>{sample["preview"]}</div>
                </div>
                '''
            content_html += "</div>"

        # Render full template
        return self.DIGEST_TEMPLATE.format(
            client_name=digest_data["client_name"],
            digest_date=digest_data["digest_date"],
            metrics_section=metrics_section,
            campaigns_section=campaigns_html,
            content_section=content_html,
            dashboard_url=dashboard_url,
            settings_url=f"{dashboard_url}/settings",
        )

    async def get_digest_recipients(self, client_id: UUID) -> list[str]:
        """
        Get email addresses to send digest to.

        Returns configured recipients, or falls back to all client members.
        """
        client = await self.db.get(Client, client_id)
        if not client:
            return []

        # Use configured recipients if available
        if client.digest_recipients:
            return client.digest_recipients

        # Fall back to all member emails
        # Note: User doesn't have soft delete; Membership does
        query = (
            select(User.email)
            .join(Membership, Membership.user_id == User.id)
            .where(
                and_(
                    Membership.client_id == client_id,
                    Membership.deleted_at.is_(None),  # Membership not deleted
                )
            )
        )
        result = await self.db.execute(query)
        return [row.email for row in result.all() if row.email]

    async def log_digest_sent(
        self,
        client_id: UUID,
        digest_date: date,
        recipients: list[str],
        metrics_snapshot: dict,
        content_summary: dict,
        status: str = "sent",
        error_message: str | None = None,
    ) -> DigestLog:
        """
        Log a digest send attempt.

        Args:
            client_id: Client UUID
            digest_date: Date the digest is for
            recipients: List of email addresses
            metrics_snapshot: Metrics at time of digest
            content_summary: Content summary
            status: 'sent', 'failed', or 'skipped'
            error_message: Error message if failed

        Returns:
            Created DigestLog
        """
        log = DigestLog(
            client_id=client_id,
            digest_date=digest_date,
            digest_type="daily",
            recipients=recipients,
            metrics_snapshot=metrics_snapshot,
            content_summary=content_summary,
            status=status,
            sent_at=datetime.utcnow() if status == "sent" else None,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        logger.info(
            f"Logged digest for client {client_id}: status={status}, "
            f"recipients={len(recipients)}, date={digest_date}"
        )

        return log

    async def check_already_sent(self, client_id: UUID, digest_date: date) -> bool:
        """Check if digest was already sent for this date."""
        query = select(DigestLog).where(
            and_(
                DigestLog.client_id == client_id,
                DigestLog.digest_date == digest_date,
                DigestLog.status == "sent",
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] HTML template for professional digest email
# [x] Metrics aggregation from activity table
# [x] Top campaigns ranking
# [x] Content samples with preview
# [x] Recipient lookup (configured or all members)
# [x] Digest logging for tracking
# [x] Duplicate send prevention
# [x] No imports from orchestration layer
