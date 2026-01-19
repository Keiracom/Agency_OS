# SDK Option A: Fixed ALS Tier Caps

**Document Type:** Financial Analysis
**Option:** A — Budget Mode (Fixed Tier Allocation)
**Date:** January 19, 2026
**Currency:** AUD

---

## 1. Executive Summary

**Concept:** Cap the NUMBER of leads in each ALS tier, regardless of actual score.

**Example:** If 500 leads score as Hot, but cap is 225, only the top 225 by ALS get Hot treatment.

**Margin Protection:** Guaranteed — COGS is fixed by cap
**Customer Impact:** Negative — Best leads may not get best treatment
**Recommendation:** NOT RECOMMENDED as primary option

---

## 2. How It Works

### Current System (Uncontrolled)
```
Lead scored 86 → Hot tier → All Hot channels + SDK
Lead scored 91 → Hot tier → All Hot channels + SDK
Lead scored 78 → Warm tier → Warm channels only

If 500 leads score 85+, all 500 get Hot treatment = uncontrolled cost
```

### Option A (Capped)
```
Velocity tier: 2,250 leads/month
Hot cap: 10% = 225 leads max

All leads scored:
- 400 leads score 85+ (would be Hot)
- Sort by ALS descending
- Top 225 get Hot treatment
- Remaining 175 (scoring 85-89) treated as Warm

Result: Exactly 225 Hot leads, cost is predictable
```

---

## 3. Tier Cap Configuration

| Subscription Tier | Total Leads | Hot Cap (10%) | Warm Cap (25%) | Cool Cap (40%) | Cold Cap (25%) |
|-------------------|-------------|---------------|----------------|----------------|----------------|
| Ignition | 1,250 | 125 | 313 | 500 | 312 |
| Velocity | 2,250 | 225 | 563 | 900 | 562 |
| Dominance | 4,500 | 450 | 1,125 | 1,800 | 1,125 |

---

## 4. Implementation

### Code Change: ScorerEngine

```python
# src/engines/scorer.py

async def score_and_assign_tier(
    self,
    db: AsyncSession,
    assignment_id: UUID,
    client_id: UUID,
) -> EngineResult:
    """Score lead and assign tier with caps."""

    # Get client's current tier counts for this month
    tier_counts = await self._get_monthly_tier_counts(db, client_id)
    tier_caps = await self._get_tier_caps(db, client_id)

    # Calculate raw ALS score
    raw_score = await self._calculate_als(db, assignment_id)
    natural_tier = self._get_tier(raw_score)

    # Check if natural tier has capacity
    assigned_tier = natural_tier
    if tier_counts[natural_tier] >= tier_caps[natural_tier]:
        # Downgrade to next available tier
        assigned_tier = self._downgrade_tier(
            natural_tier,
            tier_counts,
            tier_caps
        )

    # Update counts
    await self._increment_tier_count(db, client_id, assigned_tier)

    return EngineResult(
        success=True,
        data={
            "als_score": raw_score,
            "natural_tier": natural_tier,
            "assigned_tier": assigned_tier,
            "capped": natural_tier != assigned_tier,
        }
    )

def _downgrade_tier(self, natural, counts, caps):
    """Find next available tier below natural."""
    hierarchy = ["hot", "warm", "cool", "cold"]
    start_idx = hierarchy.index(natural)

    for tier in hierarchy[start_idx:]:
        if counts[tier] < caps[tier]:
            return tier

    # All full, assign to cold
    return "cold"
```

### Database Change

```sql
-- Add tier tracking columns to clients table
ALTER TABLE clients ADD COLUMN monthly_hot_count INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN monthly_warm_count INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN monthly_cool_count INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN monthly_cold_count INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN tier_counts_reset_at TIMESTAMP;

-- Add tier cap overrides (optional)
ALTER TABLE clients ADD COLUMN hot_cap_override INTEGER;
ALTER TABLE clients ADD COLUMN warm_cap_override INTEGER;
```

---

## 5. Financial Model — Velocity Tier

### COGS by Tier (With Caps Enforced)

| Tier | Cap | Per-Lead Cost | Monthly COGS |
|------|-----|---------------|--------------|
| Hot | 225 | $5.78 (SDK) | $1,301 |
| Warm | 563 | $1.42 | $799 |
| Cool | 900 | $0.36 | $324 |
| Cold | 562 | $0.29 | $163 |
| Infrastructure | — | — | $301 |
| **TOTAL** | **2,250** | | **$2,888** |

### Margin Analysis

| Metric | Value |
|--------|-------|
| Revenue | $5,000 |
| COGS | $2,888 |
| Gross Profit | $2,112 |
| **Margin** | **42.2%** |

### Comparison to No SDK

| Scenario | COGS | Margin | Delta |
|----------|------|--------|-------|
| No SDK | $2,168 | 56.6% | — |
| Option A (SDK with caps) | $2,888 | 42.2% | -14.4% |

---

## 6. All Tiers Financial Summary

| Tier | Revenue | COGS (Capped) | Margin |
|------|---------|---------------|--------|
| Ignition | $2,500 | $1,478 | **40.9%** |
| Velocity | $5,000 | $2,888 | **42.2%** |
| Dominance | $7,500 | $5,775 | **23.0%** |

---

## 7. What Happens to Capped Leads

### Example: 400 leads score Hot (85+), but cap is 225

| Lead | ALS Score | Natural Tier | Assigned Tier | Treatment |
|------|-----------|--------------|---------------|-----------|
| 1-225 | 95-100 | Hot | **Hot** | Full SDK + all channels |
| 226-400 | 85-94 | Hot | **Warm** | No SDK, no SMS, no Direct Mail |

### Impact on Capped Leads

These 175 leads (226-400) miss out on:
- SDK Deep Research ($1.21/lead)
- SDK Email ($0.25/lead)
- SDK Voice KB ($1.79/lead)
- SMS channel ($0.22/lead)
- Direct Mail ($0.82/lead)

**Per-lead savings: $4.29**
**Total savings: 175 × $4.29 = $751/month**

But these are genuinely high-scoring leads (85-94 ALS) that would convert well with full treatment.

---

## 8. Customer Experience Issues

### Problem 1: Visible Inconsistency

Customer logs into dashboard, sees:
- Lead A: ALS 87 → Treated as Hot
- Lead B: ALS 92 → Treated as Warm (capped)

**Customer question:** "Why is my 92-score lead getting less treatment than my 87-score lead?"

**Answer:** "You've hit your monthly Hot quota."

### Problem 2: Timing Matters

Early-month leads get Hot treatment.
Late-month leads (even with ALS 99) get downgraded.

**Customer perception:** "The system performs worse at end of month."

### Problem 3: Gaming the System

Sophisticated customers might:
- Front-load their best ICP matches early in month
- Pause campaigns mid-month to "save" Hot slots
- Complain about arbitrary limitations

---

## 9. Pros and Cons

### Pros

| Benefit | Impact |
|---------|--------|
| 100% predictable COGS | CFO loves this |
| Margin guaranteed | No runaway costs |
| Simple to implement | ~1 day engineering |
| Easy to explain internally | "We cap at X Hot leads" |

### Cons

| Issue | Impact |
|-------|--------|
| Best leads may get worst treatment | Lost revenue potential |
| Customer confusion | Support tickets |
| End-of-month degradation | Perception issue |
| Can't justify to customers | "Why pay premium if capped?" |
| Feels arbitrary | Against "smart AI" positioning |

---

## 10. When Option A Makes Sense

- **Cash-strapped startup** that must guarantee burn rate
- **Proof of concept** where margin matters more than outcomes
- **Conservative CFO** who won't accept any cost variability

---

## 11. Recommendation

**NOT RECOMMENDED as primary option.**

Option A solves the cost problem but creates a customer experience problem that undermines the value proposition.

**Better alternative:** Option C (Selective Usage) or Option B (Budget Envelope) provide cost control without visible tier manipulation.

---

## 12. If CEO Chooses Option A

Implementation checklist:
1. [ ] Add tier count columns to clients table
2. [ ] Add monthly reset job to Prefect
3. [ ] Modify ScorerEngine to check caps
4. [ ] Add "capped" flag to lead assignment
5. [ ] Add dashboard indicator for "cap status"
6. [ ] Create support documentation for "why was my lead downgraded"
7. [ ] Update pricing page to mention "up to X Hot leads/month"

**Estimated engineering time:** 2-3 days
**Estimated support overhead:** +20% ticket volume

---

**Prepared by:** CTO Office
**Reviewed by:** CFO Office
**Date:** January 19, 2026
