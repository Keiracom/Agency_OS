> ⚠️ **DEPRECATED (FCO-002):** SDK has been replaced by Smart Prompts as of 2026-02-05.
> For current margin calculations, see: `MARGIN_RECALCULATION_POST_SIEGE.md`
> This document is retained for historical reference only.

# SDK Option C: Selective Usage (Signal-Gated)

**Document Type:** Financial Analysis
**Option:** C — Selective Usage (Signal-Gated SDK)
**Date:** January 19, 2026
**Currency:** AUD

---

## 1. Executive Summary

**Concept:** SDK only fires for Hot leads that ALSO have priority signals indicating highest purchase intent. Hot leads without signals use standard (non-SDK) enrichment.

**Example:** Lead scores ALS 88 (Hot). Has recent funding + actively hiring → SDK enrichment. Another lead scores ALS 90 (Hot) but no signals → standard enrichment.

**Margin Protection:** Good — ~50% reduction in SDK calls
**Customer Impact:** Optimal — Best leads get best treatment, others still get good treatment
**Recommendation:** PRIMARY RECOMMENDATION

---

## 2. How It Works

### Two-Gate System

```
Lead scored → ALS 85+ (Hot)?
    │
    NO → Standard enrichment (Cold/Cool/Warm)
    │
    YES → Check priority signals
            │
            NO SIGNALS → Standard Hot treatment (channels, no SDK)
            │
            HAS SIGNALS → Full SDK treatment (research + personalization)
```

### Priority Signals (Any ONE qualifies)

| Signal | Detection Method | Why It Matters |
|--------|------------------|----------------|
| Recent funding (< 90 days) | Apollo/Clay data | Budget available, likely hiring |
| Actively hiring (3+ roles) | LinkedIn/Apollo | Growing, need solutions |
| Tech stack match > 80% | Clay enrichment | Already using similar tools |
| LinkedIn engagement > 70 | Scraped activity | Decision-maker is reachable |
| Referral source | Lead source field | Pre-qualified warm intro |
| Employee count 50-500 | Apollo data | Sweet spot for solution fit |

---

## 3. Implementation

### Code: should_use_sdk_brain()

```python
# src/agents/sdk_agents/sdk_eligibility.py

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

def should_use_sdk_brain(lead_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Determine if lead qualifies for SDK enrichment.

    Args:
        lead_data: Dict with lead and enrichment data

    Returns:
        Tuple of (eligible: bool, signals: list[str])
    """
    # Gate 1: Must be Hot (ALS >= 85)
    als_score = lead_data.get("als_score", 0)
    if als_score < 85:
        return False, []

    # Gate 2: Must have at least ONE priority signal
    signals = []

    # Signal 1: Recent funding
    funding_date = lead_data.get("recent_funding_date")
    if funding_date:
        if isinstance(funding_date, str):
            funding_date = datetime.fromisoformat(funding_date[:10])
        days_since_funding = (datetime.utcnow() - funding_date).days
        if days_since_funding <= 90:
            signals.append(f"recent_funding_{days_since_funding}_days")

    # Signal 2: Actively hiring
    hiring_count = lead_data.get("hiring_count", 0)
    if hiring_count >= 3:
        signals.append(f"hiring_{hiring_count}_roles")

    # Signal 3: Tech stack match
    tech_match = lead_data.get("tech_stack_match", 0)
    if tech_match > 0.8:
        signals.append(f"tech_match_{int(tech_match * 100)}pct")

    # Signal 4: LinkedIn engagement
    li_engagement = lead_data.get("linkedin_engagement_score", 0)
    if li_engagement > 70:
        signals.append(f"linkedin_engagement_{li_engagement}")

    # Signal 5: Referral source
    source = lead_data.get("source", "").lower()
    if source == "referral":
        signals.append("referral_source")

    # Signal 6: Employee count sweet spot
    employee_count = lead_data.get("company_employee_count", 0)
    if 50 <= employee_count <= 500:
        signals.append(f"sweet_spot_{employee_count}_employees")

    eligible = len(signals) > 0
    return eligible, signals
```

### Integration: Scout Engine

```python
# src/engines/scout.py

from src.agents.sdk_agents.sdk_eligibility import should_use_sdk_brain

async def enrich_assignment(
    self,
    db: AsyncSession,
    assignment_id: UUID,
    client_id: UUID,
) -> EngineResult:
    """Enrich lead with appropriate method based on eligibility."""

    # Get lead data for eligibility check
    lead_data = await self._get_lead_enrichment_data(db, assignment_id)

    # Check SDK eligibility
    sdk_eligible, signals = should_use_sdk_brain(lead_data)

    if sdk_eligible:
        logger.info(
            f"Lead {assignment_id} eligible for SDK: {signals}"
        )
        return await self._sdk_enrichment(db, assignment_id, client_id, signals)
    else:
        # Hot lead without signals OR lower tier
        als_tier = lead_data.get("als_tier")
        if als_tier == "hot":
            logger.info(
                f"Lead {assignment_id} is Hot but no signals - standard enrichment"
            )
        return await self._standard_enrichment(db, assignment_id)
```

---

## 4. Expected Signal Distribution

### Analysis of Typical B2B Lead Pool

Based on industry data and Agency OS ICP:

| Signal | % of Hot Leads | Detection Reliability |
|--------|----------------|----------------------|
| Recent funding | 8-12% | High (Apollo/Clay) |
| Actively hiring | 15-25% | High (LinkedIn/Apollo) |
| Tech stack match | 20-30% | Medium (Clay) |
| LinkedIn engagement | 10-20% | High (Scraped) |
| Referral source | 5-10% | High (Source field) |
| Employee sweet spot | 40-60% | High (Apollo) |

### Signal Overlap

Many leads have multiple signals. Conservative estimate:
- ~50% of Hot leads have at least ONE signal
- ~20% have TWO+ signals
- ~5% have THREE+ signals

**Result:** SDK fires for ~50% of Hot leads, not 100%.

---

## 5. Financial Model — Velocity Tier

### Hot Lead Split

| Category | Count | % of Hot | Treatment |
|----------|-------|----------|-----------|
| Total Hot leads | 225 | 100% | — |
| SDK-eligible (signals) | 113 | 50% | Full SDK |
| Standard Hot (no signals) | 112 | 50% | Channels only |

### COGS Breakdown

**SDK-Eligible Hot Leads (113):**
| Item | Cost |
|------|------|
| SDK Enrichment | 113 × $1.21 = $137 |
| SDK Email | 113 × $0.25 = $28 |
| SDK Voice KB | 113 × $1.79 = $202 |
| SMS | 113 × $0.22 = $25 |
| Voice calls | 113 × $0.88 = $99 |
| Direct Mail | 113 × $0.82 = $93 |
| **Subtotal** | **$584** |

**Standard Hot Leads (112):**
| Item | Cost |
|------|------|
| Standard enrichment | 112 × $0.08 = $9 |
| Standard Email | 112 × $0.03 = $3 |
| Standard Voice KB | 112 × $0.20 = $22 |
| SMS | 112 × $0.22 = $25 |
| Voice calls | 112 × $0.88 = $99 |
| Direct Mail | 112 × $0.82 = $92 |
| **Subtotal** | **$250** |

**All Hot Leads: $584 + $250 = $834**

### Full COGS Table

| Tier | Leads | Cost | Subtotal |
|------|-------|------|----------|
| Hot (SDK eligible) | 113 | $5.17 | $584 |
| Hot (standard) | 112 | $2.23 | $250 |
| Warm | 563 | $1.42 | $799 |
| Cool | 900 | $0.36 | $324 |
| Cold | 562 | $0.29 | $163 |
| Infrastructure | — | — | $301 |
| **TOTAL COGS** | | | **$2,421** |

### Margin Analysis

| Metric | No SDK | Option C | Delta |
|--------|--------|----------|-------|
| Revenue | $4,000 | $4,000 | — |
| COGS | $2,168 | $2,421 | +$253 |
| Margin | 45.8% | **39.5%** | -6.3% |

**Only 6.3% margin reduction** vs 18% for Option A or similar for Option B.

---

## 6. All Tiers Financial Summary

| Tier | Revenue | COGS | SDK Spend | Margin |
|------|---------|------|-----------|--------|
| Ignition | $2,500 | $1,175 | $77 | **53.0%** |
| Velocity | $4,000 | $2,421 | $137 | **39.5%** |
| Dominance | $7,500 | $4,538 | $274 | **39.5%** |

---

## 7. What Happens to Non-SDK Hot Leads

### Treatment Comparison

| Feature | SDK Hot Lead | Standard Hot Lead |
|---------|--------------|-------------------|
| **Channels** | All 5 | All 5 (same) |
| **Research depth** | Web search + fetch | Scraped data only |
| **Pain points** | Evidence-based | Industry generic |
| **Email** | Highly personalized | Template + name/company |
| **Voice KB** | Custom objections | Campaign script |
| **Expected reply rate** | 8-12% | 5-7% |
| **Cost per lead** | $5.17 | $2.23 |

### Quality Difference Example

**SDK Email (Lead with funding signal):**
> "Hi Sarah, I noticed TechCorp closed your Series B last month — congratulations! With the growth that typically follows funding, many CTOs in your position are wrestling with lead response times as the sales team scales. We've helped 12 companies post-funding reduce response time by 40%..."

**Standard Email (Lead without signals):**
> "Hi Sarah, as CTO at TechCorp, you're likely focused on scaling your technology infrastructure. Many technology companies we work with struggle with lead response times. We've helped similar companies improve their outreach efficiency..."

Both are personalized, but SDK version references SPECIFIC, CURRENT information.

---

## 8. Why Option C is Optimal

### 1. Preserves ALS Integrity

Unlike Option A (tier caps), leads are scored accurately. A 92 ALS lead is treated as Hot, not downgraded.

### 2. SDK Goes to Highest ROI Leads

Signals correlate with purchase readiness:
- Recent funding = Budget available
- Hiring = Active growth mode
- Tech match = Already understand category
- Referral = Pre-qualified relationship

SDK spend is concentrated where it matters most.

### 3. All Hot Leads Get Hot Channels

Even non-SDK Hot leads still receive:
- SMS outreach
- Voice AI calls
- Direct mail postcards
- LinkedIn messages

They just get template-based content instead of researched content.

### 4. Customer Experience is Consistent

Customer doesn't see "some Hot leads got downgraded." They see:
- All Hot leads get multi-channel outreach
- Some emails are more personalized than others (but all are personalized)
- No visible "budget exhausted" states

### 5. Simple Implementation

One function (`should_use_sdk_brain()`) gates all SDK usage. No complex state management, no monthly resets, no tier tracking.

---

## 9. Combining with Option B (Hybrid)

**Recommended:** Implement Option C as primary, with Option B as safety net.

```python
async def enrich_with_sdk(
    self,
    db: AsyncSession,
    assignment_id: UUID,
    client_id: UUID,
    signals: list[str],
) -> EngineResult:
    """SDK enrichment with budget safeguard."""

    # Primary gate: Option C (signal eligibility) - already passed

    # Safety gate: Option B (budget check)
    budget_ok = await self._check_sdk_budget(client_id)
    if not budget_ok:
        logger.warning(f"Client {client_id} SDK budget exhausted, using fallback")
        return await self._standard_enrichment(db, assignment_id)

    # Proceed with SDK
    result = await self.sdk_brain.run(...)

    # Deduct from budget
    if result.success:
        await self._deduct_sdk_budget(client_id, result.cost_aud)

    return result
```

**Hybrid Budget Caps (higher than Option B alone):**

| Tier | Option B Solo | Option C + B Hybrid |
|------|---------------|---------------------|
| Ignition | $75 | $100 (higher ceiling) |
| Velocity | $150 | $200 (higher ceiling) |
| Dominance | $300 | $400 (higher ceiling) |

The hybrid approach means:
1. Signal gate reduces SDK calls by ~50%
2. Budget cap catches any unexpected spikes
3. Margins protected with minimal customer impact

---

## 10. Implementation Checklist

1. [ ] Create `src/agents/sdk_agents/sdk_eligibility.py`
2. [ ] Implement `should_use_sdk_brain()` function
3. [ ] Add signal detection to lead enrichment data fetch
4. [ ] Modify scout.py to check eligibility before SDK
5. [ ] Modify content.py for email SDK eligibility
6. [ ] Modify voice.py for Voice KB SDK eligibility
7. [ ] Modify closer.py for objection SDK eligibility
8. [ ] Add `sdk_signals` field to lead_assignments table
9. [ ] Create dashboard view showing SDK vs Standard Hot leads
10. [ ] (Optional) Add Option B budget safeguard

**Estimated engineering time:** 2-3 days (Option C alone), +1 day for hybrid

---

## 11. Monitoring & Optimization

### Key Metrics to Track

```sql
-- SDK eligibility rate by client
SELECT
    c.name,
    COUNT(CASE WHEN la.sdk_signals IS NOT NULL THEN 1 END) as sdk_eligible,
    COUNT(CASE WHEN la.als_tier = 'hot' THEN 1 END) as total_hot,
    ROUND(
        COUNT(CASE WHEN la.sdk_signals IS NOT NULL THEN 1 END)::decimal /
        NULLIF(COUNT(CASE WHEN la.als_tier = 'hot' THEN 1 END), 0) * 100,
        1
    ) as eligibility_rate
FROM clients c
JOIN lead_assignments la ON la.client_id = c.id
WHERE la.created_at > CURRENT_DATE - INTERVAL '30 days'
GROUP BY c.id
ORDER BY eligibility_rate DESC;
```

### Optimization Opportunities

If eligibility rate is too high (>60%):
- Tighten signal thresholds (e.g., hiring_count >= 5 instead of 3)
- Require TWO signals instead of one

If eligibility rate is too low (<30%):
- Loosen thresholds
- Add new signals (e.g., industry growth rate)

---

## 12. Recommendation

**PRIMARY RECOMMENDATION for SDK cost control.**

Option C provides:
- 50% reduction in SDK costs vs "all Hot leads"
- No customer-visible quality degradation
- No artificial tier manipulation
- Simple implementation
- Easy to tune (adjust signal thresholds)

**Combine with Option B budget cap** as safety net for unexpected spikes.

---

**Prepared by:** CTO Office
**Reviewed by:** CFO Office
**Date:** January 19, 2026
