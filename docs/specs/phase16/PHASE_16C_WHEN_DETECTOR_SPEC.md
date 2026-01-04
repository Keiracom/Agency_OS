# Phase 16C: WHEN Detector Specification

## Technical Specification Document

**Version**: 1.0  
**Date**: December 27, 2025  
**Depends On**: Phase 16A (Data Capture)  
**Status**: Ready for Development  
**Estimated Tasks**: 4  

---

## Overview

The WHEN Detector analyzes timing patterns of successful conversions. It answers: **"When should we reach out to maximize bookings?"**

**Output**: Patterns stored in `conversion_patterns` table with `pattern_type = 'when'`

**Consumers**: 
- Sequence Builder Skill (optimal gaps between touches)
- Allocator Engine (best days/hours to send)
- Scheduler (touch timing optimization)

---

## Algorithm Specification

### File: `src/algorithms/when_detector.py`

```python
"""
WHEN Detector Algorithm

Analyzes timing patterns of converting vs non-converting touches.
Pure statistical analysis - no AI in the loop.

Key Analyses:
1. Day of week effectiveness
2. Hour of day effectiveness
3. Touch position (which touch # converts)
4. Gap between touches (optimal spacing)
5. Time to conversion (how long from first touch to booking)
6. Sequence duration patterns
"""

from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List
import statistics
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from src.models.activity import Activity
from src.models.lead import Lead


# =============================================================================
# CONSTANTS
# =============================================================================

DAYS_OF_WEEK = [
    "Monday", "Tuesday", "Wednesday", "Thursday", 
    "Friday", "Saturday", "Sunday"
]

# Hour buckets for analysis
HOUR_BUCKETS = {
    "early_morning": (6, 8),    # 6am-8am
    "morning": (9, 11),          # 9am-11am
    "midday": (12, 13),          # 12pm-1pm
    "afternoon": (14, 16),       # 2pm-4pm
    "late_afternoon": (17, 18),  # 5pm-6pm
    "evening": (19, 21),         # 7pm-9pm
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DayPattern:
    day: str
    day_index: int  # 0=Monday, 6=Sunday
    conversion_rate: float
    sample: int
    lift: float = 1.0


@dataclass
class HourPattern:
    hour: int
    conversion_rate: float
    sample: int
    lift: float = 1.0


@dataclass
class TouchDistribution:
    """Which touch number leads to conversion"""
    distribution: dict = field(default_factory=dict)
    peak_touch: int = 3
    avg_touches_to_convert: float = 0.0


@dataclass
class GapPatterns:
    """Optimal days between touches"""
    touch_1_to_2: int = 2
    touch_2_to_3: int = 3
    touch_3_to_4: int = 4
    touch_4_to_5: int = 5
    touch_5_to_6: int = 7
    
    def to_dict(self) -> dict:
        return {
            "touch_1_to_2": self.touch_1_to_2,
            "touch_2_to_3": self.touch_2_to_3,
            "touch_3_to_4": self.touch_3_to_4,
            "touch_4_to_5": self.touch_4_to_5,
            "touch_5_to_6": self.touch_5_to_6,
        }


@dataclass
class ConversionTiming:
    """How long from first touch to booking"""
    avg_days: float = 0.0
    median_days: float = 0.0
    percentile_50: int = 0
    percentile_80: int = 0
    percentile_95: int = 0
    
    def to_dict(self) -> dict:
        return {
            "avg_days_to_convert": round(self.avg_days, 1),
            "median_days_to_convert": round(self.median_days, 1),
            "percentile_50": self.percentile_50,
            "percentile_80": self.percentile_80,
            "percentile_95": self.percentile_95,
        }


@dataclass
class WhenPatterns:
    """Complete WHEN pattern output"""
    best_days: List[DayPattern]
    best_hours: List[HourPattern]
    touch_distribution: TouchDistribution
    optimal_gaps: GapPatterns
    conversion_timing: ConversionTiming
    sample_size: int
    confidence: float
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for database storage"""
        return {
            "type": "when",
            "version": "1.0",
            "best_days": [
                {
                    "day": d.day,
                    "day_index": d.day_index,
                    "conversion_rate": d.conversion_rate,
                    "sample": d.sample,
                    "lift": d.lift
                }
                for d in self.best_days
            ],
            "best_hours": [
                {
                    "hour": h.hour,
                    "conversion_rate": h.conversion_rate,
                    "sample": h.sample,
                    "lift": h.lift
                }
                for h in self.best_hours
            ],
            "converting_touch_distribution": self.touch_distribution.distribution,
            "peak_converting_touch": self.touch_distribution.peak_touch,
            "avg_touches_to_convert": round(self.touch_distribution.avg_touches_to_convert, 1),
            "optimal_sequence_gaps": self.optimal_gaps.to_dict(),
            "conversion_timing": self.conversion_timing.to_dict(),
            "sample_size": self.sample_size,
            "confidence": self.confidence
        }
    
    @classmethod
    def insufficient_data(cls) -> "WhenPatterns":
        """Return default patterns when insufficient data"""
        return cls(
            best_days=[],
            best_hours=[],
            touch_distribution=TouchDistribution(),
            optimal_gaps=GapPatterns(),
            conversion_timing=ConversionTiming(),
            sample_size=0,
            confidence=0.0
        )


# =============================================================================
# MAIN DETECTOR CLASS
# =============================================================================

class WhenDetector:
    """
    Analyzes timing patterns of converting vs non-converting touches.
    
    All analysis is pure Python - statistical calculations only.
    No AI/LLM calls involved.
    """
    
    MIN_SAMPLES_TOTAL = 20
    MIN_SAMPLES_CATEGORY = 3
    
    async def analyze(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> WhenPatterns:
        """
        Main entry point. Analyze timing patterns for a client.
        
        Args:
            db: Database session
            client_id: Client UUID
            
        Returns:
            WhenPatterns with all timing analysis
        """
        # 1. Fetch converting and non-converting touches
        converting = await self._get_converting_touches(db, client_id)
        non_converting = await self._get_non_converting_touches(db, client_id)
        
        total = len(converting) + len(non_converting)
        
        if len(converting) < 5 or total < self.MIN_SAMPLES_TOTAL:
            return WhenPatterns.insufficient_data()
        
        # 2. Fetch sequence data for converted leads
        converted_sequences = await self._get_converted_sequences(db, client_id)
        
        # 3. Run all analyses
        best_days = self._analyze_days(converting, non_converting)
        best_hours = self._analyze_hours(converting, non_converting)
        touch_distribution = self._analyze_touch_position(converting, converted_sequences)
        optimal_gaps = self._analyze_gaps(converted_sequences)
        conversion_timing = self._analyze_conversion_timing(converted_sequences)
        
        # 4. Calculate confidence
        confidence = self._calculate_confidence(len(converting), total)
        
        return WhenPatterns(
            best_days=best_days,
            best_hours=best_hours,
            touch_distribution=touch_distribution,
            optimal_gaps=optimal_gaps,
            conversion_timing=conversion_timing,
            sample_size=total,
            confidence=confidence
        )
    
    # =========================================================================
    # DATA FETCHING
    # =========================================================================
    
    async def _get_converting_touches(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> list[Activity]:
        """
        Fetch activities that led to bookings.
        """
        query = select(Activity).where(
            and_(
                Activity.client_id == client_id,
                Activity.led_to_booking == True,
                Activity.action.in_([
                    'email_sent', 'sms_sent', 
                    'linkedin_sent', 'voice_completed'
                ])
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def _get_non_converting_touches(
        self, 
        db: AsyncSession, 
        client_id: str,
        limit: int = 500
    ) -> list[Activity]:
        """
        Fetch activities that did not lead to bookings.
        """
        query = select(Activity).join(
            Lead, Activity.lead_id == Lead.id
        ).where(
            and_(
                Activity.client_id == client_id,
                Activity.led_to_booking == False,
                Activity.action.in_([
                    'email_sent', 'sms_sent', 
                    'linkedin_sent', 'voice_completed'
                ]),
                Lead.status.in_([
                    'unsubscribed', 'bounced', 
                    'not_interested', 'dead'
                ])
            )
        ).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def _get_converted_sequences(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> list[dict]:
        """
        Fetch complete activity sequences for converted leads.
        Returns list of dicts with lead_id, activities, first_touch, last_touch.
        """
        # Get all converted leads
        converted_leads_query = select(Lead.id).where(
            and_(
                Lead.client_id == client_id,
                Lead.status == 'converted',
                Lead.deleted_at.is_(None)
            )
        )
        result = await db.execute(converted_leads_query)
        converted_lead_ids = [row[0] for row in result.fetchall()]
        
        if not converted_lead_ids:
            return []
        
        # Get all activities for these leads
        activities_query = select(Activity).where(
            and_(
                Activity.lead_id.in_(converted_lead_ids),
                Activity.action.in_([
                    'email_sent', 'sms_sent', 
                    'linkedin_sent', 'voice_completed'
                ])
            )
        ).order_by(Activity.lead_id, Activity.created_at)
        
        result = await db.execute(activities_query)
        activities = list(result.scalars().all())
        
        # Group by lead
        sequences = defaultdict(list)
        for activity in activities:
            sequences[activity.lead_id].append(activity)
        
        # Format output
        output = []
        for lead_id, lead_activities in sequences.items():
            if lead_activities:
                sorted_activities = sorted(lead_activities, key=lambda a: a.created_at)
                output.append({
                    "lead_id": lead_id,
                    "activities": sorted_activities,
                    "first_touch": sorted_activities[0].created_at,
                    "last_touch": sorted_activities[-1].created_at,
                    "touch_count": len(sorted_activities)
                })
        
        return output
    
    # =========================================================================
    # DAY OF WEEK ANALYSIS
    # =========================================================================
    
    def _analyze_days(
        self, 
        converting: list[Activity], 
        non_converting: list[Activity]
    ) -> list[DayPattern]:
        """
        Analyze which days of the week have highest conversion rates.
        """
        conv_by_day = defaultdict(int)
        total_by_day = defaultdict(int)
        
        for activity in converting:
            day_idx = activity.created_at.weekday()
            conv_by_day[day_idx] += 1
            total_by_day[day_idx] += 1
        
        for activity in non_converting:
            day_idx = activity.created_at.weekday()
            total_by_day[day_idx] += 1
        
        # Calculate overall rate for lift
        total_conv = len(converting)
        total_all = len(converting) + len(non_converting)
        overall_rate = total_conv / total_all if total_all > 0 else 0
        
        patterns = []
        for day_idx in range(7):
            total = total_by_day[day_idx]
            if total >= self.MIN_SAMPLES_CATEGORY:
                conv = conv_by_day[day_idx]
                rate = conv / total
                lift = rate / overall_rate if overall_rate > 0 else 1.0
                
                patterns.append(DayPattern(
                    day=DAYS_OF_WEEK[day_idx],
                    day_index=day_idx,
                    conversion_rate=round(rate, 3),
                    sample=total,
                    lift=round(lift, 2)
                ))
        
        # Sort by conversion rate descending
        patterns.sort(key=lambda x: -x.conversion_rate)
        
        return patterns
    
    # =========================================================================
    # HOUR OF DAY ANALYSIS
    # =========================================================================
    
    def _analyze_hours(
        self, 
        converting: list[Activity], 
        non_converting: list[Activity]
    ) -> list[HourPattern]:
        """
        Analyze which hours of the day have highest conversion rates.
        """
        conv_by_hour = defaultdict(int)
        total_by_hour = defaultdict(int)
        
        for activity in converting:
            hour = activity.created_at.hour
            conv_by_hour[hour] += 1
            total_by_hour[hour] += 1
        
        for activity in non_converting:
            hour = activity.created_at.hour
            total_by_hour[hour] += 1
        
        # Calculate overall rate for lift
        total_conv = len(converting)
        total_all = len(converting) + len(non_converting)
        overall_rate = total_conv / total_all if total_all > 0 else 0
        
        patterns = []
        for hour in range(24):
            total = total_by_hour[hour]
            if total >= self.MIN_SAMPLES_CATEGORY:
                conv = conv_by_hour[hour]
                rate = conv / total
                lift = rate / overall_rate if overall_rate > 0 else 1.0
                
                patterns.append(HourPattern(
                    hour=hour,
                    conversion_rate=round(rate, 3),
                    sample=total,
                    lift=round(lift, 2)
                ))
        
        # Sort by conversion rate descending
        patterns.sort(key=lambda x: -x.conversion_rate)
        
        return patterns
    
    # =========================================================================
    # TOUCH POSITION ANALYSIS
    # =========================================================================
    
    def _analyze_touch_position(
        self, 
        converting: list[Activity],
        converted_sequences: list[dict]
    ) -> TouchDistribution:
        """
        Analyze which touch number (1st, 2nd, 3rd, etc.) leads to conversion.
        """
        touch_number_counts = defaultdict(int)
        total_touches_list = []
        
        for activity in converting:
            # Get touch number from content_snapshot or activity metadata
            touch_num = self._get_touch_number(activity)
            if touch_num:
                touch_number_counts[touch_num] += 1
        
        # Also calculate average touches from sequences
        for seq in converted_sequences:
            total_touches_list.append(seq["touch_count"])
        
        # Normalize to distribution
        total_converting = sum(touch_number_counts.values())
        distribution = {}
        
        if total_converting > 0:
            for touch_num in range(1, 11):  # Touches 1-10
                count = touch_number_counts.get(touch_num, 0)
                key = f"touch_{touch_num}"
                distribution[key] = round(count / total_converting, 3)
        
        # Find peak touch
        peak_touch = 3  # Default
        if touch_number_counts:
            peak_touch = max(touch_number_counts.keys(), key=lambda k: touch_number_counts[k])
        
        # Average touches to convert
        avg_touches = 0.0
        if total_touches_list:
            avg_touches = statistics.mean(total_touches_list)
        
        return TouchDistribution(
            distribution=distribution,
            peak_touch=peak_touch,
            avg_touches_to_convert=avg_touches
        )
    
    def _get_touch_number(self, activity: Activity) -> Optional[int]:
        """Extract touch number from activity"""
        # Try content_snapshot first
        if activity.content_snapshot and "touch_number" in activity.content_snapshot:
            return activity.content_snapshot["touch_number"]
        
        # Try metadata
        if activity.metadata and "touch_number" in activity.metadata:
            return activity.metadata["touch_number"]
        
        # Try sequence_position
        if hasattr(activity, 'sequence_position'):
            return activity.sequence_position
        
        return None
    
    # =========================================================================
    # GAP ANALYSIS
    # =========================================================================
    
    def _analyze_gaps(
        self, 
        converted_sequences: list[dict]
    ) -> GapPatterns:
        """
        Analyze optimal days between touches for converted sequences.
        """
        # Collect gaps by position
        gaps_by_position = defaultdict(list)
        
        for seq in converted_sequences:
            activities = seq["activities"]
            for i in range(1, len(activities)):
                prev = activities[i - 1]
                curr = activities[i]
                
                gap_days = (curr.created_at - prev.created_at).days
                
                # Clamp to reasonable range (0-30 days)
                if 0 <= gap_days <= 30:
                    position_key = f"touch_{i}_to_{i+1}"
                    gaps_by_position[position_key].append(gap_days)
        
        # Calculate optimal (median) gap for each position
        result = GapPatterns()
        
        position_mapping = {
            "touch_1_to_2": "touch_1_to_2",
            "touch_2_to_3": "touch_2_to_3",
            "touch_3_to_4": "touch_3_to_4",
            "touch_4_to_5": "touch_4_to_5",
            "touch_5_to_6": "touch_5_to_6",
        }
        
        for position, attr in position_mapping.items():
            gaps = gaps_by_position.get(position, [])
            if len(gaps) >= self.MIN_SAMPLES_CATEGORY:
                optimal = int(statistics.median(gaps))
                # Clamp to reasonable values
                optimal = max(1, min(14, optimal))
                setattr(result, attr, optimal)
        
        return result
    
    # =========================================================================
    # CONVERSION TIMING ANALYSIS
    # =========================================================================
    
    def _analyze_conversion_timing(
        self, 
        converted_sequences: list[dict]
    ) -> ConversionTiming:
        """
        Analyze how long from first touch to conversion.
        """
        days_to_convert = []
        
        for seq in converted_sequences:
            if seq["first_touch"] and seq["last_touch"]:
                delta = seq["last_touch"] - seq["first_touch"]
                days = delta.days
                if 0 <= days <= 90:  # Reasonable range
                    days_to_convert.append(days)
        
        if len(days_to_convert) < self.MIN_SAMPLES_CATEGORY:
            return ConversionTiming()
        
        sorted_days = sorted(days_to_convert)
        n = len(sorted_days)
        
        return ConversionTiming(
            avg_days=statistics.mean(days_to_convert),
            median_days=statistics.median(days_to_convert),
            percentile_50=sorted_days[n // 2],
            percentile_80=sorted_days[int(n * 0.8)],
            percentile_95=sorted_days[min(int(n * 0.95), n - 1)]
        )
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _calculate_confidence(
        self, 
        converting_count: int, 
        total_count: int
    ) -> float:
        """Calculate confidence based on sample size"""
        import numpy as np
        # Sigmoid centered at 50 converting samples
        confidence = 1 / (1 + np.exp(-(converting_count - 50) / 15))
        return round(float(confidence), 2)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_hour_bucket(hour: int) -> Optional[str]:
    """Map hour to named bucket"""
    for bucket_name, (start, end) in HOUR_BUCKETS.items():
        if start <= hour <= end:
            return bucket_name
    return None


def format_hour(hour: int) -> str:
    """Format hour as readable string (e.g., '9am', '2pm')"""
    if hour == 0:
        return "12am"
    elif hour < 12:
        return f"{hour}am"
    elif hour == 12:
        return "12pm"
    else:
        return f"{hour - 12}pm"
```

---

## Integration: Sequence Builder Skill

### Modified Input Model

```python
class SequenceBuilderInput(BaseModel):
    """Input for Sequence Builder Skill"""
    client_icp: dict
    campaign_type: str  # "outbound", "nurture", "re-engagement"
    touch_count: Optional[int] = None  # If not set, skill decides
    
    # NEW: Pattern context
    when_patterns: Optional[dict] = None
    how_patterns: Optional[dict] = None  # From HOW Detector
```

### Modified Prompt Construction

```python
def _build_prompt(self, input: SequenceBuilderInput) -> str:
    prompt = f"""Design a multi-touch outreach sequence.

CAMPAIGN TYPE: {input.campaign_type}

CLIENT ICP:
{json.dumps(input.client_icp, indent=2)}
"""
    
    # Add timing guidance if available
    if input.when_patterns:
        patterns = input.when_patterns
        
        prompt += "\n\n--- TIMING INTELLIGENCE (from historical conversions) ---\n"
        
        # Best days
        if patterns.get("best_days"):
            best = patterns["best_days"][:3]
            days = ", ".join(d["day"] for d in best)
            prompt += f"\nBEST DAYS TO SEND: {days}\n"
            prompt += "(Ranked by conversion rate)\n"
        
        # Best hours
        if patterns.get("best_hours"):
            best = patterns["best_hours"][:3]
            hours = ", ".join(f"{h['hour']}:00" for h in best)
            prompt += f"\nBEST HOURS TO SEND: {hours}\n"
        
        # Touch distribution
        if patterns.get("converting_touch_distribution"):
            dist = patterns["converting_touch_distribution"]
            peak = patterns.get("peak_converting_touch", 3)
            prompt += f"\nPEAK CONVERTING TOUCH: Touch #{peak}\n"
            prompt += f"(Most bookings happen on touch {peak})\n"
        
        # Optimal gaps
        if patterns.get("optimal_sequence_gaps"):
            gaps = patterns["optimal_sequence_gaps"]
            prompt += f"\nOPTIMAL GAPS BETWEEN TOUCHES:\n"
            prompt += f"  • Touch 1 → 2: {gaps.get('touch_1_to_2', 2)} days\n"
            prompt += f"  • Touch 2 → 3: {gaps.get('touch_2_to_3', 3)} days\n"
            prompt += f"  • Touch 3 → 4: {gaps.get('touch_3_to_4', 4)} days\n"
            prompt += f"  • Touch 4 → 5: {gaps.get('touch_4_to_5', 5)} days\n"
            prompt += f"  • Touch 5 → 6: {gaps.get('touch_5_to_6', 7)} days\n"
        
        # Conversion timing
        if patterns.get("conversion_timing"):
            timing = patterns["conversion_timing"]
            avg = timing.get("avg_days_to_convert", 14)
            p80 = timing.get("percentile_80", 21)
            prompt += f"\nCONVERSION WINDOW:\n"
            prompt += f"  • Average: {avg:.0f} days from first touch\n"
            prompt += f"  • 80% convert within: {p80} days\n"
        
        # Average touches
        avg_touches = patterns.get("avg_touches_to_convert", 5)
        prompt += f"\nAVG TOUCHES TO CONVERT: {avg_touches:.1f}\n"
    
    # Determine touch count
    if input.touch_count:
        prompt += f"\n\nREQUIRED TOUCHES: {input.touch_count}\n"
    elif input.when_patterns and input.when_patterns.get("avg_touches_to_convert"):
        suggested = int(input.when_patterns["avg_touches_to_convert"]) + 1
        prompt += f"\n\nSUGGESTED TOUCHES: {suggested} (based on conversion data)\n"
    else:
        prompt += "\n\nDetermine optimal touch count based on campaign type.\n"
    
    return prompt
```

---

## Integration: Allocator Engine

The Allocator Engine uses WHEN patterns to optimize send timing.

### Modified Allocator

```python
# In AllocatorEngine

async def schedule_touch(
    self, 
    db: AsyncSession,
    lead: Lead,
    touch: dict,
    when_patterns: Optional[dict] = None
) -> datetime:
    """
    Schedule optimal send time for a touch.
    Uses WHEN patterns if available.
    """
    base_time = datetime.utcnow()
    
    # Get optimal day and hour from patterns
    best_day = None
    best_hour = 10  # Default
    
    if when_patterns:
        # Get best day
        if when_patterns.get("best_days"):
            best_days = when_patterns["best_days"]
            if best_days:
                best_day = best_days[0]["day_index"]
        
        # Get best hour
        if when_patterns.get("best_hours"):
            best_hours = when_patterns["best_hours"]
            if best_hours:
                best_hour = best_hours[0]["hour"]
    
    # Calculate next occurrence of best day/hour
    scheduled = self._find_next_slot(base_time, best_day, best_hour)
    
    # Apply lead's timezone if known
    scheduled = self._adjust_for_timezone(scheduled, lead)
    
    return scheduled


def _find_next_slot(
    self, 
    base: datetime, 
    target_day: Optional[int], 
    target_hour: int
) -> datetime:
    """Find next available slot matching day/hour preferences"""
    candidate = base.replace(
        hour=target_hour, 
        minute=0, 
        second=0, 
        microsecond=0
    )
    
    # If target_day specified, find next occurrence
    if target_day is not None:
        days_ahead = target_day - candidate.weekday()
        if days_ahead <= 0:  # Target day already passed this week
            days_ahead += 7
        candidate += timedelta(days=days_ahead)
    else:
        # Just use target hour, next occurrence
        if candidate <= base:
            candidate += timedelta(days=1)
    
    # Ensure not on weekend (unless data says weekends work)
    while candidate.weekday() >= 5:  # Saturday or Sunday
        candidate += timedelta(days=1)
    
    return candidate
```

---

## Integration: Scheduler Component

For gap-based scheduling between touches:

```python
# In SchedulerService

async def schedule_sequence(
    self,
    db: AsyncSession,
    lead: Lead,
    sequence: list[dict],
    when_patterns: Optional[dict] = None
) -> list[datetime]:
    """
    Schedule all touches in a sequence with optimal gaps.
    """
    scheduled_times = []
    current_time = datetime.utcnow()
    
    # Get gap patterns
    gaps = {
        "touch_1_to_2": 2,
        "touch_2_to_3": 3,
        "touch_3_to_4": 4,
        "touch_4_to_5": 5,
        "touch_5_to_6": 7,
    }
    
    if when_patterns and when_patterns.get("optimal_sequence_gaps"):
        gaps.update(when_patterns["optimal_sequence_gaps"])
    
    # Schedule first touch
    first_time = await self._find_optimal_slot(current_time, when_patterns)
    scheduled_times.append(first_time)
    
    # Schedule subsequent touches with gaps
    prev_time = first_time
    for i in range(1, len(sequence)):
        gap_key = f"touch_{i}_to_{i+1}"
        gap_days = gaps.get(gap_key, 3)  # Default 3 days
        
        # Add gap
        next_time = prev_time + timedelta(days=gap_days)
        
        # Find optimal slot within that day
        next_time = await self._find_optimal_slot(next_time, when_patterns)
        
        scheduled_times.append(next_time)
        prev_time = next_time
    
    return scheduled_times
```

---

## Tasks

| Task | Description | File(s) | Est. Hours |
|------|-------------|---------|------------|
| 16C.1 | Create WhenDetector class with all methods | `src/algorithms/when_detector.py` | 2.5 |
| 16C.2 | Integrate patterns into SequenceBuilderSkill | `src/agents/skills/sequence_builder.py` | 1.5 |
| 16C.3 | Integrate patterns into AllocatorEngine | `src/engines/allocator.py` | 1.5 |
| 16C.4 | Write unit tests | `tests/algorithms/test_when_detector.py` | 1.5 |

**Total: 4 tasks, ~7 hours**

---

## Testing

```python
# tests/algorithms/test_when_detector.py

import pytest
from datetime import datetime, timedelta
from src.algorithms.when_detector import WhenDetector, DAYS_OF_WEEK

class TestWhenDetector:
    
    def test_analyze_days(self):
        """Test day of week analysis"""
        detector = WhenDetector()
        
        # Create mock activities - Tuesday converts best
        converting = [
            MockActivity(created_at=datetime(2025, 12, 23, 10, 0)),  # Tuesday
            MockActivity(created_at=datetime(2025, 12, 23, 14, 0)),  # Tuesday
            MockActivity(created_at=datetime(2025, 12, 24, 10, 0)),  # Wednesday
        ]
        non_converting = [
            MockActivity(created_at=datetime(2025, 12, 22, 10, 0)),  # Monday
            MockActivity(created_at=datetime(2025, 12, 22, 14, 0)),  # Monday
            MockActivity(created_at=datetime(2025, 12, 24, 10, 0)),  # Wednesday
            MockActivity(created_at=datetime(2025, 12, 24, 14, 0)),  # Wednesday
        ]
        
        result = detector._analyze_days(converting, non_converting)
        
        # Tuesday should rank highest (2/2 = 100% conv rate)
        assert result[0].day == "Tuesday"
        assert result[0].conversion_rate == 1.0
    
    def test_analyze_hours(self):
        """Test hour of day analysis"""
        detector = WhenDetector()
        
        # Create mock activities - 10am converts best
        converting = [
            MockActivity(created_at=datetime(2025, 12, 23, 10, 0)),
            MockActivity(created_at=datetime(2025, 12, 24, 10, 0)),
        ]
        non_converting = [
            MockActivity(created_at=datetime(2025, 12, 23, 14, 0)),
            MockActivity(created_at=datetime(2025, 12, 24, 14, 0)),
            MockActivity(created_at=datetime(2025, 12, 25, 14, 0)),
        ]
        
        result = detector._analyze_hours(converting, non_converting)
        
        # 10am should have 100% rate, 14:00 should have 0%
        hour_10 = next((h for h in result if h.hour == 10), None)
        assert hour_10 is not None
        assert hour_10.conversion_rate == 1.0
    
    def test_analyze_gaps(self):
        """Test gap analysis between touches"""
        detector = WhenDetector()
        
        # Create mock sequences
        sequences = [
            {
                "lead_id": "1",
                "activities": [
                    MockActivity(created_at=datetime(2025, 12, 20, 10, 0)),
                    MockActivity(created_at=datetime(2025, 12, 22, 10, 0)),  # 2 days
                    MockActivity(created_at=datetime(2025, 12, 25, 10, 0)),  # 3 days
                ],
                "first_touch": datetime(2025, 12, 20),
                "last_touch": datetime(2025, 12, 25),
                "touch_count": 3
            },
            {
                "lead_id": "2",
                "activities": [
                    MockActivity(created_at=datetime(2025, 12, 20, 10, 0)),
                    MockActivity(created_at=datetime(2025, 12, 22, 10, 0)),  # 2 days
                    MockActivity(created_at=datetime(2025, 12, 26, 10, 0)),  # 4 days
                ],
                "first_touch": datetime(2025, 12, 20),
                "last_touch": datetime(2025, 12, 26),
                "touch_count": 3
            },
        ]
        
        result = detector._analyze_gaps(sequences)
        
        # Median gap 1→2 should be 2 days
        assert result.touch_1_to_2 == 2
    
    def test_conversion_timing(self):
        """Test conversion timing calculation"""
        detector = WhenDetector()
        
        sequences = [
            {
                "lead_id": "1",
                "activities": [],
                "first_touch": datetime(2025, 12, 1),
                "last_touch": datetime(2025, 12, 10),  # 9 days
                "touch_count": 4
            },
            {
                "lead_id": "2",
                "activities": [],
                "first_touch": datetime(2025, 12, 1),
                "last_touch": datetime(2025, 12, 15),  # 14 days
                "touch_count": 5
            },
            {
                "lead_id": "3",
                "activities": [],
                "first_touch": datetime(2025, 12, 1),
                "last_touch": datetime(2025, 12, 8),  # 7 days
                "touch_count": 3
            },
        ]
        
        result = detector._analyze_conversion_timing(sequences)
        
        # Average should be (9 + 14 + 7) / 3 = 10
        assert result.avg_days == 10.0
        # Median should be 9
        assert result.median_days == 9.0
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        detector = WhenDetector()
        
        # With < 5 converting, should return empty patterns
        patterns = WhenPatterns.insufficient_data()
        
        assert patterns.sample_size == 0
        assert patterns.confidence == 0.0
        assert len(patterns.best_days) == 0


class MockActivity:
    """Mock activity for testing"""
    def __init__(self, created_at: datetime, touch_number: int = 1):
        self.created_at = created_at
        self.content_snapshot = {"touch_number": touch_number}
        self.metadata = {}
```

---

**End of Phase 16C Specification**
