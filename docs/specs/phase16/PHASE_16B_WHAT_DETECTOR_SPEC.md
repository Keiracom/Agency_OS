# Phase 16B: WHAT Detector Specification

## Technical Specification Document

**Version**: 1.0  
**Date**: December 26, 2025  
**Depends On**: Phase 16A (Data Capture)  
**Status**: Ready for Development  
**Estimated Tasks**: 5  

---

## Overview

The WHAT Detector analyzes content of messages that led to bookings vs those that didn't. It answers: **"What copy, pain points, CTAs, and angles convert?"**

**Output**: Patterns stored in `conversion_patterns` table with `pattern_type = 'what'`

**Consumers**: 
- Messaging Generator Skill (reads patterns to guide copy)
- Content Agent (uses patterns for personalization decisions)

---

## Algorithm Specification

### File: `src/algorithms/what_detector.py`

```python
"""
WHAT Detector Algorithm

Analyzes content of converting vs non-converting messages to find patterns.
Pure statistical analysis - no AI in the loop.

Key Analyses:
1. Subject line patterns
2. Pain point effectiveness
3. CTA effectiveness  
4. Message angle classification
5. Optimal length by channel
6. Personalization lift
"""

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.activity import Activity
from src.models.lead import Lead


# =============================================================================
# PATTERN VOCABULARIES
# =============================================================================

PAIN_POINT_KEYWORDS = {
    "leads": [
        "leads", "pipeline", "prospects", "opportunities", 
        "qualified", "mql", "sql", "inbound"
    ],
    "revenue": [
        "revenue", "sales", "growth", "roi", "profit", 
        "income", "deals", "closed", "won"
    ],
    "time": [
        "time", "hours", "manual", "automate", "efficiency", 
        "busy", "bandwidth", "overwhelmed", "tedious"
    ],
    "scaling": [
        "scale", "scaling", "growth", "capacity", "bandwidth", 
        "hire", "team", "expand", "growing"
    ],
    "competition": [
        "competitors", "competition", "market share", "behind", 
        "catching up", "losing", "threat"
    ],
    "cost": [
        "cost", "expensive", "budget", "waste", "spending", 
        "save", "afford", "price", "investment"
    ],
    "quality": [
        "quality", "results", "performance", "outcomes", 
        "better", "improve", "consistent"
    ],
    "clients": [
        "clients", "customers", "retention", "churn", 
        "satisfaction", "referrals", "testimonials"
    ]
}

ANGLE_PATTERNS = {
    "roi_focused": [
        "roi", "return", "revenue", "profit", "save", 
        r"\$\d+", r"\d+%", "increase", "boost", "double"
    ],
    "social_proof": [
        "clients like", "companies like", "others in your", 
        "case study", "results for", "helped", "worked with"
    ],
    "curiosity": [
        "noticed", "wondering", "quick question", "curious", 
        "idea for", "thought about", "saw that"
    ],
    "fear_based": [
        "missing out", "losing", "behind", "risk", 
        "problem", "struggle", "challenge", "pain"
    ],
    "value_add": [
        "free", "complimentary", "audit", "analysis", 
        "assessment", "no cost", "gift", "bonus"
    ],
    "authority": [
        "expert", "specialist", "years", "experience", 
        "trusted", "leading", "top", "best"
    ],
    "urgency": [
        "limited", "spots", "ending", "deadline", 
        "this week", "today only", "last chance"
    ]
}

CTA_PATTERNS = [
    ("open to a quick chat", "soft_ask"),
    ("worth 15 minutes", "time_specific"),
    ("worth a conversation", "soft_ask"),
    ("free audit", "value_offer"),
    ("free analysis", "value_offer"),
    ("quick call", "soft_ask"),
    ("schedule a call", "direct_ask"),
    ("book a time", "direct_ask"),
    ("interested in learning", "soft_ask"),
    ("happy to share", "value_offer"),
    ("let me know", "passive"),
    ("thoughts?", "question"),
    ("make sense to connect", "soft_ask"),
    ("grab 15 minutes", "time_specific"),
    ("coffee chat", "casual"),
]

SUBJECT_PATTERN_TEMPLATES = [
    (r"^question\s+(about|for|regarding)", "question_about"),
    (r"^quick\s+question", "quick_question"),
    (r"^re:", "reply_style"),
    (r"^\w+\s*[-–—]\s*", "name_dash"),
    (r"^idea\s+for", "idea_for"),
    (r"^thought\s+(about|for)", "thought_about"),
    (r"\?$", "ends_question"),
    (r"^(hey|hi)\s+\w+", "casual_greeting"),
    (r"(introduction|intro)\b", "introduction"),
    (r"(partnership|partner)\b", "partnership"),
    (r"(opportunity)\b", "opportunity"),
    (r"(congrats|congratulations)\b", "congratulatory"),
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SubjectPatterns:
    winning: list = field(default_factory=list)
    losing: list = field(default_factory=list)


@dataclass
class PainPointPatterns:
    effective: list = field(default_factory=list)
    ineffective: list = field(default_factory=list)


@dataclass
class CTAPatterns:
    effective: list = field(default_factory=list)
    by_type: dict = field(default_factory=dict)


@dataclass
class AnglePatterns:
    rankings: list = field(default_factory=list)


@dataclass
class LengthPatterns:
    email: dict = field(default_factory=dict)
    linkedin: dict = field(default_factory=dict)
    sms: dict = field(default_factory=dict)


@dataclass
class PersonalizationPatterns:
    company_mention_lift: float = 1.0
    recent_news_lift: float = 1.0
    mutual_connection_lift: float = 1.0
    industry_specific_lift: float = 1.0


@dataclass
class WhatPatterns:
    """Complete WHAT pattern output"""
    subject_patterns: SubjectPatterns
    pain_points: PainPointPatterns
    ctas: CTAPatterns
    angles: AnglePatterns
    optimal_length: LengthPatterns
    personalization: PersonalizationPatterns
    sample_size: int
    confidence: float
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for database storage"""
        return {
            "type": "what",
            "version": "1.0",
            "subject_patterns": {
                "winning": self.subject_patterns.winning,
                "losing": self.subject_patterns.losing
            },
            "pain_points": {
                "effective": self.pain_points.effective,
                "ineffective": self.pain_points.ineffective
            },
            "ctas": {
                "effective": self.ctas.effective,
                "by_type": self.ctas.by_type
            },
            "angles": {
                "rankings": self.angles.rankings
            },
            "optimal_length": {
                "email": self.optimal_length.email,
                "linkedin": self.optimal_length.linkedin,
                "sms": self.optimal_length.sms
            },
            "personalization_lift": {
                "company_mention": self.personalization.company_mention_lift,
                "recent_news": self.personalization.recent_news_lift,
                "mutual_connection": self.personalization.mutual_connection_lift,
                "industry_specific": self.personalization.industry_specific_lift
            },
            "sample_size": self.sample_size,
            "confidence": self.confidence
        }
    
    @classmethod
    def insufficient_data(cls) -> "WhatPatterns":
        """Return empty patterns when insufficient data"""
        return cls(
            subject_patterns=SubjectPatterns(),
            pain_points=PainPointPatterns(),
            ctas=CTAPatterns(),
            angles=AnglePatterns(),
            optimal_length=LengthPatterns(),
            personalization=PersonalizationPatterns(),
            sample_size=0,
            confidence=0.0
        )


# =============================================================================
# MAIN DETECTOR CLASS
# =============================================================================

class WhatDetector:
    """
    Analyzes content of converting vs non-converting messages.
    
    All analysis is pure Python - pattern matching and statistics.
    No AI/LLM calls involved.
    """
    
    MIN_SAMPLES_TOTAL = 20
    MIN_SAMPLES_CATEGORY = 3
    
    async def analyze(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> WhatPatterns:
        """
        Main entry point. Analyze content patterns for a client.
        
        Args:
            db: Database session
            client_id: Client UUID
            
        Returns:
            WhatPatterns with all content analysis
        """
        # 1. Fetch converting and non-converting touches
        converting = await self._get_converting_touches(db, client_id)
        non_converting = await self._get_non_converting_touches(db, client_id)
        
        total = len(converting) + len(non_converting)
        
        if len(converting) < 5 or total < self.MIN_SAMPLES_TOTAL:
            return WhatPatterns.insufficient_data()
        
        # 2. Run all analyses
        subject_patterns = self._analyze_subjects(converting, non_converting)
        pain_points = self._analyze_pain_points(converting, non_converting)
        ctas = self._analyze_ctas(converting, non_converting)
        angles = self._analyze_angles(converting, non_converting)
        optimal_length = self._analyze_length(converting, non_converting)
        personalization = self._analyze_personalization(converting, non_converting)
        
        # 3. Calculate confidence
        confidence = self._calculate_confidence(len(converting), total)
        
        return WhatPatterns(
            subject_patterns=subject_patterns,
            pain_points=pain_points,
            ctas=ctas,
            angles=angles,
            optimal_length=optimal_length,
            personalization=personalization,
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
        These have led_to_booking = TRUE (set by trigger in migration 014).
        """
        query = select(Activity).where(
            and_(
                Activity.client_id == client_id,
                Activity.led_to_booking == True,
                Activity.content_snapshot.isnot(None),
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
        Sample from leads that reached terminal failed state.
        """
        # Get activities from failed leads
        query = select(Activity).join(
            Lead, Activity.lead_id == Lead.id
        ).where(
            and_(
                Activity.client_id == client_id,
                Activity.led_to_booking == False,
                Activity.content_snapshot.isnot(None),
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
    
    # =========================================================================
    # SUBJECT LINE ANALYSIS
    # =========================================================================
    
    def _analyze_subjects(
        self, 
        converting: list[Activity], 
        non_converting: list[Activity]
    ) -> SubjectPatterns:
        """
        Analyze subject line patterns.
        Only applies to email activities.
        """
        # Filter to emails only
        conv_emails = [a for a in converting if a.action == 'email_sent']
        non_conv_emails = [a for a in non_converting if a.action == 'email_sent']
        
        if not conv_emails:
            return SubjectPatterns()
        
        # Count pattern occurrences
        conv_patterns = defaultdict(int)
        non_conv_patterns = defaultdict(int)
        
        for activity in conv_emails:
            subject = self._get_subject(activity)
            if subject:
                patterns = self._classify_subject(subject)
                for pattern in patterns:
                    conv_patterns[pattern] += 1
        
        for activity in non_conv_emails:
            subject = self._get_subject(activity)
            if subject:
                patterns = self._classify_subject(subject)
                for pattern in patterns:
                    non_conv_patterns[pattern] += 1
        
        # Calculate conversion rates
        total_conv = len(conv_emails)
        total_non_conv = len(non_conv_emails)
        overall_rate = total_conv / (total_conv + total_non_conv)
        
        pattern_stats = []
        all_patterns = set(conv_patterns.keys()) | set(non_conv_patterns.keys())
        
        for pattern in all_patterns:
            conv_count = conv_patterns[pattern]
            non_conv_count = non_conv_patterns[pattern]
            total = conv_count + non_conv_count
            
            if total >= self.MIN_SAMPLES_CATEGORY:
                rate = conv_count / total
                lift = rate / overall_rate if overall_rate > 0 else 1.0
                pattern_stats.append({
                    "pattern": pattern,
                    "conversion_rate": round(rate, 3),
                    "sample": total,
                    "lift": round(lift, 2)
                })
        
        # Sort by conversion rate
        pattern_stats.sort(key=lambda x: -x["conversion_rate"])
        
        # Split into winning (lift > 1) and losing (lift < 1)
        winning = [p for p in pattern_stats if p["lift"] > 1.0][:5]
        losing = [p for p in pattern_stats if p["lift"] < 0.9][:5]
        
        return SubjectPatterns(winning=winning, losing=losing)
    
    def _get_subject(self, activity: Activity) -> Optional[str]:
        """Extract subject from content_snapshot"""
        if activity.content_snapshot:
            return activity.content_snapshot.get("subject", "")
        return None
    
    def _classify_subject(self, subject: str) -> list[str]:
        """Classify a subject line into pattern categories"""
        subject_lower = subject.lower().strip()
        patterns = []
        
        for regex, pattern_name in SUBJECT_PATTERN_TEMPLATES:
            if re.search(regex, subject_lower):
                patterns.append(pattern_name)
        
        # Length category
        word_count = len(subject.split())
        if word_count <= 3:
            patterns.append("short_subject")
        elif word_count <= 6:
            patterns.append("medium_subject")
        else:
            patterns.append("long_subject")
        
        return patterns if patterns else ["other"]
    
    # =========================================================================
    # PAIN POINT ANALYSIS
    # =========================================================================
    
    def _analyze_pain_points(
        self, 
        converting: list[Activity], 
        non_converting: list[Activity]
    ) -> PainPointPatterns:
        """
        Analyze which pain points appear in converting vs non-converting messages.
        """
        conv_pain_points = defaultdict(int)
        non_conv_pain_points = defaultdict(int)
        
        for activity in converting:
            body = self._get_body(activity)
            if body:
                found = self._extract_pain_points(body)
                for pp in found:
                    conv_pain_points[pp] += 1
        
        for activity in non_converting:
            body = self._get_body(activity)
            if body:
                found = self._extract_pain_points(body)
                for pp in found:
                    non_conv_pain_points[pp] += 1
        
        # Calculate effectiveness
        total_conv = len(converting)
        total_non_conv = len(non_converting)
        overall_rate = total_conv / (total_conv + total_non_conv) if (total_conv + total_non_conv) > 0 else 0
        
        pain_point_stats = []
        all_pain_points = set(conv_pain_points.keys()) | set(non_conv_pain_points.keys())
        
        for pp in all_pain_points:
            conv_count = conv_pain_points[pp]
            non_conv_count = non_conv_pain_points[pp]
            
            # Frequency in converting messages
            frequency = conv_count / total_conv if total_conv > 0 else 0
            
            # Calculate lift (how much more likely in converting)
            conv_rate = conv_count / total_conv if total_conv > 0 else 0
            non_conv_rate = non_conv_count / total_non_conv if total_non_conv > 0 else 0
            
            if non_conv_rate > 0:
                lift = conv_rate / non_conv_rate
            else:
                lift = 2.0 if conv_rate > 0 else 1.0
            
            pain_point_stats.append({
                "pain_point": pp,
                "frequency": round(frequency, 3),
                "lift": round(lift, 2),
                "conv_count": conv_count,
                "total_count": conv_count + non_conv_count
            })
        
        # Sort by lift
        pain_point_stats.sort(key=lambda x: -x["lift"])
        
        # Effective: lift > 1.1 and used in at least 10% of converting
        effective = [
            p for p in pain_point_stats 
            if p["lift"] > 1.1 and p["frequency"] >= 0.1
        ][:5]
        
        # Ineffective: lift < 0.9
        ineffective = [
            p for p in pain_point_stats 
            if p["lift"] < 0.9 and p["total_count"] >= self.MIN_SAMPLES_CATEGORY
        ][:3]
        
        return PainPointPatterns(effective=effective, ineffective=ineffective)
    
    def _get_body(self, activity: Activity) -> Optional[str]:
        """Extract body/message from content_snapshot"""
        if activity.content_snapshot:
            return activity.content_snapshot.get("body", "")
        return None
    
    def _extract_pain_points(self, text: str) -> list[str]:
        """Extract pain points mentioned in text"""
        text_lower = text.lower()
        found = []
        
        for pain_point, keywords in PAIN_POINT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found.append(pain_point)
                    break  # Only count each pain point once
        
        return found
    
    # =========================================================================
    # CTA ANALYSIS
    # =========================================================================
    
    def _analyze_ctas(
        self, 
        converting: list[Activity], 
        non_converting: list[Activity]
    ) -> CTAPatterns:
        """
        Analyze which CTAs appear in converting messages.
        """
        cta_conv_counts = defaultdict(int)
        cta_type_conv_counts = defaultdict(int)
        cta_total_counts = defaultdict(int)
        cta_type_total_counts = defaultdict(int)
        
        for activity in converting:
            body = self._get_body(activity)
            if body:
                cta, cta_type = self._extract_cta(body)
                if cta:
                    cta_conv_counts[cta] += 1
                    cta_total_counts[cta] += 1
                    cta_type_conv_counts[cta_type] += 1
                    cta_type_total_counts[cta_type] += 1
        
        for activity in non_converting:
            body = self._get_body(activity)
            if body:
                cta, cta_type = self._extract_cta(body)
                if cta:
                    cta_total_counts[cta] += 1
                    cta_type_total_counts[cta_type] += 1
        
        # Calculate CTA effectiveness
        effective = []
        for cta, total in cta_total_counts.items():
            if total >= self.MIN_SAMPLES_CATEGORY:
                conv_count = cta_conv_counts[cta]
                rate = conv_count / total
                effective.append({
                    "cta": cta,
                    "conversion_rate": round(rate, 3),
                    "sample": total
                })
        
        effective.sort(key=lambda x: -x["conversion_rate"])
        
        # Calculate by type
        by_type = {}
        for cta_type, total in cta_type_total_counts.items():
            if total >= self.MIN_SAMPLES_CATEGORY:
                conv_count = cta_type_conv_counts[cta_type]
                by_type[cta_type] = {
                    "conversion_rate": round(conv_count / total, 3),
                    "sample": total
                }
        
        return CTAPatterns(effective=effective[:5], by_type=by_type)
    
    def _extract_cta(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Extract CTA from text, return (cta_text, cta_type)"""
        text_lower = text.lower()
        
        for cta_pattern, cta_type in CTA_PATTERNS:
            if cta_pattern in text_lower:
                return (cta_pattern, cta_type)
        
        return (None, None)
    
    # =========================================================================
    # ANGLE ANALYSIS
    # =========================================================================
    
    def _analyze_angles(
        self, 
        converting: list[Activity], 
        non_converting: list[Activity]
    ) -> AnglePatterns:
        """
        Classify messages by angle/framing and measure effectiveness.
        """
        angle_conv_counts = defaultdict(int)
        angle_total_counts = defaultdict(int)
        
        for activity in converting:
            body = self._get_body(activity)
            subject = self._get_subject(activity) or ""
            full_text = f"{subject} {body}" if body else subject
            
            if full_text:
                angles = self._classify_angles(full_text)
                for angle in angles:
                    angle_conv_counts[angle] += 1
                    angle_total_counts[angle] += 1
        
        for activity in non_converting:
            body = self._get_body(activity)
            subject = self._get_subject(activity) or ""
            full_text = f"{subject} {body}" if body else subject
            
            if full_text:
                angles = self._classify_angles(full_text)
                for angle in angles:
                    angle_total_counts[angle] += 1
        
        # Calculate effectiveness
        rankings = []
        for angle, total in angle_total_counts.items():
            if total >= self.MIN_SAMPLES_CATEGORY:
                conv_count = angle_conv_counts[angle]
                rate = conv_count / total
                rankings.append({
                    "angle": angle,
                    "conversion_rate": round(rate, 3),
                    "sample": total
                })
        
        rankings.sort(key=lambda x: -x["conversion_rate"])
        
        return AnglePatterns(rankings=rankings)
    
    def _classify_angles(self, text: str) -> list[str]:
        """Classify text into angle categories"""
        text_lower = text.lower()
        found_angles = []
        
        for angle, patterns in ANGLE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    found_angles.append(angle)
                    break
        
        return found_angles if found_angles else ["neutral"]
    
    # =========================================================================
    # LENGTH ANALYSIS
    # =========================================================================
    
    def _analyze_length(
        self, 
        converting: list[Activity], 
        non_converting: list[Activity]
    ) -> LengthPatterns:
        """
        Find optimal message length by channel.
        """
        length_data = {
            "email": {"conv": [], "non_conv": []},
            "linkedin": {"conv": [], "non_conv": []},
            "sms": {"conv": [], "non_conv": []}
        }
        
        channel_map = {
            "email_sent": "email",
            "linkedin_sent": "linkedin",
            "sms_sent": "sms"
        }
        
        for activity in converting:
            channel = channel_map.get(activity.action)
            if channel:
                length = self._get_message_length(activity, channel)
                if length:
                    length_data[channel]["conv"].append(length)
        
        for activity in non_converting:
            channel = channel_map.get(activity.action)
            if channel:
                length = self._get_message_length(activity, channel)
                if length:
                    length_data[channel]["non_conv"].append(length)
        
        # Calculate optimal lengths
        result = LengthPatterns()
        
        for channel in ["email", "linkedin", "sms"]:
            conv_lengths = length_data[channel]["conv"]
            if len(conv_lengths) >= self.MIN_SAMPLES_CATEGORY:
                avg = sum(conv_lengths) / len(conv_lengths)
                min_len = min(conv_lengths)
                max_len = max(conv_lengths)
                
                # Calculate 25th and 75th percentile for range
                sorted_lengths = sorted(conv_lengths)
                p25 = sorted_lengths[len(sorted_lengths) // 4]
                p75 = sorted_lengths[3 * len(sorted_lengths) // 4]
                
                unit = "chars" if channel == "sms" else "words"
                
                channel_data = {
                    f"optimal_{unit}": round(avg),
                    f"range_min": p25,
                    f"range_max": p75,
                    "sample": len(conv_lengths)
                }
                
                setattr(result, channel, channel_data)
        
        return result
    
    def _get_message_length(
        self, 
        activity: Activity, 
        channel: str
    ) -> Optional[int]:
        """Get message length (words for email/linkedin, chars for sms)"""
        body = self._get_body(activity)
        if not body:
            return None
        
        if channel == "sms":
            return len(body)
        else:
            return len(body.split())
    
    # =========================================================================
    # PERSONALIZATION ANALYSIS
    # =========================================================================
    
    def _analyze_personalization(
        self, 
        converting: list[Activity], 
        non_converting: list[Activity]
    ) -> PersonalizationPatterns:
        """
        Calculate lift from various personalization elements.
        """
        result = PersonalizationPatterns()
        
        # Analyze each personalization type
        personalization_checks = [
            ("company_mention", self._has_company_mention),
            ("recent_news", self._has_recent_news),
            ("mutual_connection", self._has_mutual_connection),
            ("industry_specific", self._has_industry_specific),
        ]
        
        for field_name, check_fn in personalization_checks:
            lift = self._calculate_personalization_lift(
                converting, non_converting, check_fn
            )
            setattr(result, f"{field_name}_lift", round(lift, 2))
        
        return result
    
    def _calculate_personalization_lift(
        self,
        converting: list[Activity],
        non_converting: list[Activity],
        check_fn
    ) -> float:
        """Calculate lift for a personalization element"""
        conv_with = sum(1 for a in converting if check_fn(a))
        conv_without = len(converting) - conv_with
        
        non_conv_with = sum(1 for a in non_converting if check_fn(a))
        non_conv_without = len(non_converting) - non_conv_with
        
        total_with = conv_with + non_conv_with
        total_without = conv_without + non_conv_without
        
        if total_with < self.MIN_SAMPLES_CATEGORY or total_without < self.MIN_SAMPLES_CATEGORY:
            return 1.0
        
        rate_with = conv_with / total_with
        rate_without = conv_without / total_without
        
        if rate_without > 0:
            return rate_with / rate_without
        return 1.0
    
    def _has_company_mention(self, activity: Activity) -> bool:
        """Check if message mentions the lead's company"""
        if activity.content_snapshot:
            return activity.content_snapshot.get("has_company_mention", False)
        return False
    
    def _has_recent_news(self, activity: Activity) -> bool:
        """Check if message references recent news"""
        if activity.content_snapshot:
            return activity.content_snapshot.get("has_recent_news", False)
        return False
    
    def _has_mutual_connection(self, activity: Activity) -> bool:
        """Check if message mentions mutual connection"""
        if activity.content_snapshot:
            return activity.content_snapshot.get("has_mutual_connection", False)
        return False
    
    def _has_industry_specific(self, activity: Activity) -> bool:
        """Check if message has industry-specific content"""
        if activity.content_snapshot:
            return activity.content_snapshot.get("has_industry_specific", False)
        return False
    
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
```

---

## Content Snapshot Schema

For the WHAT Detector to work, engines must capture content when sending messages.

### Email Engine Content Snapshot

```python
# In EmailEngine.send() - store this in activity.content_snapshot

content_snapshot = {
    "subject": email.subject,
    "body": email.body,
    "word_count": len(email.body.split()),
    "has_company_mention": lead.company_name.lower() in email.body.lower(),
    "has_recent_news": bool(re.search(r"(noticed|saw|congrats)", email.body.lower())),
    "has_mutual_connection": "mutual" in email.body.lower() or "connection" in email.body.lower(),
    "has_industry_specific": lead.industry.lower() in email.body.lower() if lead.industry else False,
    "pain_points_used": extract_pain_points(email.body),  # Use PAIN_POINT_KEYWORDS
    "cta_used": extract_cta(email.body),
    "template_id": email.template_id,
    "touch_number": activity.touch_number
}
```

### SMS Engine Content Snapshot

```python
content_snapshot = {
    "body": sms.message,
    "char_count": len(sms.message),
    "has_company_mention": lead.company_name.lower() in sms.message.lower(),
    "cta_used": extract_cta(sms.message),
    "touch_number": activity.touch_number
}
```

### LinkedIn Engine Content Snapshot

```python
content_snapshot = {
    "message_type": "connection_request" | "inmail" | "message",
    "body": linkedin.message,
    "word_count": len(linkedin.message.split()),
    "has_company_mention": lead.company_name.lower() in linkedin.message.lower(),
    "has_mutual_connection": "mutual" in linkedin.message.lower(),
    "touch_number": activity.touch_number
}
```

---

## Integration: Messaging Generator Skill

### Modified Input Model

```python
class MessagingGeneratorInput(BaseModel):
    """Input for Messaging Generator Skill"""
    sequence: list[dict]  # From SequenceBuilderSkill
    client_icp: dict
    lead_context: Optional[dict] = None
    
    # NEW: Pattern context
    what_patterns: Optional[dict] = None
```

### Modified Prompt Construction

```python
def _build_prompt(self, input: MessagingGeneratorInput) -> str:
    prompt = f"""Generate messaging for a {len(input.sequence)}-touch sequence.

CLIENT ICP:
{json.dumps(input.client_icp, indent=2)}

SEQUENCE:
{json.dumps(input.sequence, indent=2)}
"""
    
    # Add pattern guidance if available
    if input.what_patterns:
        patterns = input.what_patterns
        
        prompt += "\n\n--- CONVERSION INTELLIGENCE (use these insights) ---\n"
        
        # Pain points
        if patterns.get("pain_points", {}).get("effective"):
            prompt += "\nEFFECTIVE PAIN POINTS (prioritize these):\n"
            for pp in patterns["pain_points"]["effective"][:3]:
                prompt += f"  • {pp['pain_point']} - {pp['lift']}x more likely to convert\n"
        
        if patterns.get("pain_points", {}).get("ineffective"):
            prompt += "\nINEFFECTIVE PAIN POINTS (avoid these):\n"
            for pp in patterns["pain_points"]["ineffective"]:
                prompt += f"  • {pp['pain_point']}\n"
        
        # CTAs
        if patterns.get("ctas", {}).get("effective"):
            prompt += "\nEFFECTIVE CTAs (use variations of these):\n"
            for cta in patterns["ctas"]["effective"][:3]:
                prompt += f"  • \"{cta['cta']}\" ({cta['conversion_rate']*100:.0f}% conv rate)\n"
        
        # Angles
        if patterns.get("angles", {}).get("rankings"):
            top_angles = patterns["angles"]["rankings"][:2]
            prompt += f"\nBEST ANGLES: {', '.join(a['angle'] for a in top_angles)}\n"
        
        # Length
        if patterns.get("optimal_length", {}).get("email"):
            email_len = patterns["optimal_length"]["email"]
            prompt += f"\nOPTIMAL EMAIL LENGTH: {email_len.get('optimal_words', 75)} words "
            prompt += f"(range: {email_len.get('range_min', 50)}-{email_len.get('range_max', 100)})\n"
        
        # Personalization
        if patterns.get("personalization_lift"):
            pers = patterns["personalization_lift"]
            if pers.get("company_mention", 1) > 1.2:
                prompt += f"\n✓ Mentioning company name increases conversion {pers['company_mention']}x\n"
            if pers.get("recent_news", 1) > 1.3:
                prompt += f"✓ Referencing recent news increases conversion {pers['recent_news']}x\n"
    
    return prompt
```

---

## Tasks

| Task | Description | File(s) | Est. Hours |
|------|-------------|---------|------------|
| 16B.1 | Create WhatDetector class with all methods | `src/algorithms/what_detector.py` | 3 |
| 16B.2 | Add content_snapshot capture to Email engine | `src/engines/email.py` | 1 |
| 16B.3 | Add content_snapshot capture to SMS/LinkedIn engines | `src/engines/sms.py`, `linkedin.py` | 1 |
| 16B.4 | Integrate patterns into MessagingGeneratorSkill | `src/agents/skills/messaging_generator.py` | 2 |
| 16B.5 | Write unit tests | `tests/algorithms/test_what_detector.py` | 2 |

**Total: 5 tasks, ~9 hours**

---

## Testing

```python
# tests/algorithms/test_what_detector.py

import pytest
from src.algorithms.what_detector import WhatDetector, PAIN_POINT_KEYWORDS

class TestWhatDetector:
    
    def test_extract_pain_points(self):
        detector = WhatDetector()
        
        text = "Struggling to generate enough qualified leads for your pipeline?"
        result = detector._extract_pain_points(text)
        
        assert "leads" in result
    
    def test_classify_subject_patterns(self):
        detector = WhatDetector()
        
        # Question pattern
        patterns = detector._classify_subject("Question about your marketing")
        assert "question_about" in patterns
        
        # Quick question pattern
        patterns = detector._classify_subject("Quick question")
        assert "quick_question" in patterns
    
    def test_extract_cta(self):
        detector = WhatDetector()
        
        text = "Would you be open to a quick chat next week?"
        cta, cta_type = detector._extract_cta(text)
        
        assert cta == "open to a quick chat"
        assert cta_type == "soft_ask"
    
    def test_classify_angles(self):
        detector = WhatDetector()
        
        # ROI focused
        text = "Clients typically see a 3x ROI within 90 days"
        angles = detector._classify_angles(text)
        assert "roi_focused" in angles
        
        # Social proof
        text = "We've helped companies like yours generate 50+ leads"
        angles = detector._classify_angles(text)
        assert "social_proof" in angles
    
    def test_insufficient_data_returns_empty(self):
        detector = WhatDetector()
        # With < 5 converting samples, should return empty patterns
        patterns = detector.analyze_sync([], [])
        
        assert patterns.sample_size == 0
        assert patterns.confidence == 0.0
```

---

**End of Phase 16B Specification**
