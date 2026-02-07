> ⚠️ **DEPRECATED (FCO-002):** SDK has been replaced by Smart Prompts as of 2026-02-05.
> For current margin calculations, see: `MARGIN_RECALCULATION_POST_SIEGE.md`
> This document is retained for historical reference only.

# SDK Integration — Final P&L Model

**Document Type:** Comprehensive Financial Model
**For:** CEO Final Approval
**Date:** January 19, 2026
**Currency:** AUD
**Status:** FINAL

---

## Executive Summary

This document presents the complete Profit & Loss model for Agency OS subscription tiers with SDK integration using the CEO-approved hybrid model:

| Component | Treatment |
|-----------|-----------|
| SDK Enrichment | Selective (Hot + priority signals only) |
| SDK Email | ALL Hot leads (10%) |
| SDK Voice KB | ALL Hot leads (10%) |
| Dominance Pricing | Unchanged at $7,500 |

---

## 1. Subscription Tier Overview

| Tier | Monthly Price | Leads/Month | Meeting Guarantee |
|------|---------------|-------------|-------------------|
| Ignition | $2,500 | 1,250 | 10 meetings |
| Velocity | $4,000 | 2,250 | 25 meetings |
| Dominance | $7,500 | 4,500 | 60 meetings |

---

## 2. ALS Distribution Model

**Canonical distribution (approved):**

| ALS Tier | Score Range | Distribution |
|----------|-------------|--------------|
| Hot | 85-100 | 10% |
| Warm | 60-84 | 25% |
| Cool | 35-59 | 40% |
| Cold | 20-34 | 25% |

**Lead counts by subscription tier:**

| ALS Tier | Ignition (1,250) | Velocity (2,250) | Dominance (4,500) |
|----------|------------------|------------------|-------------------|
| Hot | 125 | 225 | 450 |
| Warm | 313 | 563 | 1,125 |
| Cool | 500 | 900 | 1,800 |
| Cold | 312 | 562 | 1,125 |

---

## 3. SDK Usage Model (CEO-Approved Hybrid)

### SDK Enrichment — Selective (Signals Only)

**Priority signals (ANY ONE qualifies):**
- Recent funding (< 90 days)
- Actively hiring (3+ roles)
- Tech stack match > 80%
- LinkedIn engagement > 70
- Referral source
- Employee count 50-500

**Expected signal rate:** 20% of Hot leads

| Tier | Hot Leads | SDK-Eligible (20%) | Standard Hot (80%) |
|------|-----------|--------------------|--------------------|
| Ignition | 125 | 25 | 100 |
| Velocity | 225 | 45 | 180 |
| Dominance | 450 | 90 | 360 |

### SDK Email & Voice — ALL Hot Leads

| Tier | SDK Email | SDK Voice KB |
|------|-----------|--------------|
| Ignition | 125 (all Hot) | 125 (all Hot) |
| Velocity | 225 (all Hot) | 225 (all Hot) |
| Dominance | 450 (all Hot) | 450 (all Hot) |

---

## 4. Unit Cost Reference (Verified Online)

### Lead Acquisition & Enrichment

| Item | Cost | Source | Verification |
|------|------|--------|--------------|
| Apollo credit | $0.31 | Apollo.io | Verified 2026-01-19 |
| Clay enrichment (Hot/Warm) | $0.12 | Clay.com | 12 credits @ $0.01/credit |
| Hunter email verify | $0.036 | Hunter.io | Verified 2026-01-19 |
| Apify LinkedIn scrape | $0.0047 | Apify.com | Verified 2026-01-19 |

### SDK Costs (Anthropic)

| Item | Cost | Model | Calculation |
|------|------|-------|-------------|
| SDK Enrichment | $1.21 | Claude 3.5 Sonnet | ~4,000 input + 2,000 output tokens |
| SDK Email | $0.25 | Claude 3.5 Sonnet | ~1,500 input + 500 output tokens |
| SDK Voice KB | $1.79 | Claude 3.5 Sonnet | ~6,000 input + 3,000 output tokens |
| SDK Objection | $0.25 | Claude 3.5 Sonnet | ~1,500 input + 500 output tokens |

### Standard AI Costs (Non-SDK)

| Item | Cost | Model |
|------|------|-------|
| Claude analysis | $0.08 | Haiku |
| Template email | $0.03 | Haiku |
| Template LinkedIn | $0.02 | Haiku |
| Template SMS | $0.02 | Haiku |
| Static Voice KB | $0.20 | Haiku |
| Reply classification | $0.08 | Haiku |

### Channel Delivery Costs

| Channel | Cost | Provider |
|---------|------|----------|
| Email send | $0.01 | Salesforge (included) |
| LinkedIn message | $0.00 | Unipile (flat rate) |
| SMS send | $0.072 | ClickSend |
| Voice call (2.5 min avg) | $0.88 | Vapi stack |
| Direct mail postcard | $0.82 | ClickSend |

### Infrastructure (Monthly)

| Item | Cost | Notes |
|------|------|-------|
| Railway (backend) | $50 | Pro plan |
| Supabase (database) | $25 | Pro plan |
| Vercel (frontend) | $20 | Pro plan |
| Upstash Redis | $10 | Pay-as-you-go |
| Prefect Cloud | $0 | Self-hosted |
| Monitoring (Sentry) | $26 | Team plan |
| Email infrastructure | $50 | Salesforge base |
| LinkedIn (Unipile) | $99 | Per seat |
| Voice (Vapi base) | $20 | Platform fee |
| **Total Infrastructure** | **$300** | Per month base |

---

## 5. Per-Lead COGS Breakdown

### Hot Lead — SDK Eligible (with signals)

| Line Item | Cost | Notes |
|-----------|------|-------|
| Apollo acquisition | $0.31 | 1 credit |
| Clay enrichment | $0.12 | 12 credits |
| Apify LinkedIn scrape | $0.005 | Profile scrape |
| **SDK Enrichment** | **$1.21** | Deep research |
| **SDK Email generation** | **$0.25** | Personalized |
| Email send | $0.01 | Salesforge |
| LinkedIn message (SDK) | $0.12 | Personalized |
| SMS content (SDK) | $0.08 | Personalized |
| SMS send | $0.072 | ClickSend |
| **SDK Voice KB** | **$1.79** | Custom knowledge base |
| Voice call | $0.88 | Vapi 2.5 min |
| Direct mail | $0.82 | ClickSend postcard |
| **TOTAL (SDK Hot)** | **$5.67** | |

### Hot Lead — Standard (no signals)

| Line Item | Cost | Notes |
|-----------|------|-------|
| Apollo acquisition | $0.31 | 1 credit |
| Clay enrichment | $0.12 | 12 credits |
| Apify LinkedIn scrape | $0.005 | Profile scrape |
| Claude analysis | $0.08 | Standard enrichment |
| **SDK Email generation** | **$0.25** | Personalized (ALL Hot) |
| Email send | $0.01 | Salesforge |
| LinkedIn message (template) | $0.02 | Standard |
| SMS content (template) | $0.02 | Standard |
| SMS send | $0.072 | ClickSend |
| **SDK Voice KB** | **$1.79** | Custom KB (ALL Hot) |
| Voice call | $0.88 | Vapi 2.5 min |
| Direct mail | $0.82 | ClickSend postcard |
| **TOTAL (Standard Hot)** | **$4.37** | |

### Warm Lead (ALS 60-84)

| Line Item | Cost | Notes |
|-----------|------|-------|
| Apollo acquisition | $0.31 | 1 credit |
| Clay enrichment | $0.08 | 8 credits |
| Apify LinkedIn scrape | $0.005 | Profile scrape |
| Claude analysis | $0.08 | Standard |
| Template email | $0.03 | Haiku |
| Email send | $0.01 | Salesforge |
| LinkedIn message | $0.02 | Template |
| Voice call | $0.88 | Vapi 2.5 min |
| **TOTAL (Warm)** | **$1.42** | |

### Cool Lead (ALS 35-59)

| Line Item | Cost | Notes |
|-----------|------|-------|
| Apollo acquisition | $0.29 | 1 credit |
| Hunter email verify | $0.036 | Verification |
| Apify LinkedIn scrape | $0.005 | Profile scrape |
| Template email | $0.03 | Haiku |
| Email send | $0.01 | Salesforge |
| LinkedIn message | $0.02 | Template |
| **TOTAL (Cool)** | **$0.39** | |

### Cold Lead (ALS 20-34)

| Line Item | Cost | Notes |
|-----------|------|-------|
| Apollo acquisition | $0.25 | 1 credit |
| Hunter email verify | $0.036 | Verification |
| Template email | $0.03 | Haiku |
| Email send | $0.01 | Salesforge |
| **TOTAL (Cold)** | **$0.33** | |

---

## 6. IGNITION TIER — Complete P&L

### Revenue
| Item | Amount |
|------|--------|
| Monthly subscription | $2,500 |
| **Total Revenue** | **$2,500** |

### Cost of Goods Sold (COGS)

#### Lead Processing Costs
| Category | Leads | Per-Lead | Subtotal |
|----------|-------|----------|----------|
| Hot (SDK eligible) | 25 | $5.67 | $142 |
| Hot (Standard) | 100 | $4.37 | $437 |
| Warm | 313 | $1.42 | $444 |
| Cool | 500 | $0.39 | $195 |
| Cold | 312 | $0.33 | $103 |
| **Lead Processing Total** | **1,250** | | **$1,321** |

#### Infrastructure Allocation
| Item | Calculation | Amount |
|------|-------------|--------|
| Base infrastructure | $300 × (1,250/8,000) | $47 |
| LinkedIn seats | $99 × 0.25 | $25 |
| Salesforge mailboxes | $50 × 0.20 | $10 |
| **Infrastructure Total** | | **$82** |

#### Reply Handling (Estimated)
| Item | Volume | Per-Unit | Amount |
|------|--------|----------|--------|
| Reply classification | 94 (7.5% rate) | $0.08 | $8 |
| Simple objections | 21 (30% × 75%) | $0.08 | $2 |
| Complex objections (SDK) | 7 (30% × 25%) | $0.25 | $2 |
| **Reply Handling Total** | | | **$12** |

### Ignition P&L Summary

| Line Item | Amount | % of Revenue |
|-----------|--------|--------------|
| **Revenue** | **$2,500** | 100.0% |
| | | |
| Lead Processing | $1,321 | 52.8% |
| Infrastructure | $82 | 3.3% |
| Reply Handling | $12 | 0.5% |
| **Total COGS** | **$1,415** | **56.6%** |
| | | |
| **Gross Profit** | **$1,085** | **43.4%** |

---

## 7. VELOCITY TIER — Complete P&L

### Revenue
| Item | Amount |
|------|--------|
| Monthly subscription | $4,000 |
| **Total Revenue** | **$4,000** |

### Cost of Goods Sold (COGS)

#### Lead Processing Costs
| Category | Leads | Per-Lead | Subtotal |
|----------|-------|----------|----------|
| Hot (SDK eligible) | 45 | $5.67 | $255 |
| Hot (Standard) | 180 | $4.37 | $787 |
| Warm | 563 | $1.42 | $799 |
| Cool | 900 | $0.39 | $351 |
| Cold | 562 | $0.33 | $185 |
| **Lead Processing Total** | **2,250** | | **$2,377** |

#### Infrastructure Allocation
| Item | Calculation | Amount |
|------|-------------|--------|
| Base infrastructure | $300 × (2,250/8,000) | $84 |
| LinkedIn seats | $99 × 0.75 | $74 |
| Salesforge mailboxes | $50 × 0.40 | $20 |
| **Infrastructure Total** | | **$178** |

#### Reply Handling (Estimated)
| Item | Volume | Per-Unit | Amount |
|------|--------|----------|--------|
| Reply classification | 169 (7.5% rate) | $0.08 | $14 |
| Simple objections | 38 (30% × 75%) | $0.08 | $3 |
| Complex objections (SDK) | 13 (30% × 25%) | $0.25 | $3 |
| **Reply Handling Total** | | | **$20** |

### Velocity P&L Summary

| Line Item | Amount | % of Revenue |
|-----------|--------|--------------|
| **Revenue** | **$4,000** | 100.0% |
| | | |
| Lead Processing | $2,377 | 59.4% |
| Infrastructure | $178 | 4.5% |
| Reply Handling | $20 | 0.5% |
| **Total COGS** | **$2,575** | **64.4%** |
| | | |
| **Gross Profit** | **$1,425** | **35.6%** |

---

## 8. DOMINANCE TIER — Complete P&L

### Revenue
| Item | Amount |
|------|--------|
| Monthly subscription | $7,500 |
| **Total Revenue** | **$7,500** |

### Cost of Goods Sold (COGS)

#### Lead Processing Costs
| Category | Leads | Per-Lead | Subtotal |
|----------|-------|----------|----------|
| Hot (SDK eligible) | 90 | $5.67 | $510 |
| Hot (Standard) | 360 | $4.37 | $1,573 |
| Warm | 1,125 | $1.42 | $1,598 |
| Cool | 1,800 | $0.39 | $702 |
| Cold | 1,125 | $0.33 | $371 |
| **Lead Processing Total** | **4,500** | | **$4,754** |

#### Infrastructure Allocation
| Item | Calculation | Amount |
|------|-------------|--------|
| Base infrastructure | $300 × (4,500/8,000) | $169 |
| LinkedIn seats | $99 × 1.25 | $124 |
| Salesforge mailboxes | $50 × 0.60 | $30 |
| **Infrastructure Total** | | **$323** |

#### Reply Handling (Estimated)
| Item | Volume | Per-Unit | Amount |
|------|--------|----------|--------|
| Reply classification | 338 (7.5% rate) | $0.08 | $27 |
| Simple objections | 76 (30% × 75%) | $0.08 | $6 |
| Complex objections (SDK) | 25 (30% × 25%) | $0.25 | $6 |
| **Reply Handling Total** | | | **$39** |

### Dominance P&L Summary

| Line Item | Amount | % of Revenue |
|-----------|--------|--------------|
| **Revenue** | **$7,500** | 100.0% |
| | | |
| Lead Processing | $4,754 | 63.4% |
| Infrastructure | $323 | 4.3% |
| Reply Handling | $39 | 0.5% |
| **Total COGS** | **$5,116** | **68.2%** |
| | | |
| **Gross Profit** | **$2,384** | **31.8%** |

---

## 9. Consolidated P&L — All Tiers

### Revenue by Tier

| Tier | Price | Projected Customers (Y1) | Monthly Revenue |
|------|-------|--------------------------|-----------------|
| Ignition | $2,500 | 40% | Variable |
| Velocity | $4,000 | 45% | Variable |
| Dominance | $7,500 | 15% | Variable |

### Per-Customer Economics

| Metric | Ignition | Velocity | Dominance |
|--------|----------|----------|-----------|
| Revenue | $2,500 | $4,000 | $7,500 |
| COGS | $1,415 | $2,575 | $5,116 |
| **Gross Profit** | **$1,085** | **$1,425** | **$2,384** |
| **Gross Margin** | **43.4%** | **35.6%** | **31.8%** |

### Blended Economics (Weighted by Customer Mix)

| Metric | Calculation | Amount |
|--------|-------------|--------|
| Blended Revenue | (0.40 × $2,500) + (0.45 × $4,000) + (0.15 × $7,500) | $3,925 |
| Blended COGS | (0.40 × $1,415) + (0.45 × $2,575) + (0.15 × $5,116) | $2,492 |
| **Blended Gross Profit** | | **$1,433** |
| **Blended Gross Margin** | | **36.5%** |

---

## 10. SDK Cost Impact Analysis

### SDK Spend by Tier

| Tier | SDK Enrichment | SDK Email | SDK Voice | Total SDK |
|------|----------------|-----------|-----------|-----------|
| Ignition | $30 (25 leads) | $31 (125 leads) | $224 (125 leads) | **$285** |
| Velocity | $54 (45 leads) | $56 (225 leads) | $403 (225 leads) | **$513** |
| Dominance | $109 (90 leads) | $113 (450 leads) | $806 (450 leads) | **$1,028** |

### SDK as % of COGS

| Tier | Total COGS | SDK Cost | SDK % of COGS |
|------|------------|----------|---------------|
| Ignition | $1,415 | $285 | 20.1% |
| Velocity | $2,575 | $513 | 19.9% |
| Dominance | $5,116 | $1,028 | 20.1% |

### SDK as % of Revenue

| Tier | Revenue | SDK Cost | SDK % of Revenue |
|------|---------|----------|------------------|
| Ignition | $2,500 | $285 | 11.4% |
| Velocity | $4,000 | $513 | 12.8% |
| Dominance | $7,500 | $1,028 | 13.7% |

---

## 11. Comparison: With SDK vs Without SDK

### Velocity Tier Comparison

| Line Item | Without SDK | With SDK | Delta |
|-----------|-------------|----------|-------|
| Revenue | $4,000 | $4,000 | — |
| Lead Processing | $1,864 | $2,377 | +$513 |
| Infrastructure | $178 | $178 | — |
| Reply Handling | $17 | $20 | +$3 |
| **Total COGS** | **$2,059** | **$2,575** | **+$516** |
| **Gross Profit** | **$1,941** | **$1,425** | **-$516** |
| **Gross Margin** | **48.5%** | **35.6%** | **-12.9%** |

### All Tiers Comparison

| Tier | Margin (No SDK) | Margin (With SDK) | Delta |
|------|-----------------|-------------------|-------|
| Ignition | 57.2% | 43.4% | -13.8% |
| Velocity | 48.5% | 35.6% | -12.9% |
| Dominance | 49.2% | 31.8% | -17.4% |

---

## 12. Sensitivity Analysis

### If Hot Lead % Increases (LinkedIn Boost Effect)

| Hot % | Velocity COGS | Velocity Margin |
|-------|---------------|-----------------|
| 10% (base) | $2,575 | 35.6% |
| 12% | $2,776 | 30.6% |
| 15% | $3,078 | 23.1% |
| 20% | $3,582 | 10.5% |

### If SDK Signal Rate Changes

| Signal Rate | SDK-Eligible Hot | Velocity COGS | Margin |
|-------------|------------------|---------------|--------|
| 10% | 23 | $2,546 | 36.4% |
| 20% (base) | 45 | $2,575 | 35.6% |
| 30% | 68 | $2,604 | 34.9% |
| 50% | 113 | $2,663 | 33.4% |

---

## 13. Risk Factors

### Margin Risk Matrix

| Risk | Impact | Mitigation |
|------|--------|------------|
| LinkedIn boost increases Hot % | High | Monitor distribution, adjust scoring |
| Anthropic price increase | Medium | Cache common queries, batch processing |
| ClickSend price increase | Low | Switch provider if needed |
| Higher than expected reply rate | Low | Positive — indicates quality |
| Lower signal detection rate | Medium | More leads get standard treatment (saves money) |

### Dominance Tier Concern

**Observation:** Dominance margin (31.8%) is below target (45%+)

**Options (NOT changing price):**
1. Accept lower margin for enterprise customers
2. Reduce SDK Voice to signal-only for Dominance
3. Require annual commitment for Dominance tier
4. Position Dominance as loss-leader for expansion revenue

**CEO Decision Required:** Accept 31.8% margin or modify tier structure

---

## 14. Monthly Budget Safeguard (Optional)

If CEO wants additional protection, implement hard caps:

| Tier | Monthly SDK Budget | Approx Lead Coverage |
|------|--------------------|-----------------------|
| Ignition | $300 | 125 Hot leads |
| Velocity | $550 | 225 Hot leads |
| Dominance | $1,100 | 450 Hot leads |

These caps ensure SDK spend cannot exceed 20% of COGS under any scenario.

---

## 15. Implementation Checklist

1. [ ] CEO approves this P&L model
2. [ ] Implement `should_use_sdk_brain()` for enrichment gating
3. [ ] SDK Email for ALL Hot leads (no gating)
4. [ ] SDK Voice KB for ALL Hot leads (no gating)
5. [ ] Add SDK cost tracking to usage dashboard
6. [ ] (Optional) Implement monthly budget safeguard
7. [ ] Monitor actual vs projected distribution weekly

---

## 16. Approval

**Financial Model Prepared By:**
- CTO Office
- CFO Office

**Date:** January 19, 2026

**CEO Approval:**

| Item | Status |
|------|--------|
| SDK Hybrid Model | ☐ Approved |
| Ignition P&L ($1,085 profit, 43.4% margin) | ☐ Approved |
| Velocity P&L ($1,425 profit, 35.6% margin) | ☐ Approved |
| Dominance P&L ($2,384 profit, 31.8% margin) | ☐ Approved |
| Budget Safeguard Implementation | ☐ Yes / ☐ No |

---

**Signature:** _________________________

**Date:** _________________________

