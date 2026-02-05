# NATIONWIDE_ROLLOUT.md
## Agency OS Australia-Wide Expansion Plan

**Document Version:** 1.0  
**Created:** 2026-02-04  
**Author:** Elliot (CTO)  
**Governance Event:** STRATEGIC_PIVOT_NATIONWIDE

---

## 1. Executive Summary

Agency OS is expanding from Sydney/NSW to **all 8 Australian States and Territories**. This document outlines the data acquisition strategy using the "ABN + GMB Double-Wedge" approach.

**Key Principle:** Seed with free public data (ABN), enrich with targeted scraping (GMB), verify only high-intent leads (Hunter.io/ZeroBounce).

---

## 2. Geographic Scope

### Phase 1: Primary Wedge (Current)
| State | Status | Priority |
|-------|--------|----------|
| **NSW** | ✅ Active | HIGH |

### Phase 2: Major Markets (Q2 2026)
| State | Status | Priority |
|-------|--------|----------|
| **VIC** | 📋 Planned | HIGH |
| **QLD** | 📋 Planned | HIGH |

### Phase 3: Secondary Markets (Q3 2026)
| State | Status | Priority |
|-------|--------|----------|
| **WA** | 📋 Planned | MEDIUM |
| **SA** | 📋 Planned | MEDIUM |

### Phase 4: Complete Coverage (Q4 2026)
| State | Status | Priority |
|-------|--------|----------|
| **TAS** | 📋 Planned | LOW |
| **NT** | 📋 Planned | LOW |
| **ACT** | 📋 Planned | LOW |

---

## 3. Data Acquisition Strategy: The "Double-Wedge"

### Tier 1: ABN Bulk Extract (FREE)
**Source:** data.gov.au  
**Cost:** $0 AUD  
**Records:** ~3-4 million active ABNs  

**Data Fields:**
- ABN & Status
- Entity Type (Company, Sole Trader, Trust, etc.)
- Legal Name & Trading Names
- State & Postcode
- GST Registration Status
- ACN (if applicable)

**Limitations:**
- ❌ No phone numbers
- ❌ No email addresses
- ❌ No website URLs
- ❌ No industry classification (ANZSIC)

**Update Frequency:** Weekly bulk extract + delta API

### Tier 2: GMB Scraper (LOW COST)
**Source:** Google Maps via Apify  
**Cost:** ~$6.20 AUD per 1,000 businesses  
**Strategy:** Postcode-by-postcode crawl  

**Data Fields:**
- Phone number
- Website URL
- Full address with lat/long
- Business categories
- Google rating & review count
- Opening hours

**Matching Logic:**
```
ABN Record + GMB Record → Fuzzy match on:
  1. Business name (Levenshtein distance < 3)
  2. Postcode (exact match)
  3. Street address (partial match)
```

### Tier 3: Hunter.io (TARGETED)
**Source:** Hunter.io API  
**Cost:** ~$0.0064 AUD per verification  
**Trigger:** Only for leads with ALS ≥ 60 (Warm+)  

**Data Fields:**
- Verified email address
- Email confidence score
- Email type (personal/generic)

### Tier 4: ZeroBounce (PREMIUM ESCALATION)
**Source:** ZeroBounce API  
**Cost:** ~$0.006-0.014 AUD per verification  
**Trigger:** Only when Hunter.io returns "catch_all" or confidence < 70%  

**Data Fields:**
- Email validity status
- Spam trap detection
- Activity scoring

---

## 4. Cost Projections (AUD)

### Initial Database Build (One-Time)
| Component | Records | Unit Cost | Total |
|-----------|---------|-----------|-------|
| ABN Bulk Extract | 3,000,000 | $0 | **$0** |
| GMB Enrichment (Phase 1: NSW) | 200,000 | $0.0062 | **$1,240** |
| Hunter.io (Hot/Warm only, ~20%) | 40,000 | $0.0064 | **$256** |
| ZeroBounce Escalation (~5%) | 10,000 | $0.010 | **$100** |
| **Total Phase 1** | | | **~$1,600** |

### Per-Lead Waterfall Cost (Steady State)
| Scenario | ABN | GMB | Hunter | ZeroBounce | Total |
|----------|-----|-----|--------|------------|-------|
| Cold lead (ABN only) | $0 | - | - | - | **$0** |
| Warm lead (ABN + GMB) | $0 | $0.0062 | - | - | **$0.006** |
| Hot lead (full waterfall) | $0 | $0.0062 | $0.0064 | - | **$0.013** |
| Escalated (triple-check) | $0 | $0.0062 | $0.0064 | $0.010 | **$0.023** |

---

## 5. Waterfall Verification Logic

```
┌─────────────────────────────────────────────────────────────────┐
│                    WATERFALL VERIFICATION FLOW                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐                                                   │
│  │ NEW LEAD │                                                   │
│  └────┬─────┘                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌────────────────────────────────────────────┐                │
│  │ TIER 1: ABN SEED                           │                │
│  │ • Load from ABN Bulk Extract               │                │
│  │ • Match by business name + postcode        │                │
│  │ • Cost: $0                                 │                │
│  └────────────────────┬───────────────────────┘                │
│                       │                                         │
│                       ▼                                         │
│  ┌────────────────────────────────────────────┐                │
│  │ TIER 2: GMB ENRICHMENT                     │                │
│  │ • Scrape Google Maps for phone/website     │                │
│  │ • Fuzzy match ABN ↔ GMB                    │                │
│  │ • Cost: $0.0062/lead                       │                │
│  └────────────────────┬───────────────────────┘                │
│                       │                                         │
│            ┌──────────┴──────────┐                             │
│            │ ALS ≥ 60?           │                             │
│            └──────────┬──────────┘                             │
│                 YES   │   NO → STOP (Cold lead)                │
│                       ▼                                         │
│  ┌────────────────────────────────────────────┐                │
│  │ TIER 3: HUNTER.IO EMAIL                    │                │
│  │ • Find/verify email via Hunter             │                │
│  │ • Cost: $0.0064/lead                       │                │
│  └────────────────────┬───────────────────────┘                │
│                       │                                         │
│            ┌──────────┴──────────┐                             │
│            │ Confidence ≥ 70%?   │                             │
│            └──────────┬──────────┘                             │
│                 YES   │   NO (catch_all or low confidence)     │
│                 │     ▼                                         │
│                 │  ┌────────────────────────────────────────┐  │
│                 │  │ TIER 4: ZEROBOUNCE ESCALATION         │  │
│                 │  │ • Premium triple-check verification   │  │
│                 │  │ • Cost: $0.010/lead                   │  │
│                 │  └────────────────────────────────────────┘  │
│                 │                                               │
│                 ▼                                               │
│  ┌────────────────────────────────────────────┐                │
│  │ CALCULATE ALS                              │                │
│  │ • Base ALS score                           │                │
│  │ • +15 bonus if verified across 3+ sources  │                │
│  │ • Intent signals (ad volume, hiring, etc.) │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. ABN API Registration

**Endpoint:** https://abr.business.gov.au/Tools/WebServices  
**Authentication:** GUID (free, ~24hr approval)  
**Rate Limits:** Not published (generous for legitimate use)

### Key API Methods
| Method | Purpose |
|--------|---------|
| `SearchByABNv202001` | Lookup by ABN |
| `ABRSearchByNameAdvanced2017` | Search by name + filters |
| `SearchByPostcode` | Bulk retrieve by postcode |
| `SearchByUpdateEvent` | Delta sync since date |

---

## 7. GMB Scraping Strategy

### Postcode Coverage by State
| State | Postcodes | Est. Businesses |
|-------|-----------|-----------------|
| NSW | 1000-2999 | ~800,000 |
| VIC | 3000-3999 | ~600,000 |
| QLD | 4000-4999 | ~450,000 |
| WA | 6000-6999 | ~250,000 |
| SA | 5000-5999 | ~200,000 |
| TAS | 7000-7999 | ~80,000 |
| NT | 0800-0999 | ~30,000 |
| ACT | 2600-2620 | ~50,000 |

### Industry Targeting (High-Value First)
1. Tradies (plumbers, electricians, builders)
2. Professional services (accountants, lawyers)
3. Healthcare (dentists, physios, GPs)
4. Hospitality (restaurants, cafes)
5. Retail (local shops)

---

## 8. Governance

### Cost Tracking
- All costs logged in `lead_lineage_log.cost_aud`
- Currency: Australian Dollars (AUD) only
- Daily cost reports via Prefect flow

### Audit Trail
- Every enrichment step logged to `lead_lineage_log`
- Lineage query: `SELECT get_lead_lineage_summary(lead_id)`

### Self-Healing
- Scraper failures tracked in `scraper_health_log`
- Auto-repair triggered after 3 consecutive failures

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| ABN Match Rate | ≥95% | GMB records matched to ABN |
| Email Validity | ≥98% | Post-verification bounce rate |
| Cost per Enriched Lead | ≤$0.025 AUD | Waterfall average |
| Data Freshness | ≤7 days | Time since last update |

---

*Document approved by: Dave (CEO), 2026-02-04*  
*Implementation by: Elliot (CTO)*
