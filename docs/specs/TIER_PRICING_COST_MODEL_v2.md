# Agency OS Tier Pricing & Cost Model v2

**Document Type:** Financial Analysis  
**Version:** 2.0  
**Date:** January 2026  
**Author:** CTO Office  
**Status:** APPROVED  
**Currency:** AUD (Australian Dollars) — NO USD IN THIS DOCUMENT

---

## Executive Summary

This document defines the canonical pricing, COGS, and margin model for Agency OS. All figures have been verified against current provider pricing as of January 2026.

**Key Changes from v1:**
- Updated all provider costs to current pricing (AUD)
- Implemented hybrid Clay waterfall enrichment strategy
- Reduced Dominance HeyReach seats from 10 → 5
- All margins now exceed 65%

| Tier | Price | COGS | Margin | Leads |
|------|-------|------|--------|-------|
| **Ignition** | $2,500 | $666 | **73.4%** | 1,250 |
| **Velocity** | $4,000 | $1,323 | **66.9%** | 2,250 |
| **Dominance** | $7,500 | $2,502 | **66.6%** | 4,500 |

---

## Part 1: Canonical Pricing (AUD)

| Tier | Monthly Price | Lead Pool | Max Campaigns | HeyReach Seats |
|------|---------------|-----------|---------------|----------------|
| Ignition | $2,500 | 1,250 | 5 | 1 |
| Velocity | $4,000 | 2,250 | 10 | 3 |
| Dominance | $7,500 | 4,500 | 20 | **5** |

---

## Part 2: Provider Pricing (Verified January 2026)

### 2.1 Current Provider Costs (AUD)

| Provider | Service | Unit Cost (AUD) | Notes |
|----------|---------|-----------------|-------|
| **HeyReach** | LinkedIn automation | $122/seat | $79 USD × 1.55 |
| **Hunter.io** | Email lookup | $0.023/email | Tier 1 waterfall |
| **Prospeo** | Email fallback | $0.031/email | Tier 2 waterfall |
| **Clay** | Full enrichment | $0.039-0.077/credit | Pro plan |
| **Twilio SMS** | Australia outbound | $0.08/message | Standard rate |
| **Vapi** | Voice AI (all-in) | $0.35/minute | Includes STT/TTS/LLM/telephony |
| **Lob** | Direct mail postcard | $0.98/postcard | US only, Growth tier |
| **Resend** | Transactional email | $0.0009/email | Scale plan |

### 2.2 Comparison to MASTER_SPEC v1

| Provider | v1 Cost | Actual Cost | Variance |
|----------|---------|-------------|----------|
| HeyReach | $76/seat | $122/seat | **+61%** |
| Apollo | $0.155/lead | $0.31/lead | **+100%** |
| Vapi | $0.186/min | $0.35/min | **+88%** |
| Twilio SMS | $0.08/msg | $0.08/msg | ✅ OK |
| Lob | $0.98/pc | $0.98/pc | ✅ OK |
| Resend | ~$0.001 | ~$0.001 | ✅ OK |

---

## Part 3: Hybrid Clay Waterfall Enrichment

### 3.1 Strategy

Instead of using Apollo for all leads at $0.31/lead, we implement a hybrid waterfall:

1. **Cold/Cool leads (65%):** Hunter.io direct — $0.02/lead
2. **Warm/Hot leads (35%):** Clay full waterfall — $0.25-0.50/lead

Clay's built-in waterfall automatically cascades through 75+ providers:
- Free sources first (LinkedIn scrape, company website)
- Cheap email providers (Hunter, Prospeo, Dropcontact)
- Premium fallback (Apollo, Clearbit) only if needed
- Mobile numbers only for Hot leads

### 3.2 Credit Consumption by ALS Tier

| ALS Tier | % of Leads | Clay Credits | Cost/Lead (AUD) |
|----------|------------|--------------|-----------------|
| Hot (85-100) | 10% | 15 | $0.50 |
| Warm (60-84) | 25% | 8 | $0.25 |
| Cool (35-59) | 40% | — | $0.02 (Hunter direct) |
| Cold (20-34) | 25% | — | $0.02 (Hunter direct) |

**Blended cost:** (0.10×$0.50) + (0.25×$0.25) + (0.40×$0.02) + (0.25×$0.02) = **$0.13/lead**

### 3.3 Enrichment Cost by Tier

| Tier | Leads | Blended Rate | Enrichment Cost |
|------|-------|--------------|-----------------|
| Ignition | 1,250 | $0.13 | **$163** |
| Velocity | 2,250 | $0.13 | **$293** |
| Dominance | 4,500 | $0.13 | **$585** |

---

## Part 4: Updated COGS Breakdown (AUD)

### 4.1 Ignition Tier (1,250 leads)

| Category | Cost | Calculation |
|----------|------|-------------|
| Data Enrichment | $163 | 1,250 × $0.13 (hybrid waterfall) |
| Email Infrastructure | $39 | Resend + domains |
| SMS | $10 | ~125 messages × $0.08 |
| LinkedIn (HeyReach) | $122 | 1 seat × $122 |
| Voice AI | $164 | 469 min × $0.35 |
| Direct Mail | $122 | 125 postcards × $0.98 |
| Webhook Infrastructure | $8 | Hosting |
| Prefect/Infrastructure | $39 | Orchestration |
| **TOTAL COGS** | **$666** | |

### 4.2 Velocity Tier (2,250 leads)

| Category | Cost | Calculation |
|----------|------|-------------|
| Data Enrichment | $293 | 2,250 × $0.13 |
| Email Infrastructure | $62 | Resend + domains |
| SMS | $18 | ~225 messages × $0.08 |
| LinkedIn (HeyReach) | $366 | 3 seats × $122 |
| Voice AI | $295 | 844 min × $0.35 |
| Direct Mail | $220 | 225 postcards × $0.98 |
| Webhook Infrastructure | $12 | Hosting |
| Prefect/Infrastructure | $62 | Orchestration |
| **TOTAL COGS** | **$1,323** | |

### 4.3 Dominance Tier (4,500 leads)

| Category | Cost | Calculation |
|----------|------|-------------|
| Data Enrichment | $585 | 4,500 × $0.13 |
| Email Infrastructure | $116 | Resend + domains |
| SMS | $36 | ~450 messages × $0.08 |
| LinkedIn (HeyReach) | $610 | **5 seats** × $122 |
| Voice AI | $591 | 1,688 min × $0.35 |
| Direct Mail | $441 | 450 postcards × $0.98 |
| Webhook Infrastructure | $23 | Hosting |
| Prefect/Infrastructure | $116 | Orchestration |
| **TOTAL COGS** | **$2,502** | |

---

## Part 5: Margin Analysis

| Tier | Price | COGS | Gross Profit | Margin % |
|------|-------|------|--------------|----------|
| Ignition | $2,500 | $666 | $1,834 | **73.4%** |
| Velocity | $4,000 | $1,323 | $2,677 | **66.9%** |
| Dominance | $7,500 | $2,502 | $4,998 | **66.6%** |

All tiers now exceed **65% gross margin**. ✅

### 5.1 Margin Journey

| Tier | MASTER_SPEC v1 | After Provider Update | **Final (Waterfall)** |
|------|----------------|----------------------|----------------------|
| Ignition | 76.9% | 64.4% | **73.4%** |
| Velocity | 72.3% | 56.8% | **66.9%** |
| Dominance | 66.7% | 47.7% | **66.6%** |

---

## Part 6: Cost Per Lead Analysis

| Tier | COGS | Leads | Cost/Lead | Price/Lead |
|------|------|-------|-----------|------------|
| Ignition | $666 | 1,250 | $0.53 | $2.00 |
| Velocity | $1,323 | 2,250 | $0.59 | $1.78 |
| Dominance | $2,502 | 4,500 | $0.56 | $1.67 |

Higher tiers deliver better value per lead — incentivises upgrades.

---

## Part 7: Channel Allocation by ALS

### 7.1 Channel Access Rules

| Channel | Cold | Cool | Warm | Hot |
|---------|------|------|------|-----|
| Email | ✅ | ✅ | ✅ | ✅ |
| LinkedIn | ❌ | ✅ | ✅ | ✅ |
| Voice AI | ❌ | ❌ | ✅ | ✅ |
| SMS | ❌ | ❌ | ❌ | ✅ |
| Direct Mail | ❌ | ❌ | ❌ | ✅ |

### 7.2 Voice Minutes Budget

| Tier | Budget | Rate | Minutes | Calls (2.5min avg) |
|------|--------|------|---------|-------------------|
| Ignition | $164 | $0.35 | 469 | ~188 |
| Velocity | $295 | $0.35 | 844 | ~338 |
| Dominance | $591 | $0.35 | 1,688 | ~675 |

### 7.3 Direct Mail Budget

| Tier | Budget | Rate | Postcards | Hot Leads | Coverage |
|------|--------|------|-----------|-----------|----------|
| Ignition | $122 | $0.98 | 125 | 125 | 100% |
| Velocity | $220 | $0.98 | 225 | 225 | 100% |
| Dominance | $441 | $0.98 | 450 | 450 | 100% |

---

## Part 8: Sensitivity Analysis

### 8.1 If Enrichment Costs Rise 50%

| Tier | Current COGS | +50% Enrichment | New Margin |
|------|--------------|-----------------|------------|
| Ignition | $666 | $748 | 70.1% ✅ |
| Velocity | $1,323 | $1,470 | 63.3% ⚠️ |
| Dominance | $2,502 | $2,795 | 62.7% ⚠️ |

**Mitigation:** Negotiate volume discounts with Clay at scale.

### 8.2 If Voice Costs Rise 50%

| Tier | Current COGS | +50% Voice | New Margin |
|------|--------------|------------|------------|
| Ignition | $666 | $748 | 70.1% ✅ |
| Velocity | $1,323 | $1,471 | 63.2% ⚠️ |
| Dominance | $2,502 | $2,798 | 62.7% ⚠️ |

**Mitigation:** Negotiate Vapi enterprise pricing or switch to Retell AI.

### 8.3 If HeyReach Raises Prices

| Tier | Current COGS | +25% HeyReach | New Margin |
|------|--------------|---------------|------------|
| Ignition | $666 | $697 | 72.1% ✅ |
| Velocity | $1,323 | $1,415 | 64.6% ⚠️ |
| Dominance | $2,502 | $2,655 | 64.6% ⚠️ |

**Mitigation:** HeyReach agency plan ($999/50 seats) at scale.

---

## Part 9: Competitive Comparison (AUD)

| Platform | Price/mo | Leads | Price/Lead | Channels |
|----------|----------|-------|------------|----------|
| **Agency OS Ignition** | $2,500 | 1,250 | $2.00 | ✅ All 5 |
| **Agency OS Velocity** | $4,000 | 2,250 | $1.78 | ✅ All 5 |
| **Agency OS Dominance** | $7,500 | 4,500 | $1.67 | ✅ All 5 |
| AiSDR Starter | ~$1,400 | 1,000 | $1.40 | ❌ Email only |
| AiSDR Pro | ~$3,100 | 3,000 | $1.03 | ❌ Email only |
| 11x.ai | ~$15,000+ | Custom | ~$3.00+ | ✅ Multi |
| Artisan | ~$3,500+ | 2,000 | $1.75 | ❌ Email + LinkedIn |

**Agency OS Advantage:**
- Only platform with 5-channel orchestration (Email, SMS, LinkedIn, Voice, Direct Mail)
- Australian market focus
- Agency-specific ICP and messaging
- Full-stack (enrichment → delivery → booking)

---

## Part 10: Implementation Notes

### 10.1 Database Schema Updates Required

```sql
-- Add waterfall enrichment tracking
ALTER TABLE leads ADD COLUMN enrichment_source VARCHAR(50);
ALTER TABLE leads ADD COLUMN enrichment_credits_used INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN enrichment_cost_aud DECIMAL(10,4);

-- Add tier configuration
ALTER TABLE clients ADD COLUMN heyreach_seats INTEGER DEFAULT 1;
```

### 10.2 Enrichment Waterfall Implementation

```python
async def enrich_lead(lead: Lead) -> EnrichedLead:
    """
    Hybrid waterfall enrichment strategy.
    Cold/Cool leads: Hunter direct
    Warm/Hot leads: Clay full waterfall
    """
    als_score = lead.als_score or 0
    
    if als_score < 60:  # Cold or Cool
        return await hunter_enrich(lead)
    else:  # Warm or Hot
        return await clay_waterfall_enrich(lead)
```

### 10.3 Margin Monitoring Dashboard

Real-time tracking required:
- Enrichment cost per lead (actual vs budget)
- Voice minutes consumed vs budget
- Direct mail pieces sent vs budget
- Blended COGS per client
- Alert if margin drops below 60%

---

## Part 11: Decisions Log

| Decision | Date | Rationale |
|----------|------|-----------|
| Reduce Dominance HeyReach 10→5 seats | Jan 2026 | Margin was 47.7%, now 66.6% |
| Implement hybrid Clay waterfall | Jan 2026 | Reduces enrichment cost 58% |
| Keep pricing unchanged | Jan 2026 | Market competitive, margins healthy |
| Lob US-only (no AU direct mail) | Jan 2026 | No AU API provider found |
| Bombora excluded | Jan 2026 | $30K/yr minimum not viable at launch |

---

## Part 12: Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Provider price increases | Margin erosion | Medium | Volume contracts, alternatives identified |
| ALS skews Hot (higher costs) | COGS overrun | Low | Real-time margin monitoring |
| Clay waterfall fails | Higher enrichment cost | Low | Fallback to Apollo direct |
| Voice quality issues | Customer complaints | Medium | Vapi monitoring + ElevenLabs fallback |
| AU direct mail needed | Feature gap | Medium | Research PostGrid, Stannp |

---

## Appendix A: Provider Account Requirements

| Provider | Plan Needed | Monthly Cost (AUD) | Setup |
|----------|-------------|-------------------|-------|
| HeyReach | Starter (per seat) | $122/seat | API key |
| Clay | Explorer 20k | $975 | API key + workspace |
| Hunter.io | Starter | $75 | API key |
| Twilio | Pay-as-you-go | Variable | Account SID + Auth Token |
| Vapi | Pay-as-you-go | Variable | API key |
| Lob | Growth | $550 platform + usage | API key |
| Resend | Scale | $140 | API key + domain verification |

---

## Appendix B: Fixed Infrastructure Costs (AUD)

| Service | Monthly Cost |
|---------|--------------|
| Supabase Pro | $39 |
| Vercel Pro | $31 |
| Railway | $31-78 |
| Prefect Cloud | $0 (self-hosted) |
| Upstash Redis | $16 |
| Cloudflare R2 | $8 |
| Sentry Team | $40 |
| Smartproxy Micro | $78 |
| **TOTAL** | **$243-290** |

At 20 clients: ~$12-15/client/month fixed overhead.

---

## Appendix C: Exchange Rate Assumption

All USD → AUD conversions use **1.55** rate.

| Provider | USD Price | AUD Price |
|----------|-----------|-----------|
| HeyReach | $79/seat | $122/seat |
| Clay Explorer 20k | $629/mo | $975/mo |
| Vapi | $0.05-0.20/min | $0.08-0.31/min |

---

*Document approved by CEO. Last updated January 2026.*
