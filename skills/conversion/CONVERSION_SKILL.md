# SKILL.md — Phase 16: Conversion Intelligence System

**Skill:** Conversion Intelligence  
**Author:** Dave + Claude  
**Version:** 1.0  
**Created:** December 27, 2025  
**Phase:** 16  
**Specification:** `docs/phase16/PHASE_16_MASTER_INDEX.md`

---

## Purpose

Build the Conversion Intelligence System - a statistical learning layer that analyzes conversion outcomes to optimize lead scoring (WHO), messaging (WHAT), timing (WHEN), and channel sequences (HOW).

**Core Principle:** Claude cannot learn between conversations. All "learning" = database + scheduled Python algorithms (scipy/numpy).

---

## Prerequisites

- Phase 11 complete (ICP Discovery)
- Supabase migrations 001-013 applied
- Existing engines: Scorer, Allocator, Email, SMS, LinkedIn, Voice
- Existing skills infrastructure

---

## Required Files

### Database (16A.1)

| File | Purpose |
|------|---------|
| `supabase/migrations/014_conversion_intelligence.sql` | Schema for patterns + tracking |

### Models (16A.2)

| File | Purpose |
|------|---------|
| `src/models/conversion_patterns.py` | ConversionPattern + History models |

### Algorithms (16A-16D)

| File | Purpose | Spec |
|------|---------|------|
| `src/algorithms/__init__.py` | Package init |  |
| `src/algorithms/who_detector.py` | Lead attribute analysis | 16A |
| `src/algorithms/what_detector.py` | Content pattern analysis | 16B |
| `src/algorithms/when_detector.py` | Timing pattern analysis | 16C |
| `src/algorithms/how_detector.py` | Channel sequence analysis | 16D |

### Engine Utilities (16E)

| File | Purpose |
|------|---------|
| `src/engines/content_utils.py` | Shared pain point/CTA extraction |

### Engine Modifications (16E)

| File | Change |
|------|--------|
| `src/engines/scorer.py` | Load WHO patterns, store als_components |
| `src/engines/allocator.py` | Load WHEN/HOW patterns for scheduling |
| `src/engines/email.py` | Store content_snapshot on send |
| `src/engines/sms.py` | Store content_snapshot on send |
| `src/engines/linkedin.py` | Store content_snapshot on send |
| `src/engines/voice.py` | Store content_snapshot on complete |

### Orchestration (16F)

| File | Purpose |
|------|---------|
| `src/orchestration/flows/pattern_learning_flow.py` | Weekly batch learning |
| `src/orchestration/flows/pattern_health_flow.py` | Daily validation |
| `src/orchestration/flows/pattern_backfill_flow.py` | Historical analysis |
| `src/orchestration/schedules/pattern_schedules.py` | Cron schedules |

### API (16F)

| File | Purpose |
|------|---------|
| `src/api/routes/patterns.py` | Pattern CRUD + manual triggers |

### Tests

| File | Purpose |
|------|---------|
| `tests/algorithms/test_who_detector.py` | WHO unit tests |
| `tests/algorithms/test_what_detector.py` | WHAT unit tests |
| `tests/algorithms/test_when_detector.py` | WHEN unit tests |
| `tests/algorithms/test_how_detector.py` | HOW unit tests |
| `tests/integration/test_who_integration.py` | End-to-end WHO tests |

---

## Required Patterns

### Import Hierarchy (CRITICAL)

```
src/models/           → Can only import from src/exceptions.py
src/algorithms/       → Can import from src/models/
src/engines/          → Can import from src/models/, src/algorithms/
src/orchestration/    → Can import from everything
```

### Detector Pattern

All detectors follow this structure:

```python
"""
[DETECTOR_TYPE] Detector Algorithm

Analyzes [what it analyzes] to find [patterns].
Pure statistical analysis - no AI involved.
"""

from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class [Type]Patterns:
    # Pattern fields
    sample_size: int
    confidence: float
    
    @classmethod
    def insufficient_data(cls) -> "[Type]Patterns":
        """Return defaults when insufficient data"""
        ...

class [Type]Detector:
    MIN_SAMPLES_TOTAL = 30
    MIN_SAMPLES_CATEGORY = 5
    
    async def analyze(self, db: AsyncSession, client_id: str) -> [Type]Patterns:
        """Main entry point"""
        ...
    
    def _calculate_confidence(self, sample_size: int) -> float:
        """Sigmoid-based confidence from sample size"""
        ...
```

### Content Snapshot Schema

When engines send messages, store:

```python
content_snapshot = {
    "subject": str,           # Email only
    "body": str,
    "word_count": int,
    "char_count": int,
    "pain_points_used": list[str],
    "cta_used": str | None,
    "has_company_mention": bool,
    "has_first_name": bool,
    "has_recent_news": bool,
    "has_mutual_connection": bool,
    "has_industry_specific": bool,
    "touch_number": int,
    "sequence_id": str,
    "sent_at": datetime,
    "day_of_week": int,       # 0=Monday
    "hour_of_day": int,       # 0-23
}
```

### Pattern Storage Schema

```python
# conversion_patterns table
{
    "client_id": UUID,
    "pattern_type": "who" | "what" | "when" | "how",
    "patterns": JSONB,        # Type-specific schema
    "sample_size": int,
    "confidence": float,      # 0.0 - 1.0
    "computed_at": datetime,
    "valid_until": datetime,  # +14 days from computed_at
}
```

---

## Implementation Order

**CRITICAL:** Build in this exact order due to dependencies.

### Week 1: Foundation + Content Capture

```
16A.1 → Migration 014
16A.2 → ConversionPattern model
16E.1 → content_utils.py (shared utilities)
16E.2 → Email engine (content_snapshot)
16E.3 → SMS, LinkedIn, Voice engines (content_snapshot)
```

### Week 2: WHO + WHAT Detectors

```
16A.3 → WhoDetector class
16A.4 → conversion_rate_by analysis
16A.5 → Weight optimization (scipy)
16A.6 → Integrate Scorer engine
16A.7 → WHO unit tests
16A.8 → WHO integration tests
16B.1-5 → WHAT Detector complete
```

### Week 3: WHEN + HOW Detectors

```
16C.1-4 → WHEN Detector complete
16D.1-4 → HOW Detector complete
```

### Week 4: Integration + Orchestration

```
16E.4 → Scorer pattern consumption
16E.5 → Allocator pattern consumption
16F.1-4 → All Prefect flows + schedules
```

---

## Success Criteria

### Migration Applied
- [ ] `als_components` column exists on leads
- [ ] `als_weights_used` column exists on leads
- [ ] `led_to_booking` column exists on activities
- [ ] `content_snapshot` column exists on activities
- [ ] `als_learned_weights` column exists on clients
- [ ] `conversion_patterns` table exists
- [ ] `conversion_pattern_history` table exists
- [ ] Trigger `mark_converting_touch` exists

### Detectors Working
- [ ] WhoDetector returns patterns for client with 30+ outcomes
- [ ] WhoDetector returns `insufficient_data()` for <30 outcomes
- [ ] Weight optimization converges (scipy.minimize succeeds)
- [ ] All 4 detectors pass unit tests

### Engines Capturing
- [ ] Email engine stores content_snapshot
- [ ] SMS engine stores content_snapshot
- [ ] LinkedIn engine stores content_snapshot
- [ ] Voice engine stores content_snapshot
- [ ] Scorer stores als_components + als_weights_used

### Engines Consuming
- [ ] Scorer loads WHO patterns from conversion_patterns
- [ ] Scorer falls back to defaults if no patterns
- [ ] Allocator loads WHEN/HOW patterns
- [ ] Allocator uses optimal gaps and days

### Flows Running
- [ ] pattern_learning_flow runs for all active clients
- [ ] pattern_health_flow detects expired patterns
- [ ] Patterns stored with confidence scores
- [ ] Weekly schedule registered

---

## QA Checks (for QA Agent)

### CRITICAL Violations

| Check | File | Issue |
|-------|------|-------|
| Import hierarchy | `src/algorithms/*.py` | Cannot import from engines |
| scipy dependency | `src/algorithms/who_detector.py` | Must use scipy.optimize.minimize |
| No AI in detectors | `src/algorithms/*.py` | No Anthropic calls allowed |
| DB session pattern | All detectors | Must accept `db: AsyncSession` |

### HIGH Violations

| Check | File | Issue |
|-------|------|-------|
| Missing contract | All new files | Must have docstring header |
| Missing tests | `tests/algorithms/` | Each detector needs tests |
| Hardcoded weights | `src/engines/scorer.py` | Must load from patterns first |

### MEDIUM Issues

| Check | File | Issue |
|-------|------|-------|
| Confidence bounds | Detectors | Must be 0.0-1.0 |
| Sample size check | Detectors | Must return defaults if <30 |

---

## Fix Patterns (for Fixer Agent)

### Import Violation Fix

```python
# WRONG - algorithms importing from engines
from src.engines.scorer import ScorerEngine

# RIGHT - engines import from algorithms
# In src/engines/scorer.py:
from src.algorithms.who_detector import WhoPatterns
```

### Missing content_snapshot Fix

```python
# In email engine send():
activity.content_snapshot = build_content_snapshot(
    body=body,
    lead=lead,
    subject=subject,
    touch_number=touch_number,
    channel="email",
)
```

### Missing als_components Fix

```python
# In scorer engine score_lead():
lead.als_components = {
    "data_quality": data_quality,
    "authority": authority,
    "company_fit": company_fit,
    "timing": timing,
    "risk": risk,
}
lead.als_weights_used = weights
lead.scored_at = datetime.utcnow()
```

---

## Dependencies

Add to `requirements.txt`:

```
numpy>=1.24.0
scipy>=1.10.0
```

---

## Specification Documents

Full specs with complete code in `docs/phase16/`:

| Document | Content |
|----------|---------|
| `PHASE_16_MASTER_INDEX.md` | Overview, build order, all tasks |
| `PHASE_16_CONVERSION_INTELLIGENCE_SPEC.md` | Data model + WHO Detector |
| `PHASE_16B_WHAT_DETECTOR_SPEC.md` | Content pattern analysis |
| `PHASE_16C_WHEN_DETECTOR_SPEC.md` | Timing pattern analysis |
| `PHASE_16D_HOW_DETECTOR_SPEC.md` | Channel sequence analysis |
| `PHASE_16E_ENGINE_MODIFICATIONS_SPEC.md` | Engine updates |
| `PHASE_16F_PREFECT_FLOWS_SPEC.md` | Orchestration flows |

**IMPORTANT:** Specs contain production-ready code. Copy implementations directly.

---

## Quick Reference

### Pattern Types

| Type | Detector | Consumer |
|------|----------|----------|
| `who` | WhoDetector | Scorer Engine |
| `what` | WhatDetector | MessagingGeneratorSkill |
| `when` | WhenDetector | Allocator, SequenceBuilderSkill |
| `how` | HowDetector | Allocator, SequenceBuilderSkill |

### Schedules

| Flow | Schedule | Purpose |
|------|----------|---------|
| Pattern Learning | Sunday 2am UTC | Weekly batch |
| Pattern Health | Daily 6am UTC | Validation |
| Pattern Backfill | Manual | Historical |

---

**END OF SKILL**
