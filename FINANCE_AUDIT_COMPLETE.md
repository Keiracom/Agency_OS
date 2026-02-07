# Agency OS Financial Documentation Audit

**Audit Date:** 2026-02-06  
**Auditor:** RESEARCHER-FINANCE (Subagent)  
**Scope:** All files in `/Agency_OS/docs/finance/`  
**Files Reviewed:** 18 documents

---

## Executive Summary

Agency OS is a B2B SaaS targeting marketing agencies in Australia (Y1) expanding to USA, UK, Canada, and New Zealand (Y2). The financial model shows strong unit economics with projected profitability from Month 1.

| Key Metric | Y1 (Final) | Y2 (Final) |
|------------|------------|------------|
| Revenue | $1,798,500 | $6,673,000 |
| Net Profit | $995,644 | $3,319,737 |
| Customers (EOY) | 82 | 462 |
| Employees (EOY) | 5 | 12 |
| Founder Draw | $149,347 | $497,961 |

---

## 1. Pricing Tiers and What's Included

### Standard Pricing (AUD)

| Tier | Monthly | Annual (15% off) | Leads/Month | Meeting Guarantee |
|------|---------|------------------|-------------|-------------------|
| **Ignition** | $2,500 | $25,500/yr | 1,250 | 10 meetings |
| **Velocity** | $4,000 | $40,800/yr | 2,250 | 25 meetings |
| **Dominance** | $7,500 | $76,500/yr | 4,500 | 60 meetings |

*Note: Velocity pricing has been standardized at $4,000/mo across all documents (Feb 2026 audit).*

### Discount Cohorts (Launch Phase)

| Cohort | Discount | Terms | Timing |
|--------|----------|-------|--------|
| Founding 20 | 50% off | For life, monthly only | M1-M2 |
| Early Access 20 | 25% off | For life, monthly only | M2-M3 |
| Full Price | 0% | Monthly or Annual | M4+ |

### Effective Pricing by Cohort

| Tier | Founding (50% off) | Early Access (25% off) | Full Price |
|------|--------------------|-----------------------|------------|
| Ignition | $1,250 | $1,875 | $2,500 |
| Velocity | $2,000 | $3,000 | $4,000 (full price) |
| Dominance | $3,750 | $5,625 | $7,500 |

### What's Included Per Tier

| Feature | Ignition | Velocity | Dominance |
|---------|----------|----------|-----------|
| Leads/month | 1,250 | 2,250 | 4,500 |
| LinkedIn seats | 1 | 3 | 5 |
| Email sequences | ✅ | ✅ | ✅ |
| LinkedIn automation | ✅ | ✅ | ✅ |
| Voice AI calls | ✅ (Warm/Hot) | ✅ (Warm/Hot) | ✅ (Warm/Hot) |
| SMS outreach | ✅ (Hot only) | ✅ (Hot only) | ✅ (Hot only) |
| Direct mail | ✅ (Hot only) | ✅ (Hot only) | ✅ (Hot only) |
| ALS Lead Scoring | ✅ | ✅ | ✅ |
| Analytics dashboard | ✅ | ✅ | ✅ |

### International Pricing (Y2)

| Tier | USD | GBP | CAD | NZD |
|------|-----|-----|-----|-----|
| Ignition | $1,650 | £1,300 | $2,200 | $2,750 |
| Velocity | $2,640 | £2,080 | $3,520 | $4,400 |
| Dominance | $4,950 | £3,900 | $6,600 | $8,250 |

---

## 2. Cost Structure Per Customer

### Variable COGS Per Customer (by tier)

| Cost Category | Ignition | Velocity | Dominance |
|---------------|----------|----------|-----------|
| Data Enrichment | $163 | $293 | $585 |
| Email Infrastructure | $39 | $62 | $116 |
| SMS | $10 | $18 | $36 |
| LinkedIn (HeyReach) | $122 | $366 | $610 |
| Voice AI (Vapi) | $164 | $295 | $591 |
| Direct Mail (Lob) | $122 | $220 | $441 |
| Webhooks | $8 | $12 | $23 |
| Infrastructure | $39 | $62 | $116 |
| **Total COGS/Customer** | **$666** | **$1,323** | **$2,502** |

### Detailed Per-Lead Costs (with SDK Integration)

#### Hot Lead with SDK (ALS 85+, priority signals)
| Item | Cost |
|------|------|
| Apollo acquisition | $0.31 |
| Clay enrichment | $0.12 |
| LinkedIn scrape | $0.005 |
| SDK Enrichment | $1.21 |
| SDK Email | $0.25 |
| Email send | $0.01 |
| LinkedIn message | $0.12 |
| SMS content + send | $0.22 |
| SDK Voice KB | $1.79 |
| Voice call (2.5 min) | $0.88 |
| Direct mail | $0.82 |
| **Total** | **$5.78** |

#### Hot Lead without SDK (standard)
| Item | Cost |
|------|------|
| All standard processing | $2.58 |

#### Warm Lead (ALS 60-84)
| Item | Cost |
|------|------|
| All processing | $1.42 |

#### Cool Lead (ALS 35-59)
| Item | Cost |
|------|------|
| All processing | $0.39 |

#### Cold Lead (ALS 20-34)
| Item | Cost |
|------|------|
| All processing | $0.33 |

### ALS (Agency Lead Score) Distribution

| Tier | Score Range | % of Leads | Treatment |
|------|-------------|------------|-----------|
| Hot | 85-100 | 10% | All 5 channels + SDK |
| Warm | 60-84 | 25% | Email + LinkedIn + Voice |
| Cool | 35-59 | 40% | Email + LinkedIn |
| Cold | 20-34 | 25% | Email only |

### Infrastructure Costs (Fixed Monthly)

| Service | Y1 Monthly | Y2 Monthly |
|---------|------------|------------|
| Supabase | $39 | $155 |
| Vercel | $31 | $78 |
| Railway | $78 | $195 |
| Upstash Redis | $16 | $62 |
| Sentry | $40 | $78 |
| Smartproxy | $78 | $155 |
| **Total** | **$290** | **$754** |

### Payment Processing

| Processor | Y1 (Stripe) | Y2 (Paddle) |
|-----------|-------------|-------------|
| Base rate | 2.9% | 5.0% |
| Per transaction | $0.30 | $0.50 |
| Y1 Total fees | $33,906 | N/A |
| Y2 Total fees | N/A | $341,150 |

*Paddle used in Y2 for multi-country VAT/GST compliance*

---

## 3. Margin Targets

### Gross Margin by Tier

| Tier | Revenue | COGS | Gross Margin |
|------|---------|------|--------------|
| Ignition | $2,500 | $666 | **73.4%** |
| Velocity | $4,000 | $1,323 | **66.9%** |
| Dominance | $7,500 | $2,502 | **66.6%** |

### Actual Margins with SDK Integration (Final Model)

| Tier | Revenue | COGS (SDK) | Gross Profit | Margin |
|------|---------|------------|--------------|--------|
| Ignition | $2,500 | $1,415 | $1,085 | **43.4%** |
| Velocity | $4,000 | $2,575 | $1,425 | **35.6%** |
| Dominance | $7,500 | $5,116 | $2,384 | **31.8%** |

*Note: Dominance margin (31.8%) is below target. This was flagged for CEO decision.*

### Target Margins (Original vs Actual)

| Metric | Target | Y1 Actual | Y2 Projected |
|--------|--------|-----------|--------------|
| Gross Margin | 65-73% | 52-57% | 65% |
| Net Margin | 45%+ | 45.3% | 58% |

### Blended Margin (Weighted by Customer Mix)

Assuming 40% Ignition, 45% Velocity, 15% Dominance:
- Blended ARPU: $4,375
- Blended COGS: $2,492
- **Blended Gross Margin: 43.0%**

---

## 4. Break-Even Analysis

### Customer Acquisition Cost (CAC)

| Source | CAC | Notes |
|--------|-----|-------|
| Dogfooding (self-marketing) | $37-$74 | Varies by month |
| Average Y1 | $49 | Via organic/dogfooding |
| Y2 with ads | $94 | Includes ad spend |

### Break-Even by Tier

| Tier | Monthly Price | Break-even Clients |
|------|---------------|-------------------|
| Ignition | $2,500 | 1 client @ $2,500+ |
| Velocity | $4,000 | 1 client @ $4,000 |
| Dominance | $7,500 | 2-3 clients @ $2,500-3,750 |

### LTV:CAC Analysis

| Cohort | LTV (18mo) | CAC | LTV:CAC |
|--------|------------|-----|---------|
| Founding | $22,500 | $37 | 608:1 |
| Early Access | $33,750 | $25 | 1,350:1 |
| Full Price | $45,000 | $74 | 608:1 |

*Exceptional unit economics across all cohorts.*

### Month 1 Budget (Detailed)

| Category | Budget |
|----------|--------|
| AI & Compute | $160 (subscription model) |
| Voice AI | $107 |
| Email Infrastructure | $155 |
| Enrichment | $197 |
| Infrastructure | $161 |
| Marketing & Ads | $480 |
| Tools & Subscriptions | $127 |
| Contingency | $120 |
| **Total M1 Budget** | **$1,507** |

### Break-Even Timeline

- **Cash positive from Month 1** ✅
- M1 profit: $4,067
- M3 profit: $26,010 (with engineer)
- Cumulative positive cash flow throughout Y1

---

## 5. Financial Decisions Made

### Pricing Decisions

1. **Founding/Early Access Discounts** — 50%/25% off for life to build social proof and case studies
2. **Annual Subscription Option** — 15% discount for upfront payment (M4+)
3. **Dominance Pricing** — Kept at $7,500 despite lower margins (31.8%) — flagged for review
4. **International Pricing** — Localized by market with exchange rate adjustments

### SDK Integration Decision (CEO Approved)

**Hybrid Model Selected:**
- SDK Enrichment: Selective (Hot leads + priority signals only)
- SDK Email: ALL Hot leads (10%)
- SDK Voice KB: ALL Hot leads (10%)
- Budget safeguard: Hard caps per tier

| Tier | SDK Monthly Budget |
|------|-------------------|
| Ignition | $100 |
| Velocity | $200 |
| Dominance | $400 |

### Payment Processor Decision

- **Y1:** Stripe (2.9% + $0.30)
- **Y2:** Paddle (5% + $0.50) — MoR model for international VAT/GST compliance
- **Rationale:** Saves $20,000-50,000/yr in compliance costs

### Profit Allocation Model

| Period | Ad Spend | Founder Draw | Retained |
|--------|----------|--------------|----------|
| M1-M3 | 0% | 0% | 100% |
| M4+ | 70% of Net | 50% of Remaining | 50% of Remaining |

### Staffing Decisions

**Critical Change:** Engineer moved from M19 → M3 (non-technical founder)

| Role | Month | Location | Monthly Cost |
|------|-------|----------|--------------|
| Engineer #1 | M3 | Poland | $7,000 |
| CS Lead | M4 | AU Remote | $9,000 |
| Tech Support | M6 | Philippines | $2,500 |
| Marketing | M9 | Philippines | $2,000 |
| US CSM | M13 | USA | $12,000 |
| Engineer #2 | M19 | Poland | $7,000 |

**Total Y1 Staffing:** $176,500
**Total Y2 Staffing:** $600,500

### Meeting Guarantee Decision

| Tier | Guarantee | If Not Met |
|------|-----------|------------|
| Ignition | 10 meetings/month | Next month free |
| Velocity | 25 meetings/month | Next month free |
| Dominance | 60 meetings/month | Next month free |

*Guarantee kicks in after 30-day onboarding period.*

### Ad Spend Allocation by Channel (Y1)

| Channel | % | Purpose |
|---------|---|---------|
| LinkedIn Ads | 35% | Primary B2B lead gen |
| Google Ads | 25% | Capture demand |
| Meta (FB/IG) | 15% | Awareness + retargeting |
| YouTube | 10% | Brand building |
| Retargeting | 10% | Conversion optimization |
| Sponsorships | 5% | Credibility |

### Risk Mitigations

1. **15% revenue reserve** for refunds/guarantees
2. **Budget safeguards** on SDK spend
3. **Contractor network** on standby for engineering bus factor
4. **Multiple market expansion** to reduce AU dependency

---

## 6. Key Financial Projections Summary

### Year 1 P&L (Final)

| Line Item | Amount |
|-----------|--------|
| Revenue | $1,798,500 |
| COGS | ($551,286) |
| Staffing | ($176,500) |
| Other OpEx | ($74,570) |
| **Net Profit** | **$995,644** |
| Ad Spend (70%) | ($696,951) |
| Founder Draw | ($149,347) |
| **Retained** | **$149,347** |

### Year 2 P&L (Final)

| Line Item | Amount |
|-----------|--------|
| Revenue | $6,673,000 |
| COGS | ($2,357,265) |
| Staffing | ($600,500) |
| Other OpEx | ($419,498) |
| **Net Profit** | **$3,319,737** |
| Ad Spend (70%) | ($2,323,816) |
| Founder Draw | ($497,961) |
| **Retained** | **$497,961** |

### Two-Year Combined

| Metric | Total |
|--------|-------|
| Revenue | $8,471,500 |
| Net Profit | $4,315,381 |
| Founder Draw | $647,308 |
| Retained | $647,308 |
| Customers (Y2 End) | 462 |
| Employees (Y2 End) | 12 |
| ARR Run Rate (Y2 End) | $13.5M |

---

## 7. Document Inconsistencies Noted

1. **Velocity Pricing:** RESOLVED — standardized at $4,000/mo
2. **ALS Distribution:** 10% Hot in most docs, 5% Hot in MEETING_GUARANTEE_ANALYSIS.md
3. **SDK Cost per lead:** Varies slightly between SDK option docs
4. **Meeting projections:** Original buyer guide (8-9 meetings) vs. revised analysis (20-30 meetings)

---

## 8. Outstanding Decisions Required

1. **Dominance margin (31.8%)** — Accept or increase price to $8,500?
2. ~~**Velocity pricing standardization**~~ — RESOLVED: $4,000/mo confirmed
3. **SDK tiered service** (Option D) — Implement as future upsell?

---

*Audit completed by RESEARCHER-FINANCE subagent*
