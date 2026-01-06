"""
FILE: src/detectors/how_detector.py
PURPOSE: HOW Detector - Analyzes channel sequences that correlate with conversions
PHASE: 16 (Conversion Intelligence), Updated Phase 24C, 24D
TASK: 16D, ENGAGE-007, THREAD-008
DEPENDENCIES:
  - src/detectors/base.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Detectors can import from models only

HOW Pattern Outputs:
  - channel_effectiveness: Which channels convert best
  - sequence_patterns: Which channel sequences convert
  - tier_channel_effectiveness: Channel effectiveness by ALS tier
  - multi_channel_lift: Lift from using multiple channels
  - email_engagement_correlation: Open/click patterns that predict conversion (Phase 24C)
  - channel_conversation_quality: Conversation metrics by channel (Phase 24D)
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.detectors.base import BaseDetector
from src.models.activity import Activity
from src.models.base import LeadStatus
from src.models.conversion_patterns import ConversionPattern
from src.models.lead import Lead


class HowDetector(BaseDetector):
    """
    HOW Detector - Analyzes which channel strategies predict conversions.

    Analyzes:
    - Channel effectiveness (which channels convert?)
    - Sequence patterns (which channel orders convert?)
    - Tier-based channel effectiveness
    - Multi-channel vs single-channel lift
    - Email engagement correlation (Phase 24C)
    - Conversation quality by channel (Phase 24D)
    """

    pattern_type = "how"

    async def detect(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> ConversionPattern:
        """
        Run HOW pattern detection for a client.

        Analyzes channel usage patterns across lead journeys.
        """
        # Get leads with activities
        leads_data = await self._get_leads_with_channels(db, client_id)

        if len(leads_data) < self.min_sample_size:
            return await self.save_pattern(
                db=db,
                client_id=client_id,
                patterns=self._default_patterns(),
                sample_size=len(leads_data),
                confidence=self.calculate_confidence(len(leads_data)),
            )

        converting = [l for l in leads_data if l["converted"]]
        baseline_rate = len(converting) / len(leads_data) if leads_data else 0

        # Analyze each dimension
        channel_effectiveness = self._analyze_channels(leads_data, baseline_rate)
        sequence_patterns = self._analyze_sequences(leads_data, baseline_rate)
        tier_effectiveness = self._analyze_tier_channels(leads_data, baseline_rate)
        multi_channel = self._analyze_multi_channel(leads_data, baseline_rate)

        # Phase 24C: Analyze email engagement correlation
        engagement_correlation = await self._analyze_engagement_correlation(db, client_id)

        # Phase 24D: Analyze conversation quality by channel
        conversation_quality = await self._analyze_channel_conversations(db, client_id)

        patterns = {
            "type": "how",
            "version": "2.1",  # Updated for Phase 24C
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": len(leads_data),
            "baseline_conversion_rate": round(baseline_rate, 4),
            "channel_effectiveness": channel_effectiveness,
            "sequence_patterns": sequence_patterns,
            "tier_channel_effectiveness": tier_effectiveness,
            "multi_channel_lift": multi_channel,
            "email_engagement_correlation": engagement_correlation,  # Phase 24C
            "channel_conversation_quality": conversation_quality,  # Phase 24D
        }

        return await self.save_pattern(
            db=db,
            client_id=client_id,
            patterns=patterns,
            sample_size=len(leads_data),
            confidence=self.calculate_confidence(len(leads_data)),
        )

    async def _get_leads_with_channels(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get leads with their channel usage data."""
        cutoff = datetime.utcnow() - timedelta(days=90)

        # Get leads with outcomes
        leads_stmt = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.status.in_([
                    LeadStatus.CONVERTED,
                    LeadStatus.BOUNCED,
                    LeadStatus.OPT_OUT,
                    LeadStatus.NURTURING,
                ]),
                Lead.created_at >= cutoff,
                Lead.deleted_at.is_(None),
            )
        )

        leads_result = await db.execute(leads_stmt)
        leads = list(leads_result.scalars().all())

        # Get activities for these leads
        lead_ids = [l.id for l in leads]
        if not lead_ids:
            return []

        activities_stmt = select(Activity).where(
            and_(
                Activity.lead_id.in_(lead_ids),
                Activity.action.in_(["sent", "email_sent", "sms_sent", "linkedin_sent", "voice_completed"]),
            )
        ).order_by(Activity.lead_id, Activity.created_at)

        activities_result = await db.execute(activities_stmt)
        activities = list(activities_result.scalars().all())

        # Group activities by lead
        lead_activities: dict[UUID, list[Activity]] = defaultdict(list)
        for activity in activities:
            lead_activities[activity.lead_id].append(activity)

        # Build lead data
        leads_data = []
        for lead in leads:
            acts = lead_activities.get(lead.id, [])
            channels_used = list(set(a.channel.value for a in acts if a.channel))
            sequence = [a.channel.value for a in acts if a.channel]

            leads_data.append({
                "lead_id": lead.id,
                "converted": lead.status == LeadStatus.CONVERTED,
                "als_tier": lead.als_tier,
                "als_score": lead.als_score,
                "channels_used": channels_used,
                "channel_sequence": sequence[:6],  # First 6 touches
                "touch_count": len(acts),
            })

        return leads_data

    def _analyze_channels(
        self,
        leads_data: list[dict[str, Any]],
        baseline_rate: float,
    ) -> list[dict[str, Any]]:
        """Analyze effectiveness of each channel."""
        channel_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "converted": 0}
        )

        for lead in leads_data:
            for channel in lead["channels_used"]:
                channel_stats[channel]["total"] += 1
                if lead["converted"]:
                    channel_stats[channel]["converted"] += 1

        results = []
        for channel, stats in channel_stats.items():
            if stats["total"] < 5:
                continue
            rate = stats["converted"] / stats["total"]
            lift = self.calculate_lift(rate, baseline_rate)

            results.append({
                "channel": channel,
                "conversion_rate": round(rate, 4),
                "sample": stats["total"],
                "lift": round(lift, 2),
            })

        results.sort(key=lambda x: x["conversion_rate"], reverse=True)
        return results

    def _analyze_sequences(
        self,
        leads_data: list[dict[str, Any]],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze channel sequence patterns."""
        sequence_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "converted": 0}
        )

        for lead in leads_data:
            seq = lead["channel_sequence"]
            if len(seq) < 2:
                continue

            # First 3 channels as sequence key
            seq_key = "→".join(seq[:3])
            sequence_stats[seq_key]["total"] += 1
            if lead["converted"]:
                sequence_stats[seq_key]["converted"] += 1

        winning = []
        for seq, stats in sequence_stats.items():
            if stats["total"] < 3:
                continue
            rate = stats["converted"] / stats["total"]
            if rate > baseline_rate:
                winning.append({
                    "sequence": seq,
                    "conversion_rate": round(rate, 4),
                    "sample": stats["total"],
                })

        winning.sort(key=lambda x: x["conversion_rate"], reverse=True)
        return {"winning_sequences": winning[:5]}

    def _analyze_tier_channels(
        self,
        leads_data: list[dict[str, Any]],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze channel effectiveness by ALS tier."""
        tier_channel_stats: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"total": 0, "converted": 0})
        )

        for lead in leads_data:
            tier = lead.get("als_tier") or "unknown"
            for channel in lead["channels_used"]:
                tier_channel_stats[tier][channel]["total"] += 1
                if lead["converted"]:
                    tier_channel_stats[tier][channel]["converted"] += 1

        result = {}
        for tier, channel_data in tier_channel_stats.items():
            tier_results = []
            for channel, stats in channel_data.items():
                if stats["total"] < 3:
                    continue
                rate = stats["converted"] / stats["total"]
                tier_results.append({
                    "channel": channel,
                    "conversion_rate": round(rate, 4),
                    "sample": stats["total"],
                })
            tier_results.sort(key=lambda x: x["conversion_rate"], reverse=True)
            result[tier] = tier_results[:3]

        return result

    def _analyze_multi_channel(
        self,
        leads_data: list[dict[str, Any]],
        baseline_rate: float,
    ) -> dict[str, Any]:
        """Analyze lift from multi-channel vs single-channel."""
        single_stats = {"total": 0, "converted": 0}
        multi_stats = {"total": 0, "converted": 0}

        for lead in leads_data:
            num_channels = len(lead["channels_used"])
            if num_channels == 1:
                single_stats["total"] += 1
                if lead["converted"]:
                    single_stats["converted"] += 1
            elif num_channels > 1:
                multi_stats["total"] += 1
                if lead["converted"]:
                    multi_stats["converted"] += 1

        single_rate = (
            single_stats["converted"] / single_stats["total"]
            if single_stats["total"] > 0 else 0
        )
        multi_rate = (
            multi_stats["converted"] / multi_stats["total"]
            if multi_stats["total"] > 0 else 0
        )

        lift = multi_rate / single_rate if single_rate > 0 else 1.0

        return {
            "single_channel_rate": round(single_rate, 4),
            "multi_channel_rate": round(multi_rate, 4),
            "multi_channel_lift": round(lift, 2),
            "recommendation": "multi" if lift > 1.2 else "single",
        }

    async def _analyze_engagement_correlation(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """
        Analyze email engagement patterns that correlate with conversion (Phase 24C).

        This helps CIS learn which engagement signals predict conversion.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Engagement correlation metrics
        """
        query = text("""
            WITH email_activities AS (
                SELECT
                    a.lead_id,
                    a.email_opened,
                    a.email_clicked,
                    a.email_open_count,
                    a.email_click_count,
                    a.time_to_open_minutes,
                    a.time_to_click_minutes,
                    l.status,
                    CASE WHEN l.status = 'converted' THEN TRUE ELSE FALSE END as converted
                FROM activities a
                JOIN leads l ON l.id = a.lead_id
                WHERE a.client_id = :client_id
                AND a.channel = 'email'
                AND a.action IN ('sent', 'email_sent')
                AND a.created_at >= NOW() - INTERVAL '90 days'
                AND l.deleted_at IS NULL
            )
            SELECT
                -- Overall engagement rates
                COUNT(*) as total_emails,
                COUNT(*) FILTER (WHERE email_opened) as opened,
                COUNT(*) FILTER (WHERE email_clicked) as clicked,
                COUNT(*) FILTER (WHERE converted) as converted,

                -- Conversion by engagement type
                COUNT(*) FILTER (WHERE email_opened AND converted) as opened_and_converted,
                COUNT(*) FILTER (WHERE email_clicked AND converted) as clicked_and_converted,
                COUNT(*) FILTER (WHERE NOT email_opened AND converted) as not_opened_but_converted,

                -- Click-to-open correlation
                COUNT(*) FILTER (WHERE email_clicked AND email_opened) as clicked_after_open,

                -- Time patterns (for converting leads)
                AVG(time_to_open_minutes) FILTER (WHERE converted AND time_to_open_minutes IS NOT NULL) as avg_convert_open_time,
                AVG(time_to_click_minutes) FILTER (WHERE converted AND time_to_click_minutes IS NOT NULL) as avg_convert_click_time,

                -- Repeat engagement
                AVG(email_open_count) FILTER (WHERE converted) as avg_opens_converted,
                AVG(email_open_count) FILTER (WHERE NOT converted) as avg_opens_not_converted
            FROM email_activities
        """)

        try:
            result = await db.execute(query, {"client_id": client_id})
            row = result.fetchone()

            if not row or row.total_emails == 0:
                return {}

            total = row.total_emails
            opened = row.opened or 0
            clicked = row.clicked or 0
            converted = row.converted or 0

            # Calculate conversion rates by engagement type
            open_conversion_rate = (
                row.opened_and_converted / opened * 100 if opened > 0 else 0
            )
            no_open_conversion_rate = (
                row.not_opened_but_converted / (total - opened) * 100
                if (total - opened) > 0 else 0
            )
            click_conversion_rate = (
                row.clicked_and_converted / clicked * 100 if clicked > 0 else 0
            )

            # Calculate lift from engagement
            baseline_conversion = converted / total * 100 if total > 0 else 0
            open_lift = open_conversion_rate / baseline_conversion if baseline_conversion > 0 else 1.0
            click_lift = click_conversion_rate / baseline_conversion if baseline_conversion > 0 else 1.0

            return {
                "sample_size": total,
                "open_rate": round(opened / total * 100, 2),
                "click_rate": round(clicked / total * 100, 2),
                "click_to_open_rate": round(row.clicked_after_open / opened * 100, 2) if opened > 0 else 0,

                # Conversion correlation
                "conversion_rate_if_opened": round(open_conversion_rate, 2),
                "conversion_rate_if_not_opened": round(no_open_conversion_rate, 2),
                "conversion_rate_if_clicked": round(click_conversion_rate, 2),

                # Lift calculations
                "open_conversion_lift": round(open_lift, 2),
                "click_conversion_lift": round(click_lift, 2),

                # Engagement depth insights
                "avg_opens_converted": round(float(row.avg_opens_converted or 0), 1),
                "avg_opens_not_converted": round(float(row.avg_opens_not_converted or 0), 1),

                # Timing insights
                "avg_time_to_open_converted": round(float(row.avg_convert_open_time or 0), 0),
                "avg_time_to_click_converted": round(float(row.avg_convert_click_time or 0), 0),

                # Recommendations
                "insights": self._generate_engagement_insights(
                    open_lift, click_lift,
                    float(row.avg_opens_converted or 0),
                    float(row.avg_opens_not_converted or 0)
                ),
            }

        except Exception:
            return {}

    def _generate_engagement_insights(
        self,
        open_lift: float,
        click_lift: float,
        avg_opens_converted: float,
        avg_opens_not_converted: float,
    ) -> list[str]:
        """Generate actionable insights from engagement data."""
        insights = []

        if open_lift > 1.5:
            insights.append("Email opens strongly predict conversion - focus on subject line optimization")
        elif open_lift < 0.8:
            insights.append("Opens don't correlate with conversion - consider testing different CTAs")

        if click_lift > 2.0:
            insights.append("Link clicks are a strong conversion signal - include clear CTAs in every email")
        elif click_lift > 1.0:
            insights.append("Clicks moderately predict conversion - A/B test different link placements")

        if avg_opens_converted > avg_opens_not_converted * 1.5:
            insights.append("Converting leads open emails multiple times - consider follow-up sequences for re-openers")

        if not insights:
            insights.append("Collect more engagement data for actionable insights")

        return insights

    async def _analyze_channel_conversations(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """
        Analyze conversation quality metrics by channel (Phase 24D).

        This helps CIS learn which channels lead to better conversations,
        not just conversions.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Conversation quality metrics by channel
        """
        query = text("""
            SELECT
                ct.channel,
                COUNT(*) as thread_count,
                AVG(ct.message_count) as avg_messages,
                AVG(ct.their_message_count) as avg_lead_messages,
                AVG(ct.avg_their_response_minutes) as avg_lead_response_time,
                COUNT(*) FILTER (WHERE ct.outcome = 'converted' OR ct.outcome = 'meeting_booked') as converted,
                COUNT(*) FILTER (WHERE ct.outcome = 'rejected') as rejected,
                (
                    SELECT json_agg(t)
                    FROM (
                        SELECT sentiment, COUNT(*) as cnt
                        FROM thread_messages tm
                        WHERE tm.thread_id = ANY(ARRAY_AGG(ct.id))
                        AND tm.direction = 'inbound'
                        AND tm.sentiment IS NOT NULL
                        GROUP BY sentiment
                    ) t
                ) as sentiment_dist
            FROM conversation_threads ct
            WHERE ct.client_id = :client_id
            AND ct.created_at >= NOW() - INTERVAL '90 days'
            GROUP BY ct.channel
        """)

        try:
            result = await db.execute(query, {"client_id": client_id})
            rows = result.fetchall()

            channel_quality = {}
            for row in rows:
                channel = row.channel
                if not channel:
                    continue

                total = row.thread_count or 0
                converted = row.converted or 0

                channel_quality[channel] = {
                    "thread_count": total,
                    "avg_messages_per_thread": round(float(row.avg_messages or 0), 1),
                    "avg_lead_messages": round(float(row.avg_lead_messages or 0), 1),
                    "avg_lead_response_minutes": round(float(row.avg_lead_response_time or 0), 0),
                    "conversion_rate": round(converted / total * 100, 2) if total > 0 else 0,
                    "sentiment_distribution": row.sentiment_dist or [],
                }

            return channel_quality

        except Exception:
            # Return empty if query fails (tables might not exist yet)
            return {}

    def _default_patterns(self) -> dict[str, Any]:
        """Return default patterns when insufficient data."""
        return {
            "type": "how",
            "version": "2.1",
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": 0,
            "channel_effectiveness": [],
            "sequence_patterns": {"winning_sequences": []},
            "tier_channel_effectiveness": {},
            "multi_channel_lift": {
                "single_channel_rate": 0,
                "multi_channel_rate": 0,
                "multi_channel_lift": 1.0,
                "recommendation": "multi",
            },
            "email_engagement_correlation": {},  # Phase 24C
            "channel_conversation_quality": {},  # Phase 24D
            "note": "Insufficient data. Default to multi-channel strategy.",
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] Extends BaseDetector
# [x] pattern_type = "how"
# [x] detect() method implemented
# [x] Channel effectiveness analysis
# [x] Sequence pattern analysis
# [x] Tier-based channel analysis
# [x] Multi-channel lift analysis
# [x] All functions have type hints
# [x] All functions have docstrings
#
# Phase 24C Additions (ENGAGE-007):
# [x] _analyze_engagement_correlation() for open/click patterns
# [x] Conversion rate by engagement type (opened/clicked)
# [x] Open/click lift calculations
# [x] Engagement depth insights (avg opens)
# [x] _generate_engagement_insights() for actionable recommendations
#
# Phase 24D Additions (THREAD-008):
# [x] _analyze_channel_conversations() for conversation quality
# [x] Thread count and message averages by channel
# [x] Lead response time by channel
# [x] Sentiment distribution by channel
# [x] Updated version to 2.1
