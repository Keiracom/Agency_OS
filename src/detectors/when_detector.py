"""
FILE: src/detectors/when_detector.py
PURPOSE: WHEN Detector - Analyzes timing patterns that correlate with conversions
PHASE: 16 (Conversion Intelligence), Updated Phase 24C
TASK: 16C, ENGAGE-006
DEPENDENCIES:
  - src/detectors/base.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Detectors can import from models only

WHEN Pattern Outputs:
  - best_days: Which days of week convert best (uses lead local time)
  - best_hours: Which hours convert best (uses lead local time)
  - converting_touch_distribution: Which touch number converts most
  - optimal_sequence_gaps: Optimal days between touches
  - engagement_timing: Time-to-open/click patterns for optimization (Phase 24C)
  - timezone_insights: Conversion patterns by timezone (Phase 24C)
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.detectors.base import BaseDetector
from src.models.activity import Activity
from src.models.conversion_patterns import ConversionPattern


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class WhenDetector(BaseDetector):
    """
    WHEN Detector - Analyzes which timing patterns predict conversions.

    Analyzes:
    - Day of week effectiveness (using lead local time when available)
    - Hour of day effectiveness (using lead local time when available)
    - Touch number distribution (which touch converts)
    - Optimal sequence gaps
    - Email engagement timing (time-to-open, time-to-click) - Phase 24C
    - Timezone-based patterns - Phase 24C
    """

    pattern_type = "when"

    async def detect(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> ConversionPattern:
        """
        Run WHEN pattern detection for a client.

        Analyzes activities with timing data to find patterns.
        """
        activities = await self._get_activities_with_timing(db, client_id)

        if len(activities) < self.min_sample_size:
            return await self.save_pattern(
                db=db,
                client_id=client_id,
                patterns=self._default_patterns(),
                sample_size=len(activities),
                confidence=self.calculate_confidence(len(activities)),
            )

        converting = [a for a in activities if a.led_to_booking]
        baseline_rate = len(converting) / len(activities) if activities else 0

        # Analyze each dimension
        best_days = self._analyze_days(activities, baseline_rate)
        best_hours = self._analyze_hours(activities, baseline_rate)
        touch_distribution = self._analyze_touch_distribution(converting, activities)
        sequence_gaps = self._analyze_sequence_gaps(activities, client_id)

        # Phase 24C: Engagement timing analysis
        engagement_timing = self._analyze_engagement_timing(activities)
        timezone_insights = await self._analyze_timezone_patterns(db, client_id)

        patterns = {
            "type": "when",
            "version": "2.0",  # Updated for Phase 24C
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": len(activities),
            "baseline_conversion_rate": round(baseline_rate, 4),
            "best_days": best_days,
            "best_hours": best_hours,
            "converting_touch_distribution": touch_distribution,
            "optimal_sequence_gaps": sequence_gaps,
            "engagement_timing": engagement_timing,  # Phase 24C
            "timezone_insights": timezone_insights,  # Phase 24C
        }

        return await self.save_pattern(
            db=db,
            client_id=client_id,
            patterns=patterns,
            sample_size=len(activities),
            confidence=self.calculate_confidence(len(activities)),
        )

    async def _get_activities_with_timing(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> list[Activity]:
        """Get outbound activities with timing data."""
        cutoff = datetime.utcnow() - timedelta(days=90)

        stmt = select(Activity).where(
            and_(
                Activity.client_id == client_id,
                Activity.action.in_(["sent", "email_sent", "sms_sent", "linkedin_sent"]),
                Activity.created_at >= cutoff,
            )
        ).order_by(Activity.lead_id, Activity.created_at)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    def _analyze_days(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> list[dict[str, Any]]:
        """
        Analyze conversion rates by day of week.

        Phase 24C: Uses lead_local_day_of_week when available
        for more accurate local time analysis.
        """
        day_stats: dict[int, dict[str, int]] = {
            i: {"total": 0, "converted": 0} for i in range(7)
        }

        for activity in activities:
            # Phase 24C: Use lead's local day of week if available
            if activity.lead_local_day_of_week is not None:
                day = activity.lead_local_day_of_week
            else:
                day = activity.created_at.weekday()

            day_stats[day]["total"] += 1
            if activity.led_to_booking:
                day_stats[day]["converted"] += 1

        results = []
        for day_index, stats in day_stats.items():
            if stats["total"] < 5:
                continue
            rate = stats["converted"] / stats["total"]
            results.append({
                "day": DAY_NAMES[day_index],
                "day_index": day_index,
                "conversion_rate": round(rate, 4),
                "sample": stats["total"],
            })

        results.sort(key=lambda x: x["conversion_rate"], reverse=True)
        return results[:5]

    def _analyze_hours(
        self,
        activities: list[Activity],
        baseline_rate: float,
    ) -> list[dict[str, Any]]:
        """
        Analyze conversion rates by hour of day.

        Phase 24C: Uses lead_local_time when available
        for more accurate local time analysis.
        """
        hour_stats: dict[int, dict[str, int]] = {
            i: {"total": 0, "converted": 0} for i in range(24)
        }

        for activity in activities:
            # Phase 24C: Use lead's local time if available
            if activity.lead_local_time is not None:
                hour = activity.lead_local_time.hour
            else:
                hour = activity.created_at.hour

            hour_stats[hour]["total"] += 1
            if activity.led_to_booking:
                hour_stats[hour]["converted"] += 1

        results = []
        for hour, stats in hour_stats.items():
            if stats["total"] < 5:
                continue
            rate = stats["converted"] / stats["total"]
            results.append({
                "hour": hour,
                "conversion_rate": round(rate, 4),
                "sample": stats["total"],
            })

        results.sort(key=lambda x: x["conversion_rate"], reverse=True)
        return results[:5]

    def _analyze_touch_distribution(
        self,
        converting: list[Activity],
        all_activities: list[Activity],
    ) -> dict[str, float]:
        """
        Analyze which touch number leads to conversion.

        Phase 24C: Uses touch_number field set by database trigger.
        """
        touch_counts: dict[int, int] = defaultdict(int)

        for activity in converting:
            # Phase 24C: Use touch_number from DB trigger, fallback to sequence_step
            touch = activity.touch_number or activity.sequence_step or 1
            touch_counts[touch] += 1

        total_conversions = len(converting)
        if total_conversions == 0:
            return {}

        distribution = {}
        for touch in range(1, 7):
            count = touch_counts.get(touch, 0)
            distribution[f"touch_{touch}"] = round(count / total_conversions, 2)

        return distribution

    def _analyze_sequence_gaps(
        self,
        activities: list[Activity],
        client_id: UUID,
    ) -> dict[str, int]:
        """
        Analyze optimal gaps between touches for converting sequences.

        Phase 24C: Uses days_since_last_touch field when available.
        """
        # Group by lead
        lead_activities: dict[UUID, list[Activity]] = defaultdict(list)
        for activity in activities:
            lead_activities[activity.lead_id].append(activity)

        # Calculate gaps for converting sequences
        gap_data: dict[str, list[int]] = defaultdict(list)

        for lead_id, lead_acts in lead_activities.items():
            # Sort by time
            lead_acts.sort(key=lambda a: a.created_at)

            # Check if any converted
            if not any(a.led_to_booking for a in lead_acts):
                continue

            # Calculate gaps using days_since_last_touch when available
            for i, act in enumerate(lead_acts[1:], 1):
                # Phase 24C: Use pre-calculated days_since_last_touch
                if act.days_since_last_touch is not None:
                    gap_days = act.days_since_last_touch
                else:
                    gap_days = (act.created_at - lead_acts[i-1].created_at).days

                if 0 <= gap_days < 30:  # Reasonable gap
                    touch_num = act.touch_number or (i + 1)
                    gap_data[f"touch_{touch_num-1}_to_{touch_num}"].append(gap_days)

        # Calculate median gaps
        result = {}
        for gap_key, gaps in gap_data.items():
            if len(gaps) >= 3:
                gaps.sort()
                median = gaps[len(gaps) // 2]
                result[gap_key] = median

        return result

    def _analyze_engagement_timing(
        self,
        activities: list[Activity],
    ) -> dict[str, Any]:
        """
        Analyze email engagement timing patterns (Phase 24C).

        Looks at time-to-open and time-to-click to find optimal patterns.
        """
        open_times: list[int] = []
        click_times: list[int] = []
        open_to_click_times: list[int] = []

        # For correlation with conversion
        opened_and_converted: list[int] = []
        clicked_and_converted: list[int] = []

        for activity in activities:
            if activity.time_to_open_minutes is not None:
                open_times.append(activity.time_to_open_minutes)
                if activity.led_to_booking:
                    opened_and_converted.append(activity.time_to_open_minutes)

            if activity.time_to_click_minutes is not None:
                click_times.append(activity.time_to_click_minutes)
                if activity.led_to_booking:
                    clicked_and_converted.append(activity.time_to_click_minutes)

                # Calculate open-to-click time
                if activity.time_to_open_minutes is not None:
                    open_to_click = activity.time_to_click_minutes - activity.time_to_open_minutes
                    if open_to_click > 0:
                        open_to_click_times.append(open_to_click)

        result = {}

        # Calculate averages and medians
        if open_times:
            open_times.sort()
            result["avg_time_to_open_minutes"] = round(sum(open_times) / len(open_times), 1)
            result["median_time_to_open_minutes"] = open_times[len(open_times) // 2]

        if click_times:
            click_times.sort()
            result["avg_time_to_click_minutes"] = round(sum(click_times) / len(click_times), 1)
            result["median_time_to_click_minutes"] = click_times[len(click_times) // 2]

        if open_to_click_times:
            open_to_click_times.sort()
            result["median_open_to_click_minutes"] = open_to_click_times[len(open_to_click_times) // 2]

        # Calculate optimal windows (when converting leads opened/clicked)
        if opened_and_converted:
            opened_and_converted.sort()
            # Find the window where most converting opens happened
            result["optimal_open_window_minutes"] = opened_and_converted[len(opened_and_converted) // 2]

        if clicked_and_converted:
            clicked_and_converted.sort()
            result["optimal_click_window_minutes"] = clicked_and_converted[len(clicked_and_converted) // 2]

        # Engagement rates
        total_email = len([a for a in activities if a.channel and a.channel.value == "email"])
        if total_email > 0:
            opened = len([a for a in activities if a.email_opened])
            clicked = len([a for a in activities if a.email_clicked])
            result["open_rate"] = round(opened / total_email * 100, 2)
            result["click_rate"] = round(clicked / total_email * 100, 2)
            if opened > 0:
                result["click_to_open_rate"] = round(clicked / opened * 100, 2)

        return result

    async def _analyze_timezone_patterns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any]:
        """
        Analyze conversion patterns by lead timezone (Phase 24C).

        Helps optimize send times for different geographic regions.
        """
        query = text("""
            SELECT
                a.lead_timezone,
                COUNT(*) as total_sent,
                COUNT(*) FILTER (WHERE a.email_opened = TRUE) as total_opened,
                COUNT(*) FILTER (WHERE a.email_clicked = TRUE) as total_clicked,
                AVG(a.time_to_open_minutes) FILTER (WHERE a.time_to_open_minutes IS NOT NULL) as avg_time_to_open,
                AVG(EXTRACT(HOUR FROM a.lead_local_time)) as avg_send_hour
            FROM activities a
            WHERE a.client_id = :client_id
            AND a.lead_timezone IS NOT NULL
            AND a.action IN ('sent', 'email_sent')
            AND a.created_at >= NOW() - INTERVAL '90 days'
            GROUP BY a.lead_timezone
            HAVING COUNT(*) >= 5
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)

        try:
            result = await db.execute(query, {"client_id": client_id})
            rows = result.fetchall()

            timezone_data = []
            for row in rows:
                total = row.total_sent or 0
                opened = row.total_opened or 0
                clicked = row.total_clicked or 0

                timezone_data.append({
                    "timezone": row.lead_timezone,
                    "sample": total,
                    "open_rate": round(opened / total * 100, 2) if total > 0 else 0,
                    "click_rate": round(clicked / total * 100, 2) if total > 0 else 0,
                    "avg_time_to_open": round(float(row.avg_time_to_open or 0), 0),
                    "avg_send_hour_local": round(float(row.avg_send_hour or 12), 1),
                })

            return {
                "by_timezone": timezone_data,
                "timezone_coverage": len([a for a in self._activities_cache if a.lead_timezone]) / len(self._activities_cache) if hasattr(self, '_activities_cache') and self._activities_cache else 0,
            }

        except Exception:
            return {"by_timezone": [], "timezone_coverage": 0}

    def _default_patterns(self) -> dict[str, Any]:
        """Return default patterns when insufficient data."""
        return {
            "type": "when",
            "version": "2.0",
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": 0,
            "best_days": [],
            "best_hours": [],
            "converting_touch_distribution": {},
            "optimal_sequence_gaps": {
                "touch_1_to_2": 2,
                "touch_2_to_3": 3,
                "touch_3_to_4": 4,
            },
            "engagement_timing": {},  # Phase 24C
            "timezone_insights": {"by_timezone": [], "timezone_coverage": 0},  # Phase 24C
            "note": "Insufficient data. Using default gaps.",
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] Extends BaseDetector
# [x] pattern_type = "when"
# [x] detect() method implemented
# [x] Day of week analysis (uses lead local day when available)
# [x] Hour of day analysis (uses lead local time when available)
# [x] Touch distribution analysis (uses touch_number field)
# [x] Sequence gap analysis (uses days_since_last_touch field)
# [x] All functions have type hints
# [x] All functions have docstrings
#
# Phase 24C Additions (ENGAGE-006):
# [x] _analyze_engagement_timing() for email open/click patterns
# [x] _analyze_timezone_patterns() for timezone-based insights
# [x] Uses lead_local_time and lead_local_day_of_week for accuracy
# [x] Updated version to 2.0
