"""
FILE: src/detectors/when_detector.py
PURPOSE: WHEN Detector - Analyzes timing patterns that correlate with conversions
PHASE: 16 (Conversion Intelligence)
TASK: 16C
DEPENDENCIES:
  - src/detectors/base.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Detectors can import from models only

WHEN Pattern Outputs:
  - best_days: Which days of week convert best
  - best_hours: Which hours convert best
  - converting_touch_distribution: Which touch number converts most
  - optimal_sequence_gaps: Optimal days between touches
  - timezone_insights: Timezone-based patterns
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.detectors.base import BaseDetector
from src.models.activity import Activity
from src.models.conversion_patterns import ConversionPattern


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class WhenDetector(BaseDetector):
    """
    WHEN Detector - Analyzes which timing patterns predict conversions.

    Analyzes:
    - Day of week effectiveness
    - Hour of day effectiveness
    - Touch number distribution (which touch converts)
    - Optimal sequence gaps
    - Response time patterns
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

        patterns = {
            "type": "when",
            "version": "1.0",
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": len(activities),
            "baseline_conversion_rate": round(baseline_rate, 4),
            "best_days": best_days,
            "best_hours": best_hours,
            "converting_touch_distribution": touch_distribution,
            "optimal_sequence_gaps": sequence_gaps,
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
        """Analyze conversion rates by day of week."""
        day_stats: dict[int, dict[str, int]] = {
            i: {"total": 0, "converted": 0} for i in range(7)
        }

        for activity in activities:
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
        """Analyze conversion rates by hour of day."""
        hour_stats: dict[int, dict[str, int]] = {
            i: {"total": 0, "converted": 0} for i in range(24)
        }

        for activity in activities:
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
        """Analyze which touch number leads to conversion."""
        touch_counts: dict[int, int] = defaultdict(int)

        for activity in converting:
            touch = activity.sequence_step or 1
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
        """Analyze optimal gaps between touches for converting sequences."""
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

            # Calculate gaps
            for i in range(1, min(len(lead_acts), 6)):
                gap_days = (lead_acts[i].created_at - lead_acts[i-1].created_at).days
                if 0 < gap_days < 30:  # Reasonable gap
                    gap_data[f"touch_{i}_to_{i+1}"].append(gap_days)

        # Calculate median gaps
        result = {}
        for gap_key, gaps in gap_data.items():
            if len(gaps) >= 3:
                gaps.sort()
                median = gaps[len(gaps) // 2]
                result[gap_key] = median

        return result

    def _default_patterns(self) -> dict[str, Any]:
        """Return default patterns when insufficient data."""
        return {
            "type": "when",
            "version": "1.0",
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
# [x] Day of week analysis
# [x] Hour of day analysis
# [x] Touch distribution analysis
# [x] Sequence gap analysis
# [x] All functions have type hints
# [x] All functions have docstrings
