"""
Contract: src/engines/reporter.py
Purpose: Metrics aggregation and reporting engine
Layer: 3 - engines
Imports: models
Consumers: orchestration, API routes

FILE: src/engines/reporter.py
PURPOSE: Metrics aggregation and reporting engine
PHASE: 4 (Engines)
TASK: ENG-012
DEPENDENCIES:
  - src/engines/base.py
  - src/models/activity.py
  - src/models/campaign.py
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines
  - Rule 14: Soft delete checks in queries
"""

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import BaseEngine, EngineResult
from src.models.activity import Activity
from src.models.campaign import Campaign
from src.models.lead import Lead


class ReporterEngine(BaseEngine):
    """
    Reporter engine for metrics aggregation and reporting.

    Aggregates campaign metrics from activities:
    - Send rates per channel
    - Open/click rates for email
    - Reply rates
    - Conversion rates
    - ALS tier distribution
    """

    @property
    def name(self) -> str:
        return "reporter"

    async def get_campaign_metrics(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get comprehensive metrics for a campaign.

        Args:
            db: Database session (passed by caller)
            campaign_id: Campaign UUID
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            EngineResult with campaign metrics

        Raises:
            NotFoundError: If campaign not found
        """
        try:
            # Validate campaign exists
            campaign = await self.get_campaign_by_id(db, campaign_id)

            # Set default date range if not provided
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Get all activities for campaign in date range
            activities_query = select(Activity).where(
                and_(
                    Activity.campaign_id == campaign_id,
                    func.date(Activity.created_at) >= start_date,
                    func.date(Activity.created_at) <= end_date,
                )
            )
            result = await db.execute(activities_query)
            activities = result.scalars().all()

            # Calculate metrics by channel
            metrics = {
                "campaign_id": str(campaign_id),
                "campaign_name": campaign.name,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "channels": {},
                "overall": {
                    "total_sent": 0,
                    "total_delivered": 0,
                    "total_opened": 0,
                    "total_clicked": 0,
                    "total_replied": 0,
                    "total_bounced": 0,
                    "total_unsubscribed": 0,
                    "total_converted": 0,
                },
            }

            # Group activities by channel
            for activity in activities:
                channel = activity.channel.value
                action = activity.action

                # Initialize channel metrics if needed
                if channel not in metrics["channels"]:
                    metrics["channels"][channel] = {
                        "sent": 0,
                        "delivered": 0,
                        "opened": 0,
                        "clicked": 0,
                        "replied": 0,
                        "bounced": 0,
                        "unsubscribed": 0,
                        "converted": 0,
                    }

                # Count actions
                if action == "sent":
                    metrics["channels"][channel]["sent"] += 1
                    metrics["overall"]["total_sent"] += 1
                elif action == "delivered":
                    metrics["channels"][channel]["delivered"] += 1
                    metrics["overall"]["total_delivered"] += 1
                elif action == "opened":
                    metrics["channels"][channel]["opened"] += 1
                    metrics["overall"]["total_opened"] += 1
                elif action == "clicked":
                    metrics["channels"][channel]["clicked"] += 1
                    metrics["overall"]["total_clicked"] += 1
                elif action == "replied":
                    metrics["channels"][channel]["replied"] += 1
                    metrics["overall"]["total_replied"] += 1
                elif action == "bounced":
                    metrics["channels"][channel]["bounced"] += 1
                    metrics["overall"]["total_bounced"] += 1
                elif action == "unsubscribed":
                    metrics["channels"][channel]["unsubscribed"] += 1
                    metrics["overall"]["total_unsubscribed"] += 1
                elif action == "converted":
                    metrics["channels"][channel]["converted"] += 1
                    metrics["overall"]["total_converted"] += 1

            # Calculate rates for each channel
            for channel, stats in metrics["channels"].items():
                # Delivery rate
                stats["delivery_rate"] = (
                    (stats["delivered"] / stats["sent"] * 100) if stats["sent"] > 0 else 0.0
                )

                # Open rate (email only)
                if channel == "email":
                    stats["open_rate"] = (
                        (stats["opened"] / stats["delivered"] * 100)
                        if stats["delivered"] > 0
                        else 0.0
                    )
                    stats["click_rate"] = (
                        (stats["clicked"] / stats["opened"] * 100) if stats["opened"] > 0 else 0.0
                    )
                    stats["click_through_rate"] = (
                        (stats["clicked"] / stats["delivered"] * 100)
                        if stats["delivered"] > 0
                        else 0.0
                    )

                # Reply rate
                stats["reply_rate"] = (
                    (stats["replied"] / stats["sent"] * 100) if stats["sent"] > 0 else 0.0
                )

                # Conversion rate
                stats["conversion_rate"] = (
                    (stats["converted"] / stats["sent"] * 100) if stats["sent"] > 0 else 0.0
                )

                # Bounce rate
                stats["bounce_rate"] = (
                    (stats["bounced"] / stats["sent"] * 100) if stats["sent"] > 0 else 0.0
                )

            # Calculate overall rates
            overall = metrics["overall"]
            overall["delivery_rate"] = (
                (overall["total_delivered"] / overall["total_sent"] * 100)
                if overall["total_sent"] > 0
                else 0.0
            )
            overall["reply_rate"] = (
                (overall["total_replied"] / overall["total_sent"] * 100)
                if overall["total_sent"] > 0
                else 0.0
            )
            overall["conversion_rate"] = (
                (overall["total_converted"] / overall["total_sent"] * 100)
                if overall["total_sent"] > 0
                else 0.0
            )

            return EngineResult.ok(
                data=metrics,
                metadata={
                    "activities_count": len(activities),
                    "channels_used": list(metrics["channels"].keys()),
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={"campaign_id": str(campaign_id)},
            )

    async def get_client_metrics(
        self,
        db: AsyncSession,
        client_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get aggregated metrics for a client across all campaigns.

        Args:
            db: Database session (passed by caller)
            client_id: Client UUID
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            EngineResult with client metrics

        Raises:
            NotFoundError: If client not found
        """
        try:
            # Validate client exists
            client = await self.get_client_by_id(db, client_id)

            # Set default date range if not provided
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Get all campaigns for client (not deleted)
            campaigns_query = select(Campaign).where(
                and_(
                    Campaign.client_id == client_id,
                    Campaign.deleted_at.is_(None),
                )
            )
            campaigns_result = await db.execute(campaigns_query)
            campaigns = campaigns_result.scalars().all()

            # Get all activities for client in date range
            activities_query = select(Activity).where(
                and_(
                    Activity.client_id == client_id,
                    func.date(Activity.created_at) >= start_date,
                    func.date(Activity.created_at) <= end_date,
                )
            )
            result = await db.execute(activities_query)
            activities = result.scalars().all()

            # Calculate overall metrics
            metrics = {
                "client_id": str(client_id),
                "client_name": client.name,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "campaigns_count": len(campaigns),
                "campaigns": [],
                "overall": {
                    "total_sent": 0,
                    "total_delivered": 0,
                    "total_opened": 0,
                    "total_clicked": 0,
                    "total_replied": 0,
                    "total_bounced": 0,
                    "total_unsubscribed": 0,
                    "total_converted": 0,
                },
                "by_channel": {},
            }

            # Aggregate activities
            for activity in activities:
                channel = activity.channel.value
                action = activity.action

                # Initialize channel if needed
                if channel not in metrics["by_channel"]:
                    metrics["by_channel"][channel] = {
                        "sent": 0,
                        "delivered": 0,
                        "replied": 0,
                        "converted": 0,
                    }

                # Count actions
                if action == "sent":
                    metrics["overall"]["total_sent"] += 1
                    metrics["by_channel"][channel]["sent"] += 1
                elif action == "delivered":
                    metrics["overall"]["total_delivered"] += 1
                    metrics["by_channel"][channel]["delivered"] += 1
                elif action == "opened":
                    metrics["overall"]["total_opened"] += 1
                elif action == "clicked":
                    metrics["overall"]["total_clicked"] += 1
                elif action == "replied":
                    metrics["overall"]["total_replied"] += 1
                    metrics["by_channel"][channel]["replied"] += 1
                elif action == "bounced":
                    metrics["overall"]["total_bounced"] += 1
                elif action == "unsubscribed":
                    metrics["overall"]["total_unsubscribed"] += 1
                elif action == "converted":
                    metrics["overall"]["total_converted"] += 1
                    metrics["by_channel"][channel]["converted"] += 1

            # Calculate rates
            overall = metrics["overall"]
            overall["delivery_rate"] = (
                (overall["total_delivered"] / overall["total_sent"] * 100)
                if overall["total_sent"] > 0
                else 0.0
            )
            overall["reply_rate"] = (
                (overall["total_replied"] / overall["total_sent"] * 100)
                if overall["total_sent"] > 0
                else 0.0
            )
            overall["conversion_rate"] = (
                (overall["total_converted"] / overall["total_sent"] * 100)
                if overall["total_sent"] > 0
                else 0.0
            )

            # Get per-campaign summary
            for campaign in campaigns:
                campaign_activities = [a for a in activities if a.campaign_id == campaign.id]
                sent_count = sum(1 for a in campaign_activities if a.action == "sent")
                replied_count = sum(1 for a in campaign_activities if a.action == "replied")
                converted_count = sum(1 for a in campaign_activities if a.action == "converted")

                metrics["campaigns"].append(
                    {
                        "id": str(campaign.id),
                        "name": campaign.name,
                        "status": campaign.status.value,
                        "sent": sent_count,
                        "replied": replied_count,
                        "converted": converted_count,
                        "reply_rate": (replied_count / sent_count * 100) if sent_count > 0 else 0.0,
                    }
                )

            return EngineResult.ok(
                data=metrics,
                metadata={
                    "activities_count": len(activities),
                    "channels_used": list(metrics["by_channel"].keys()),
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={"client_id": str(client_id)},
            )

    async def get_als_distribution(
        self,
        db: AsyncSession,
        campaign_id: UUID | None = None,
        client_id: UUID | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get ALS tier distribution for leads.

        Args:
            db: Database session (passed by caller)
            campaign_id: Optional campaign UUID to filter by
            client_id: Optional client UUID to filter by

        Returns:
            EngineResult with ALS tier distribution

        Raises:
            ValidationError: If neither campaign_id nor client_id provided
        """
        try:
            if not campaign_id and not client_id:
                from src.exceptions import ValidationError

                raise ValidationError(
                    field="campaign_id/client_id",
                    message="Either campaign_id or client_id must be provided",
                )

            # Build query
            query = select(Lead.als_tier, func.count(Lead.id)).where(
                and_(
                    Lead.deleted_at.is_(None),
                    Lead.als_tier.isnot(None),
                )
            )

            if campaign_id:
                query = query.where(Lead.campaign_id == campaign_id)
            elif client_id:
                query = query.where(Lead.client_id == client_id)

            query = query.group_by(Lead.als_tier)

            # Execute query
            result = await db.execute(query)
            rows = result.all()

            # Build distribution
            distribution = {
                "hot": 0,
                "warm": 0,
                "cool": 0,
                "cold": 0,
                "dead": 0,
                "unscored": 0,
            }

            total = 0
            for tier, count in rows:
                distribution[tier] = count
                total += count

            # Calculate percentages
            percentages = {}
            for tier, count in distribution.items():
                percentages[tier] = (count / total * 100) if total > 0 else 0.0

            return EngineResult.ok(
                data={
                    "distribution": distribution,
                    "percentages": percentages,
                    "total_leads": total,
                },
                metadata={
                    "campaign_id": str(campaign_id) if campaign_id else None,
                    "client_id": str(client_id) if client_id else None,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "campaign_id": str(campaign_id) if campaign_id else None,
                    "client_id": str(client_id) if client_id else None,
                },
            )

    async def get_lead_engagement(
        self,
        db: AsyncSession,
        lead_id: UUID,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get engagement metrics for a specific lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID

        Returns:
            EngineResult with lead engagement metrics

        Raises:
            NotFoundError: If lead not found
        """
        try:
            # Get lead
            lead = await self.get_lead_by_id(db, lead_id)

            # Get all activities for lead
            activities_query = (
                select(Activity)
                .where(Activity.lead_id == lead_id)
                .order_by(Activity.created_at.desc())
            )
            result = await db.execute(activities_query)
            activities = result.scalars().all()

            # Calculate engagement metrics
            metrics = {
                "lead_id": str(lead_id),
                "lead_name": lead.full_name,
                "lead_email": lead.email,
                "als_score": lead.als_score,
                "als_tier": lead.als_tier,
                "status": lead.status.value,
                "timeline": [],
                "engagement_summary": {
                    "total_touches": 0,
                    "channels_used": set(),
                    "last_contacted": None,
                    "last_replied": None,
                    "reply_count": 0,
                    "open_count": 0,
                    "click_count": 0,
                    "is_engaged": False,
                },
            }

            # Process activities
            for activity in activities:
                # Add to timeline
                metrics["timeline"].append(
                    {
                        "date": activity.created_at.isoformat(),
                        "channel": activity.channel.value,
                        "action": activity.action,
                        "sequence_step": activity.sequence_step,
                    }
                )

                # Update summary
                metrics["engagement_summary"]["total_touches"] += 1
                metrics["engagement_summary"]["channels_used"].add(activity.channel.value)

                if (
                    activity.action == "sent"
                    and not metrics["engagement_summary"]["last_contacted"]
                ):
                    metrics["engagement_summary"]["last_contacted"] = (
                        activity.created_at.isoformat()
                    )

                if activity.action == "replied":
                    metrics["engagement_summary"]["reply_count"] += 1
                    if not metrics["engagement_summary"]["last_replied"]:
                        metrics["engagement_summary"]["last_replied"] = (
                            activity.created_at.isoformat()
                        )

                if activity.action == "opened":
                    metrics["engagement_summary"]["open_count"] += 1

                if activity.action == "clicked":
                    metrics["engagement_summary"]["click_count"] += 1

            # Convert set to list for JSON
            metrics["engagement_summary"]["channels_used"] = list(
                metrics["engagement_summary"]["channels_used"]
            )

            # Determine if engaged
            metrics["engagement_summary"]["is_engaged"] = (
                metrics["engagement_summary"]["reply_count"] > 0
                or metrics["engagement_summary"]["click_count"] > 0
                or metrics["engagement_summary"]["open_count"] > 1
            )

            return EngineResult.ok(
                data=metrics,
                metadata={
                    "activities_count": len(activities),
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={"lead_id": str(lead_id)},
            )

    async def get_daily_activity(
        self,
        db: AsyncSession,
        client_id: UUID,
        target_date: date | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get daily activity metrics for a client.

        Args:
            db: Database session (passed by caller)
            client_id: Client UUID
            target_date: Optional target date (defaults to today)

        Returns:
            EngineResult with daily activity metrics

        Raises:
            NotFoundError: If client not found
        """
        try:
            # Validate client exists
            await self.validate_client_active(db, client_id)

            # Set default date
            if not target_date:
                target_date = date.today()

            # Get all activities for client on target date
            activities_query = select(Activity).where(
                and_(
                    Activity.client_id == client_id,
                    func.date(Activity.created_at) == target_date,
                )
            )
            result = await db.execute(activities_query)
            activities = result.scalars().all()

            # Calculate daily metrics
            metrics = {
                "client_id": str(client_id),
                "date": target_date.isoformat(),
                "hourly_breakdown": {},
                "by_channel": {},
                "summary": {
                    "total_activities": len(activities),
                    "sent": 0,
                    "delivered": 0,
                    "opened": 0,
                    "clicked": 0,
                    "replied": 0,
                },
            }

            # Process activities
            for activity in activities:
                hour = activity.created_at.hour
                channel = activity.channel.value
                action = activity.action

                # Initialize hour if needed
                if hour not in metrics["hourly_breakdown"]:
                    metrics["hourly_breakdown"][hour] = 0
                metrics["hourly_breakdown"][hour] += 1

                # Initialize channel if needed
                if channel not in metrics["by_channel"]:
                    metrics["by_channel"][channel] = 0
                metrics["by_channel"][channel] += 1

                # Update summary
                if action == "sent":
                    metrics["summary"]["sent"] += 1
                elif action == "delivered":
                    metrics["summary"]["delivered"] += 1
                elif action == "opened":
                    metrics["summary"]["opened"] += 1
                elif action == "clicked":
                    metrics["summary"]["clicked"] += 1
                elif action == "replied":
                    metrics["summary"]["replied"] += 1

            return EngineResult.ok(
                data=metrics,
                metadata={
                    "peak_hour": max(
                        metrics["hourly_breakdown"], key=metrics["hourly_breakdown"].get
                    )
                    if metrics["hourly_breakdown"]
                    else None,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "client_id": str(client_id),
                    "date": target_date.isoformat() if target_date else None,
                },
            )


# Singleton instance
_reporter_engine: ReporterEngine | None = None


def get_reporter_engine() -> ReporterEngine:
    """Get or create Reporter engine instance."""
    global _reporter_engine
    if _reporter_engine is None:
        _reporter_engine = ReporterEngine()
    return _reporter_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete checks in queries (Rule 14)
# [x] Campaign metrics aggregation
# [x] Client metrics aggregation
# [x] ALS tier distribution
# [x] Lead engagement tracking
# [x] Daily activity metrics
# [x] Date range filtering
# [x] Per-channel metrics
# [x] Rate calculations (delivery, open, click, reply, conversion)
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
