"""
FILE: src/detectors/funnel_detector.py
PURPOSE: Detector for downstream funnel patterns (meetings, deals, revenue)
PHASE: 24E (Downstream Outcomes)
TASK: OUTCOME-005
DEPENDENCIES:
  - src/detectors/base.py
  - src/models/conversion_patterns.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Detectors can import from models only

This detector analyzes downstream outcomes to learn:
- Which leads become good meetings (show rate patterns)
- Which meetings become deals (meeting-to-deal patterns)
- Which deals close (win rate patterns)
- What predicts lost deals (churn patterns)
- Which channels drive the most revenue (attribution patterns)
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.detectors.base import BaseDetector
from src.models.conversion_patterns import ConversionPattern


class FunnelDetector(BaseDetector):
    """
    Detector for downstream funnel conversion patterns.

    Learns from meetings, deals, and revenue data to understand
    what predicts successful outcomes beyond just booking meetings.
    """

    pattern_type = "funnel"
    min_sample_size = 20
    validity_days = 14

    async def detect(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> ConversionPattern:
        """
        Detect funnel conversion patterns for a client.

        Analyzes:
        1. Show rate patterns (what predicts attendance)
        2. Meeting-to-deal patterns (what predicts deals)
        3. Deal win patterns (what predicts closed-won)
        4. Lost deal patterns (why deals are lost)
        5. Revenue attribution patterns (which channels drive revenue)

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            ConversionPattern with funnel insights
        """
        # Check for existing valid pattern
        existing = await self.get_existing_pattern(db, client_id)
        if existing:
            return existing

        # Collect all pattern data
        patterns = {}
        total_samples = 0

        # 1. Show rate patterns
        show_patterns = await self._detect_show_patterns(db, client_id)
        patterns["show_rate"] = show_patterns
        total_samples += show_patterns.get("sample_size", 0)

        # 2. Meeting-to-deal patterns
        deal_patterns = await self._detect_deal_patterns(db, client_id)
        patterns["meeting_to_deal"] = deal_patterns
        total_samples += deal_patterns.get("sample_size", 0)

        # 3. Win rate patterns
        win_patterns = await self._detect_win_patterns(db, client_id)
        patterns["win_rate"] = win_patterns
        total_samples += win_patterns.get("sample_size", 0)

        # 4. Lost deal patterns
        lost_patterns = await self._detect_lost_patterns(db, client_id)
        patterns["lost_deals"] = lost_patterns

        # 5. Channel attribution
        attribution_patterns = await self._detect_attribution_patterns(db, client_id)
        patterns["channel_attribution"] = attribution_patterns

        # 6. Velocity patterns (time to close)
        velocity_patterns = await self._detect_velocity_patterns(db, client_id)
        patterns["velocity"] = velocity_patterns

        # Calculate overall confidence
        confidence = self._calculate_confidence(patterns, total_samples)

        # Save and return pattern
        return await self.save_pattern(
            db=db,
            client_id=client_id,
            patterns=patterns,
            sample_size=total_samples,
            confidence=confidence,
        )

    async def _detect_show_patterns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """Detect patterns that predict meeting attendance."""

        # Query show rate by various factors
        query = text("""
            WITH meeting_analysis AS (
                SELECT
                    m.*,
                    l.als_tier,
                    l.organization_industry,
                    l.organization_employee_count,
                    EXTRACT(DOW FROM m.scheduled_at) as day_of_week,
                    EXTRACT(HOUR FROM m.scheduled_at) as hour_of_day,
                    m.rescheduled_count,
                    m.confirmed,
                    m.reminder_sent
                FROM meetings m
                JOIN leads l ON l.id = m.lead_id
                WHERE m.client_id = :client_id
                AND m.scheduled_at <= NOW()
                AND m.showed_up IS NOT NULL
                AND m.booked_at >= NOW() - INTERVAL '90 days'
            )
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE showed_up = TRUE) as showed,

                -- By ALS tier
                COUNT(*) FILTER (WHERE als_tier = 'hot' AND showed_up) as hot_showed,
                COUNT(*) FILTER (WHERE als_tier = 'hot') as hot_total,
                COUNT(*) FILTER (WHERE als_tier = 'warm' AND showed_up) as warm_showed,
                COUNT(*) FILTER (WHERE als_tier = 'warm') as warm_total,
                COUNT(*) FILTER (WHERE als_tier = 'cool' AND showed_up) as cool_showed,
                COUNT(*) FILTER (WHERE als_tier = 'cool') as cool_total,

                -- By confirmation
                COUNT(*) FILTER (WHERE confirmed AND showed_up) as confirmed_showed,
                COUNT(*) FILTER (WHERE confirmed) as confirmed_total,
                COUNT(*) FILTER (WHERE NOT confirmed AND showed_up) as unconfirmed_showed,
                COUNT(*) FILTER (WHERE NOT confirmed) as unconfirmed_total,

                -- By reminder
                COUNT(*) FILTER (WHERE reminder_sent AND showed_up) as reminded_showed,
                COUNT(*) FILTER (WHERE reminder_sent) as reminded_total,

                -- By reschedule count
                COUNT(*) FILTER (WHERE rescheduled_count = 0 AND showed_up) as no_resched_showed,
                COUNT(*) FILTER (WHERE rescheduled_count = 0) as no_resched_total,
                COUNT(*) FILTER (WHERE rescheduled_count > 0 AND showed_up) as resched_showed,
                COUNT(*) FILTER (WHERE rescheduled_count > 0) as resched_total,

                -- By day of week
                MODE() WITHIN GROUP (ORDER BY day_of_week) FILTER (WHERE showed_up) as best_show_day,
                MODE() WITHIN GROUP (ORDER BY hour_of_day) FILTER (WHERE showed_up) as best_show_hour,

                -- By touches before booking
                AVG(touches_before_booking) FILTER (WHERE showed_up) as avg_touches_showed,
                AVG(touches_before_booking) FILTER (WHERE NOT showed_up) as avg_touches_no_show

            FROM meeting_analysis
        """)

        result = await db.execute(query, {"client_id": client_id})
        row = result.fetchone()

        if not row or row.total == 0:
            return {"sample_size": 0, "insights": []}

        insights = []

        # Overall show rate
        overall_rate = row.showed / row.total * 100 if row.total > 0 else 0

        # Confirmation impact
        if row.confirmed_total > 0 and row.unconfirmed_total > 0:
            confirmed_rate = row.confirmed_showed / row.confirmed_total * 100
            unconfirmed_rate = row.unconfirmed_showed / row.unconfirmed_total * 100
            if confirmed_rate > unconfirmed_rate + 10:
                insights.append({
                    "type": "confirmation_impact",
                    "message": f"Confirmed meetings show {confirmed_rate:.0f}% vs {unconfirmed_rate:.0f}% unconfirmed",
                    "impact": "high",
                    "action": "Always send confirmation requests",
                })

        # Reminder impact
        if row.reminded_total > 0:
            reminded_rate = row.reminded_showed / row.reminded_total * 100
            if reminded_rate > overall_rate + 5:
                insights.append({
                    "type": "reminder_impact",
                    "message": f"Reminded leads show {reminded_rate:.0f}% vs {overall_rate:.0f}% overall",
                    "impact": "medium",
                    "action": "Send reminders 24h before meetings",
                })

        # Reschedule impact
        if row.resched_total >= 5 and row.no_resched_total >= 5:
            resched_rate = row.resched_showed / row.resched_total * 100
            no_resched_rate = row.no_resched_showed / row.no_resched_total * 100
            if no_resched_rate > resched_rate + 10:
                insights.append({
                    "type": "reschedule_risk",
                    "message": f"First-time bookings show {no_resched_rate:.0f}% vs {resched_rate:.0f}% rescheduled",
                    "impact": "medium",
                    "action": "Minimize reschedules; confirm commitment",
                })

        # ALS tier impact
        tier_rates = {}
        if row.hot_total >= 5:
            tier_rates["hot"] = row.hot_showed / row.hot_total * 100
        if row.warm_total >= 5:
            tier_rates["warm"] = row.warm_showed / row.warm_total * 100
        if row.cool_total >= 5:
            tier_rates["cool"] = row.cool_showed / row.cool_total * 100

        if tier_rates:
            best_tier = max(tier_rates, key=tier_rates.get)
            insights.append({
                "type": "als_tier_impact",
                "tier_show_rates": tier_rates,
                "best_tier": best_tier,
                "message": f"{best_tier.upper()} leads have highest show rate ({tier_rates[best_tier]:.0f}%)",
            })

        return {
            "sample_size": row.total,
            "overall_rate": round(overall_rate, 1),
            "best_day": int(row.best_show_day) if row.best_show_day else None,
            "best_hour": int(row.best_show_hour) if row.best_show_hour else None,
            "insights": insights,
        }

    async def _detect_deal_patterns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """Detect patterns that predict meeting-to-deal conversion."""

        query = text("""
            WITH meeting_deal_analysis AS (
                SELECT
                    m.*,
                    l.als_tier,
                    l.organization_industry,
                    l.organization_employee_count,
                    m.meeting_outcome,
                    CASE WHEN d.id IS NOT NULL THEN TRUE ELSE FALSE END as became_deal,
                    d.value as deal_value,
                    d.won as deal_won
                FROM meetings m
                JOIN leads l ON l.id = m.lead_id
                LEFT JOIN deals d ON d.meeting_id = m.id
                WHERE m.client_id = :client_id
                AND m.showed_up = TRUE
                AND m.booked_at >= NOW() - INTERVAL '90 days'
            )
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE became_deal) as deals,
                COUNT(*) FILTER (WHERE became_deal AND deal_won) as won_deals,
                AVG(deal_value) FILTER (WHERE became_deal) as avg_deal_value,

                -- By outcome
                COUNT(*) FILTER (WHERE meeting_outcome = 'good' AND became_deal) as good_deals,
                COUNT(*) FILTER (WHERE meeting_outcome = 'good') as good_total,
                COUNT(*) FILTER (WHERE meeting_outcome = 'bad' AND became_deal) as bad_deals,
                COUNT(*) FILTER (WHERE meeting_outcome = 'bad') as bad_total,

                -- By ALS tier
                COUNT(*) FILTER (WHERE als_tier = 'hot' AND became_deal) as hot_deals,
                COUNT(*) FILTER (WHERE als_tier = 'hot') as hot_total,
                COUNT(*) FILTER (WHERE als_tier = 'warm' AND became_deal) as warm_deals,
                COUNT(*) FILTER (WHERE als_tier = 'warm') as warm_total,

                -- By company size
                AVG(organization_employee_count) FILTER (WHERE became_deal) as avg_employees_deal,
                AVG(organization_employee_count) FILTER (WHERE NOT became_deal) as avg_employees_no_deal

            FROM meeting_deal_analysis
        """)

        result = await db.execute(query, {"client_id": client_id})
        row = result.fetchone()

        if not row or row.total == 0:
            return {"sample_size": 0, "insights": []}

        insights = []
        deal_rate = row.deals / row.total * 100 if row.total > 0 else 0

        # Good vs bad meeting outcome
        if row.good_total >= 5 and row.bad_total >= 5:
            good_rate = row.good_deals / row.good_total * 100
            bad_rate = row.bad_deals / row.bad_total * 100 if row.bad_total > 0 else 0
            insights.append({
                "type": "outcome_impact",
                "good_meeting_deal_rate": round(good_rate, 1),
                "bad_meeting_deal_rate": round(bad_rate, 1),
                "message": f"Good meetings convert {good_rate:.0f}% vs {bad_rate:.0f}% for bad meetings",
            })

        # Company size impact
        if row.avg_employees_deal and row.avg_employees_no_deal:
            if row.avg_employees_deal > row.avg_employees_no_deal * 1.5:
                insights.append({
                    "type": "company_size_preference",
                    "avg_deal_employees": int(row.avg_employees_deal),
                    "avg_no_deal_employees": int(row.avg_employees_no_deal),
                    "message": f"Larger companies ({int(row.avg_employees_deal)} avg employees) more likely to become deals",
                })

        return {
            "sample_size": row.total,
            "meeting_to_deal_rate": round(deal_rate, 1),
            "avg_deal_value": float(row.avg_deal_value) if row.avg_deal_value else 0,
            "insights": insights,
        }

    async def _detect_win_patterns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """Detect patterns that predict deal wins."""

        query = text("""
            WITH deal_analysis AS (
                SELECT
                    d.*,
                    l.als_tier,
                    l.organization_industry,
                    l.organization_employee_count,
                    m.meeting_outcome,
                    m.touches_before_booking
                FROM deals d
                JOIN leads l ON l.id = d.lead_id
                LEFT JOIN meetings m ON m.id = d.meeting_id
                WHERE d.client_id = :client_id
                AND d.closed_at IS NOT NULL
                AND d.created_at >= NOW() - INTERVAL '180 days'
            )
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE won = TRUE) as won,
                AVG(value) FILTER (WHERE won = TRUE) as avg_won_value,
                AVG(value) FILTER (WHERE won = FALSE) as avg_lost_value,
                AVG(days_to_close) FILTER (WHERE won = TRUE) as avg_days_to_win,
                AVG(days_to_close) FILTER (WHERE won = FALSE) as avg_days_to_lose,
                AVG(touches_before_deal) FILTER (WHERE won = TRUE) as avg_touches_won,
                AVG(touches_before_deal) FILTER (WHERE won = FALSE) as avg_touches_lost,

                -- By first touch channel
                COUNT(*) FILTER (WHERE first_touch_channel = 'email' AND won) as email_won,
                COUNT(*) FILTER (WHERE first_touch_channel = 'email') as email_total,
                COUNT(*) FILTER (WHERE first_touch_channel = 'linkedin' AND won) as linkedin_won,
                COUNT(*) FILTER (WHERE first_touch_channel = 'linkedin') as linkedin_total,

                -- By ALS tier
                COUNT(*) FILTER (WHERE als_tier = 'hot' AND won) as hot_won,
                COUNT(*) FILTER (WHERE als_tier = 'hot') as hot_total

            FROM deal_analysis
        """)

        result = await db.execute(query, {"client_id": client_id})
        row = result.fetchone()

        if not row or row.total == 0:
            return {"sample_size": 0, "insights": []}

        insights = []
        win_rate = row.won / row.total * 100 if row.total > 0 else 0

        # Deal velocity insight
        if row.avg_days_to_win and row.avg_days_to_lose:
            if row.avg_days_to_win < row.avg_days_to_lose:
                insights.append({
                    "type": "velocity_indicator",
                    "avg_days_to_win": round(row.avg_days_to_win, 0),
                    "avg_days_to_lose": round(row.avg_days_to_lose, 0),
                    "message": f"Won deals close in {row.avg_days_to_win:.0f} days vs {row.avg_days_to_lose:.0f} for lost",
                    "action": "Deals stalling beyond average may be at risk",
                })

        # Touch count insight
        if row.avg_touches_won and row.avg_touches_lost:
            insights.append({
                "type": "touch_count",
                "avg_touches_won": round(row.avg_touches_won, 1),
                "avg_touches_lost": round(row.avg_touches_lost, 1),
            })

        # Channel win rates
        channel_rates = {}
        if row.email_total >= 5:
            channel_rates["email"] = row.email_won / row.email_total * 100
        if row.linkedin_total >= 5:
            channel_rates["linkedin"] = row.linkedin_won / row.linkedin_total * 100

        if len(channel_rates) >= 2:
            best_channel = max(channel_rates, key=channel_rates.get)
            insights.append({
                "type": "channel_win_rates",
                "rates": {k: round(v, 1) for k, v in channel_rates.items()},
                "best_channel": best_channel,
                "message": f"{best_channel} leads have highest win rate ({channel_rates[best_channel]:.0f}%)",
            })

        return {
            "sample_size": row.total,
            "win_rate": round(win_rate, 1),
            "avg_won_value": float(row.avg_won_value) if row.avg_won_value else 0,
            "avg_days_to_close": round(row.avg_days_to_win, 0) if row.avg_days_to_win else 0,
            "insights": insights,
        }

    async def _detect_lost_patterns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """Detect patterns in lost deals."""

        query = text("""
            SELECT
                lost_reason,
                COUNT(*) as count,
                SUM(value) as total_value,
                AVG(days_to_close) as avg_days
            FROM deals
            WHERE client_id = :client_id
            AND won = FALSE
            AND closed_at >= NOW() - INTERVAL '180 days'
            GROUP BY lost_reason
            ORDER BY count DESC
        """)

        result = await db.execute(query, {"client_id": client_id})
        rows = result.fetchall()

        if not rows:
            return {"sample_size": 0, "top_reasons": []}

        total = sum(row.count for row in rows)
        top_reasons = []

        for row in rows[:5]:  # Top 5 reasons
            percentage = row.count / total * 100
            top_reasons.append({
                "reason": row.lost_reason or "unknown",
                "count": row.count,
                "percentage": round(percentage, 1),
                "total_value_lost": float(row.total_value) if row.total_value else 0,
                "avg_days_in_pipeline": round(row.avg_days, 0) if row.avg_days else 0,
            })

        return {
            "sample_size": total,
            "top_reasons": top_reasons,
        }

    async def _detect_attribution_patterns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """Detect channel revenue attribution patterns."""

        query = text("""
            SELECT
                first_touch_channel,
                COUNT(*) FILTER (WHERE won = TRUE) as won_count,
                COUNT(*) as total_count,
                SUM(value) FILTER (WHERE won = TRUE) as won_value,
                AVG(value) FILTER (WHERE won = TRUE) as avg_deal_value
            FROM deals
            WHERE client_id = :client_id
            AND closed_at >= NOW() - INTERVAL '180 days'
            AND first_touch_channel IS NOT NULL
            GROUP BY first_touch_channel
            ORDER BY won_value DESC NULLS LAST
        """)

        result = await db.execute(query, {"client_id": client_id})
        rows = result.fetchall()

        if not rows:
            return {"sample_size": 0, "channels": []}

        total_revenue = sum(row.won_value or 0 for row in rows)
        channels = []

        for row in rows:
            revenue = float(row.won_value) if row.won_value else 0
            percentage = revenue / total_revenue * 100 if total_revenue > 0 else 0

            channels.append({
                "channel": row.first_touch_channel,
                "deals_won": row.won_count,
                "deals_total": row.total_count,
                "win_rate": round(row.won_count / row.total_count * 100, 1) if row.total_count > 0 else 0,
                "revenue": revenue,
                "revenue_percentage": round(percentage, 1),
                "avg_deal_value": float(row.avg_deal_value) if row.avg_deal_value else 0,
            })

        return {
            "sample_size": sum(row.total_count for row in rows),
            "total_revenue": total_revenue,
            "channels": channels,
        }

    async def _detect_velocity_patterns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """Detect deal velocity patterns."""

        query = text("""
            WITH stage_durations AS (
                SELECT
                    d.id,
                    d.won,
                    dsh.from_stage,
                    dsh.to_stage,
                    dsh.days_in_previous_stage
                FROM deals d
                JOIN deal_stage_history dsh ON dsh.deal_id = d.id
                WHERE d.client_id = :client_id
                AND d.closed_at >= NOW() - INTERVAL '180 days'
            )
            SELECT
                from_stage,
                AVG(days_in_previous_stage) FILTER (WHERE won = TRUE) as avg_days_won,
                AVG(days_in_previous_stage) FILTER (WHERE won = FALSE) as avg_days_lost,
                COUNT(*) FILTER (WHERE won = TRUE) as won_count,
                COUNT(*) FILTER (WHERE won = FALSE) as lost_count
            FROM stage_durations
            WHERE from_stage IS NOT NULL
            GROUP BY from_stage
            ORDER BY
                CASE from_stage
                    WHEN 'qualification' THEN 1
                    WHEN 'proposal' THEN 2
                    WHEN 'negotiation' THEN 3
                    WHEN 'verbal_commit' THEN 4
                    WHEN 'contract_sent' THEN 5
                END
        """)

        result = await db.execute(query, {"client_id": client_id})
        rows = result.fetchall()

        if not rows:
            return {"sample_size": 0, "stage_velocity": []}

        stage_velocity = []
        for row in rows:
            stage_velocity.append({
                "stage": row.from_stage,
                "avg_days_won": round(row.avg_days_won, 1) if row.avg_days_won else 0,
                "avg_days_lost": round(row.avg_days_lost, 1) if row.avg_days_lost else 0,
                "won_count": row.won_count,
                "lost_count": row.lost_count,
            })

        return {
            "sample_size": sum(row.won_count + row.lost_count for row in rows),
            "stage_velocity": stage_velocity,
        }

    def _calculate_confidence(
        self,
        patterns: dict[str, Any],
        total_samples: int,
    ) -> float:
        """Calculate overall confidence score."""

        if total_samples < self.min_sample_size:
            return 0.3

        # Base confidence on sample size
        if total_samples >= 100:
            base_confidence = 0.9
        elif total_samples >= 50:
            base_confidence = 0.7
        else:
            base_confidence = 0.5

        # Adjust based on insight quality
        total_insights = 0
        for section in ["show_rate", "meeting_to_deal", "win_rate"]:
            if section in patterns and "insights" in patterns[section]:
                total_insights += len(patterns[section]["insights"])

        if total_insights >= 5:
            base_confidence += 0.1
        elif total_insights >= 3:
            base_confidence += 0.05

        return min(base_confidence, 1.0)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Extends BaseDetector
# [x] pattern_type = "funnel"
# [x] Show rate pattern detection
# [x] Meeting-to-deal pattern detection
# [x] Win rate pattern detection
# [x] Lost deal pattern detection
# [x] Channel attribution detection
# [x] Velocity pattern detection
# [x] Confidence calculation
# [x] All methods have type hints
# [x] All methods have docstrings
