# Agency OS 12-Month P&L Projection

**Document Type:** Financial Projection  
**Version:** 1.0  
**Date:** January 2026  
**Prepared By:** CFO Office  
**Status:** DRAFT FOR CEO REVIEW  
**Currency:** AUD (Australian Dollars)

---

## Executive Summary

This P&L projection models Agency OS's first 12 months based on:
- **Founding 20 (Dogfooding):** 50% off for life
- **Early Access 20:** 25% off for life  
- **Full Price:** Month 4 onwards

### 12-Month Summary

| Metric | Value |
|--------|-------|
| **Total Revenue** | $1,162,500 |
| **Total COGS** | $551,286 |
| **Gross Profit** | $611,214 |
| **Operating Expenses** | $84,708 |
| **Net Operating Profit** | $526,506 |
| **Net Margin** | **45.3%** |
| **Customers (M12)** | 82 |
| **MRR (M12)** | $167,500 |
| **ARR Run Rate (M12)** | $2,010,000 |

---

## Part 1: Pricing Tiers & Customer Cohorts

### 1.1 Standard Pricing (AUD)

| Tier | Monthly Price | COGS | Gross Margin |
|------|---------------|------|--------------|
| Ignition | $2,500 | $666 | 73.4% |
| Velocity | $4,000 | $1,323 | 66.9% |
| Dominance | $7,500 | $2,502 | 66.6% |

### 1.2 Customer Cohorts

| Cohort | Customers | Discount | Timing | Tier Mix |
|--------|-----------|----------|--------|----------|
| **Founding 20** | 20 | 50% for life | M1-M2 | 100% Ignition |
| **Early Access 20** | 20 | 25% for life | M2-M3 | 80% Ignition, 20% Velocity |
| **Full Price** | 45+ | 0% | M4+ | 60% Ignition, 30% Velocity, 10% Dominance |

### 1.3 Effective Pricing by Cohort

| Cohort | Ignition | Velocity | Dominance |
|--------|----------|----------|-----------|
| Founding (50% off) | $1,250 | $2,000 | $3,750 |
| Early Access (25% off) | $1,875 | $3,000 | $5,625 |
| Full Price | $2,500 | $4,000 | $7,500 |

---

## Part 2: Customer Acquisition Model

### 2.1 Conversion Funnel (Conservative)

Based on dogfooding with Agency OS outbound:

| Stage | Volume/Month | Conversion | Output |
|-------|--------------|------------|--------|
| Leads Enriched | 1,250 | — | 1,250 |
| Emails Sent | 1,250 | 100% | 1,250 |
| Opens | 438 | 35% | 438 |
| Replies | 63 | 5% | 63 |
| Positive Replies | 25 | 2% | 25 |
| Meetings Booked | 13 | 1% | 13 |
| Demos Completed | 10 | 0.8% | 10 |
| Closed Won | 5 | 0.4% | **5** |

**Conservative assumption:** 5 new customers/month from M4 onwards.

### 2.2 Customer Growth Schedule

| Month | New | Churn | Net | Cumulative |
|-------|-----|-------|-----|------------|
| M1 | 10 | 0 | 10 | 10 |
| M2 | 15 | 0 | 15 | 25 |
| M3 | 15 | 1 | 14 | 39 |
| M4 | 5 | 1 | 4 | 43 |
| M5 | 5 | 1 | 4 | 47 |
| M6 | 6 | 2 | 4 | 51 |
| M7 | 6 | 2 | 4 | 55 |
| M8 | 7 | 2 | 5 | 60 |
| M9 | 7 | 2 | 5 | 65 |
| M10 | 8 | 3 | 5 | 70 |
| M11 | 8 | 3 | 5 | 75 |
| M12 | 10 | 3 | 7 | **82** |

**Churn assumption:** 5% monthly from M3 onwards (conservative for B2B SaaS).

---

## Part 3: Revenue Projections (Monthly)

### 3.1 Detailed Revenue by Month

#### Month 1 (Launch)
| Cohort | Customers | Tier | Price | Revenue |
|--------|-----------|------|-------|---------|
| Founding | 10 | Ignition | $1,250 | $12,500 |
| **Total** | **10** | | | **$12,500** |

#### Month 2
| Cohort | Customers | Tier | Price | Revenue |
|--------|-----------|------|-------|---------|
| Founding | 20 | Ignition | $1,250 | $25,000 |
| Early Access | 5 | Ignition | $1,875 | $9,375 |
| **Total** | **25** | | | **$34,375** |

#### Month 3
| Cohort | Customers | Tier | Price | Revenue |
|--------|-----------|------|-------|---------|
| Founding | 20 | Ignition | $1,250 | $25,000 |
| Early Access | 18 | Ignition | $1,875 | $33,750 |
| Early Access | 2 | Velocity | $3,000 | $6,000 |
| Less: Churn | -1 | | | -$1,875 |
| **Total** | **39** | | | **$62,875** |

#### Month 4 (Full Price Begins)
| Cohort | Customers | Tier | Price | Revenue |
|--------|-----------|------|-------|---------|
| Founding | 20 | Ignition | $1,250 | $25,000 |
| Early Access | 16 | Ignition | $1,875 | $30,000 |
| Early Access | 2 | Velocity | $3,000 | $6,000 |
| Full Price | 3 | Ignition | $2,500 | $7,500 |
| Full Price | 2 | Velocity | $4,000 | $8,000 |
| Less: Churn | -1 | | | -$2,500 |
| **Total** | **42** | | | **$74,000** |

### 3.2 Monthly Revenue Summary

| Month | Customers | MRR | Cumulative Revenue |
|-------|-----------|-----|-------------------|
| M1 | 10 | $12,500 | $12,500 |
| M2 | 25 | $34,375 | $46,875 |
| M3 | 39 | $62,875 | $109,750 |
| M4 | 43 | $74,000 | $183,750 |
| M5 | 47 | $83,125 | $266,875 |
| M6 | 51 | $93,750 | $360,625 |
| M7 | 55 | $103,125 | $463,750 |
| M8 | 60 | $115,000 | $578,750 |
| M9 | 65 | $126,875 | $705,625 |
| M10 | 70 | $138,750 | $844,375 |
| M11 | 75 | $150,625 | $995,000 |
| M12 | 82 | $167,500 | **$1,162,500** |

---

## Part 4: Cost of Goods Sold (COGS)

### 4.1 Variable COGS per Customer (by tier)

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
| **Total COGS** | **$666** | **$1,323** | **$2,502** |

### 4.2 Monthly COGS Calculation

| Month | Ignition | Velocity | Dominance | Total COGS |
|-------|----------|----------|-----------|------------|
| M1 | 10 × $666 = $6,660 | 0 | 0 | $6,660 |
| M2 | 25 × $666 = $16,650 | 0 | 0 | $16,650 |
| M3 | 36 × $666 = $23,976 | 2 × $1,323 = $2,646 | 0 | $26,622 |
| M4 | 38 × $666 = $25,308 | 4 × $1,323 = $5,292 | 0 | $30,600 |
| M5 | 40 × $666 = $26,640 | 6 × $1,323 = $7,938 | 1 × $2,502 = $2,502 | $37,080 |
| M6 | 41 × $666 = $27,306 | 8 × $1,323 = $10,584 | 2 × $2,502 = $5,004 | $42,894 |
| M7 | 42 × $666 = $27,972 | 10 × $1,323 = $13,230 | 3 × $2,502 = $7,506 | $48,708 |
| M8 | 44 × $666 = $29,304 | 12 × $1,323 = $15,876 | 4 × $2,502 = $10,008 | $55,188 |
| M9 | 46 × $666 = $30,636 | 14 × $1,323 = $18,522 | 5 × $2,502 = $12,510 | $61,668 |
| M10 | 48 × $666 = $31,968 | 16 × $1,323 = $21,168 | 6 × $2,502 = $15,012 | $68,148 |
| M11 | 50 × $666 = $33,300 | 18 × $1,323 = $23,814 | 7 × $2,502 = $17,514 | $74,628 |
| M12 | 54 × $666 = $35,964 | 20 × $1,323 = $26,460 | 8 × $2,502 = $20,016 | $82,440 |

**12-Month Total COGS: $551,286**

---

## Part 5: Gross Profit

| Month | Revenue | COGS | Gross Profit | Margin % |
|-------|---------|------|--------------|----------|
| M1 | $12,500 | $6,660 | $5,840 | 46.7% |
| M2 | $34,375 | $16,650 | $17,725 | 51.6% |
| M3 | $62,875 | $26,622 | $36,253 | 57.7% |
| M4 | $74,000 | $30,600 | $43,400 | 58.6% |
| M5 | $83,125 | $37,080 | $46,045 | 55.4% |
| M6 | $93,750 | $42,894 | $50,856 | 54.2% |
| M7 | $103,125 | $48,708 | $54,417 | 52.8% |
| M8 | $115,000 | $55,188 | $59,812 | 52.0% |
| M9 | $126,875 | $61,668 | $65,207 | 51.4% |
| M10 | $138,750 | $68,148 | $70,602 | 50.9% |
| M11 | $150,625 | $74,628 | $76,022 | 50.5% |
| M12 | $167,500 | $82,440 | $85,060 | 50.8% |

**12-Month Gross Profit: $611,214**
**Average Gross Margin: 52.6%**

*Note: Margin lower than standard due to 50% Founding + 25% Early Access discounts.*

---

## Part 6: Operating Expenses (OpEx)

### 6.1 Fixed Infrastructure (Monthly)

| Service | Monthly Cost (AUD) |
|---------|-------------------|
| Supabase Pro | $39 |
| Vercel Pro | $31 |
| Railway (3 services) | $78 |
| Upstash Redis | $16 |
| Cloudflare R2 | $8 |
| Sentry Team | $40 |
| Smartproxy Micro | $78 |
| **Subtotal** | **$290** |

### 6.2 Marketing & Content Automation (Monthly)

| Item | Monthly Cost (AUD) |
|------|-------------------|
| HeyGen Creator | $70 |
| Claude API (content) | $8 |
| Buffer | $9 |
| Twitter API Basic | $155 |
| Domain/SSL | $8 |
| **Subtotal** | **$250** |

### 6.3 Business Operations (Monthly)

| Item | Monthly Cost (AUD) |
|------|-------------------|
| Stripe Fees (2.9% + $0.30) | Variable |
| Accounting Software | $50 |
| Legal Reserve | $200 |
| Insurance | $150 |
| Miscellaneous | $100 |
| **Subtotal** | **$500 + Stripe** |

### 6.4 Payment Processing (Stripe)

| Month | Revenue | Stripe Fee (2.9% + $0.30×txns) |
|-------|---------|-------------------------------|
| M1 | $12,500 | $365 |
| M2 | $34,375 | $1,004 |
| M3 | $62,875 | $1,835 |
| M4 | $74,000 | $2,159 |
| M5 | $83,125 | $2,425 |
| M6 | $93,750 | $2,734 |
| M7 | $103,125 | $3,008 |
| M8 | $115,000 | $3,354 |
| M9 | $126,875 | $3,700 |
| M10 | $138,750 | $4,046 |
| M11 | $150,625 | $4,392 |
| M12 | $167,500 | $4,884 |

**12-Month Stripe Fees: $33,906**

### 6.5 Dogfooding COGS (Self-Marketing)

Agency OS uses itself to acquire customers. This is internal COGS:

| Item | Monthly Cost (AUD) |
|------|-------------------|
| 1,250 leads enriched | $163 |
| Email sends | $39 |
| Voice calls (~50) | $44 |
| LinkedIn outreach | $122 |
| **Subtotal** | **$368** |

### 6.6 Total Monthly OpEx

| Category | Monthly |
|----------|---------|
| Fixed Infrastructure | $290 |
| Marketing Automation | $250 |
| Business Operations | $500 |
| Dogfooding COGS | $368 |
| Stripe (avg) | ~$2,826 |
| **Total OpEx** | **~$4,234** |

---

## Part 7: Net Operating Profit

### 7.1 Monthly P&L Summary

| Month | Revenue | COGS | Gross Profit | OpEx | **Net Profit** |
|-------|---------|------|--------------|------|----------------|
| M1 | $12,500 | $6,660 | $5,840 | $1,773 | **$4,067** |
| M2 | $34,375 | $16,650 | $17,725 | $2,412 | **$15,313** |
| M3 | $62,875 | $26,622 | $36,253 | $3,243 | **$33,010** |
| M4 | $74,000 | $30,600 | $43,400 | $3,567 | **$39,833** |
| M5 | $83,125 | $37,080 | $46,045 | $3,833 | **$42,212** |
| M6 | $93,750 | $42,894 | $50,856 | $4,142 | **$46,714** |
| M7 | $103,125 | $48,708 | $54,417 | $4,416 | **$50,001** |
| M8 | $115,000 | $55,188 | $59,812 | $4,762 | **$55,050** |
| M9 | $126,875 | $61,668 | $65,207 | $5,108 | **$60,099** |
| M10 | $138,750 | $68,148 | $70,602 | $5,454 | **$65,148** |
| M11 | $150,625 | $74,628 | $76,022 | $5,800 | **$70,222** |
| M12 | $167,500 | $82,440 | $85,060 | $6,292 | **$78,768** |

### 7.2 12-Month Totals

| Line Item | 12-Month Total |
|-----------|----------------|
| **Revenue** | $1,162,500 |
| **COGS** | $551,286 |
| **Gross Profit** | $611,214 |
| **Operating Expenses** | $84,708 |
| **Net Operating Profit** | **$526,506** |
| **Net Margin** | **45.3%** |

---

## Part 8: Cash Flow Analysis

### 8.1 Monthly Cash Position

Assumptions:
- Customers pay monthly in advance
- COGS paid same month
- OpEx paid same month
- Starting cash: $0

| Month | Cash In | Cash Out | Net | Cumulative |
|-------|---------|----------|-----|------------|
| M1 | $12,500 | $8,433 | $4,067 | $4,067 |
| M2 | $34,375 | $19,062 | $15,313 | $19,380 |
| M3 | $62,875 | $29,865 | $33,010 | $52,390 |
| M4 | $74,000 | $34,167 | $39,833 | $92,223 |
| M5 | $83,125 | $40,913 | $42,212 | $134,435 |
| M6 | $93,750 | $47,036 | $46,714 | $181,149 |
| M7 | $103,125 | $53,124 | $50,001 | $231,150 |
| M8 | $115,000 | $59,950 | $55,050 | $286,200 |
| M9 | $126,875 | $66,776 | $60,099 | $346,299 |
| M10 | $138,750 | $73,602 | $65,148 | $411,447 |
| M11 | $150,625 | $80,428 | $70,222 | $481,669 |
| M12 | $167,500 | $88,732 | $78,768 | **$560,437** |

**Cash positive from Month 1.** ✅

---

## Part 9: Conversion Funnel Detail

### 9.1 Self-Marketing Funnel (Dogfooding)

| Stage | M1 | M2 | M3 | M4 | M5 | M6 |
|-------|----|----|----|----|----|----|
| Leads Enriched | 1,250 | 1,250 | 1,250 | 1,250 | 1,250 | 1,250 |
| Emails Sent | 1,250 | 1,250 | 1,250 | 1,250 | 1,250 | 1,250 |
| Open Rate | 35% | 36% | 37% | 38% | 38% | 39% |
| Opens | 438 | 450 | 463 | 475 | 475 | 488 |
| Reply Rate | 5% | 5.2% | 5.5% | 5.5% | 5.8% | 6% |
| Replies | 63 | 65 | 69 | 69 | 73 | 75 |
| Positive % | 40% | 42% | 43% | 45% | 45% | 46% |
| Positive Replies | 25 | 27 | 30 | 31 | 33 | 35 |
| Meeting Rate | 50% | 52% | 53% | 55% | 55% | 56% |
| Meetings | 13 | 14 | 16 | 17 | 18 | 20 |
| Close Rate | 38% | 40% | 44% | 29% | 28% | 30% |
| **New Customers** | **5** | **6** | **7** | **5** | **5** | **6** |

*Close rate drops M4+ as Founding/Early Access urgency ends.*

### 9.2 Customer Acquisition Cost (CAC)

| Month | Dogfooding Cost | New Customers | CAC |
|-------|-----------------|---------------|-----|
| M1 | $368 | 10 | $37 |
| M2 | $368 | 15 | $25 |
| M3 | $368 | 15 | $25 |
| M4 | $368 | 5 | $74 |
| M5 | $368 | 5 | $74 |
| M6 | $368 | 6 | $61 |
| M7 | $368 | 6 | $61 |
| M8 | $368 | 7 | $53 |
| M9 | $368 | 7 | $53 |
| M10 | $368 | 8 | $46 |
| M11 | $368 | 8 | $46 |
| M12 | $368 | 10 | $37 |

**Average CAC: $49**

---

## Part 10: Customer Lifetime Value (LTV)

### 10.1 LTV by Cohort

Assumptions:
- Average customer lifespan: 18 months
- Churn: 5% monthly
- Upsell rate: 15% Y1

| Cohort | Monthly Price | Months | LTV |
|--------|---------------|--------|-----|
| Founding (50% off) | $1,250 | 18 | $22,500 |
| Early Access (25% off) | $1,875 | 18 | $33,750 |
| Full Price | $2,500 | 18 | $45,000 |

### 10.2 LTV:CAC Ratio

| Cohort | LTV | CAC | LTV:CAC |
|--------|-----|-----|---------|
| Founding | $22,500 | $37 | **608:1** |
| Early Access | $33,750 | $25 | **1,350:1** |
| Full Price | $45,000 | $74 | **608:1** |

**Exceptional unit economics.** ✅

---

## Part 11: Sensitivity Analysis

### 11.1 Scenario: 50% Lower Conversion

| Metric | Base Case | Pessimistic |
|--------|-----------|-------------|
| New customers/month | 5-10 | 2-5 |
| M12 Customers | 82 | 45 |
| M12 MRR | $167,500 | $85,000 |
| 12-Month Revenue | $1,162,500 | $580,000 |
| 12-Month Profit | $526,506 | $210,000 |

Still profitable at 50% lower acquisition. ✅

### 11.2 Scenario: 10% Monthly Churn

| Metric | Base (5%) | High Churn (10%) |
|--------|-----------|------------------|
| M12 Customers | 82 | 58 |
| M12 MRR | $167,500 | $115,000 |
| 12-Month Revenue | $1,162,500 | $820,000 |
| 12-Month Profit | $526,506 | $320,000 |

Still profitable at double churn. ✅

### 11.3 Scenario: Provider Costs +25%

| Metric | Base | +25% COGS |
|--------|------|-----------|
| Ignition COGS | $666 | $833 |
| 12-Month COGS | $551,286 | $689,108 |
| 12-Month Profit | $526,506 | $388,684 |
| Net Margin | 45.3% | 33.4% |

Still highly profitable. ✅

---

## Part 12: Key Metrics Dashboard

### 12.1 Monthly KPIs

| KPI | M1 | M3 | M6 | M12 |
|-----|----|----|----|----|
| MRR | $12,500 | $62,875 | $93,750 | $167,500 |
| Customers | 10 | 39 | 51 | 82 |
| ARPU | $1,250 | $1,612 | $1,838 | $2,043 |
| Gross Margin | 46.7% | 57.7% | 54.2% | 50.8% |
| Net Margin | 32.5% | 52.5% | 49.8% | 47.0% |
| CAC | $37 | $25 | $61 | $37 |
| LTV:CAC | 608:1 | 1,350:1 | 553:1 | 608:1 |
| Churn | 0% | 2.6% | 3.9% | 3.7% |

### 12.2 Milestone Targets

| Milestone | Target | ETA |
|-----------|--------|-----|
| First customer | 1 | Week 1 |
| Founding 20 sold out | 20 | M2 |
| Early Access 20 sold out | 40 | M3 |
| $50K MRR | $50,000 | M3 |
| $100K MRR | $100,000 | M7 |
| 50 customers | 50 | M6 |
| $150K MRR | $150,000 | M11 |
| 80 customers | 80 | M12 |

---

## Part 13: Detailed Line Items (M1-M12)

### 13.1 Revenue by Source

| Month | Founding | Early Access | Full Price | Total |
|-------|----------|--------------|------------|-------|
| M1 | $12,500 | $0 | $0 | $12,500 |
| M2 | $25,000 | $9,375 | $0 | $34,375 |
| M3 | $25,000 | $37,875 | $0 | $62,875 |
| M4 | $25,000 | $37,500 | $11,500 | $74,000 |
| M5 | $25,000 | $37,500 | $20,625 | $83,125 |
| M6 | $25,000 | $37,500 | $31,250 | $93,750 |
| M7 | $25,000 | $37,500 | $40,625 | $103,125 |
| M8 | $25,000 | $37,500 | $52,500 | $115,000 |
| M9 | $25,000 | $37,500 | $64,375 | $126,875 |
| M10 | $25,000 | $37,500 | $76,250 | $138,750 |
| M11 | $25,000 | $37,500 | $88,125 | $150,625 |
| M12 | $25,000 | $37,500 | $105,000 | $167,500 |

### 13.2 COGS by Category (Full Year)

| Category | 12-Month Total | % of COGS |
|----------|----------------|-----------|
| Data Enrichment | $98,280 | 17.8% |
| Email Infrastructure | $29,484 | 5.3% |
| SMS | $7,560 | 1.4% |
| LinkedIn (HeyReach) | $165,648 | 30.1% |
| Voice AI (Vapi) | $124,236 | 22.5% |
| Direct Mail (Lob) | $92,484 | 16.8% |
| Webhooks | $6,048 | 1.1% |
| Infrastructure | $27,546 | 5.0% |
| **Total COGS** | **$551,286** | **100%** |

### 13.3 OpEx by Category (Full Year)

| Category | 12-Month Total | % of OpEx |
|----------|----------------|-----------|
| Fixed Infrastructure | $3,480 | 4.1% |
| Marketing Automation | $3,000 | 3.5% |
| Business Operations | $6,000 | 7.1% |
| Dogfooding COGS | $4,416 | 5.2% |
| Stripe Fees | $33,906 | 40.0% |
| Legal/Insurance | $4,200 | 5.0% |
| Miscellaneous | $1,200 | 1.4% |
| **Total OpEx** | **$84,708** | **100%** |

---

## Part 14: Discount Impact Analysis

### 14.1 Revenue Lost to Discounts

| Cohort | Full Price Revenue | Discounted Revenue | Lost Revenue |
|--------|-------------------|-------------------|--------------|
| Founding 20 (12mo) | $600,000 | $300,000 | $300,000 |
| Early Access 20 (10mo) | $500,000 | $375,000 | $125,000 |
| **Total** | **$1,100,000** | **$675,000** | **$425,000** |

### 14.2 Why It's Worth It

| Benefit | Value |
|---------|-------|
| Cash flow from Day 1 | $4,067 M1 profit |
| Social proof (20 customers) | Priceless |
| Case studies for full-price sales | 10x leverage |
| Product feedback loop | Faster iteration |
| Build-in-public momentum | Viral marketing |

**Strategic discount, not a discount.**

---

## Part 15: Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Lower conversion rate | Medium | High | Improve messaging, add channels |
| Higher churn | Low | High | Onboarding, success program |
| Provider price increases | Medium | Medium | Volume contracts, alternatives |
| Competitive pressure | Medium | Medium | Feature velocity, niche focus |
| Economic downturn | Low | High | Focus on ROI messaging |

---

## Part 16: Recommendations

### 16.1 Immediate Actions (M1-M2)
1. ✅ Lock Founding 20 pricing at 50% off
2. ✅ Prepare Early Access 20 at 25% off
3. Launch dogfooding campaign Day 1
4. Daily content automation active

### 16.2 Growth Actions (M3-M6)
1. Transition to full pricing M4
2. Implement customer success program
3. Begin Velocity tier upselling
4. Add referral program

### 16.3 Scale Actions (M7-M12)
1. Launch Dominance tier actively
2. Expand to adjacent verticals
3. Consider UK/US expansion
4. Build case studies from Founding 20

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| CFO | | | |
| CEO | | | |
| COO | | | |

---

**END OF 12-MONTH P&L PROJECTION**
