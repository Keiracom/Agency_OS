# Phase 16: Conversion Intelligence System

## Technical Specification Document

**Version**: 1.0  
**Date**: December 26, 2025  
**Author**: Claude + Dave (CEO)  
**Status**: Ready for Development  
**Estimated Tasks**: 26  

---

## Executive Summary

This document specifies the **Conversion Intelligence System** - a data-driven algorithm that learns from historical outcomes to optimize both **lead selection** (WHO to target) and **engagement strategy** (HOW to convert them).

**Key Principle**: Claude cannot learn between conversations. All "learning" happens through:
1. Database storage of historical patterns
2. Scheduled Python jobs that analyze data
3. Statistical algorithms (no AI in the loop)
4. Pattern outputs fed to existing agents/engines

**Success Metric**: Meeting bookings. Every component traces back to this single outcome.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [System Architecture](#2-system-architecture)
3. [Data Model](#3-data-model)
4. [Algorithm Specifications](#4-algorithm-specifications)
5. [Integration Points](#5-integration-points)
6. [Implementation Phases](#6-implementation-phases)
7. [Testing Strategy](#7-testing-strategy)
8. [Success Metrics](#8-success-metrics)

---

## 1. Problem Statement

### 1.1 The Two Core Problems

**Problem 1: WHO to Target (Lead Selection)**
- Current state: Static ALS formula with fixed weights
- Problem: Weights are guesses, not data-driven
- Goal: Dynamically adjust weights based on which leads actually convert

**Problem 2: HOW to Convert (Engagement Optimization)**
- Current state: Generic sequences and copy
- Problem: No feedback loop from outcomes to content
- Goal: Learn what copy, timing, channels, and angles lead to bookings

### 1.2 Constraints

| Constraint | Implication |
|------------|-------------|
| Claude can't learn | All learning via database + Python algorithms |
| Small sample sizes | Bayesian/statistical methods, not ML |
| Per-client patterns | Each agency may have different optimal patterns |
| Real-time scoring | Patterns computed offline, applied in real-time |
| Deterministic execution | Engines remain deterministic, only inputs change |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONVERSION INTELLIGENCE SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     PATTERN DETECTORS                                │   │
│  │                  (Weekly Prefect Jobs)                               │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   WHO       │  │   WHAT      │  │   WHEN      │  │   HOW       │ │   │
│  │  │  Detector   │  │  Detector   │  │  Detector   │  │  Detector   │ │   │
│  │  │             │  │             │  │             │  │             │ │   │
│  │  │ Lead attrs  │  │ Content     │  │ Timing      │  │ Channel     │ │   │
│  │  │ that book   │  │ that books  │  │ that books  │  │ sequences   │ │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │   │
│  │         │                │                │                │        │   │
│  └─────────┼────────────────┼────────────────┼────────────────┼────────┘   │
│            │                │                │                │            │
│            ▼                ▼                ▼                ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     PATTERN STORAGE                                  │   │
│  │                (conversion_patterns table)                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                │                │                │            │
│            ▼                ▼                ▼                ▼            │
│  ┌─────────────────────┐    │    ┌─────────────────────────────────────┐   │
│  │    ALS SCORER       │    │    │    CAMPAIGN GENERATION              │   │
│  │    (Engine)         │    │    │    (Agent + Skills)                 │   │
│  │                     │    │    │                                     │   │
│  │ Reads WHO patterns  │    └───▶│ Reads WHAT/WHEN/HOW patterns        │   │
│  │ Applies weights     │         │ Generates optimized sequences       │   │
│  └─────────────────────┘         └─────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
RUNTIME PATH (real-time):
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│  New     │────▶│ Scorer reads │────▶│ Lead scored │
│  Lead    │     │ WHO patterns │     │ with learned│
└──────────┘     └──────────────┘     │ weights     │
                                      └─────────────┘

LEARNING PATH (weekly batch):
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│ Leads w/ │────▶│ Detectors    │────▶│ Patterns    │
│ outcomes │     │ analyze data │     │ saved to DB │
└──────────┘     └──────────────┘     └─────────────┘
```

---

## 3. Data Model

### 3.1 Migration: 014_conversion_intelligence.sql

```sql
-- ============================================================================
-- Migration 014: Conversion Intelligence System
-- ============================================================================

-- 1. Add ALS component snapshot to leads (for learning)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS als_components JSONB;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS als_weights_used JSONB;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;

-- Example als_components:
-- {
--   "data_quality": 16,
--   "authority": 22,
--   "company_fit": 18,
--   "timing": 9,
--   "risk": 0
-- }

-- 2. Add converting touch tracking to activities
ALTER TABLE activities ADD COLUMN IF NOT EXISTS led_to_booking BOOLEAN DEFAULT FALSE;
ALTER TABLE activities ADD COLUMN IF NOT EXISTS content_snapshot JSONB;

-- Example content_snapshot (stored when activity created):
-- {
--   "subject": "Quick question about {company}",
--   "body": "Hi {first_name}, I noticed...",
--   "pain_points": ["leads", "scaling"],
--   "cta": "open to a quick chat",
--   "word_count": 78,
--   "personalization_level": 3
-- }

-- 3. Add learned weights to clients
ALTER TABLE clients ADD COLUMN IF NOT EXISTS als_learned_weights JSONB;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS als_weights_updated_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS conversion_sample_count INTEGER DEFAULT 0;

-- 4. Create conversion_patterns table
CREATE TABLE IF NOT EXISTS conversion_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('who', 'what', 'when', 'how')),
    patterns JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_client_pattern_type UNIQUE (client_id, pattern_type)
);

-- Indexes
CREATE INDEX idx_conversion_patterns_client ON conversion_patterns(client_id);
CREATE INDEX idx_conversion_patterns_type ON conversion_patterns(pattern_type);
CREATE INDEX idx_conversion_patterns_valid ON conversion_patterns(valid_until);

CREATE INDEX idx_leads_als_components ON leads USING GIN (als_components);
CREATE INDEX idx_activities_led_to_booking ON activities(led_to_booking) WHERE led_to_booking = TRUE;

-- 5. Create pattern history table (for tracking pattern evolution)
CREATE TABLE IF NOT EXISTS conversion_pattern_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL,
    patterns JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pattern_history_client ON conversion_pattern_history(client_id, pattern_type, computed_at DESC);

-- 6. RLS Policies
ALTER TABLE conversion_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversion_pattern_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_patterns ON conversion_patterns
    FOR ALL USING (
        client_id IN (
            SELECT client_id FROM memberships 
            WHERE user_id = auth.uid() AND accepted_at IS NOT NULL
        )
    );

CREATE POLICY tenant_isolation_pattern_history ON conversion_pattern_history
    FOR ALL USING (
        client_id IN (
            SELECT client_id FROM memberships 
            WHERE user_id = auth.uid() AND accepted_at IS NOT NULL
        )
    );

-- 7. Function to mark converting touch
CREATE OR REPLACE FUNCTION mark_converting_touch()
RETURNS TRIGGER AS $$
BEGIN
    -- When a lead status changes to 'converted' or meeting_booked activity created
    IF NEW.status = 'converted' AND (OLD.status IS NULL OR OLD.status != 'converted') THEN
        -- Find the most recent activity before conversion and mark it
        UPDATE activities
        SET led_to_booking = TRUE
        WHERE lead_id = NEW.id
        AND action IN ('email_sent', 'sms_sent', 'linkedin_sent', 'voice_completed')
        AND created_at = (
            SELECT MAX(created_at) FROM activities
            WHERE lead_id = NEW.id
            AND action IN ('email_sent', 'sms_sent', 'linkedin_sent', 'voice_completed')
            AND created_at < NOW()
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_mark_converting_touch
    AFTER UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION mark_converting_touch();
```

### 3.2 Pattern Schema Definitions

#### WHO Pattern Schema

```json
{
  "type": "who",
  "version": "1.0",
  "computed_at": "2025-12-26T10:00:00Z",
  "sample_size": 156,
  "confidence": 0.82,
  
  "title_rankings": [
    {"title": "Marketing Director", "conversion_rate": 0.31, "sample": 45, "lift": 1.8},
    {"title": "CEO", "conversion_rate": 0.23, "sample": 112, "lift": 1.4},
    {"title": "Owner", "conversion_rate": 0.18, "sample": 89, "lift": 1.1}
  ],
  
  "industry_rankings": [
    {"industry": "Dental", "conversion_rate": 0.28, "sample": 67, "lift": 1.7},
    {"industry": "Legal", "conversion_rate": 0.22, "sample": 54, "lift": 1.3}
  ],
  
  "size_analysis": {
    "sweet_spot": {"min": 16, "max": 30, "conversion_rate": 0.34},
    "distribution": [
      {"range": "1-5", "conversion_rate": 0.12},
      {"range": "6-15", "conversion_rate": 0.19},
      {"range": "16-30", "conversion_rate": 0.34},
      {"range": "31-50", "conversion_rate": 0.21},
      {"range": "51-100", "conversion_rate": 0.14}
    ]
  },
  
  "timing_signals": {
    "new_role_lift": 1.8,
    "hiring_lift": 1.4,
    "funded_lift": 2.1
  },
  
  "recommended_weights": {
    "data_quality": 0.15,
    "authority": 0.20,
    "company_fit": 0.35,
    "timing": 0.30
  }
}
```

#### WHAT Pattern Schema

```json
{
  "type": "what",
  "version": "1.0",
  "computed_at": "2025-12-26T10:00:00Z",
  "sample_size": 89,
  "confidence": 0.75,
  
  "subject_patterns": {
    "winning": [
      {"pattern": "Question about {company}", "conversion_rate": 0.12, "sample": 34},
      {"pattern": "Quick question", "conversion_rate": 0.09, "sample": 67},
      {"pattern": "{first_name} - {pain_point}", "conversion_rate": 0.08, "sample": 28}
    ],
    "losing": [
      {"pattern": "Partnership opportunity", "conversion_rate": 0.02, "sample": 45},
      {"pattern": "Introduction", "conversion_rate": 0.03, "sample": 38}
    ]
  },
  
  "pain_points": {
    "effective": [
      {"pain_point": "leads", "frequency": 0.67, "lift": 1.4},
      {"pain_point": "time", "frequency": 0.54, "lift": 1.2},
      {"pain_point": "scaling", "frequency": 0.43, "lift": 1.8}
    ],
    "ineffective": [
      {"pain_point": "cost", "frequency": 0.23, "lift": 0.7},
      {"pain_point": "competition", "frequency": 0.18, "lift": 0.9}
    ]
  },
  
  "ctas": {
    "effective": [
      {"cta": "open to a quick chat", "conversion_rate": 0.11, "sample": 56},
      {"cta": "worth 15 minutes", "conversion_rate": 0.09, "sample": 43}
    ]
  },
  
  "angles": {
    "rankings": [
      {"angle": "roi_focused", "conversion_rate": 0.14},
      {"angle": "social_proof", "conversion_rate": 0.11},
      {"angle": "curiosity", "conversion_rate": 0.08},
      {"angle": "fear_based", "conversion_rate": 0.05}
    ]
  },
  
  "optimal_length": {
    "email": {"optimal_words": 75, "range_min": 50, "range_max": 100},
    "linkedin": {"optimal_words": 40, "range_min": 30, "range_max": 50},
    "sms": {"optimal_chars": 120, "range_min": 100, "range_max": 140}
  },
  
  "personalization_lift": {
    "company_mention": 1.3,
    "recent_news": 1.6,
    "mutual_connection": 2.1,
    "industry_specific": 1.4
  }
}
```

#### WHEN Pattern Schema

```json
{
  "type": "when",
  "version": "1.0",
  "computed_at": "2025-12-26T10:00:00Z",
  "sample_size": 89,
  "confidence": 0.78,
  
  "best_days": [
    {"day": "Tuesday", "day_index": 2, "conversion_rate": 0.14, "sample": 45},
    {"day": "Wednesday", "day_index": 3, "conversion_rate": 0.12, "sample": 52},
    {"day": "Thursday", "day_index": 4, "conversion_rate": 0.11, "sample": 48}
  ],
  
  "best_hours": [
    {"hour": 10, "conversion_rate": 0.15, "sample": 38},
    {"hour": 14, "conversion_rate": 0.13, "sample": 42},
    {"hour": 9, "conversion_rate": 0.11, "sample": 35}
  ],
  
  "converting_touch_distribution": {
    "touch_1": 0.08,
    "touch_2": 0.15,
    "touch_3": 0.28,
    "touch_4": 0.22,
    "touch_5": 0.18,
    "touch_6": 0.09
  },
  
  "optimal_sequence_gaps": {
    "touch_1_to_2": 2,
    "touch_2_to_3": 3,
    "touch_3_to_4": 4,
    "touch_4_to_5": 5,
    "touch_5_to_6": 7
  },
  
  "conversion_timing": {
    "avg_days_to_convert": 11.3,
    "median_days_to_convert": 8,
    "percentile_50": 8,
    "percentile_80": 16,
    "percentile_95": 28
  }
}
```

#### HOW Pattern Schema

```json
{
  "type": "how",
  "version": "1.0",
  "computed_at": "2025-12-26T10:00:00Z",
  "sample_size": 89,
  "confidence": 0.72,
  
  "booking_channel_distribution": {
    "email": 0.52,
    "linkedin": 0.28,
    "sms": 0.12,
    "voice": 0.08
  },
  
  "first_touch_effectiveness": {
    "email_first": {"conversion_rate": 0.11, "sample": 234},
    "linkedin_first": {"conversion_rate": 0.14, "sample": 156},
    "sms_first": {"conversion_rate": 0.06, "sample": 45}
  },
  
  "multi_channel_lift": {
    "1_channel": {"conversion_rate": 0.06, "lift": 1.0},
    "2_channels": {"conversion_rate": 0.11, "lift": 1.8},
    "3_channels": {"conversion_rate": 0.16, "lift": 2.7},
    "4_plus_channels": {"conversion_rate": 0.19, "lift": 3.2}
  },
  
  "winning_sequences": [
    {
      "sequence": ["email", "linkedin", "email", "sms", "voice", "email"],
      "conversion_rate": 0.18,
      "sample_size": 45
    },
    {
      "sequence": ["linkedin", "email", "email", "linkedin", "sms", "email"],
      "conversion_rate": 0.15,
      "sample_size": 38
    }
  ],
  
  "channel_effectiveness_by_tier": {
    "hot": {
      "voice": {"conversion_rate": 0.24, "sample": 23},
      "email": {"conversion_rate": 0.18, "sample": 67},
      "linkedin": {"conversion_rate": 0.15, "sample": 45}
    },
    "warm": {
      "email": {"conversion_rate": 0.14, "sample": 134},
      "linkedin": {"conversion_rate": 0.12, "sample": 98},
      "sms": {"conversion_rate": 0.08, "sample": 56}
    },
    "cool": {
      "email": {"conversion_rate": 0.07, "sample": 189},
      "linkedin": {"conversion_rate": 0.05, "sample": 112}
    }
  }
}
```

---

## 4. Algorithm Specifications

### 4.1 WHO Detector Algorithm

**File**: `src/algorithms/who_detector.py`

**Purpose**: Analyze which lead attributes predict bookings

**Input**: All leads with terminal outcomes for a client

**Output**: WHO pattern (see schema above)

```python
"""
WHO Detector Algorithm Specification

This algorithm analyzes historical lead data to determine which
lead attributes are predictive of booking meetings.

Key Methods:
1. conversion_rate_by(field) - Calculate conversion rate per field value
2. calculate_lift(flag) - Calculate lift for boolean flags
3. derive_optimal_weights(booked, failed) - Compute ALS weights via optimization

Statistical Approach:
- Minimum sample size: 5 per category (configurable)
- Confidence calculation: Based on sample size and variance
- Weight optimization: Constrained optimization (scipy.optimize.minimize)
  - Constraint: weights sum to 0.85 (leaving 0.15 for risk)
  - Bounds: each weight between 0.05 and 0.50
  - Method: SLSQP with logistic regression loss
"""

from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from scipy.optimize import minimize
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

@dataclass
class WhoPatterns:
    title_rankings: list[dict]
    industry_rankings: list[dict]
    size_analysis: dict
    timing_signals: dict
    recommended_weights: dict
    sample_size: int
    confidence: float
    
    @classmethod
    def insufficient_data(cls) -> "WhoPatterns":
        """Return default patterns when insufficient data"""
        return cls(
            title_rankings=[],
            industry_rankings=[],
            size_analysis={},
            timing_signals={"new_role_lift": 1.0, "hiring_lift": 1.0, "funded_lift": 1.0},
            recommended_weights={
                "data_quality": 0.20,
                "authority": 0.25,
                "company_fit": 0.25,
                "timing": 0.15
            },
            sample_size=0,
            confidence=0.0
        )


class WhoDetector:
    """
    Analyzes converted vs failed leads to find predictive attributes.
    Pure statistical analysis - no AI involved.
    """
    
    MIN_SAMPLES_TOTAL = 30  # Minimum leads with outcomes to run analysis
    MIN_SAMPLES_CATEGORY = 5  # Minimum per category to include
    
    DEFAULT_WEIGHTS = {
        "data_quality": 0.20,
        "authority": 0.25,
        "company_fit": 0.25,
        "timing": 0.15
    }
    
    async def analyze(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> WhoPatterns:
        """
        Main entry point. Returns WHO patterns for a client.
        """
        # 1. Fetch leads with terminal outcomes
        booked = await self._get_converted_leads(db, client_id)
        failed = await self._get_failed_leads(db, client_id)
        
        total_samples = len(booked) + len(failed)
        
        if len(booked) < 10 or total_samples < self.MIN_SAMPLES_TOTAL:
            return WhoPatterns.insufficient_data()
        
        # 2. Analyze each dimension
        title_rankings = self._analyze_field(booked, failed, "title")
        industry_rankings = self._analyze_field(booked, failed, "industry")
        size_analysis = self._analyze_company_size(booked, failed)
        timing_signals = self._analyze_timing_signals(booked, failed)
        
        # 3. Derive optimal weights
        recommended_weights = self._derive_optimal_weights(booked, failed)
        
        # 4. Calculate confidence
        confidence = self._calculate_confidence(len(booked), total_samples)
        
        return WhoPatterns(
            title_rankings=title_rankings,
            industry_rankings=industry_rankings,
            size_analysis=size_analysis,
            timing_signals=timing_signals,
            recommended_weights=recommended_weights,
            sample_size=total_samples,
            confidence=confidence
        )
    
    async def _get_converted_leads(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> list:
        """Fetch leads that resulted in bookings"""
        # Lead is converted if:
        # - status = 'converted' OR
        # - has activity with action = 'meeting_booked'
        query = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.deleted_at.is_(None),
                Lead.status == 'converted'
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def _get_failed_leads(
        self, 
        db: AsyncSession, 
        client_id: str
    ) -> list:
        """Fetch leads that failed to convert"""
        query = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.deleted_at.is_(None),
                Lead.status.in_(['unsubscribed', 'bounced', 'not_interested', 'dead'])
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    def _analyze_field(
        self, 
        booked: list, 
        failed: list, 
        field: str
    ) -> list[dict]:
        """Calculate conversion rate for each value of a field"""
        totals = defaultdict(int)
        conversions = defaultdict(int)
        
        for lead in booked:
            value = getattr(lead, field, None)
            if value:
                totals[value] += 1
                conversions[value] += 1
        
        for lead in failed:
            value = getattr(lead, field, None)
            if value:
                totals[value] += 1
        
        # Calculate overall conversion rate for lift calculation
        overall_rate = len(booked) / (len(booked) + len(failed))
        
        results = []
        for value, total in totals.items():
            if total >= self.MIN_SAMPLES_CATEGORY:
                rate = conversions[value] / total
                lift = rate / overall_rate if overall_rate > 0 else 1.0
                results.append({
                    field: value,
                    "conversion_rate": round(rate, 3),
                    "sample": total,
                    "lift": round(lift, 2)
                })
        
        # Sort by conversion rate descending
        return sorted(results, key=lambda x: -x["conversion_rate"])
    
    def _analyze_company_size(
        self, 
        booked: list, 
        failed: list
    ) -> dict:
        """Analyze conversion by company size ranges"""
        ranges = [
            (1, 5, "1-5"),
            (6, 15, "6-15"),
            (16, 30, "16-30"),
            (31, 50, "31-50"),
            (51, 100, "51-100"),
            (101, 500, "101-500")
        ]
        
        distribution = []
        best_range = None
        best_rate = 0
        
        for min_size, max_size, label in ranges:
            booked_in_range = sum(
                1 for l in booked 
                if l.employee_count and min_size <= l.employee_count <= max_size
            )
            failed_in_range = sum(
                1 for l in failed 
                if l.employee_count and min_size <= l.employee_count <= max_size
            )
            total = booked_in_range + failed_in_range
            
            if total >= self.MIN_SAMPLES_CATEGORY:
                rate = booked_in_range / total
                distribution.append({
                    "range": label,
                    "conversion_rate": round(rate, 3),
                    "sample": total
                })
                
                if rate > best_rate:
                    best_rate = rate
                    best_range = {"min": min_size, "max": max_size, "conversion_rate": round(rate, 3)}
        
        return {
            "sweet_spot": best_range,
            "distribution": distribution
        }
    
    def _analyze_timing_signals(
        self, 
        booked: list, 
        failed: list
    ) -> dict:
        """Calculate lift for timing signals"""
        signals = {}
        
        for signal_name, field in [
            ("new_role_lift", "is_new_role"),
            ("hiring_lift", "is_hiring"),
            ("funded_lift", "recently_funded")
        ]:
            lift = self._calculate_lift(booked, failed, field)
            signals[signal_name] = round(lift, 2)
        
        return signals
    
    def _calculate_lift(
        self, 
        booked: list, 
        failed: list, 
        flag_field: str
    ) -> float:
        """Calculate how much a boolean flag increases conversion probability"""
        with_flag_booked = sum(1 for l in booked if getattr(l, flag_field, False))
        with_flag_failed = sum(1 for l in failed if getattr(l, flag_field, False))
        with_flag_total = with_flag_booked + with_flag_failed
        
        without_flag_booked = sum(1 for l in booked if not getattr(l, flag_field, False))
        without_flag_failed = sum(1 for l in failed if not getattr(l, flag_field, False))
        without_flag_total = without_flag_booked + without_flag_failed
        
        if with_flag_total < self.MIN_SAMPLES_CATEGORY or without_flag_total < self.MIN_SAMPLES_CATEGORY:
            return 1.0  # No lift if insufficient data
        
        rate_with = with_flag_booked / with_flag_total
        rate_without = without_flag_booked / without_flag_total
        
        return rate_with / rate_without if rate_without > 0 else 1.0
    
    def _derive_optimal_weights(
        self, 
        booked: list, 
        failed: list
    ) -> dict:
        """
        Use optimization to find weights that best predict conversions.
        
        Approach:
        1. Extract ALS component scores for each lead
        2. Use logistic regression loss function
        3. Constrain weights to sum to 0.85 and be positive
        """
        # Build feature matrix and labels
        X = []
        y = []
        
        for lead in booked:
            if lead.als_components:
                X.append([
                    lead.als_components.get("data_quality", 0) / 20,
                    lead.als_components.get("authority", 0) / 25,
                    lead.als_components.get("company_fit", 0) / 25,
                    lead.als_components.get("timing", 0) / 15
                ])
                y.append(1)
        
        for lead in failed:
            if lead.als_components:
                X.append([
                    lead.als_components.get("data_quality", 0) / 20,
                    lead.als_components.get("authority", 0) / 25,
                    lead.als_components.get("company_fit", 0) / 25,
                    lead.als_components.get("timing", 0) / 15
                ])
                y.append(0)
        
        if len(X) < self.MIN_SAMPLES_TOTAL:
            return self.DEFAULT_WEIGHTS
        
        X = np.array(X)
        y = np.array(y)
        
        def loss(weights):
            """Logistic regression loss with regularization"""
            scores = X @ weights
            # Sigmoid
            probs = 1 / (1 + np.exp(-np.clip(scores, -500, 500)))
            # Binary cross-entropy
            epsilon = 1e-10
            bce = -np.mean(
                y * np.log(probs + epsilon) + 
                (1 - y) * np.log(1 - probs + epsilon)
            )
            # L2 regularization
            reg = 0.01 * np.sum(weights ** 2)
            return bce + reg
        
        # Starting point: default weights
        initial = np.array([0.20, 0.25, 0.25, 0.15])
        
        # Bounds: each weight between 5% and 50%
        bounds = [(0.05, 0.50)] * 4
        
        # Constraint: weights sum to 0.85
        constraint = {"type": "eq", "fun": lambda w: np.sum(w) - 0.85}
        
        try:
            result = minimize(
                loss,
                initial,
                method="SLSQP",
                bounds=bounds,
                constraints=constraint
            )
            
            if result.success:
                return {
                    "data_quality": round(float(result.x[0]), 3),
                    "authority": round(float(result.x[1]), 3),
                    "company_fit": round(float(result.x[2]), 3),
                    "timing": round(float(result.x[3]), 3)
                }
        except Exception:
            pass
        
        return self.DEFAULT_WEIGHTS
    
    def _calculate_confidence(
        self, 
        booked_count: int, 
        total_count: int
    ) -> float:
        """
        Calculate confidence score based on sample size.
        Uses sigmoid function to map sample size to 0-1 confidence.
        """
        # Sigmoid centered at 100 samples
        confidence = 1 / (1 + np.exp(-(total_count - 100) / 30))
        return round(float(confidence), 2)
```

### 4.2 WHAT Detector Algorithm

**File**: `src/algorithms/what_detector.py`

**Purpose**: Analyze which content elements lead to bookings

**Input**: Activities marked as `led_to_booking = TRUE`

```python
"""
WHAT Detector Algorithm Specification

Analyzes content of messages that led to bookings vs those that didn't.

Key Methods:
1. analyze_subjects() - Find winning subject line patterns
2. extract_pain_points() - Identify effective pain points
3. analyze_ctas() - Find effective calls-to-action
4. classify_angles() - Categorize message angles
5. analyze_length() - Find optimal message length
6. analyze_personalization() - Calculate personalization lift

No AI involved - pure pattern matching and statistics.
"""

# Pain point keywords for extraction
PAIN_POINT_KEYWORDS = {
    "leads": ["leads", "pipeline", "prospects", "opportunities", "qualified"],
    "revenue": ["revenue", "sales", "growth", "roi", "profit", "income"],
    "time": ["time", "hours", "manual", "automate", "efficiency", "busy"],
    "scaling": ["scale", "growth", "capacity", "bandwidth", "hire", "team"],
    "competition": ["competitors", "market share", "behind", "catching up"],
    "cost": ["cost", "expensive", "budget", "waste", "spending", "save"],
    "quality": ["quality", "results", "performance", "outcomes", "better"]
}

# Angle classification patterns
ANGLE_PATTERNS = {
    "roi_focused": ["roi", "return", "revenue", "profit", "save", "$", "percent"],
    "social_proof": ["clients", "companies like", "others in", "case study", "results"],
    "curiosity": ["noticed", "wondering", "quick question", "curious", "idea"],
    "fear_based": ["missing", "losing", "behind", "risk", "problem"],
    "value_add": ["free", "complimentary", "audit", "analysis", "assessment"]
}

# CTA patterns to detect
CTA_PATTERNS = [
    "open to a quick chat",
    "worth 15 minutes",
    "free audit",
    "quick call",
    "interested in learning",
    "schedule a call",
    "book a time",
    "happy to share",
    "let me know"
]
```

### 4.3 WHEN Detector Algorithm

**File**: `src/algorithms/when_detector.py`

**Purpose**: Analyze timing patterns of successful conversions

```python
"""
WHEN Detector Algorithm Specification

Analyzes timing patterns:
1. Day of week effectiveness
2. Hour of day effectiveness
3. Touch position (which touch # converts)
4. Gap between touches
5. Time to conversion

All statistical analysis - no AI.
"""
```

### 4.4 HOW Detector Algorithm

**File**: `src/algorithms/how_detector.py`

**Purpose**: Analyze channel sequence patterns

```python
"""
HOW Detector Algorithm Specification

Analyzes channel patterns:
1. Which channel gets the booking reply
2. First touch channel effectiveness
3. Multi-channel lift
4. Full sequence pattern analysis
5. Channel effectiveness by ALS tier

All statistical analysis - no AI.
"""
```

---

## 5. Integration Points

### 5.1 Scorer Engine Integration

**File**: `src/engines/scorer.py`

**Changes**:

```python
class ScorerEngine:
    """
    MODIFIED: Now loads learned weights from client record.
    Falls back to defaults if no learned weights.
    
    Also stores als_components snapshot for future learning.
    """
    
    DEFAULT_WEIGHTS = {
        "data_quality": 0.20,
        "authority": 0.25,
        "company_fit": 0.25,
        "timing": 0.15
    }
    
    async def score_lead(
        self, 
        db: AsyncSession, 
        lead: Lead
    ) -> int:
        # 1. Get client with learned weights
        client = await self._get_client(db, lead.client_id)
        weights = client.als_learned_weights or self.DEFAULT_WEIGHTS
        
        # 2. Calculate component scores (existing logic)
        data_quality = self._score_data_quality(lead)
        authority = self._score_authority(lead)
        company_fit = self._score_company_fit(lead, client)
        timing = self._score_timing(lead)
        risk = self._score_risk(lead)
        
        # 3. Store component snapshot for learning
        lead.als_components = {
            "data_quality": data_quality,
            "authority": authority,
            "company_fit": company_fit,
            "timing": timing,
            "risk": risk
        }
        lead.als_weights_used = weights
        lead.scored_at = datetime.utcnow()
        
        # 4. Apply weights
        raw_score = (
            (data_quality / 20) * weights["data_quality"] * 100 +
            (authority / 25) * weights["authority"] * 100 +
            (company_fit / 25) * weights["company_fit"] * 100 +
            (timing / 15) * weights["timing"] * 100 -
            risk
        )
        
        return int(np.clip(raw_score, 0, 100))
```

### 5.2 Campaign Generation Agent Integration

**File**: `src/agents/campaign_generation_agent.py`

**Changes**:

```python
class CampaignGenerationAgent:
    """
    MODIFIED: Now reads conversion patterns and includes them in context.
    """
    
    async def generate_campaign(
        self, 
        db: AsyncSession, 
        client: Client
    ) -> CampaignTemplate:
        # 1. Load conversion patterns
        patterns = await self._load_patterns(db, client.id)
        
        # 2. Build context with pattern insights
        context = self._build_pattern_context(patterns)
        
        # 3. Pass to skills with pattern context
        # Skills use patterns to inform generation
        ...
    
    def _build_pattern_context(self, patterns: dict) -> str:
        """
        Convert patterns into natural language context for skills.
        """
        context_parts = []
        
        if patterns.get("what"):
            what = patterns["what"]
            if what.get("pain_points", {}).get("effective"):
                top_pain = what["pain_points"]["effective"][0]
                context_parts.append(
                    f"Most effective pain point: '{top_pain['pain_point']}' "
                    f"(used in {top_pain['frequency']*100:.0f}% of converting messages)"
                )
            
            if what.get("ctas", {}).get("effective"):
                top_cta = what["ctas"]["effective"][0]
                context_parts.append(
                    f"Best performing CTA: '{top_cta['cta']}' "
                    f"({top_cta['conversion_rate']*100:.1f}% conversion rate)"
                )
            
            if what.get("optimal_length"):
                context_parts.append(
                    f"Optimal email length: {what['optimal_length']['email']['optimal_words']} words"
                )
        
        if patterns.get("when"):
            when = patterns["when"]
            if when.get("converting_touch_distribution"):
                # Find peak touch
                dist = when["converting_touch_distribution"]
                peak = max(dist.items(), key=lambda x: x[1])
                context_parts.append(
                    f"Most conversions happen on {peak[0].replace('_', ' ')} "
                    f"({peak[1]*100:.0f}% of bookings)"
                )
            
            if when.get("optimal_sequence_gaps"):
                context_parts.append(
                    f"Optimal sequence gaps: {when['optimal_sequence_gaps']}"
                )
        
        if patterns.get("how"):
            how = patterns["how"]
            if how.get("winning_sequences"):
                top_seq = how["winning_sequences"][0]
                context_parts.append(
                    f"Best performing sequence: {' → '.join(top_seq['sequence'])} "
                    f"({top_seq['conversion_rate']*100:.1f}% conversion)"
                )
        
        return "\n".join(context_parts)
```

### 5.3 Sequence Builder Skill Integration

**File**: `src/agents/skills/sequence_builder.py`

**Changes**:

```python
class SequenceBuilderSkill(BaseSkill):
    """
    MODIFIED: Uses WHEN and HOW patterns to inform sequence design.
    """
    
    class Input(BaseModel):
        client_icp: dict
        when_patterns: Optional[dict] = None
        how_patterns: Optional[dict] = None
    
    async def execute(self, input: Input, anthropic: AnthropicClient) -> SkillResult:
        # Build prompt with pattern context
        prompt = self._build_prompt(input)
        
        # If we have winning sequences, bias toward them
        if input.how_patterns and input.how_patterns.get("winning_sequences"):
            prompt += f"\n\nHistorical winning sequences:\n"
            for seq in input.how_patterns["winning_sequences"][:3]:
                prompt += f"- {' → '.join(seq['sequence'])} ({seq['conversion_rate']*100:.1f}% conv)\n"
        
        # If we have optimal gaps, use them
        if input.when_patterns and input.when_patterns.get("optimal_sequence_gaps"):
            gaps = input.when_patterns["optimal_sequence_gaps"]
            prompt += f"\n\nOptimal gaps between touches: {gaps}\n"
        
        # Generate sequence
        ...
```

### 5.4 Messaging Generator Skill Integration

**File**: `src/agents/skills/messaging_generator.py`

**Changes**:

```python
class MessagingGeneratorSkill(BaseSkill):
    """
    MODIFIED: Uses WHAT patterns to inform copy generation.
    """
    
    class Input(BaseModel):
        sequence: list
        client_icp: dict
        lead_context: Optional[dict] = None
        what_patterns: Optional[dict] = None
    
    async def execute(self, input: Input, anthropic: AnthropicClient) -> SkillResult:
        prompt = self._build_prompt(input)
        
        if input.what_patterns:
            what = input.what_patterns
            
            # Add effective pain points
            if what.get("pain_points", {}).get("effective"):
                prompt += "\n\nEFFECTIVE PAIN POINTS (use these):\n"
                for pp in what["pain_points"]["effective"][:3]:
                    prompt += f"- {pp['pain_point']} (lift: {pp['lift']}x)\n"
            
            # Add ineffective pain points to avoid
            if what.get("pain_points", {}).get("ineffective"):
                prompt += "\n\nINEFFECTIVE PAIN POINTS (avoid these):\n"
                for pp in what["pain_points"]["ineffective"]:
                    prompt += f"- {pp['pain_point']}\n"
            
            # Add CTA guidance
            if what.get("ctas", {}).get("effective"):
                prompt += "\n\nEFFECTIVE CTAs:\n"
                for cta in what["ctas"]["effective"][:3]:
                    prompt += f"- \"{cta['cta']}\"\n"
            
            # Add length constraints
            if what.get("optimal_length"):
                lengths = what["optimal_length"]
                prompt += f"\n\nOPTIMAL LENGTH:\n"
                prompt += f"- Email: {lengths['email']['optimal_words']} words\n"
                prompt += f"- LinkedIn: {lengths['linkedin']['optimal_words']} words\n"
                prompt += f"- SMS: {lengths['sms']['optimal_chars']} characters\n"
        
        # Generate messaging
        ...
```

---

## 6. Implementation Phases

### Phase 16A: Data Capture (3 tasks)

| Task | Description | File(s) |
|------|-------------|---------|
| 16A.1 | Create migration 014 | `supabase/migrations/014_conversion_intelligence.sql` |
| 16A.2 | Update Scorer to store als_components | `src/engines/scorer.py` |
| 16A.3 | Update activity creation to store content_snapshot | `src/engines/email.py`, `sms.py`, `linkedin.py` |

### Phase 16B: WHO Detector (5 tasks)

| Task | Description | File(s) |
|------|-------------|---------|
| 16B.1 | Create WhoDetector class | `src/algorithms/who_detector.py` |
| 16B.2 | Implement conversion_rate_by analysis | `src/algorithms/who_detector.py` |
| 16B.3 | Implement weight optimization | `src/algorithms/who_detector.py` |
| 16B.4 | Integrate with Scorer engine | `src/engines/scorer.py` |
| 16B.5 | Write unit tests | `tests/algorithms/test_who_detector.py` |

### Phase 16C: WHAT Detector (5 tasks)

| Task | Description | File(s) |
|------|-------------|---------|
| 16C.1 | Create WhatDetector class | `src/algorithms/what_detector.py` |
| 16C.2 | Implement pain point extraction | `src/algorithms/what_detector.py` |
| 16C.3 | Implement subject/CTA/angle analysis | `src/algorithms/what_detector.py` |
| 16C.4 | Integrate with MessagingGeneratorSkill | `src/agents/skills/messaging_generator.py` |
| 16C.5 | Write unit tests | `tests/algorithms/test_what_detector.py` |

### Phase 16D: WHEN Detector (4 tasks)

| Task | Description | File(s) |
|------|-------------|---------|
| 16D.1 | Create WhenDetector class | `src/algorithms/when_detector.py` |
| 16D.2 | Implement timing analysis | `src/algorithms/when_detector.py` |
| 16D.3 | Integrate with SequenceBuilderSkill | `src/agents/skills/sequence_builder.py` |
| 16D.4 | Write unit tests | `tests/algorithms/test_when_detector.py` |

### Phase 16E: HOW Detector (4 tasks)

| Task | Description | File(s) |
|------|-------------|---------|
| 16E.1 | Create HowDetector class | `src/algorithms/how_detector.py` |
| 16E.2 | Implement channel sequence analysis | `src/algorithms/how_detector.py` |
| 16E.3 | Integrate with Allocator engine | `src/engines/allocator.py` |
| 16E.4 | Write unit tests | `tests/algorithms/test_how_detector.py` |

### Phase 16F: Orchestration (2 tasks)

| Task | Description | File(s) |
|------|-------------|---------|
| 16F.1 | Create pattern_learning_flow | `src/orchestration/flows/pattern_learning_flow.py` |
| 16F.2 | Add weekly schedule | `src/orchestration/schedules/pattern_learning.py` |

### Phase 16G: Admin Dashboard (3 tasks)

| Task | Description | File(s) |
|------|-------------|---------|
| 16G.1 | Create patterns API endpoints | `src/api/routes/patterns.py` |
| 16G.2 | Create patterns admin page | `frontend/app/admin/patterns/page.tsx` |
| 16G.3 | Create pattern visualization components | `frontend/components/admin/PatternCharts.tsx` |

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/algorithms/test_who_detector.py

import pytest
from src.algorithms.who_detector import WhoDetector

class TestWhoDetector:
    
    def test_insufficient_data_returns_defaults(self):
        """When < 30 samples, return default weights"""
        detector = WhoDetector()
        # Mock with 10 leads
        patterns = detector.analyze_sync(mock_db, mock_client_id)
        assert patterns.recommended_weights == detector.DEFAULT_WEIGHTS
        assert patterns.confidence == 0.0
    
    def test_conversion_rate_by_field(self):
        """Correctly calculates conversion rate per field value"""
        detector = WhoDetector()
        booked = [MockLead(title="CEO"), MockLead(title="CEO"), MockLead(title="Director")]
        failed = [MockLead(title="CEO"), MockLead(title="Director"), MockLead(title="Director")]
        
        results = detector._analyze_field(booked, failed, "title")
        
        # CEO: 2/3 = 0.67, Director: 1/3 = 0.33
        assert results[0]["title"] == "CEO"
        assert results[0]["conversion_rate"] == pytest.approx(0.67, rel=0.01)
    
    def test_weight_optimization_converges(self):
        """Optimizer finds weights that improve over defaults"""
        detector = WhoDetector()
        # Generate synthetic data where high timing score predicts conversion
        booked = [MockLead(als_components={"timing": 15, "authority": 10}) for _ in range(50)]
        failed = [MockLead(als_components={"timing": 5, "authority": 20}) for _ in range(50)]
        
        weights = detector._derive_optimal_weights(booked, failed)
        
        # Timing weight should be higher than default
        assert weights["timing"] > 0.15
```

### 7.2 Integration Tests

```python
# tests/integration/test_pattern_learning.py

@pytest.mark.asyncio
async def test_full_pattern_learning_pipeline():
    """Test end-to-end pattern detection and application"""
    async with get_test_db() as db:
        # 1. Create client with historical data
        client = await create_test_client(db)
        await create_test_leads_with_outcomes(db, client.id, converted=50, failed=150)
        
        # 2. Run all detectors
        who_patterns = await WhoDetector().analyze(db, client.id)
        what_patterns = await WhatDetector().analyze(db, client.id)
        
        # 3. Verify patterns stored
        assert who_patterns.sample_size == 200
        assert who_patterns.confidence > 0.5
        
        # 4. Verify Scorer uses new weights
        lead = await create_test_lead(db, client.id)
        score = await ScorerEngine().score_lead(db, lead)
        
        assert lead.als_weights_used == who_patterns.recommended_weights
```

---

## 8. Success Metrics

### 8.1 Algorithm Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Weight convergence | Weights stabilize after 100 outcomes | Variance of weights across weekly runs |
| Prediction accuracy | >60% of high-scored leads convert | Conversion rate of top 20% ALS leads |
| Pattern confidence | >0.7 after 200 outcomes | Confidence score from detectors |

### 8.2 Business Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Booking rate | ~3% | 5%+ | Bookings / leads contacted |
| Time to conversion | ~14 days | <10 days | Avg days from first touch to booking |
| Touch efficiency | 6 touches avg | <5 touches | Avg touches before conversion |

### 8.3 Monitoring

```python
# Pattern health checks (in weekly flow)

def check_pattern_health(patterns: ConversionPatterns) -> list[str]:
    """Return list of warnings if patterns look unhealthy"""
    warnings = []
    
    if patterns.sample_size < 50:
        warnings.append(f"Low sample size: {patterns.sample_size}")
    
    if patterns.confidence < 0.5:
        warnings.append(f"Low confidence: {patterns.confidence}")
    
    # Check for dramatic weight shifts
    if patterns.who and patterns.who.recommended_weights:
        for key, value in patterns.who.recommended_weights.items():
            if value > 0.45 or value < 0.08:
                warnings.append(f"Extreme weight for {key}: {value}")
    
    return warnings
```

---

## Appendix A: File Structure

```
src/
├── algorithms/
│   ├── __init__.py
│   ├── base_detector.py
│   ├── who_detector.py
│   ├── what_detector.py
│   ├── when_detector.py
│   └── how_detector.py
├── engines/
│   └── scorer.py (modified)
├── agents/
│   ├── campaign_generation_agent.py (modified)
│   └── skills/
│       ├── sequence_builder.py (modified)
│       └── messaging_generator.py (modified)
├── orchestration/
│   └── flows/
│       └── pattern_learning_flow.py (new)
└── api/
    └── routes/
        └── patterns.py (new)

frontend/
└── app/
    └── admin/
        └── patterns/
            └── page.tsx (new)

supabase/
└── migrations/
    └── 014_conversion_intelligence.sql (new)

tests/
└── algorithms/
    ├── test_who_detector.py
    ├── test_what_detector.py
    ├── test_when_detector.py
    └── test_how_detector.py
```

---

## Appendix B: Dependencies

```
# requirements.txt additions
numpy>=1.24.0
scipy>=1.10.0  # For optimization
```

---

**End of Specification**

---

*This document provides complete specifications for Claude Code to implement the Conversion Intelligence System. All algorithms are deterministic Python code - no AI learning required.*
