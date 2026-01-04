"""
FILE: src/detectors/how_detector.py
PURPOSE: HOW Detector - Analyzes channel sequences that correlate with conversions
PHASE: 16 (Conversion Intelligence)
TASK: 16D
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
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
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

        patterns = {
            "type": "how",
            "version": "1.0",
            "computed_at": datetime.utcnow().isoformat(),
            "sample_size": len(leads_data),
            "baseline_conversion_rate": round(baseline_rate, 4),
            "channel_effectiveness": channel_effectiveness,
            "sequence_patterns": sequence_patterns,
            "tier_channel_effectiveness": tier_effectiveness,
            "multi_channel_lift": multi_channel,
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

    def _default_patterns(self) -> dict[str, Any]:
        """Return default patterns when insufficient data."""
        return {
            "type": "how",
            "version": "1.0",
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
