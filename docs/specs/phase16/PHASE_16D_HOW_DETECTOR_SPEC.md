# Phase 16D: HOW Detector Specification

## Technical Specification Document

**Version**: 1.0  
**Date**: December 27, 2025  
**Depends On**: Phase 16A (Data Capture)  
**Status**: Ready for Development  
**Estimated Tasks**: 4  

---

## Overview

The HOW Detector analyzes channel sequence patterns of successful conversions. It answers: **"What channel mix and sequence leads to bookings?"**

**Output**: Patterns stored in `conversion_patterns` table with `pattern_type = 'how'`

**Consumers**: 
- Sequence Builder Skill (channel sequence design)
- Allocator Engine (channel selection per touch)
- Campaign Generation Agent (multi-channel strategy)

---

## Algorithm Specification

### File: `src/algorithms/how_detector.py`

```python
"""
HOW Detector Algorithm

Analyzes channel patterns of converting vs non-converting sequences.
Pure statistical analysis - no AI in the loop.

Key Analyses:
1. Booking channel distribution (which channel gets the final reply)
2. First touch effectiveness (which channel to start with)
3. Multi-channel lift (does using more channels help)
4. Winning sequence patterns (full channel sequences that work)
5. Channel effectiveness by ALS tier (hot/warm/cool)
6. Channel transition analysis (what channel follows what)
"""

from dataclasses import dataclass, field
from collections import defaultdict, Counter
from typing import Optional, List, Tuple
import statistics
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.activity import Activity
from src.models.lead import Lead


# =============================================================================
# CONSTANTS
# =============================================================================

CHANNEL_MAP = {
    "email_sent": "email",
    "sms_sent": "sms",
    "linkedin_sent": "linkedin",
    "voice_completed": "voice",
    "mail_sent": "mail",
}

CHANNEL_ORDER = ["email", "linkedin", "sms", "voice", "mail"]

ALS_TIERS = {
    "hot": (80, 100),
    "warm": (50, 79),
    "cool": (0, 49),
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ChannelDistribution:
    """Distribution of bookings by channel"""
    email: float = 0.0
    linkedin: float = 0.0
    sms: float = 0.0
    voice: float = 0.0
    mail: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "email": round(self.email, 3),
            "linkedin": round(self.linkedin, 3),
            "sms": round(self.sms, 3),
            "voice": round(self.voice, 3),
            "mail": round(self.mail, 3),
        }


@dataclass
class FirstTouchEffectiveness:
    """Conversion rate by first touch channel"""
    results: dict = field(default_factory=dict)
    best_channel: str = "email"
    
    def to_dict(self) -> dict:
        return self.results


@dataclass
class MultiChannelLift:
    """Lift from using multiple channels"""
    by_channel_count: dict = field(default_factory=dict)
    optimal_channel_count: int = 3
    
    def to_dict(self) -> dict:
        return self.by_channel_count


@dataclass
class SequencePattern:
    """A specific channel sequence pattern"""
    sequence: List[str]
    conversion_rate: float
    sample_size: int
    
    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "conversion_rate": round(self.conversion_rate, 3),
            "sample_size": self.sample_size,
        }


@dataclass
class ChannelByTier:
    """Channel effectiveness broken down by ALS tier"""
    hot: dict = field(default_factory=dict)
    warm: dict = field(default_factory=dict)
    cool: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "hot": self.hot,
            "warm": self.warm,
            "cool": self.cool,
        }


@dataclass
class ChannelTransitions:
    """What channel works best after another channel"""
    transitions: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return self.transitions


@dataclass
class HowPatterns:
    """Complete HOW pattern output"""
    booking_channel: ChannelDistribution
    first_touch: FirstTouchEffectiveness
    multi_channel: MultiChannelLift
    winning_sequences: List[SequencePattern]
    channel_by_tier: ChannelByTier
    channel_transitions: ChannelTransitions
    sample_size: int
    confidence: float
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for database storage"""
        return {
            "type": "how",
            "version": "1.0",
            "booking_channel_distribution": self.booking_channel.to_dict(),
            "first_touch_effectiveness": self.first_touch.to_dict(),
            "best_first_channel": self.first_touch.best_channel,
            "multi_channel_lift": self.multi_channel.to_dict(),
            "optimal_channel_count": self.multi_channel.optimal_channel_count,
            "winning_sequences": [s.to_dict() for s in self.winning_sequences],
            "channel_effectiveness_by_tier": self.channel_by_tier.to_dict(),
            "channel_transitions": self.channel_transitions.to_dict(),
            "sample_size": self.sample_size,
            "confidence": self.confidence,
        }
    
    @classmethod
    def insufficient_data(cls) -> "HowPatterns":
        """Return default patterns when insufficient data"""
        return cls(
            booking_channel=ChannelDistribution(),
            first_touch=FirstTouchEffectiveness(),
            multi_channel=MultiChannelLift(),
            winning_sequences=[],
            channel_by_tier=ChannelByTier(),
            channel_transitions=ChannelTransitions(),
            sample_size=0,
            confidence=0.0,
        )


# =============================================================================
# MAIN DETECTOR CLASS
# =============================================================================

class HowDetector:
    """
    Analyzes channel patterns of converting vs non-converting sequences.
    
    All analysis is pure Python - statistical calculations only.
    No AI/LLM calls involved.
    """
    
    MIN_SAMPLES_TOTAL = 20
    MIN_SAMPLES_CATEGORY = 3
    MIN_SEQUENCE_SAMPLES = 5
    
    async def analyze(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> HowPatterns:
        """
        Main entry point. Analyze channel patterns for a client.
        
        Args:
            db: Database session
            client_id: Client UUID
            
        Returns:
            HowPatterns with all channel analysis
        """
        # 1. Fetch converted and failed sequences
        converted_sequences = await self._get_converted_sequences(db, client_id)
        failed_sequences = await self._get_failed_sequences(db, client_id)
        
        total = len(converted_sequences) + len(failed_sequences)
        
        if len(converted_sequences) < 5 or total < self.MIN_SAMPLES_TOTAL:
            return HowPatterns.insufficient_data()
        
        # 2. Fetch converting touches for booking channel analysis
        converting_touches = await self._get_converting_touches(db, client_id)
        
        # 3. Run all analyses
        booking_channel = self._analyze_booking_channel(converting_touches)
        first_touch = self._analyze_first_touch(converted_sequences, failed_sequences)
        multi_channel = self._analyze_multi_channel_lift(converted_sequences, failed_sequences)
        winning_sequences = self._analyze_winning_sequences(converted_sequences, failed_sequences)
        channel_by_tier = self._analyze_channel_by_tier(converted_sequences, failed_sequences)
        channel_transitions = self._analyze_transitions(converted_sequences)
        
        # 4. Calculate confidence
        confidence = self._calculate_confidence(len(converted_sequences), total)
        
        return HowPatterns(
            booking_channel=booking_channel,
            first_touch=first_touch,
            multi_channel=multi_channel,
            winning_sequences=winning_sequences,
            channel_by_tier=channel_by_tier,
            channel_transitions=channel_transitions,
            sample_size=total,
            confidence=confidence,
        )
    
    # =========================================================================
    # DATA FETCHING
    # =========================================================================
    
    async def _get_converting_touches(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> list[Activity]:
        """Fetch activities that led to bookings."""
        query = select(Activity).where(
            and_(
                Activity.client_id == client_id,
                Activity.led_to_booking == True,
                Activity.action.in_(list(CHANNEL_MAP.keys()))
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def _get_converted_sequences(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> list[dict]:
        """
        Fetch complete activity sequences for converted leads.
        Returns list of dicts with lead info and channel sequence.
        """
        # Get converted leads with ALS score
        query = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.status == 'converted',
                Lead.deleted_at.is_(None)
            )
        )
        result = await db.execute(query)
        converted_leads = {lead.id: lead for lead in result.scalars().all()}
        
        if not converted_leads:
            return []
        
        # Get activities for these leads
        activities_query = select(Activity).where(
            and_(
                Activity.lead_id.in_(converted_leads.keys()),
                Activity.action.in_(list(CHANNEL_MAP.keys()))
            )
        ).order_by(Activity.lead_id, Activity.created_at)
        
        result = await db.execute(activities_query)
        activities = list(result.scalars().all())
        
        # Group by lead and build sequences
        sequences_by_lead = defaultdict(list)
        for activity in activities:
            channel = CHANNEL_MAP.get(activity.action)
            if channel:
                sequences_by_lead[activity.lead_id].append({
                    "channel": channel,
                    "created_at": activity.created_at,
                    "led_to_booking": activity.led_to_booking,
                })
        
        # Format output
        output = []
        for lead_id, touches in sequences_by_lead.items():
            lead = converted_leads.get(lead_id)
            if lead and touches:
                sorted_touches = sorted(touches, key=lambda t: t["created_at"])
                channel_sequence = [t["channel"] for t in sorted_touches]
                
                output.append({
                    "lead_id": lead_id,
                    "als_score": lead.als_score or 50,
                    "als_tier": self._get_als_tier(lead.als_score or 50),
                    "channel_sequence": channel_sequence,
                    "channel_count": len(set(channel_sequence)),
                    "touch_count": len(channel_sequence),
                    "first_channel": channel_sequence[0] if channel_sequence else None,
                    "converted": True,
                })
        
        return output
    
    async def _get_failed_sequences(
        self, 
        db: AsyncSession, 
        client_id: str,
        limit: int = 300
    ) -> list[dict]:
        """
        Fetch activity sequences for failed leads.
        """
        # Get failed leads
        query = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.status.in_(['unsubscribed', 'bounced', 'not_interested', 'dead']),
                Lead.deleted_at.is_(None)
            )
        ).limit(limit)
        
        result = await db.execute(query)
        failed_leads = {lead.id: lead for lead in result.scalars().all()}
        
        if not failed_leads:
            return []
        
        # Get activities
        activities_query = select(Activity).where(
            and_(
                Activity.lead_id.in_(failed_leads.keys()),
                Activity.action.in_(list(CHANNEL_MAP.keys()))
            )
        ).order_by(Activity.lead_id, Activity.created_at)
        
        result = await db.execute(activities_query)
        activities = list(result.scalars().all())
        
        # Group by lead
        sequences_by_lead = defaultdict(list)
        for activity in activities:
            channel = CHANNEL_MAP.get(activity.action)
            if channel:
                sequences_by_lead[activity.lead_id].append(channel)
        
        # Format output
        output = []
        for lead_id, channel_sequence in sequences_by_lead.items():
            lead = failed_leads.get(lead_id)
            if lead and channel_sequence:
                output.append({
                    "lead_id": lead_id,
                    "als_score": lead.als_score or 50,
                    "als_tier": self._get_als_tier(lead.als_score or 50),
                    "channel_sequence": channel_sequence,
                    "channel_count": len(set(channel_sequence)),
                    "touch_count": len(channel_sequence),
                    "first_channel": channel_sequence[0] if channel_sequence else None,
                    "converted": False,
                })
        
        return output
    
    def _get_als_tier(self, score: int) -> str:
        """Map ALS score to tier"""
        for tier, (min_score, max_score) in ALS_TIERS.items():
            if min_score <= score <= max_score:
                return tier
        return "warm"
    
    # =========================================================================
    # BOOKING CHANNEL ANALYSIS
    # =========================================================================
    
    def _analyze_booking_channel(
        self, 
        converting_touches: list[Activity]
    ) -> ChannelDistribution:
        """
        Analyze which channel gets the booking reply.
        """
        channel_counts = defaultdict(int)
        total = 0
        
        for activity in converting_touches:
            channel = CHANNEL_MAP.get(activity.action)
            if channel:
                channel_counts[channel] += 1
                total += 1
        
        if total == 0:
            return ChannelDistribution()
        
        return ChannelDistribution(
            email=channel_counts["email"] / total,
            linkedin=channel_counts["linkedin"] / total,
            sms=channel_counts["sms"] / total,
            voice=channel_counts["voice"] / total,
            mail=channel_counts["mail"] / total,
        )
    
    # =========================================================================
    # FIRST TOUCH ANALYSIS
    # =========================================================================
    
    def _analyze_first_touch(
        self, 
        converted: list[dict], 
        failed: list[dict]
    ) -> FirstTouchEffectiveness:
        """
        Analyze conversion rate by first touch channel.
        """
        conv_by_first = defaultdict(int)
        total_by_first = defaultdict(int)
        
        for seq in converted:
            if seq["first_channel"]:
                conv_by_first[seq["first_channel"]] += 1
                total_by_first[seq["first_channel"]] += 1
        
        for seq in failed:
            if seq["first_channel"]:
                total_by_first[seq["first_channel"]] += 1
        
        results = {}
        best_channel = "email"
        best_rate = 0.0
        
        for channel in CHANNEL_ORDER:
            total = total_by_first[channel]
            if total >= self.MIN_SAMPLES_CATEGORY:
                rate = conv_by_first[channel] / total
                results[f"{channel}_first"] = {
                    "conversion_rate": round(rate, 3),
                    "sample": total,
                }
                if rate > best_rate:
                    best_rate = rate
                    best_channel = channel
        
        return FirstTouchEffectiveness(
            results=results,
            best_channel=best_channel,
        )
    
    # =========================================================================
    # MULTI-CHANNEL LIFT ANALYSIS
    # =========================================================================
    
    def _analyze_multi_channel_lift(
        self, 
        converted: list[dict], 
        failed: list[dict]
    ) -> MultiChannelLift:
        """
        Analyze how conversion rate changes with channel count.
        """
        conv_by_count = defaultdict(int)
        total_by_count = defaultdict(int)
        
        for seq in converted:
            count = seq["channel_count"]
            # Bucket 4+ together
            bucket = min(count, 4)
            conv_by_count[bucket] += 1
            total_by_count[bucket] += 1
        
        for seq in failed:
            count = seq["channel_count"]
            bucket = min(count, 4)
            total_by_count[bucket] += 1
        
        # Calculate rates and lift
        results = {}
        baseline_rate = None
        optimal_count = 1
        best_rate = 0.0
        
        for count in [1, 2, 3, 4]:
            total = total_by_count[count]
            if total >= self.MIN_SAMPLES_CATEGORY:
                rate = conv_by_count[count] / total
                
                if baseline_rate is None:
                    baseline_rate = rate
                
                lift = rate / baseline_rate if baseline_rate > 0 else 1.0
                
                label = f"{count}_channel" if count < 4 else "4_plus_channels"
                results[label] = {
                    "conversion_rate": round(rate, 3),
                    "lift": round(lift, 2),
                    "sample": total,
                }
                
                if rate > best_rate:
                    best_rate = rate
                    optimal_count = count
        
        return MultiChannelLift(
            by_channel_count=results,
            optimal_channel_count=optimal_count,
        )
    
    # =========================================================================
    # WINNING SEQUENCES ANALYSIS
    # =========================================================================
    
    def _analyze_winning_sequences(
        self, 
        converted: list[dict], 
        failed: list[dict]
    ) -> list[SequencePattern]:
        """
        Find the most successful channel sequences.
        """
        # Normalize sequences to fixed length for comparison
        sequence_conv = defaultdict(int)
        sequence_total = defaultdict(int)
        
        for seq in converted:
            # Use first 6 touches or pad with None
            normalized = self._normalize_sequence(seq["channel_sequence"], 6)
            key = tuple(normalized)
            sequence_conv[key] += 1
            sequence_total[key] += 1
        
        for seq in failed:
            normalized = self._normalize_sequence(seq["channel_sequence"], 6)
            key = tuple(normalized)
            sequence_total[key] += 1
        
        # Calculate conversion rates
        patterns = []
        for sequence, total in sequence_total.items():
            if total >= self.MIN_SEQUENCE_SAMPLES:
                conv = sequence_conv[sequence]
                rate = conv / total
                
                # Remove None padding for output
                clean_sequence = [c for c in sequence if c is not None]
                
                patterns.append(SequencePattern(
                    sequence=clean_sequence,
                    conversion_rate=rate,
                    sample_size=total,
                ))
        
        # Sort by conversion rate
        patterns.sort(key=lambda p: -p.conversion_rate)
        
        # Return top 5
        return patterns[:5]
    
    def _normalize_sequence(
        self, 
        sequence: list[str], 
        length: int
    ) -> list[Optional[str]]:
        """Normalize sequence to fixed length"""
        result = sequence[:length]
        while len(result) < length:
            result.append(None)
        return result
    
    # =========================================================================
    # CHANNEL BY TIER ANALYSIS
    # =========================================================================
    
    def _analyze_channel_by_tier(
        self, 
        converted: list[dict], 
        failed: list[dict]
    ) -> ChannelByTier:
        """
        Analyze which channels work best for each ALS tier.
        """
        result = ChannelByTier()
        
        for tier in ["hot", "warm", "cool"]:
            tier_converted = [s for s in converted if s["als_tier"] == tier]
            tier_failed = [s for s in failed if s["als_tier"] == tier]
            
            channel_stats = self._analyze_channels_for_tier(
                tier_converted, tier_failed
            )
            setattr(result, tier, channel_stats)
        
        return result
    
    def _analyze_channels_for_tier(
        self, 
        converted: list[dict], 
        failed: list[dict]
    ) -> dict:
        """Analyze channel effectiveness within a tier"""
        # Count conversions by channel used anywhere in sequence
        channel_conv = defaultdict(int)
        channel_total = defaultdict(int)
        
        for seq in converted:
            channels_used = set(seq["channel_sequence"])
            for channel in channels_used:
                channel_conv[channel] += 1
                channel_total[channel] += 1
        
        for seq in failed:
            channels_used = set(seq["channel_sequence"])
            for channel in channels_used:
                channel_total[channel] += 1
        
        results = {}
        for channel in CHANNEL_ORDER:
            total = channel_total[channel]
            if total >= self.MIN_SAMPLES_CATEGORY:
                rate = channel_conv[channel] / total
                results[channel] = {
                    "conversion_rate": round(rate, 3),
                    "sample": total,
                }
        
        return results
    
    # =========================================================================
    # CHANNEL TRANSITION ANALYSIS
    # =========================================================================
    
    def _analyze_transitions(
        self, 
        converted: list[dict]
    ) -> ChannelTransitions:
        """
        Analyze what channel works best after another channel.
        E.g., after email, does LinkedIn or SMS work better?
        """
        transition_counts = defaultdict(lambda: defaultdict(int))
        
        for seq in converted:
            channel_sequence = seq["channel_sequence"]
            for i in range(len(channel_sequence) - 1):
                from_channel = channel_sequence[i]
                to_channel = channel_sequence[i + 1]
                transition_counts[from_channel][to_channel] += 1
        
        # Normalize to percentages
        results = {}
        for from_channel, to_channels in transition_counts.items():
            total = sum(to_channels.values())
            if total >= self.MIN_SAMPLES_CATEGORY:
                results[from_channel] = {
                    to_ch: {
                        "frequency": round(count / total, 3),
                        "count": count,
                    }
                    for to_ch, count in to_channels.items()
                }
        
        return ChannelTransitions(transitions=results)
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _calculate_confidence(
        self, 
        converted_count: int, 
        total_count: int
    ) -> float:
        """Calculate confidence based on sample size"""
        import numpy as np
        confidence = 1 / (1 + np.exp(-(converted_count - 50) / 15))
        return round(float(confidence), 2)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def sequence_to_string(sequence: list[str]) -> str:
    """Convert channel sequence to readable string"""
    abbrev = {
        "email": "E",
        "linkedin": "L",
        "sms": "S",
        "voice": "V",
        "mail": "M",
    }
    return "-".join(abbrev.get(c, "?") for c in sequence)


def string_to_sequence(s: str) -> list[str]:
    """Convert string back to channel sequence"""
    abbrev_reverse = {
        "E": "email",
        "L": "linkedin",
        "S": "sms",
        "V": "voice",
        "M": "mail",
    }
    return [abbrev_reverse.get(c, "email") for c in s.split("-")]
```

---

## Integration: Sequence Builder Skill

### Updated Input Model (combines WHEN + HOW patterns)

```python
class SequenceBuilderInput(BaseModel):
    """Input for Sequence Builder Skill"""
    client_icp: dict
    campaign_type: str
    touch_count: Optional[int] = None
    
    # Pattern context
    when_patterns: Optional[dict] = None
    how_patterns: Optional[dict] = None
```

### Modified Prompt Construction (HOW section)

```python
def _build_prompt(self, input: SequenceBuilderInput) -> str:
    prompt = f"""Design a multi-touch outreach sequence.

CAMPAIGN TYPE: {input.campaign_type}

CLIENT ICP:
{json.dumps(input.client_icp, indent=2)}
"""
    
    # Add channel guidance if available
    if input.how_patterns:
        patterns = input.how_patterns
        
        prompt += "\n\n--- CHANNEL INTELLIGENCE (from historical conversions) ---\n"
        
        # Best first channel
        if patterns.get("best_first_channel"):
            prompt += f"\nBEST FIRST CHANNEL: {patterns['best_first_channel']}\n"
        
        # First touch effectiveness
        if patterns.get("first_touch_effectiveness"):
            first = patterns["first_touch_effectiveness"]
            prompt += "\nFIRST TOUCH EFFECTIVENESS:\n"
            for channel, stats in sorted(
                first.items(), 
                key=lambda x: -x[1].get("conversion_rate", 0)
            )[:3]:
                rate = stats.get("conversion_rate", 0) * 100
                prompt += f"  • {channel}: {rate:.1f}% conversion\n"
        
        # Multi-channel lift
        if patterns.get("multi_channel_lift"):
            lift = patterns["multi_channel_lift"]
            optimal = patterns.get("optimal_channel_count", 3)
            prompt += f"\nOPTIMAL CHANNEL COUNT: {optimal}\n"
            prompt += "MULTI-CHANNEL LIFT:\n"
            for count, stats in lift.items():
                lift_val = stats.get("lift", 1.0)
                prompt += f"  • {count}: {lift_val:.1f}x lift\n"
        
        # Winning sequences
        if patterns.get("winning_sequences"):
            prompt += "\nWINNING SEQUENCES (use as templates):\n"
            for i, seq in enumerate(patterns["winning_sequences"][:3], 1):
                seq_str = " → ".join(seq["sequence"])
                rate = seq["conversion_rate"] * 100
                prompt += f"  {i}. {seq_str} ({rate:.1f}% conv)\n"
        
        # Channel transitions
        if patterns.get("channel_transitions"):
            trans = patterns["channel_transitions"]
            prompt += "\nEFFECTIVE CHANNEL TRANSITIONS:\n"
            for from_ch, to_channels in trans.items():
                best_next = max(to_channels.items(), key=lambda x: x[1].get("frequency", 0))
                prompt += f"  • After {from_ch} → {best_next[0]} works best\n"
        
        # Booking channel
        if patterns.get("booking_channel_distribution"):
            dist = patterns["booking_channel_distribution"]
            top_channel = max(dist.items(), key=lambda x: x[1])
            prompt += f"\nMOST BOOKINGS FROM: {top_channel[0]} ({top_channel[1]*100:.0f}%)\n"
    
    return prompt
```

---

## Integration: Allocator Engine

### Modified Channel Selection

```python
# In AllocatorEngine

async def select_channel(
    self,
    db: AsyncSession,
    lead: Lead,
    touch_number: int,
    sequence: list[dict],
    how_patterns: Optional[dict] = None
) -> str:
    """
    Select optimal channel for a touch.
    Uses HOW patterns if available.
    """
    # Get lead's ALS tier
    als_tier = self._get_als_tier(lead.als_score or 50)
    
    # Default channel from sequence
    default_channel = sequence[touch_number - 1].get("channel", "email")
    
    if not how_patterns:
        return default_channel
    
    # For first touch, use best first channel
    if touch_number == 1:
        best_first = how_patterns.get("best_first_channel")
        if best_first:
            return best_first
    
    # For subsequent touches, use channel by tier if available
    if how_patterns.get("channel_effectiveness_by_tier"):
        tier_data = how_patterns["channel_effectiveness_by_tier"].get(als_tier, {})
        if tier_data:
            # Get best channel for this tier
            best_for_tier = max(
                tier_data.items(),
                key=lambda x: x[1].get("conversion_rate", 0)
            )
            return best_for_tier[0]
    
    # Check transitions from previous channel
    if touch_number > 1 and how_patterns.get("channel_transitions"):
        prev_channel = sequence[touch_number - 2].get("channel")
        transitions = how_patterns["channel_transitions"].get(prev_channel, {})
        if transitions:
            best_next = max(
                transitions.items(),
                key=lambda x: x[1].get("frequency", 0)
            )
            return best_next[0]
    
    return default_channel


def _get_als_tier(self, score: int) -> str:
    """Map ALS score to tier"""
    if score >= 80:
        return "hot"
    elif score >= 50:
        return "warm"
    else:
        return "cool"
```

### Modified Sequence Generation

```python
async def generate_sequence(
    self,
    db: AsyncSession,
    client: Client,
    lead: Lead,
    how_patterns: Optional[dict] = None,
    when_patterns: Optional[dict] = None
) -> list[dict]:
    """
    Generate a channel sequence for a lead.
    Uses patterns for optimization.
    """
    # Determine touch count
    touch_count = 6  # Default
    
    if when_patterns and when_patterns.get("avg_touches_to_convert"):
        touch_count = int(when_patterns["avg_touches_to_convert"]) + 1
    
    # Start with winning sequence if available
    sequence = []
    
    if how_patterns and how_patterns.get("winning_sequences"):
        # Use top winning sequence as base
        top_seq = how_patterns["winning_sequences"][0]
        base_channels = top_seq["sequence"]
        
        # Extend or trim to desired length
        while len(base_channels) < touch_count:
            base_channels.append("email")
        base_channels = base_channels[:touch_count]
        
        for i, channel in enumerate(base_channels):
            sequence.append({
                "touch_number": i + 1,
                "channel": channel,
            })
    else:
        # Fallback to default pattern
        default_pattern = ["email", "linkedin", "email", "sms", "voice", "email"]
        for i in range(touch_count):
            sequence.append({
                "touch_number": i + 1,
                "channel": default_pattern[i % len(default_pattern)],
            })
    
    # Adjust based on lead's tier
    als_tier = self._get_als_tier(lead.als_score or 50)
    
    if als_tier == "hot" and how_patterns:
        # Hot leads: prioritize voice if it works
        tier_data = how_patterns.get("channel_effectiveness_by_tier", {}).get("hot", {})
        if tier_data.get("voice", {}).get("conversion_rate", 0) > 0.15:
            # Add voice earlier in sequence
            if len(sequence) > 2:
                sequence[2]["channel"] = "voice"
    
    return sequence
```

---

## Integration: Campaign Generation Agent

```python
# In CampaignGenerationAgent

async def generate_campaign(
    self,
    db: AsyncSession,
    client: Client
) -> Campaign:
    """Generate campaign with pattern-optimized sequence."""
    
    # Load patterns
    patterns = await self._load_patterns(db, client.id)
    
    how_patterns = patterns.get("how")
    when_patterns = patterns.get("when")
    what_patterns = patterns.get("what")
    
    # Build sequence with HOW + WHEN patterns
    sequence = await self._generate_sequence(
        db, client, how_patterns, when_patterns
    )
    
    # Generate messaging with WHAT patterns
    messaging = await self._generate_messaging(
        db, client, sequence, what_patterns
    )
    
    # Combine into campaign
    return Campaign(
        client_id=client.id,
        sequence=sequence,
        messaging=messaging,
        patterns_used={
            "how_confidence": how_patterns.get("confidence", 0) if how_patterns else 0,
            "when_confidence": when_patterns.get("confidence", 0) if when_patterns else 0,
            "what_confidence": what_patterns.get("confidence", 0) if what_patterns else 0,
        }
    )
```

---

## Tasks

| Task | Description | File(s) | Est. Hours |
|------|-------------|---------|------------|
| 16D.1 | Create HowDetector class with all methods | `src/algorithms/how_detector.py` | 3 |
| 16D.2 | Integrate patterns into SequenceBuilderSkill | `src/agents/skills/sequence_builder.py` | 1.5 |
| 16D.3 | Integrate patterns into AllocatorEngine | `src/engines/allocator.py` | 2 |
| 16D.4 | Write unit tests | `tests/algorithms/test_how_detector.py` | 1.5 |

**Total: 4 tasks, ~8 hours**

---

## Testing

```python
# tests/algorithms/test_how_detector.py

import pytest
from src.algorithms.how_detector import (
    HowDetector, 
    sequence_to_string, 
    string_to_sequence
)

class TestHowDetector:
    
    def test_booking_channel_distribution(self):
        """Test booking channel analysis"""
        detector = HowDetector()
        
        # Mock activities - 2 email, 1 linkedin
        converting = [
            MockActivity(action="email_sent"),
            MockActivity(action="email_sent"),
            MockActivity(action="linkedin_sent"),
        ]
        
        result = detector._analyze_booking_channel(converting)
        
        assert result.email == pytest.approx(0.667, rel=0.01)
        assert result.linkedin == pytest.approx(0.333, rel=0.01)
    
    def test_first_touch_effectiveness(self):
        """Test first touch analysis"""
        detector = HowDetector()
        
        converted = [
            {"first_channel": "linkedin", "converted": True},
            {"first_channel": "linkedin", "converted": True},
            {"first_channel": "email", "converted": True},
        ]
        failed = [
            {"first_channel": "email", "converted": False},
            {"first_channel": "email", "converted": False},
            {"first_channel": "email", "converted": False},
        ]
        
        result = detector._analyze_first_touch(converted, failed)
        
        # LinkedIn: 2/2 = 100%, Email: 1/4 = 25%
        assert result.best_channel == "linkedin"
    
    def test_multi_channel_lift(self):
        """Test multi-channel lift calculation"""
        detector = HowDetector()
        
        converted = [
            {"channel_count": 1, "converted": True},
            {"channel_count": 3, "converted": True},
            {"channel_count": 3, "converted": True},
            {"channel_count": 3, "converted": True},
        ]
        failed = [
            {"channel_count": 1, "converted": False},
            {"channel_count": 1, "converted": False},
            {"channel_count": 1, "converted": False},
            {"channel_count": 3, "converted": False},
        ]
        
        result = detector._analyze_multi_channel_lift(converted, failed)
        
        # 1 channel: 1/4 = 25%, 3 channels: 3/4 = 75%
        # Lift = 75/25 = 3x
        assert result.optimal_channel_count == 3
        assert result.by_channel_count["3_channel"]["lift"] == pytest.approx(3.0, rel=0.1)
    
    def test_winning_sequences(self):
        """Test sequence pattern detection"""
        detector = HowDetector()
        
        converted = [
            {"channel_sequence": ["email", "linkedin", "email"]},
            {"channel_sequence": ["email", "linkedin", "email"]},
            {"channel_sequence": ["email", "linkedin", "email"]},
            {"channel_sequence": ["email", "linkedin", "email"]},
            {"channel_sequence": ["email", "linkedin", "email"]},
            {"channel_sequence": ["linkedin", "email", "sms"]},
        ]
        failed = [
            {"channel_sequence": ["email", "email", "email"]},
            {"channel_sequence": ["email", "email", "email"]},
            {"channel_sequence": ["linkedin", "email", "sms"]},
        ]
        
        result = detector._analyze_winning_sequences(converted, failed)
        
        # E-L-E appears 5 times converted, should be top
        assert len(result) > 0
        assert result[0].sequence == ["email", "linkedin", "email"]
    
    def test_channel_transitions(self):
        """Test transition analysis"""
        detector = HowDetector()
        
        converted = [
            {"channel_sequence": ["email", "linkedin", "sms"]},
            {"channel_sequence": ["email", "linkedin", "email"]},
            {"channel_sequence": ["email", "sms", "voice"]},
        ]
        
        result = detector._analyze_transitions(converted)
        
        # After email: linkedin appears 2x, sms 1x
        assert "email" in result.transitions
        assert result.transitions["email"]["linkedin"]["count"] == 2
    
    def test_sequence_string_conversion(self):
        """Test helper functions"""
        sequence = ["email", "linkedin", "sms", "voice"]
        
        s = sequence_to_string(sequence)
        assert s == "E-L-S-V"
        
        back = string_to_sequence(s)
        assert back == sequence
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        patterns = HowPatterns.insufficient_data()
        
        assert patterns.sample_size == 0
        assert patterns.confidence == 0.0
        assert len(patterns.winning_sequences) == 0


class MockActivity:
    """Mock activity for testing"""
    def __init__(self, action: str):
        self.action = action
        self.led_to_booking = True
```

---

## Output Example

```json
{
  "type": "how",
  "version": "1.0",
  "booking_channel_distribution": {
    "email": 0.52,
    "linkedin": 0.28,
    "sms": 0.12,
    "voice": 0.08,
    "mail": 0.0
  },
  "first_touch_effectiveness": {
    "email_first": {"conversion_rate": 0.11, "sample": 234},
    "linkedin_first": {"conversion_rate": 0.14, "sample": 156}
  },
  "best_first_channel": "linkedin",
  "multi_channel_lift": {
    "1_channel": {"conversion_rate": 0.06, "lift": 1.0, "sample": 89},
    "2_channel": {"conversion_rate": 0.11, "lift": 1.8, "sample": 134},
    "3_channel": {"conversion_rate": 0.16, "lift": 2.7, "sample": 98},
    "4_plus_channels": {"conversion_rate": 0.19, "lift": 3.2, "sample": 45}
  },
  "optimal_channel_count": 4,
  "winning_sequences": [
    {
      "sequence": ["email", "linkedin", "email", "sms", "voice", "email"],
      "conversion_rate": 0.18,
      "sample_size": 45
    },
    {
      "sequence": ["linkedin", "email", "email", "linkedin", "sms"],
      "conversion_rate": 0.15,
      "sample_size": 38
    }
  ],
  "channel_effectiveness_by_tier": {
    "hot": {
      "voice": {"conversion_rate": 0.24, "sample": 23},
      "email": {"conversion_rate": 0.18, "sample": 67}
    },
    "warm": {
      "email": {"conversion_rate": 0.14, "sample": 134},
      "linkedin": {"conversion_rate": 0.12, "sample": 98}
    },
    "cool": {
      "email": {"conversion_rate": 0.07, "sample": 189}
    }
  },
  "channel_transitions": {
    "email": {
      "linkedin": {"frequency": 0.45, "count": 89},
      "sms": {"frequency": 0.30, "count": 59}
    },
    "linkedin": {
      "email": {"frequency": 0.55, "count": 67},
      "sms": {"frequency": 0.25, "count": 30}
    }
  },
  "sample_size": 412,
  "confidence": 0.85
}
```

---

**End of Phase 16D Specification**
