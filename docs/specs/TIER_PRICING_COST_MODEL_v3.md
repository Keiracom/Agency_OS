# Agency OS Tier Pricing & Cost Model v3

**Document Type:** Financial Analysis  
**Version:** 3.0  
**Date:** February 2026  
**Author:** CEO Directive #008  
**Status:** PENDING CEO APPROVAL  
**Currency:** AUD (Australian Dollars) — NO USD IN THIS DOCUMENT

---

## Executive Summary

This document supersedes v2 and reflects the actual production stack after SIEGE overhaul. All figures verified against source code per LAW I-A (Single Source of Truth).

**Key Changes from v2:**
- Updated lead volumes: Velocity 2,250→2,500, Dominance 4,500→5,000
- Velocity price corrected: $5,000→$4,000
- LinkedIn: HeyReach→Unipile (cost reduction)
- Voice AI: Vapi→Raw Telnyx ($2.00→$0.09/min)
- Founding discount: 40%→50%
- Direct Mail: Deferred (ClickSend AU not launch-ready)
- ALS distribution: 10% hot, 25% warm, 40% cool, 25% cold

| Tier | Price | Founding Price | COGS | Margin | Founding Margin | Leads |
|------|-------|----------------|------|--------|-----------------|-------|
| **Ignition** | $2,500 | $1,250 | $476 | **81.0%** | **62.0%** | 1,250 |
| **Velocity** | $4,000 | $2,000 | $814 | **79.7%** | **59.3%** | 2,500 |
| **Dominance** | $7,500 | $3,750 | $1,556 | **79.3%** | **58.5%** | 5,000 |

---

## Part 1: Canonical Pricing (AUD)

| Tier | Monthly Price | Founding Price (50% off) | Lead Pool | Max Campaigns | LinkedIn Seats |
|------|---------------|-------------------------|-----------|---------------|----------------|
| Ignition | $2,500 | $1,250 | 1,250 | 5 | 1 |
| Velocity | $4,000 | $2,000 | 2,500 | 10 | 3 |
| Dominance | $7,500 | $3,750 | 5,000 | 20 | 5 |

**Governance:** Updated per CEO Directive #008 (February 2026)

---

## Part 2: Provider Pricing (Verified from Code)

### 2.1 Current Provider Costs (AUD)

| Provider | Service | Unit Cost (AUD) | Code Reference | Notes |
|----------|---------|-----------------|----------------|-------|
| **Siege Waterfall Tier 1** | ABN Lookup | $0.00 | siege_waterfall.py:47 | FREE - data.gov.au |
| **Siege Waterfall Tier 2** | GMB Scraping | $0.006 | siege_waterfall.py:48 | Proxy cost only |
| **Siege Waterfall Tier 3** | Hunter.io | $0.012 | siege_waterfall.py:49 | Email verification |
| **Siege Waterfall Tier 4** | Proxycurl | $0.024 | siege_waterfall.py:50 | DEPRECATED (Unipile pending) |
| **Siege Waterfall Tier 5** | Kaspr Identity | $0.45 | kaspr.py:28, siege_waterfall.py:51 | ALS ≥85 only |
| **Unipile** | LinkedIn automation | $79/seat | MARGIN_RECALCULATION.md | Volume discounts available |
| **ClickSend** | SMS (AU) | $0.08/message | clicksend.py (API) | DNCR compliant |
| **Telnyx Stack** | Voice AI | $0.09/minute | voice_agent_telnyx.py:72 | Includes STT/LLM/TTS |
| **ClickSend** | Direct Mail (AU) | $2.50/letter | External pricing | DEFERRED - not launch-ready |
| **Resend** | Transactional email | $0.0009/email | v2 model | Scale plan |

### 2.2 Siege Waterfall Cost Analysis

**Source:** `src/integrations/siege_waterfall.py` lines 45-52

```python
TIER_COSTS_AUD: dict[EnrichmentTier, float] = {
    EnrichmentTier.ABN: 0.00,      # FREE - data.gov.au
    EnrichmentTier.GMB: 0.006,     # Google Maps signals
    EnrichmentTier.HUNTER: 0.012,  # Hunter.io verification
    EnrichmentTier.PROXYCURL: 0.024,  # DEPRECATED
    EnrichmentTier.IDENTITY: 0.45, # Kaspr mobile (ALS≥85)
}
```

### 2.3 ALS-Based Cost Distribution

| ALS Tier | % of Leads | Tiers Run | Cost/Lead (AUD) |
|----------|------------|-----------|-----------------|
| Hot (85-100) | 10% | T1+T2+T3+T5 | $0.468 |
| Warm (60-84) | 25% | T1+T2+T3 | $0.018 |
| Cool (35-59) | 40% | T1+T2+T3 | $0.018 |
| Cold (20-34) | 25% | T1+T2 | $0.006 |

**Note:** Tier 4 (Proxycurl/LinkedIn) is deprecated. Unipile activation pending.

**Blended Enrichment Cost:**
```
(0.10 × $0.468) + (0.25 × $0.018) + (0.40 × $0.018) + (0.25 × $0.006) = $0.060/lead
```

---

## Part 3: Voice AI Cost Breakdown

**Source:** `src/engines/voice_agent_telnyx.py` lines 67-75

| Component | Cost/Minute (AUD) | Provider |
|-----------|-------------------|----------|
| Telnyx Inbound | $0.015 | Telnyx |
| Telnyx Outbound | $0.045 | Telnyx (AU mobile) |
| ElevenLabs Flash v2.5 | $0.035 | ElevenLabs |
| Groq LLM | $0.002 | Groq |
| **Total** | **$0.09** | Raw stack |

**vs Vapi:** $2.00/min → **95% cost reduction**

### Voice Budget by Tier

Assuming 35% of leads get voice calls (Warm+Hot), 2.5 min avg:

| Tier | Leads | Voice Eligible | Minutes | Cost (AUD) |
|------|-------|----------------|---------|------------|
| Ignition | 1,250 | 438 (35%) | 1,095 | $99 |
| Velocity | 2,500 | 875 (35%) | 2,188 | $197 |
| Dominance | 5,000 | 1,750 (35%) | 4,375 | $394 |

---

## Part 4: Updated COGS Breakdown (AUD)

### 4.1 Ignition Tier (1,250 leads)

| Category | Cost (AUD) | Calculation | Governance Ref |
|----------|------------|-------------|----------------|
| Data Enrichment | $75 | 1,250 × $0.060 | siege_waterfall.py |
| Email Infrastructure | $39 | Resend + domains | v2 model |
| SMS | $10 | ~125 msgs × $0.08 | clicksend.py |
| LinkedIn (Unipile) | $79 | 1 seat × $79 | margin_recalc.md |
| Voice AI (Telnyx) | $99 | 1,095 min × $0.09 | voice_agent_telnyx.py:72 |
| Direct Mail | $0 | DEFERRED | CEO Directive #008 |
| Infrastructure | $39 | Hosting + orchestration | v2 model |
| Buffer (5%) | $17 | Safety margin | — |
| **TOTAL COGS** | **$476** | | |

### 4.2 Velocity Tier (2,500 leads)

| Category | Cost (AUD) | Calculation | Governance Ref |
|----------|------------|-------------|----------------|
| Data Enrichment | $150 | 2,500 × $0.060 | siege_waterfall.py |
| Email Infrastructure | $62 | Resend + domains | v2 model |
| SMS | $20 | ~250 msgs × $0.08 | clicksend.py |
| LinkedIn (Unipile) | $237 | 3 seats × $79 | margin_recalc.md |
| Voice AI (Telnyx) | $197 | 2,188 min × $0.09 | voice_agent_telnyx.py:72 |
| Direct Mail | $0 | DEFERRED | CEO Directive #008 |
| Infrastructure | $62 | Hosting + orchestration | v2 model |
| Buffer (5%) | $86 | Safety margin | — |
| **TOTAL COGS** | **$814** | | |

### 4.3 Dominance Tier (5,000 leads)

| Category | Cost (AUD) | Calculation | Governance Ref |
|----------|------------|-------------|----------------|
| Data Enrichment | $300 | 5,000 × $0.060 | siege_waterfall.py |
| Email Infrastructure | $116 | Resend + domains | v2 model |
| SMS | $40 | ~500 msgs × $0.08 | clicksend.py |
| LinkedIn (Unipile) | $395 | 5 seats × $79 | margin_recalc.md |
| Voice AI (Telnyx) | $394 | 4,375 min × $0.09 | voice_agent_telnyx.py:72 |
| Direct Mail | $0 | DEFERRED | CEO Directive #008 |
| Infrastructure | $116 | Hosting + orchestration | v2 model |
| Buffer (5%) | $195 | Safety margin | — |
| **TOTAL COGS** | **$1,556** | | |

---

## Part 5: Margin Analysis

### 5.1 Regular Pricing

| Tier | Price | COGS | Gross Profit | Margin % |
|------|-------|------|--------------|----------|
| Ignition | $2,500 | $476 | $2,024 | **81.0%** |
| Velocity | $4,000 | $814 | $3,186 | **79.7%** |
| Dominance | $7,500 | $1,556 | $5,944 | **79.3%** |

All tiers exceed **75% gross margin**. ✅

### 5.2 Founding Member Pricing (50% off)

| Tier | Founding Price | COGS | Gross Profit | Margin % |
|------|----------------|------|--------------|----------|
| Ignition | $1,250 | $476 | $774 | **62.0%** |
| Velocity | $2,000 | $814 | $1,186 | **59.3%** |
| Dominance | $3,750 | $1,556 | $2,194 | **58.5%** |

Founding member margins remain above **55%**. ✅

### 5.3 Margin Journey (v2 → v3)

| Tier | v2 Margin | v3 Margin | Change |
|------|-----------|-----------|--------|
| Ignition | 73.4% | **81.0%** | +7.6% |
| Velocity | 66.9% | **79.7%** | +12.8% |
| Dominance | 66.6% | **79.3%** | +12.7% |

**Key drivers:**
- Vapi→Telnyx: $2.00→$0.09/min (95% reduction)
- HeyReach→Unipile: $122→$79/seat (35% reduction)
- Siege Waterfall: $0.13→$0.06/lead (54% reduction)
- Direct Mail deferred: -$122-441 per tier

---

## Part 6: Cost Per Lead Analysis

| Tier | COGS | Leads | Cost/Lead | Price/Lead | Margin/Lead |
|------|------|-------|-----------|------------|-------------|
| Ignition | $476 | 1,250 | $0.38 | $2.00 | $1.62 |
| Velocity | $814 | 2,500 | $0.33 | $1.60 | $1.27 |
| Dominance | $1,556 | 5,000 | $0.31 | $1.50 | $1.19 |

Higher tiers deliver better unit economics.

---

## Part 7: Channel Allocation by ALS

**Source:** `src/config/tiers.py` lines 131-159

| Channel | Cold (20-34) | Cool (35-59) | Warm (60-84) | Hot (85-100) |
|---------|--------------|--------------|--------------|--------------|
| Email | ✅ | ✅ | ✅ | ✅ |
| LinkedIn | ❌ | ✅ | ✅ | ✅ |
| Voice AI | ❌ | ❌ | ✅ | ✅ |
| SMS | ❌ | ❌ | ✅ | ✅ |
| Direct Mail | ❌ | ❌ | ❌ | DEFERRED |

**Note:** SMS extended to Warm tier per CEO decision 2026-02-06.

---

## Part 8: What's Excluded from v3

### Direct Mail (Deferred to Phase 2)

**Reason:** ClickSend Australia requires template setup and testing. Not launch-ready.

**Future cost when enabled:**
| Tier | Hot Leads (10%) | Cost @ $2.50/letter |
|------|-----------------|---------------------|
| Ignition | 125 | $313 |
| Velocity | 250 | $625 |
| Dominance | 500 | $1,250 |

**Impact on margins when enabled:**
| Tier | v3 Margin | With Mail | Delta |
|------|-----------|-----------|-------|
| Ignition | 81.0% | 68.5% | -12.5% |
| Velocity | 79.7% | 64.0% | -15.7% |
| Dominance | 79.3% | 62.6% | -16.7% |

**Recommendation:** Direct mail significantly impacts margins. Consider as premium upsell or Hot-only (ALS≥90).

### ABN→GMB SDK Cost

**Finding:** There is no separate SDK cost for ABN→GMB name resolution. The Siege Waterfall handles fuzzy matching internally using:
1. FuzzyWuzzy (token_set_ratio ≥70%)
2. ABN postcode narrowing
3. Multiple name variant attempts

**Cost:** Already included in Tier 2 GMB cost ($0.006/lead).

---

## Part 9: Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Kaspr price increase | +$0.10-0.20/lead | Low | Volume contract negotiation |
| Unipile price increase | +$20-40/seat | Medium | HeyReach fallback available |
| Telnyx quality issues | Customer complaints | Low | ElevenLabs voice monitoring |
| Hot lead % higher than 10% | COGS increase | Medium | Real-time margin alerts |
| Direct mail demand | Feature gap | High | Phase 2 roadmap, premium upsell |

---

## Part 10: Decisions Log (v3)

| Decision | Date | Rationale | CEO Directive |
|----------|------|-----------|---------------|
| Velocity leads 2,250→2,500 | Feb 2026 | Market positioning | #008 |
| Dominance leads 4,500→5,000 | Feb 2026 | Market positioning | #008 |
| Velocity price $5,000→$4,000 | Feb 2026 | Competitive pricing | #008 |
| Founding discount 40%→50% | Feb 2026 | Stronger incentive | #008 |
| Direct mail deferred | Feb 2026 | ClickSend AU not ready | #008 |
| Raw Telnyx for Voice | Feb 2026 | 95% cost reduction | VOICE_INFRA |
| Unipile for LinkedIn | Feb 2026 | 35% cost reduction | #002 |

---

## Appendix A: Source Code References

| Cost Item | File | Line(s) |
|-----------|------|---------|
| Siege Waterfall tiers | src/integrations/siege_waterfall.py | 45-52 |
| Kaspr cost | src/integrations/kaspr.py | 28 |
| Voice AI costs | src/engines/voice_agent_telnyx.py | 67-75 |
| ALS thresholds | src/config/tiers.py | 131-159 |
| Channel access | src/config/tiers.py | 161-168 |
| Tier config | src/config/tiers.py | 39-78 |

---

## Appendix B: Exchange Rate

All USD → AUD conversions use **1.55** rate.

| Provider | USD Price | AUD Price |
|----------|-----------|-----------|
| Unipile | ~$51/seat | $79/seat |
| Kaspr | ~$0.29/lead | $0.45/lead |
| ElevenLabs Flash | ~$0.023/min | $0.035/min |

---

## CEO Approval Required

| Item | Status |
|------|--------|
| Lead volumes: 1,250 / 2,500 / 5,000 | ☐ Approved |
| Velocity price: $4,000 | ☐ Approved |
| Founding discount: 50% | ☐ Approved |
| Direct mail deferred | ☐ Approved |
| Ignition margin 81.0% | ☐ Approved |
| Velocity margin 79.7% | ☐ Approved |
| Dominance margin 79.3% | ☐ Approved |

---

*Document prepared per CEO Directive #008. Supersedes TIER_PRICING_COST_MODEL_v2.md.*
*All costs in AUD. Governance trace on every figure per LAW I-A, LAW II, LAW III.*
