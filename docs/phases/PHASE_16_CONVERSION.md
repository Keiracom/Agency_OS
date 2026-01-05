# Phase 16: Conversion Intelligence System

**Status:** ✅ Complete  
**Tasks:** 30 (~50.5 hours)  
**Dependencies:** Phase 11 complete (ICP Discovery working)

---

## Overview

Transform Agency OS from "dumb pipe" to learning platform that improves based on outcomes.

**Core Question:** "How do we 1) Find correct candidates to convert and 2) Convert those candidates into bookings?"

---

## The Four Pattern Detectors

| Detector | Question | Output | Consumer |
|----------|----------|--------|----------|
| **WHO** | Which leads convert? | Optimized ALS weights | Scorer Engine |
| **WHAT** | Which content converts? | Effective messaging patterns | Content Agent |
| **WHEN** | When do leads convert? | Optimal timing patterns | Allocator Engine |
| **HOW** | Which channels convert? | Winning sequence patterns | Allocator Engine |

---

## Architecture Principle

- **ENGINES** execute deterministically (no AI)
- **AGENTS** decide using AI (Claude)
- **LEARNING** happens offline via statistical algorithms (Python + scipy)
- Claude CANNOT learn between conversations - all "learning" = database + scheduled jobs

---

## Task Summary

### 16A: Data Capture + WHO Detector (8 tasks, ~12 hours)
- Migration 014
- ConversionPattern model
- WhoDetector class
- Weight optimization (scipy)
- Scorer integration

### 16B: WHAT Detector (5 tasks, ~9 hours)
- WhatDetector class
- Pain point extraction
- Subject/CTA/angle analysis

### 16C: WHEN Detector (4 tasks, ~7 hours)
- WhenDetector class
- Day/hour analysis
- Allocator integration

### 16D: HOW Detector (4 tasks, ~8 hours)
- HowDetector class
- Channel sequence analysis
- Allocator integration

### 16E: Engine Modifications (5 tasks, ~8 hours)
- Content snapshot storage
- Scorer pattern integration
- Allocator pattern integration

### 16F: Prefect Flows (4 tasks, ~6.5 hours)
- pattern_learning_flow (weekly)
- pattern_health_flow (daily)
- pattern_backfill_flow (manual)

---

## Schedules

| Flow | Schedule | Purpose |
|------|----------|---------|
| Pattern Learning | Sunday 2am UTC | Weekly batch learning |
| Pattern Health | Daily 6am UTC | Validation + alerts |
| Pattern Backfill | Manual | Historical data analysis |

---

## Files Structure

```
src/
├── algorithms/
│   ├── who_detector.py
│   ├── what_detector.py
│   ├── when_detector.py
│   └── how_detector.py
├── orchestration/flows/
│   ├── pattern_learning_flow.py
│   ├── pattern_health_flow.py
│   └── pattern_backfill_flow.py
└── api/routes/
    └── patterns.py
```

---

## Full Specifications

See `docs/specs/phase16/` for detailed specs:
- `PHASE_16_MASTER_INDEX.md` — Overview and build order
- `PHASE_16_CONVERSION_INTELLIGENCE_SPEC.md` — WHO Detector
- `PHASE_16B_WHAT_DETECTOR_SPEC.md` — Content patterns
- `PHASE_16C_WHEN_DETECTOR_SPEC.md` — Timing patterns
- `PHASE_16D_HOW_DETECTOR_SPEC.md` — Channel sequences
- `PHASE_16E_ENGINE_MODIFICATIONS_SPEC.md` — Engine updates
- `PHASE_16F_PREFECT_FLOWS_SPEC.md` — Orchestration

---

## Checkpoint 8 Criteria

- [ ] Migration 014 applied successfully
- [ ] All 4 detectors implemented and tested
- [ ] Engines capture content_snapshot on send
- [ ] Scorer uses learned weights from patterns
- [ ] Allocator uses WHEN/HOW patterns
- [ ] Weekly pattern learning flow runs
- [ ] Patterns visible in admin dashboard
- [ ] Pattern health alerts working
