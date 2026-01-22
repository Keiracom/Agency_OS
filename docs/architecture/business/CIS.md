# Conversion Intelligence System (CIS) — Agency OS

**Purpose:** Learn from conversion outcomes to continuously improve lead scoring, timing, content, and channel selection.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-21

---

## Overview

The Conversion Intelligence System (CIS) analyzes historical conversion data to discover patterns that predict successful outcomes. It learns from every conversion and non-conversion to:

1. **Optimize ALS weights** — Adjust scoring component weights based on what actually converts
2. **Improve targeting** — Identify which lead attributes correlate with conversions
3. **Refine content** — Learn which messaging patterns resonate
4. **Optimize timing** — Discover best days, hours, and touch sequences
5. **Guide channel selection** — Understand which channels work for which leads
6. **Track downstream outcomes** — Learn from meetings, deals, and revenue

CIS runs weekly via Prefect flow, processing clients with sufficient conversion data (20+ conversions in last 90 days).

---

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| **Abstract Base** | `src/detectors/base.py` | Shared logic for all detectors |
| **WHO Detector** | `src/detectors/who_detector.py` | Lead attributes that convert |
| **WHAT Detector** | `src/detectors/what_detector.py` | Content patterns that convert |
| **WHEN Detector** | `src/detectors/when_detector.py` | Timing patterns that convert |
| **HOW Detector** | `src/detectors/how_detector.py` | Channel effectiveness |
| **Funnel Detector** | `src/detectors/funnel_detector.py` | Downstream outcomes (meetings/deals) |
| **Weight Optimizer** | `src/detectors/weight_optimizer.py` | ALS weight optimization via scipy |
| **Pattern Model** | `src/models/conversion_patterns.py` | Pattern storage schema |
| **Pattern Flow** | `src/orchestration/flows/pattern_learning_flow.py` | Weekly learning orchestration |
| **API Routes** | `src/api/routes/patterns.py` | Pattern retrieval endpoints |
| **Package Init** | `src/detectors/__init__.py` | Public exports |

---

## The 5 Detectors

CIS uses five specialized detectors, each analyzing a different dimension of conversion data.

### 1. WHO Detector — Lead Attributes

**File:** `src/detectors/who_detector.py`
**Pattern Type:** `who`

Analyzes which lead attributes correlate with conversions.

| Analysis | Output Key | Description |
|----------|------------|-------------|
| Job title effectiveness | `title_rankings` | Which titles convert best (normalized) |
| Industry performance | `industry_rankings` | Which industries convert best |
| Company size sweet spot | `size_analysis` | Optimal employee count range |
| Timing signals | `timing_signals` | Lift from new role, hiring, funding |
| Objection patterns | `objection_patterns` | Which segments raise which objections (Phase 24D) |

**Title Normalization:** Maps variations like "Chief Executive", "CEO", "C.E.O" to canonical forms.

**Size Ranges:** 1-5, 6-15, 16-30, 31-50, 51-100, 101-250, 251-500, 501+

**Timing Signal Lift:** Calculated from enriched data fields:
- `job_change_90d` — New role within 90 days
- `actively_hiring` — Has job listings
- `recent_funding` — Recent funding round

### 2. WHAT Detector — Content Patterns

**File:** `src/detectors/what_detector.py`
**Pattern Type:** `what`

Analyzes which content patterns predict conversions.

| Analysis | Output Key | Description |
|----------|------------|-------------|
| Subject line patterns | `subject_patterns` | Which subject types convert |
| Pain point effectiveness | `pain_points` | Effective vs ineffective pain points |
| CTA effectiveness | `ctas` | Which calls-to-action work |
| Message angles | `angles` | ROI, social proof, curiosity, etc. |
| Optimal length | `optimal_length` | Word count by channel |
| Personalization lift | `personalization_lift` | Lift from personalization elements |
| Template performance | `template_performance` | Which templates convert best (Phase 24B) |
| A/B test insights | `ab_test_insights` | Aggregated test results (Phase 24B) |
| Link effectiveness | `link_effectiveness` | Whether links help or hurt (Phase 24B) |
| AI model performance | `ai_model_performance` | Which models generate better content (Phase 24B) |

**Subject Pattern Detection:** Uses regex patterns:
- `question_about` — "question about/for/regarding"
- `quick_question` — "quick question"
- `reply_style` — "re:"
- `idea_for` — "idea for"
- `thought_about` — "thought about/for"
- `personalized` — Contains {company} or {first_name}

**Angle Detection:** Keyword matching for:
- `roi_focused` — roi, return, revenue, profit, save
- `social_proof` — clients like, case study, helped
- `curiosity` — noticed, wondering, quick question
- `fear_based` — missing out, losing, behind
- `value_add` — free, complimentary, audit
- `authority` — expert, specialist, trusted

### 3. WHEN Detector — Timing Patterns

**File:** `src/detectors/when_detector.py`
**Pattern Type:** `when`

Analyzes which timing patterns predict conversions.

| Analysis | Output Key | Description |
|----------|------------|-------------|
| Best days of week | `best_days` | Conversion rate by day (lead local time) |
| Best hours of day | `best_hours` | Conversion rate by hour (lead local time) |
| Touch distribution | `converting_touch_distribution` | Which touch number converts |
| Sequence gaps | `optimal_sequence_gaps` | Days between touches |
| Engagement timing | `engagement_timing` | Time-to-open/click patterns (Phase 24C) |
| Timezone insights | `timezone_insights` | Patterns by lead timezone (Phase 24C) |

**Local Time Analysis:** Uses `lead_local_time` and `lead_local_day_of_week` fields when available for accurate timezone-adjusted analysis.

**Touch Distribution:** Reports percentage of conversions at each touch (touch_1 through touch_6).

**Default Gaps:** When insufficient data:
- Touch 1→2: 2 days
- Touch 2→3: 3 days
- Touch 3→4: 4 days

### 4. HOW Detector — Channel Effectiveness

**File:** `src/detectors/how_detector.py`
**Pattern Type:** `how`

Analyzes which channel strategies predict conversions.

| Analysis | Output Key | Description |
|----------|------------|-------------|
| Channel effectiveness | `channel_effectiveness` | Conversion rate by channel |
| Sequence patterns | `sequence_patterns` | Which channel orders convert |
| Tier-based channels | `tier_channel_effectiveness` | Best channels per ALS tier |
| Multi-channel lift | `multi_channel_lift` | Single vs multi-channel comparison |
| Engagement correlation | `email_engagement_correlation` | Open/click patterns (Phase 24C) |
| Conversation quality | `channel_conversation_quality` | Thread metrics by channel (Phase 24D) |

**Sequence Pattern:** First 3 channels joined with "→" (e.g., "email→linkedin→voice").

**Multi-channel Recommendation:** Returns "multi" if lift > 1.2, otherwise "single".

**Engagement Insights:** Generates actionable recommendations like:
- "Email opens strongly predict conversion - focus on subject line optimization"
- "Link clicks are a strong conversion signal - include clear CTAs"

### 5. Funnel Detector — Downstream Outcomes

**File:** `src/detectors/funnel_detector.py`
**Pattern Type:** `funnel`

Analyzes downstream conversion patterns beyond booking meetings.

| Analysis | Output Key | Description |
|----------|------------|-------------|
| Show rate patterns | `show_rate` | What predicts meeting attendance |
| Meeting-to-deal patterns | `meeting_to_deal` | What predicts deals from meetings |
| Win rate patterns | `win_rate` | What predicts closed-won deals |
| Lost deal patterns | `lost_deals` | Top reasons for lost deals |
| Channel attribution | `channel_attribution` | Revenue by first-touch channel |
| Velocity patterns | `velocity` | Time-to-close by stage |

**Show Rate Insights:**
- Confirmation impact (confirmed vs unconfirmed)
- Reminder impact (reminded vs not reminded)
- Reschedule risk (first-time vs rescheduled)
- ALS tier show rates

**Deal Velocity:** Tracks days-in-stage for won vs lost deals to identify stalled opportunities.

---

## Weight Optimizer

**File:** `src/detectors/weight_optimizer.py`

Optimizes ALS component weights using scipy's SLSQP optimizer.

### Default Weights

```python
DEFAULT_WEIGHTS = {
    "data_quality": 0.20,
    "authority": 0.25,
    "company_fit": 0.25,
    "timing": 0.15,
    "risk": 0.15,
}
```

### Optimization Process

1. **Extract data** — Get leads with ALS components and outcomes (90 days)
2. **Prepare matrix** — Build component matrix X and conversion labels y
3. **Minimize objective** — Maximize correlation between weighted score and conversion
4. **Apply constraints**:
   - All weights sum to 1.0
   - Each weight between 0.05 and 0.50
5. **Calculate confidence** — Based on sample size and improvement

### Constraints

| Constraint | Value |
|------------|-------|
| Minimum weight | 0.05 |
| Maximum weight | 0.50 |
| Sum constraint | 1.0 |
| Minimum samples | 50 |

### Output

```python
{
    "weights": {"data_quality": 0.18, "authority": 0.28, ...},
    "confidence": 0.75,
    "sample_size": 150,
    "optimization_status": "success",
    "correlation_improvement": 0.12,
    "iterations": 23,
}
```

---

## Data Flow

### Weekly Pattern Learning Cycle

```
┌─────────────────────────────────────────────────────────┐
│                weekly_pattern_learning_flow             │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Archive expired patterns (valid_until < now)         │
│    → Move to conversion_pattern_history table           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Get eligible clients                                 │
│    → Active/trialing subscription                       │
│    → 20+ conversions in last 90 days                    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 3. For each client, run all 4 detectors:                │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│    │   WHO   │  │  WHAT   │  │  WHEN   │  │   HOW   │  │
│    └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │
│         └────────────┼───────────┼───────────┘         │
│                      ▼                                  │
│              Store in conversion_patterns               │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Optimize ALS weights (if 2+ detectors succeeded)     │
│    → Update client.als_learned_weights                  │
│    → Update client.als_weights_updated_at               │
└─────────────────────────────────────────────────────────┘
```

### Pattern Consumption Flow

```
┌─────────────────┐     ┌─────────────────────────────────┐
│ Allocator Engine│────▶│ Query conversion_patterns       │
│ (scorer.py)     │     │ for timing/channel recs         │
└─────────────────┘     └─────────────────────────────────┘

┌─────────────────┐     ┌─────────────────────────────────┐
│ Content Engine  │────▶│ Query WHAT patterns for         │
│ (content.py)    │     │ effective pain points/CTAs      │
└─────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────────────────────┐
│ Outreach Flow   │────▶│ Query WHEN patterns for         │
│ (outreach_flow) │     │ optimal send timing             │
└─────────────────┘     └─────────────────────────────────┘
```

---

## Pattern Storage Schema

### conversion_patterns Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| client_id | UUID | Foreign key to clients |
| pattern_type | VARCHAR(10) | who, what, when, how, funnel |
| patterns | JSONB | Detected patterns data |
| sample_size | INTEGER | Samples used for detection |
| confidence | FLOAT | Score 0.0-1.0 |
| computed_at | TIMESTAMP | When pattern was computed |
| valid_until | TIMESTAMP | Expiry (default +14 days) |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |
| deleted_at | TIMESTAMP | Soft delete (Rule 14) |

**Unique Constraint:** (client_id, pattern_type) — One active pattern per type per client.

### conversion_pattern_history Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| client_id | UUID | Foreign key to clients |
| pattern_type | VARCHAR(10) | who, what, when, how, funnel |
| patterns | JSONB | Archived pattern data |
| sample_size | INTEGER | Samples used |
| confidence | FLOAT | Confidence score |
| computed_at | TIMESTAMP | When originally computed |
| valid_until | TIMESTAMP | When it expired |
| archived_at | TIMESTAMP | When archived |

---

## Key Rules

### Minimum Sample Requirements

| Context | Minimum | Notes |
|---------|---------|-------|
| Pattern detection | 30 samples | Per detector |
| Segment analysis | 5 samples | Per segment (title, industry, etc.) |
| Weight optimization | 50 leads | With components and outcomes |
| Client eligibility | 20 conversions | In last 90 days |

### Confidence Calculation

Uses logarithmic scale based on sample size:

| Sample Size | Confidence |
|-------------|------------|
| < 10 | 0.2 |
| 10-29 | 0.3-0.5 (linear) |
| 30 | 0.5 |
| 100 | 0.7 |
| 500 | 0.85 |
| 1000+ | 0.95 (max) |

### Pattern Validity

- **Default validity:** 14 days
- **Expired patterns:** Archived to history table, soft-deleted from main table
- **High confidence threshold:** >= 0.7

### Lift Calculation

```
lift = segment_rate / baseline_rate
```

- lift > 1.0 = Better than average
- lift < 1.0 = Worse than average
- lift = 1.0 = Same as average

### Import Hierarchy (Layer 3)

Detectors are Layer 3 components:
- **CAN import:** models (Layer 1)
- **CANNOT import:** integrations (Layer 2), engines (Layer 3), orchestration (Layer 4)

---

## Configuration

### Pattern Learning Flow

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_conversions` | 20 | Minimum conversions for eligibility |
| `lookback_days` | 90 | Days of history to analyze |
| `validity_days` | 14 | Pattern validity period |
| `max_workers` | 5 | Concurrent task runner workers |

### Weight Optimizer

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_weight` | 0.05 | Minimum component weight |
| `max_weight` | 0.50 | Maximum component weight |
| `min_samples` | 50 | Minimum samples for optimization |
| `lookback_days` | 90 | Days of history to analyze |

### Detector Retries

All detector tasks have:
- **Retries:** 2
- **Retry delay:** 10 seconds

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/patterns` | GET | List all patterns for client |
| `/patterns/{type}` | GET | Get specific pattern (who/what/when/how) |
| `/patterns/recommendations/channels` | GET | Channel recommendations from HOW |
| `/patterns/recommendations/timing` | GET | Timing recommendations from WHEN |
| `/patterns/weights` | GET | Current ALS weights |
| `/patterns/history` | GET | Archived pattern history |
| `/patterns/trigger` | POST | Manually trigger pattern learning |

---

## Cross-References

| Topic | Document |
|-------|----------|
| ALS scoring formula | `business/SCORING.md` |
| Lead tiers | `business/TIERS_AND_BILLING.md` |
| Channel allocation | `flows/OUTREACH.md` |
| Content generation | `content/SDK_AND_PROMPTS.md` |
| Meeting tracking | `flows/MEETINGS_CRM.md` |
| Prefect flows | `foundation/DECISIONS.md` |

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
