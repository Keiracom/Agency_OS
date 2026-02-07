> ⚠️ **DEPRECATED (FCO-002):** SDK has been replaced by Smart Prompts as of 2026-02-05.
> For current margin calculations, see: `MARGIN_RECALCULATION_POST_SIEGE.md`
> This document is retained for historical reference only.

# SDK Integration Margin Analysis — Executive Summary

**Document Type:** CTO/CFO Joint Analysis
**For:** CEO Decision
**Date:** January 19, 2026
**Classification:** Strategic — Core Business Decision
**Currency:** AUD

---

## 1. The Business Question

**How do we integrate Claude Agent SDK without destroying our margins?**

Current margins (without SDK): 60-73%
Worst-case with SDK: 22-42%
Target with SDK: **55-65%**

---

## 2. Critical Discovery: We Don't Control Costs

| Factor | Status | Risk |
|--------|--------|------|
| ALS tier distribution | Uncontrolled | High |
| LinkedIn scrape eligibility | All assigned leads | High |
| LinkedIn boost effect | Up to +10 points | Medium |
| SDK trigger threshold | Fixed at ALS 85 | High |
| SDK budget cap | Per-day (allows $6K/mo runaway) | Critical |

**Problem:** A lead scoring 78 (Warm) can be boosted to 88 (Hot) by LinkedIn scrape, triggering ~$3.50 in additional per-lead costs (SDK + SMS + Voice + Direct Mail).

---

## 3. The Full Sales Funnel with SDK Touchpoints

```
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: POOL POPULATION                                                │
│ Source: Apollo → Lead Pool                                              │
│ Cost: $0.31/lead (Apollo) + $0.036-0.77/lead (Hunter/Clay enrichment)  │
│ SDK: None                                                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: ASSIGNMENT & LINKEDIN SCRAPE                                   │
│ Trigger: Lead assigned to campaign                                      │
│ Cost: $0.0047/lead (Apify LinkedIn scrape)                             │
│ SDK: None                                                               │
│                                                                         │
│ ⚠️ LINKEDIN BOOST APPLIED HERE                                         │
│ - Person has posts: +3 points                                          │
│ - Recent activity (30 days): +1 point                                  │
│ - 500+ connections: +2 points                                          │
│ - Company posts: +2 points                                             │
│ - Company 1000+ followers: +2 points                                   │
│ - MAX BOOST: +10 points                                                │
│                                                                         │
│ LEADS AFFECTED: ALL assigned leads with LinkedIn URL                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: ALS SCORING                                                    │
│ Components: Data Quality (20) + Authority (25) + Company Fit (25)      │
│            + Timing (15) - Risk (15) + LinkedIn Boost (10)             │
│ MAX SCORE: 110 (but capped at 100)                                     │
│                                                                         │
│ TIER ASSIGNMENT:                                                        │
│ - Hot:  85-100 → Email, LinkedIn, SMS, Voice, Direct Mail, SDK         │
│ - Warm: 60-84  → Email, LinkedIn, Voice                                │
│ - Cool: 35-59  → Email, LinkedIn                                       │
│ - Cold: 20-34  → Email only                                            │
│ - Dead: 0-19   → Suppressed                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: SDK ENRICHMENT (HOT LEADS ONLY)                               │
│ Trigger: ALS >= 85                                                      │
│ Cost: $1.21/lead (SDK Deep Research)                                   │
│ What it does:                                                           │
│ - web_search for company news, funding, hiring                         │
│ - web_fetch company website, careers page                              │
│ - Generates: pain_points, personalization_hooks, talking_points        │
│                                                                         │
│ FALLBACK (non-SDK leads):                                              │
│ - Uses existing Claude PersonalizationAnalysisSkill                    │
│ - Cost: ~$0.08/lead (single Claude call, no tools)                     │
│ - Quality: Template-based personalization from scraped data only       │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: CONTENT GENERATION                                             │
│                                                                         │
│ EMAIL (ALL TIERS):                                                      │
│ - SDK leads: $0.25/email (SDK personalized writing)                    │
│ - Non-SDK: $0.03/email (template + basic Claude)                       │
│                                                                         │
│ LINKEDIN (WARM+):                                                       │
│ - SDK leads: $0.12/message (SDK personalized)                          │
│ - Non-SDK: $0.02/message (template-based)                              │
│                                                                         │
│ SMS (HOT ONLY):                                                         │
│ - SDK leads: $0.15/message (SDK + send cost)                           │
│ - Non-SDK: $0.08/message (template + send cost)                        │
│                                                                         │
│ VOICE KB (HOT ONLY):                                                    │
│ - SDK leads: $1.79/call (SDK knowledge base generation)                │
│ - Non-SDK: $0.20/call (static script)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 6: OUTREACH EXECUTION                                             │
│                                                                         │
│ CHANNEL COSTS (provider fees, not AI):                                 │
│ - Email: $0.01/email (Salesforge included in base)                     │
│ - LinkedIn: $0.00/message (Unipile flat rate)                          │
│ - SMS: $0.072/message (ClickSend)                                      │
│ - Voice: $0.35/minute (Vapi stack, avg 2.5 min = $0.88/call)          │
│ - Direct Mail: $0.82/postcard (ClickSend)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 7: REPLY HANDLING                                                 │
│ Trigger: Lead replies to any channel                                    │
│                                                                         │
│ CLASSIFICATION:                                                         │
│ - All replies: $0.08/reply (Haiku classification)                      │
│                                                                         │
│ OBJECTION HANDLING:                                                     │
│ - Simple objections: $0.08/objection (Haiku response)                  │
│ - Complex objections (SDK): $0.25/objection (SDK with context)         │
│                                                                         │
│ EXPECTED VOLUMES (per 1000 leads):                                     │
│ - Reply rate: 7.5% = 75 replies                                        │
│ - Objection rate: 30% of replies = 23 objections                       │
│ - Complex objections: 20% = 5 SDK calls                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. ALS Distribution: The Core Variable

### What the Documents Say

| Source | Hot | Warm | Cool | Cold |
|--------|-----|------|------|------|
| TIER_PRICING_COST_MODEL_v2.md | 10% | 25% | 40% | 25% |
| MEETING_GUARANTEE_ANALYSIS.md | 5% | 25% | 35% | 35% |
| sdk_cost_comparison_all_tiers.csv | 15% (cap) | 30% | — | — |

**Resolution Required:** Finance and Engineering must agree on canonical distribution.

### LinkedIn Boost Impact on Distribution

**Before LinkedIn scrape (base ALS only):**
| Tier | Velocity (2250 leads) |
|------|----------------------|
| Hot (85+) | 5% = 113 leads |
| Warm (60-84) | 25% = 563 leads |
| Near-Hot (75-84) | ~10% = 225 leads |

**After LinkedIn scrape (with boost):**
- ~50% of Near-Hot leads (75-84) gain 5-10 points
- ~113 additional leads cross into Hot tier
- New Hot: 113 + 113 = **226 leads (10%)**

**Worst case (all Near-Hot get max boost):**
- 225 Near-Hot leads all become Hot
- New Hot: 113 + 225 = **338 leads (15%)**

---

## 5. Per-Lead Cost Breakdown by Tier

### Hot Lead (ALS 85+) — WITH SDK

| Stage | Cost | Notes |
|-------|------|-------|
| Pool population | $0.43 | Apollo + Clay |
| LinkedIn scrape | $0.005 | Apify |
| SDK Enrichment | $1.21 | Deep research |
| SDK Email | $0.25 | Personalized writing |
| Email send | $0.01 | Salesforge |
| LinkedIn message | $0.12 | SDK + Unipile |
| SMS | $0.22 | SDK + ClickSend |
| Voice KB | $1.79 | SDK generation |
| Voice call | $0.88 | Vapi 2.5 min |
| Direct Mail | $0.82 | ClickSend postcard |
| **TOTAL** | **$5.78/lead** | |

### Hot Lead (ALS 85+) — WITHOUT SDK (Fallback)

| Stage | Cost | Notes |
|-------|------|-------|
| Pool population | $0.43 | Apollo + Clay |
| LinkedIn scrape | $0.005 | Apify |
| Claude analysis | $0.08 | Single call |
| Template Email | $0.03 | Basic Claude |
| Email send | $0.01 | Salesforge |
| LinkedIn message | $0.02 | Template |
| SMS | $0.08 | Template + ClickSend |
| Static Voice | $0.20 | Script only |
| Voice call | $0.88 | Vapi 2.5 min |
| Direct Mail | $0.82 | ClickSend postcard |
| **TOTAL** | **$2.58/lead** | |

**SDK Premium per Hot Lead: $3.20**

### Warm Lead (ALS 60-84)

| Stage | Cost | Notes |
|-------|------|-------|
| Pool population | $0.39 | Apollo + Clay (8 credits) |
| LinkedIn scrape | $0.005 | Apify |
| Claude analysis | $0.08 | Single call |
| Template Email | $0.03 | Basic Claude |
| Email send | $0.01 | Salesforge |
| LinkedIn message | $0.02 | Template |
| Voice call | $0.88 | Vapi 2.5 min |
| **TOTAL** | **$1.42/lead** | |

### Cool Lead (ALS 35-59)

| Stage | Cost | Notes |
|-------|------|-------|
| Pool population | $0.29 | Apollo + Hunter |
| LinkedIn scrape | $0.005 | Apify |
| Template Email | $0.03 | Basic Claude |
| Email send | $0.01 | Salesforge |
| LinkedIn message | $0.02 | Template |
| **TOTAL** | **$0.36/lead** | |

### Cold Lead (ALS 20-34)

| Stage | Cost | Notes |
|-------|------|-------|
| Pool population | $0.25 | Apollo + Hunter |
| Template Email | $0.03 | Basic Claude |
| Email send | $0.01 | Salesforge |
| **TOTAL** | **$0.29/lead** | |

---

## 6. Velocity Tier Model (2,250 leads/month)

### Scenario A: Current (No SDK)

| Tier | Leads | Per-Lead | Subtotal |
|------|-------|----------|----------|
| Hot (10%) | 225 | $2.58 | $581 |
| Warm (25%) | 563 | $1.42 | $799 |
| Cool (40%) | 900 | $0.36 | $324 |
| Cold (25%) | 562 | $0.29 | $163 |
| Infrastructure | — | — | $301 |
| **TOTAL COGS** | | | **$2,168** |
| Revenue | | | $4,000 |
| **Margin** | | | **45.8%** |

### Scenario B: SDK for All Hot Leads

| Tier | Leads | Per-Lead | Subtotal |
|------|-------|----------|----------|
| Hot (10%) | 225 | $5.78 | $1,301 |
| Warm (25%) | 563 | $1.42 | $799 |
| Cool (40%) | 900 | $0.36 | $324 |
| Cold (25%) | 562 | $0.29 | $163 |
| Infrastructure | — | — | $301 |
| **TOTAL COGS** | | | **$2,888** |
| Revenue | | | $4,000 |
| **Margin** | | | **27.8%** |

### Scenario C: SDK for All Hot Leads + LinkedIn Boost (15% Hot)

| Tier | Leads | Per-Lead | Subtotal |
|------|-------|----------|----------|
| Hot (15%) | 338 | $5.78 | **$1,954** |
| Warm (22%) | 495 | $1.42 | $703 |
| Cool (40%) | 900 | $0.36 | $324 |
| Cold (23%) | 517 | $0.29 | $150 |
| Infrastructure | — | — | $301 |
| **TOTAL COGS** | | | **$3,432** |
| Revenue | | | $4,000 |
| **Margin** | | | **14.2%** |

---

## 7. Four Strategic Options

See detailed analysis in:
- `SDK_OPTION_A_TIER_CAPS.md`
- `SDK_OPTION_B_BUDGET_ENVELOPE.md`
- `SDK_OPTION_C_SELECTIVE_USAGE.md`
- `SDK_OPTION_D_SERVICE_TIERS.md`

### Summary Comparison

| Metric | Option A | Option B | Option C | Option D |
|--------|----------|----------|----------|----------|
| Name | Fixed Tier Caps | Budget Envelope | Selective Usage | Service Tiers |
| Margin Protection | Guaranteed | Guaranteed | Variable | Guaranteed |
| Customer Experience | Compromised | Variable | Optimal | Tiered |
| Implementation | Medium | Medium | Low | High |
| SDK Cost | $0 (capped) | $200/mo max | ~$100/mo | Customer choice |
| Velocity Margin | 56.6% | 52-57% | 54-58% | 56.6% base |
| Recommendation | Not Recommended | Backup | **Primary** | Future upsell |

---

## 8. CTO/CFO Joint Recommendation

**Implement Option C (Selective Usage) with Option B (Budget Envelope) as safeguard.**

### Why Option C

1. **Preserves ALS integrity** — Leads are scored accurately, no artificial caps
2. **SDK goes to highest-value leads** — Priority signals gate ensures ROI
3. **Customer experience optimal** — Hot leads get best treatment, others get good treatment
4. **Implementation simple** — Single `should_use_sdk_brain()` function

### Budget Safeguard (Option B)

| Tier | Monthly SDK Budget | Safety Cap |
|------|--------------------| -----------|
| Ignition | $75 | Hard stop |
| Velocity | $150 | Hard stop |
| Dominance | $300 | Hard stop |

### Expected Outcome

| Tier | Revenue | COGS | Margin |
|------|---------|------|--------|
| Ignition | $2,500 | $1,050 | **58.0%** |
| Velocity | $4,000 | $2,250 | **43.8%** |
| Dominance | $7,500 | $3,900 | **48.0%** |

---

## 9. Immediate Actions Required

1. **CEO Decision:** Approve Option C + B hybrid
2. **Engineering:** Implement `should_use_sdk_brain()` gate
3. **Engineering:** Add `sdk_monthly_budget` to Client model
4. **Finance:** Update P&L projections with SDK line item
5. **Finance:** Reconcile ALS distribution across all docs (use 10% Hot as canonical)
6. **Product:** Consider Dominance tier price increase ($7,500 → $8,500) to restore margin

---

**Prepared by:**
CTO Office & CFO Office
January 19, 2026
