# Phase 16: Conversion Intelligence System
## Master Index Document

**Version**: 1.0  
**Date**: December 27, 2025  
**Status**: Ready for Development  
**Total Specs**: 6 documents (~3,500 lines)  
**Total Tasks**: 30 tasks  
**Total Estimated Hours**: ~50.5 hours  

---

## Executive Summary

The Conversion Intelligence System transforms Agency OS from a "dumb pipe" that sends messages into a **learning platform** that continuously improves based on outcomes.

### The Billion-Dollar Question
> "How do we 1) Find correct candidates to convert and 2) Convert those candidates into bookings?"

### The Answer: Four Pattern Detectors

| Detector | Question Answered | Output |
|----------|-------------------|--------|
| **WHO** | Which leads convert? | Optimized ALS weights |
| **WHAT** | Which content converts? | Effective messaging patterns |
| **WHEN** | When do leads convert? | Optimal timing patterns |
| **HOW** | Which channels convert? | Winning sequence patterns |

### Core Architecture Principle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONVERSION INTELLIGENCE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ENGINES execute deterministically (no AI)                                 │
│   AGENTS decide using AI (Claude)                                           │
│   LEARNING happens offline via statistical algorithms                       │
│                                                                             │
│   Claude CANNOT learn between conversations.                                │
│   All "learning" = database + scheduled Python algorithms.                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Specification Documents

### Document Inventory

| Spec | Filename | Lines | Focus |
|------|----------|-------|-------|
| 16A | `PHASE_16_CONVERSION_INTELLIGENCE_SPEC.md` | ~800 | Data model + WHO Detector |
| 16B | `PHASE_16B_WHAT_DETECTOR_SPEC.md` | ~500 | Content pattern analysis |
| 16C | `PHASE_16C_WHEN_DETECTOR_SPEC.md` | ~450 | Timing pattern analysis |
| 16D | `PHASE_16D_HOW_DETECTOR_SPEC.md` | ~550 | Channel sequence analysis |
| 16E | `PHASE_16E_ENGINE_MODIFICATIONS_SPEC.md` | ~650 | Engine content capture + pattern consumption |
| 16F | `PHASE_16F_PREFECT_FLOWS_SPEC.md` | ~550 | Orchestration + scheduling |

### Document Dependencies

```
16A (Foundation)
 │
 ├──► 16B (WHAT Detector)
 │     │
 ├──► 16C (WHEN Detector)
 │     │
 ├──► 16D (HOW Detector)
 │     │
 │     ▼
 └──► 16E (Engine Modifications) ◄── Requires all detectors
       │
       ▼
      16F (Prefect Flows) ◄── Orchestrates everything
```

---

## Build Order

### Recommended Sequence

Build in this order to ensure dependencies are satisfied:

```
WEEK 1: Foundation
├── 16A.1: Migration 014_conversion_intelligence.sql
├── 16A.2: ConversionPattern model
├── 16E.1: Create content_utils.py (shared utilities)
└── 16E.2-3: Modify engines for content capture

WEEK 2: WHO + WHAT Detectors
├── 16A.3-6: WHO Detector complete
├── 16B.1-5: WHAT Detector complete
└── Tests for both

WEEK 3: WHEN + HOW Detectors
├── 16C.1-4: WHEN Detector complete
├── 16D.1-4: HOW Detector complete
└── Tests for both

WEEK 4: Integration + Orchestration
├── 16E.4: Scorer engine pattern consumption
├── 16E.5: Allocator engine pattern consumption
├── 16F.1-4: All Prefect flows
└── End-to-end testing
```

---

## Complete Task List

### Phase 16A: Data Capture + WHO Detector (8 tasks, ~12 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16A.1 | Create migration 014 | `migrations/014_conversion_intelligence.sql` | 1 |
| 16A.2 | Create ConversionPattern model | `src/models/conversion_patterns.py` | 0.5 |
| 16A.3 | Create WhoDetector class | `src/algorithms/who_detector.py` | 2.5 |
| 16A.4 | Implement conversion_rate_by analysis | `src/algorithms/who_detector.py` | 2 |
| 16A.5 | Implement weight optimization (scipy) | `src/algorithms/who_detector.py` | 3 |
| 16A.6 | Integrate with Scorer engine | `src/engines/scorer.py` | 1.5 |
| 16A.7 | Write unit tests | `tests/algorithms/test_who_detector.py` | 1.5 |
| 16A.8 | Integration tests | `tests/integration/test_who_integration.py` | 1 |

### Phase 16B: WHAT Detector (5 tasks, ~9 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16B.1 | Create WhatDetector class | `src/algorithms/what_detector.py` | 2.5 |
| 16B.2 | Implement pain point extraction | `src/algorithms/what_detector.py` | 1.5 |
| 16B.3 | Implement subject/CTA/angle analysis | `src/algorithms/what_detector.py` | 2 |
| 16B.4 | Integrate with MessagingGeneratorSkill | `src/agents/skills/messaging_generator.py` | 1.5 |
| 16B.5 | Write unit tests | `tests/algorithms/test_what_detector.py` | 1.5 |

### Phase 16C: WHEN Detector (4 tasks, ~7 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16C.1 | Create WhenDetector class | `src/algorithms/when_detector.py` | 2.5 |
| 16C.2 | Integrate with SequenceBuilderSkill | `src/agents/skills/sequence_builder.py` | 1.5 |
| 16C.3 | Integrate with AllocatorEngine | `src/engines/allocator.py` | 1.5 |
| 16C.4 | Write unit tests | `tests/algorithms/test_when_detector.py` | 1.5 |

### Phase 16D: HOW Detector (4 tasks, ~8 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16D.1 | Create HowDetector class | `src/algorithms/how_detector.py` | 3 |
| 16D.2 | Integrate with SequenceBuilderSkill | `src/agents/skills/sequence_builder.py` | 1.5 |
| 16D.3 | Integrate with AllocatorEngine | `src/engines/allocator.py` | 2 |
| 16D.4 | Write unit tests | `tests/algorithms/test_how_detector.py` | 1.5 |

### Phase 16E: Engine Modifications (5 tasks, ~8 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16E.1 | Create shared content_utils module | `src/engines/content_utils.py` | 1 |
| 16E.2 | Modify Email engine | `src/engines/email.py` | 1.5 |
| 16E.3 | Modify SMS + LinkedIn + Voice engines | `src/engines/sms.py`, `linkedin.py`, `voice.py` | 2 |
| 16E.4 | Modify Scorer engine | `src/engines/scorer.py` | 1.5 |
| 16E.5 | Modify Allocator engine | `src/engines/allocator.py` | 2 |

### Phase 16F: Prefect Flows (4 tasks, ~6.5 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16F.1 | Create pattern_learning_flow | `src/orchestration/flows/pattern_learning_flow.py` | 2 |
| 16F.2 | Create pattern_health_flow | `src/orchestration/flows/pattern_health_flow.py` | 1.5 |
| 16F.3 | Create pattern_backfill_flow | `src/orchestration/flows/pattern_backfill_flow.py` | 1.5 |
| 16F.4 | Create schedules + API endpoints | `schedules/`, `api/routes/patterns.py` | 1.5 |

---

## Data Model Summary

### Database Migration (014_conversion_intelligence.sql)

```sql
-- Lead tracking
ALTER TABLE leads ADD COLUMN als_components JSONB;
ALTER TABLE leads ADD COLUMN als_weights_used JSONB;
ALTER TABLE leads ADD COLUMN scored_at TIMESTAMPTZ;

-- Activity tracking  
ALTER TABLE activities ADD COLUMN led_to_booking BOOLEAN DEFAULT FALSE;
ALTER TABLE activities ADD COLUMN content_snapshot JSONB;

-- Client learned weights
ALTER TABLE clients ADD COLUMN als_learned_weights JSONB;
ALTER TABLE clients ADD COLUMN als_weights_updated_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN conversion_sample_count INTEGER DEFAULT 0;

-- Pattern storage
CREATE TABLE conversion_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    pattern_type TEXT CHECK (pattern_type IN ('who', 'what', 'when', 'how')),
    patterns JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    computed_at TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    UNIQUE (client_id, pattern_type)
);

-- Pattern history (for tracking drift)
CREATE TABLE conversion_pattern_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    pattern_type TEXT,
    patterns JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL
);

-- Trigger: Mark converting touch
CREATE FUNCTION mark_converting_touch();
CREATE TRIGGER on_lead_converted;
```

---

## Integration Points Summary

| Component | Reads Patterns | Writes Data |
|-----------|---------------|-------------|
| **Scorer Engine** | WHO (weights) | als_components, als_weights_used |
| **Allocator Engine** | WHEN (timing), HOW (channels) | scheduled_at |
| **Email Engine** | - | content_snapshot |
| **SMS Engine** | - | content_snapshot |
| **LinkedIn Engine** | - | content_snapshot |
| **Voice Engine** | - | content_snapshot |
| **SequenceBuilderSkill** | WHEN, HOW | sequence design |
| **MessagingGeneratorSkill** | WHAT | message content |
| **CampaignGenerationAgent** | All patterns | campaign structure |

---

## Success Metrics

### Algorithm Metrics
- [ ] Weight convergence after 100 outcomes
- [ ] >60% of high-scored leads convert
- [ ] Pattern confidence >0.7 after 200 outcomes

### Business Metrics
| Metric | Baseline | Target |
|--------|----------|--------|
| Booking rate | 3% | 5%+ |
| Time to conversion | ~14 days | <10 days |
| Touches to convert | 6 avg | <5 avg |
| Multi-channel lift | Unknown | Measured |

---

## Claude Code Instructions

When building from these specs:

1. **Read the full spec** before starting any task
2. **Build in order**: 16A → 16B → 16C → 16D → 16E → 16F
3. **Run tests** after each spec is complete
4. **Copy code exactly** - specs contain production-ready code
5. **Don't skip tasks** - each builds on previous

### Example Prompt for Claude Code

```
Build Phase 16A from the specification in:
C:\AI\Agency_OS\docs\phase16\PHASE_16_CONVERSION_INTELLIGENCE_SPEC.md

Start with Task 16A.1 (migration) and work through all 8 tasks in order.
Run tests after completing all tasks.
```

---

## Quick Reference

### Schedules
| Flow | Schedule | Purpose |
|------|----------|---------|
| Pattern Learning | Sunday 2am UTC | Weekly batch learning |
| Pattern Health | Daily 6am UTC | Validation + alerts |
| Pattern Backfill | Manual | Historical analysis |

### API Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/patterns/{client_id}` | View all patterns |
| GET | `/patterns/{client_id}/{type}` | View specific pattern |
| POST | `/patterns/learn` | Trigger learning (admin) |
| POST | `/patterns/backfill/{client_id}` | Trigger backfill (admin) |

### Pattern Types
| Type | Detector | Consumers |
|------|----------|-----------|
| `who` | WhoDetector | Scorer Engine |
| `what` | WhatDetector | MessagingGeneratorSkill |
| `when` | WhenDetector | SequenceBuilderSkill, Allocator |
| `how` | HowDetector | SequenceBuilderSkill, Allocator |

---

**End of Master Index Document**
