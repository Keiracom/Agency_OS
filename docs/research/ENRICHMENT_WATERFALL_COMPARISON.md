# Enrichment Waterfall Comparison: Current vs Proposed

**Analysis Date:** January 4, 2026
**Purpose:** Evaluate proposed enrichment stack change

---

## Stack Comparison

### Current Stack (from TIER_PRICING_COST_MODEL_v2.md)

```
Tier 1: Hunter.io (Cold/Cool - 65% of leads) → $0.02/lead
Tier 2: Clay Waterfall (Warm/Hot - 35% of leads) → $0.25-0.50/lead
Blended Cost: $0.13/lead
```

**Provider Details:**
- **Hunter.io:** $0.023/email - email lookup only
- **Prospeo:** $0.031/email - email fallback (in Clay waterfall)
- **Clay:** $0.039-0.077/credit - full enrichment (75+ providers)
- **Apollo:** $0.31/lead - available in Clay waterfall, NOT used directly

### Proposed Stack

```
Primary: Apollo.io (The Engine) → Contact enrichment
Backup: Prospeo (The Safety Net) → Email finder fallback
Enrichment: BuiltWith (The Alpha) → Technographics
```

---

## Provider Deep Dive

### 1. Apollo.io (Already in Current Stack via Clay)

**API Capabilities:**
| Capability | Available | Notes |
|------------|-----------|-------|
| Email lookup | ✅ Yes | `/people/match` endpoint |
| Phone numbers | ✅ Yes | Direct dial when available |
| Company data | ✅ Yes | Firmographic enrichment |
| Bulk enrichment | ✅ Yes | Batch API available |
| Webhooks | ❌ No | No webhook support |
| Real-time | ✅ Yes | API response in seconds |

**Pricing (AUD):**
| Plan | Credits | Cost | Per Lead |
|------|---------|------|----------|
| Free | 100/month | $0 | — |
| Basic | 2,500/month | $75 (~$49 USD) | $0.03 |
| Professional | 4,000/month | $152 (~$99 USD) | $0.038 |
| Organization | Unlimited | $186 (~$119 USD) | Variable |

**Current Usage:** Available via Clay waterfall (Tier 2 fallback)

### 2. Prospeo (Already Considered)

**API Capabilities:**
| Capability | Endpoint | Cost |
|------------|----------|------|
| Email finder | `/email-finder` | 1 credit |
| Email verifier | `/email-verifier` | 0.5 credits |
| Domain search | `/domain-search` | 1 credit/50 emails |
| Mobile finder | `/mobile-finder` | 10 credits |
| LinkedIn enrichment | `/social-url-enrichment` | 2 credits |

**Pricing (AUD):**
| Plan | Credits | Cost | Per Email |
|------|---------|------|-----------|
| Free | 75/month | $0 | — |
| Starter | 1,000/month | $60 (~$39 USD) | $0.06 |
| Growth | 5,000/month | $152 (~$99 USD) | $0.03 |
| Business | 50,000/month | $566 (~$369 USD) | $0.011 |

**Key Features:**
- Built-in email verification (included)
- No charge for catch-all or invalid results
- 90%+ accuracy reported
- Deep catch-all detection technology

### 3. BuiltWith (NEW - Technographics)

**API Capabilities:**
| API | Purpose | Notes |
|-----|---------|-------|
| Domain API | Tech stack lookup | Returns 109k+ technologies |
| Lists API | Find sites by tech | "All Shopify users" |
| Free API | Basic tech counts | Rate limited (1/sec) |
| Relationships API | Site connections | Linked domains |
| Trust API | Fraud detection | Site trust score |

**Pricing (AUD):**
| Plan | Monthly | Per Lookup | Notes |
|------|---------|------------|-------|
| Basic | $453 (~$295 USD) | ~$0.45 | 2 tech reports |
| Pro | $760 (~$495 USD) | Unlimited | Most popular |
| Team | $1,528 (~$995 USD) | Unlimited | Multi-user |

**API Credit System:** Separate from plans, credit-based for high-volume API access

**Use Case for Agency OS:**
- Identify tech stack of prospect companies
- Find companies using specific tools (Salesforce, HubSpot, etc.)
- Competitive intelligence signals
- ICP matching based on technology adoption

---

## Cost Comparison Analysis

### Scenario: 1,250 leads (Ignition Tier)

**Current Stack (Hunter + Clay Waterfall):**
```
Cold/Cool (65% = 813 leads): 813 × $0.02 = $16
Warm/Hot (35% = 437 leads): 437 × $0.35 avg = $153
Total: $169/month
```

**Proposed Stack (Apollo + Prospeo + BuiltWith):**
```
Apollo (100%): 1,250 × $0.038 = $48
Prospeo fallback (20% miss rate): 250 × $0.03 = $8
BuiltWith Pro: $760/month (unlimited)
Total: $816/month
```

### Scenario: 4,500 leads (Dominance Tier)

**Current Stack:**
```
Cold/Cool: 2,925 × $0.02 = $59
Warm/Hot: 1,575 × $0.35 = $551
Total: $610/month
```

**Proposed Stack:**
```
Apollo Org: $186/month (unlimited)
Prospeo Business: $566/month
BuiltWith Pro: $760/month
Total: $1,512/month
```

---

## Decision Matrix

| Factor | Current (Clay Waterfall) | Proposed (Apollo+Prospeo+BuiltWith) |
|--------|-------------------------|--------------------------------------|
| **Cost Efficiency** | ✅ Lower ($0.13/lead) | ❌ Higher (~$0.35+/lead) |
| **Email Accuracy** | ✅ Good (75+ sources) | ✅ Good (Apollo + Prospeo verify) |
| **Phone Numbers** | ✅ Via Clay | ✅ Via Apollo + Prospeo mobile |
| **Technographics** | ⚠️ Limited | ✅ Full via BuiltWith |
| **API Simplicity** | ❌ Complex (Clay orchestration) | ✅ Simple (3 direct APIs) |
| **Vendor Lock-in** | ⚠️ Clay dependency | ✅ Independent providers |
| **Warm/Hot Enrichment** | ✅ Full Clay waterfall | ⚠️ Less comprehensive |
| **Scale Cost** | ✅ Predictable | ⚠️ BuiltWith fixed cost |

---

## Recommendation

### NOT RECOMMENDED to replace current stack

**Rationale:**

1. **Cost:** Proposed stack costs 2-3x more at Ignition tier, primarily due to BuiltWith's fixed monthly cost ($760/month)

2. **Redundancy:** Apollo is already available via Clay waterfall - you're paying for it anyway

3. **BuiltWith Value:** Technographics are interesting but not essential for contact enrichment. They're more useful for:
   - Account-based marketing targeting
   - ICP refinement (which companies to pursue)
   - Competitive intelligence
   - NOT for lead contact data

4. **Clay Advantage:** Clay's waterfall already cascades through 75+ providers including Apollo, Prospeo, Hunter, Clearbit, etc. You get the best of all worlds.

### POTENTIAL HYBRID APPROACH

If you want technographics without the cost:

```
Keep Current:
├── Hunter.io (Tier 1) - $0.02/lead
└── Clay Waterfall (Tier 2) - $0.25-0.50/lead

Add Optional:
└── BuiltWith Free API - Tech category counts (rate limited)
    OR
└── Clay BuiltWith Integration - Pay per lookup within Clay
```

**Clay includes BuiltWith as an integration** - you can add it to your waterfall for specific use cases (Hot leads only) without a separate subscription.

---

## Alternative: BuiltWith for ICP Discovery ONLY

If you want technographics specifically for the ICP Discovery Agent (Phase 11), consider:

| Use Case | Provider | Cost |
|----------|----------|------|
| Contact enrichment | Keep Clay waterfall | $0.13/lead |
| Tech stack for ICP | BuiltWith Free API | Free (rate limited) |
| Premium tech data | Clay + BuiltWith integration | Per-credit |

This keeps your COGS low while adding technographic intelligence where it matters - during ICP analysis, not for every lead.

---

## Final Answer

**Question:** Would Apollo + Prospeo + BuiltWith work better?

**Answer:** No, for lead enrichment. Your current Clay waterfall is more cost-effective and comprehensive.

**However:** BuiltWith could add value for:
1. ICP Discovery Agent (company tech stack analysis)
2. Account selection (find companies using specific tools)
3. Competitive intelligence signals

Consider adding BuiltWith as an **ICP enhancement tool**, not a contact enrichment replacement.
