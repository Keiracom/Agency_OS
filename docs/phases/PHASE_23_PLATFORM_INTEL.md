# Phase 23: Platform Intelligence

**Status:** 📋 Planned (Post-Launch)  
**Tasks:** 18  
**Trigger:** 10+ clients with 50+ conversions each

---

## Purpose

Cross-client learning system that aggregates conversion patterns across the platform, enabling new clients to benefit from collective learnings on Day 1.

---

## Current vs Future

**Current (Phase 16 - Per-Client):**
```
Client A learns → Benefits Client A only
New Client → Starts from defaults
```

**With Platform Intelligence:**
```
All clients → Platform aggregates
New Client → Inherits platform-learned weights
```

---

## Weight Fallback Hierarchy

```python
1. Client learned weights (confidence > 0.7, sample >= 50)
2. Industry-specific platform weights
3. Global platform weights
4. Platform priors (industry benchmarks)
5. Default weights
```

---

## Data Strategy

### Phase 1: Seed with Benchmarks
Use industry research (Ruler Analytics, First Page Sage, Martal 2025) for initial priors.

### Phase 2: Data Co-op
Founding customer terms include anonymized pattern sharing consent.

### Phase 3: Platform Learning
Monthly aggregation once sufficient conversions exist.

---

## Tasks Overview

### 23A: Platform Priors (5 tasks)
- PLT-001 to PLT-005

### 23B: Platform Learning Engine (6 tasks)
- PLT-006 to PLT-011

### 23C: Scorer Integration (4 tasks)
- PLT-012 to PLT-015

### 23D: Testing (3 tasks)
- TST-023-1 to TST-023-3

---

## Database Schema

**Migration:** `023_platform_intelligence.sql`

Tables:
- `platform_patterns` — Cross-client patterns
- `platform_weights` — Platform-wide ALS weights

---

## Activation Criteria

- ✅ 10+ clients with data_sharing_consent = TRUE
- ✅ Combined 500+ conversions
- ✅ At least 3 clients with learned weights

---

## Full Spec

See `PROJECT_BLUEPRINT_FULL_ARCHIVE.md` Phase 23 (Platform Intelligence) section for complete details.
