# AGENCY_OS_STRATEGY.md
## The Siege Waterfall — Australian B2B Intelligence Engine

**Last Updated:** 2026-02-04
**Governance Event:** FULL_SYSTEM_RE_SYNC_WF_002
**Lead Operative:** Elliot (CTO)

---

## 1. STRATEGIC PIVOT: NATIONWIDE

### Target Market
- **Geography:** Australia-wide (NSW, VIC, QLD, WA, SA, TAS, NT, ACT)
- **Segment:** Marketing Agencies (5-50 employees)
- **Pricing:** High-ticket SaaS ($2,500 - $7,500 AUD/month)
- **TAM:** ~12,000 agencies nationwide

### Seed Layer: ABN Bulk Extract
- **Source:** data.gov.au ABN Bulk Extract
- **Volume:** 3.5M+ active business records
- **Cost:** FREE (public data)
- **Role:** Primary discovery engine — replaces Apollo as seed source

### Goal
Proven B2B client acquisition for Australian agencies via multi-channel distribution:
- Email
- SMS
- Voice AI
- LinkedIn
- Direct Mail

---

## 2. THE SIEGE WATERFALL (Data Pipeline)

### 5-Tier Architecture

| Tier | Name | Source | Cost (AUD) | Trigger |
|------|------|--------|------------|---------|
| **1** | ABN Bulk | data.gov.au | FREE | Always (seed) |
| **2** | GMB/Ads Signals | Google Maps + Meta Ads | ~$0.006 | Always |
| **3** | Hunter.io | hunter.io API | ~$0.012 | Email needed |
| **4** | LinkedIn Pulse | Proxycurl | ~$0.024 | Social context |
| **5** | Identity Gold | Kaspr/Lusha | ~$0.45 | **ALS ≥ 85 ONLY** |

### Tier Details

#### Tier 1: ABN Bulk (Discovery)
- **Purpose:** Seed the funnel with verified Australian businesses
- **Data:** ABN, ACN, legal name, trading names, state, postcode, GST status
- **Matching:** Fuzzy match to GMB via name + postcode
- **Cost:** FREE

#### Tier 2: GMB/Ads Signals
- **Purpose:** Enrich with contact info + intent signals
- **Data:** Phone, website, address, rating, reviews, ad presence
- **Matching:** ABN ↔ GMB fuzzy match (Levenshtein ≥70%)
- **Intent Signals:**
  - Ad volume: >50 ads = high intent
  - Ad longevity: >60 days = sustained spend
- **Cost:** ~$0.006 AUD per lead

#### Tier 3: Hunter.io (Professional Email)
- **Purpose:** Find verified work email
- **Data:** Email, email confidence, email type
- **Escalation:** If catch_all or confidence <70%, escalate to ZeroBounce
- **Cost:** ~$0.012 AUD per lead

#### Tier 4: LinkedIn Pulse (Social Context)
- **Purpose:** Decision maker identification + social signals
- **Data:** LinkedIn URL, job title, seniority, recent activity
- **Provider:** Proxycurl
- **Cost:** ~$0.024 AUD per lead

#### Tier 5: Identity Gold (Mobile Enrichment)
- **Purpose:** Direct mobile for Voice AI + SMS channels
- **Data:** Verified mobile number, direct email
- **Providers:** Kaspr (primary), Lusha (fallback)
- **⚠️ MANDATE:** Only triggers when **ALS ≥ 85**
- **Cost:** ~$0.45 AUD per lead

### Waterfall Flow
```
ABN Bulk (FREE)
    ↓
GMB/Ads Signals ($0.006)
    ↓
Hunter.io Email ($0.012)
    ↓
LinkedIn Pulse ($0.024)
    ↓ [ALS ≥ 85]
Identity Gold ($0.45)
```

---

## 3. ALS (AUTOMATED LEAD SCORING) ENHANCEMENT

### Base Score
The ALS (Automated Lead Scoring) rates lead quality 0-100.

### Verification Bonus
- **+15 points** for 3+ source verification (triple-check)

### Tier Gates
| ALS | Tier | Enrichment Level |
|-----------|------|------------------|
| 0-59 | Cold | Tiers 1-3 only |
| 60-84 | Warm | Tiers 1-4 |
| **85-100** | **Hot** | **Full waterfall (Tiers 1-5)** |

### Intent Signal Multipliers
- Ad volume ≥50 + longevity ≥60 days: +10
- Is hiring: +3
- Recent funding: +5
- Multi-source verified: +15

---

## 4. IDENTITY ESCALATION PROTOCOL

### Problem
Generic inboxes (info@, admin@, hello@) are useless for multi-channel outreach.

### Solution: Director Hunt
When generic email detected:
1. Scrape Team/About page for names
2. LinkedIn employee search via Proxycurl
3. ASIC Director Hunt (ACN → Company Extract)
4. Mobile enrichment via Kaspr/Lusha (ALS ≥85 only)

### Channel Mapping
| Channel | Field | Source |
|---------|-------|--------|
| SMS | `mobile_number_verified` | Kaspr/Lusha |
| Voice AI | `mobile_number_verified` | Kaspr/Lusha |
| Email | `work_email_verified` | Hunter.io |
| Direct Mail | `registered_office_address` | ABN/GMB |
| LinkedIn | `linkedin_profile_url` | Proxycurl |

---

## 5. FINANCIALS

### Currency: $AUD (Mandatory)
All costs, pricing, and budgets in Australian Dollars.
USD tool credits converted at **1.55 multiplier**.

### Cost Per Lead (Full Waterfall)
| Tier | Cost |
|------|------|
| 1 | $0.00 |
| 2 | $0.006 |
| 3 | $0.012 |
| 4 | $0.024 |
| 5 | $0.45 |
| **Total** | **~$0.49 AUD** |

### Ignition Tier Modeling
| Metric | Value |
|--------|-------|
| Leads/month | 1,250 |
| Avg cost/lead | $0.105 AUD (weighted) |
| Monthly spend | **$131.10 AUD** |

*Note: Not all leads reach Tier 5. Weighted average assumes 20% hit Identity Gold.*

### SaaS Pricing Tiers
| Tier | Price (AUD/mo) | Lead Credits | Cost/Lead |
|------|----------------|--------------|-----------|
| Ignition | $2,500 | 1,250 | $2.00 |
| Growth | $5,000 | 3,500 | $1.43 |
| Domination | $7,500 | 7,500 | $1.00 |

---

## 6. COMPLIANCE (ACMA)

### Voice AI Requirements
- **DNCR Wash:** Every 30 days before calling
- **Hours:** Weekdays 9am-8pm, Sat 9am-5pm
- **Prohibited:** Sundays, public holidays
- **AI Disclosure:** Recommended (not legally required)

### SMS Requirements
- **Alpha Tag Registration:** Mandatory by **1 July 2026**
- **Provider:** Twilio Trust Hub
- **Opt-out:** Within 5 business days

### Penalties
- Up to **$2.22 million AUD per day** per violation
- CBA fined $7.5M in 2024 for 170M non-compliant messages

### Implementation
- DNCR SOAP API integration for real-time washing
- Twilio Trust Hub for alpha tag registration
- Timezone-aware calling hour enforcement
- Automated opt-out processing (same-day target)

---

## 7. INFRASTRUCTURE

### Engines
| File | Purpose |
|------|---------|
| `src/engines/waterfall_verification_worker.py` | Tiers 1-4 + ZeroBounce escalation |
| `src/engines/identity_escalation.py` | Tier 5 + Director Hunt |

### Database
- **Platform:** Supabase (Postgres)
- **Indexing:** BRIN on `created_at` for time-series queries
- **Partitioning:** State-based (`company_state`) for regional queries

### Tables
| Table | Purpose |
|-------|---------|
| `lead_pool` | Central lead repository |
| `lead_lineage_log` | Full enrichment audit trail |
| `audit_logs` | System events and governance |

### Migrations
- `055_waterfall_enrichment_architecture.sql` — Lineage tracking + BRIN indexes

---

## 8. GOVERNANCE EVENTS

| Date | Event | Description |
|------|-------|-------------|
| 2026-02-04 | WF-001 | Waterfall Reliability Shift (Apollo SPOF elimination) |
| 2026-02-04 | WF-002 | Full System Re-Sync (Siege Waterfall doctrine) |

---

## 9. ACTION ITEMS

### Immediate
- [x] Create Siege Waterfall engines
- [x] Update lead_pool.py with WF-001 fields
- [ ] Execute migration 055 in Supabase
- [ ] Register SMS alpha tags with Twilio Trust Hub

### Q1 2026
- [ ] Integrate DNCR SOAP API
- [ ] Build ABN Bulk Extract ingestion pipeline
- [ ] Test Kaspr free tier for AU mobile accuracy
- [ ] Evaluate Cognism for premium mobile data

---

## 10. FIXED-COST FORTRESS (Approved Optimizations)

**Phase:** FIXED_COST_OPTIMIZATION_PHASE_1
**Total Savings:** ~$116 AUD/month
**Status:** APPROVED

### Approved Optimizations

| Optimization | Savings (AUD/mo) | Risk | Status |
|--------------|------------------|------|--------|
| Proxy Waterfall | $11 | Low | ✅ Implemented |
| Prefect Spot Instances | $25 | None | 📋 Planned |
| ~~Titan/Neo Email~~ | ~~$80~~ | — | ❌ REJECTED (Forge Stack validated) |
| **Total** | **$36** | — | — |

### Implementation Files
- `src/engines/proxy_waterfall.py` — Datacenter → ISP → Residential escalation
- `docs/PREFECT_SPOT_MIGRATION.md` — Bulk flow migration plan

### Email Infrastructure Decision (2026-02-05)
**VALIDATED:** Forge Stack (InfraForge + WarmForge + Salesforge) is optimal.
- Comprehensive research: 8 agents, 15 competitors, 7 platforms (Twitter, Reddit, HN, YouTube)
- Forge Stack at $111 AUD/mo is CHEAPEST when including all infrastructure
- Smartlead/Instantly are MORE expensive ($149-612 AUD) with add-ons
- Self-hosted has no warmup tools; DIY warmup detected by Gmail
- Research: `research/COLD_EMAIL_INFRASTRUCTURE_FINAL_REPORT.md`

### Proxy Waterfall Logic
```
Datacenter ($0.001) — 40% success on GMB
    ↓ [403/429/503]
ISP ($0.008) — 75% success
    ↓ [403/429/503]
Residential ($0.015) — 95% success

Weighted Average: ~$0.006/request (60% savings)
```

### Prefect Tier Classification
| Tier | Infrastructure | Cost | Use Case |
|------|---------------|------|----------|
| `realtime` | Railway | $50/mo | Webhooks, user-triggered flows |
| `bulk` | AWS Spot | $5/mo | ABN ingestion, batch verification |

### Email Distribution (Forge Stack)
| Provider | Accounts | Cost/User | Use Case |
|----------|----------|-----------|----------|
| Google Workspace | 2 | $10 AUD | admin@, ceo@ (deliverability critical) |
| InfraForge/Mailforge | 20 | $4.65 AUD | Outreach (auto DNS, integrated warmup) |

**Note:** Titan/Neo was considered but rejected — Forge Stack provides automated DNS, 
integrated WarmForge warmup, and native Salesforge integration. Total: $111 AUD/mo.

---

## 11. REJECTED INFRASTRUCTURE ⛔

**Governance:** These optimizations were evaluated and formally rejected.

### SMTP Pinging (Local Email Verification)

**Proposal:** Build local SMTP handshake verifier to reduce Hunter.io costs by 20%.

**Rejection Rationale:**
| Problem | Impact |
|---------|--------|
| Greylisting | 10-15% false negatives (valid emails marked invalid) |
| Catch-all domains | Cannot verify individual addresses |
| IP Reputation | SMTP probing risks our sending IPs |
| Rate Limiting | Mail servers block probing IPs |

**The Math:**
- Savings: $3 AUD/month at Ignition tier
- Risk: One blacklisting event = campaign death
- **Verdict: $3/month ≠ sender reputation risk**

**Status:** ❌ PERMANENTLY REJECTED
**Governance Trace:** `[AGENTS.md §2 - Radical Honesty] → Risk outweighs savings`

---

### Self-Hosted Email (Postal/Mautic)

**Proposal:** Replace Google Workspace with self-hosted Postal for $15/month.

**Rejection Rationale:**
| Task | Maintenance | Failure Impact |
|------|-------------|----------------|
| DKIM rotation | Quarterly per domain | Emails fail DMARC → spam |
| IP warmup | 4-6 weeks per IP | Blacklist if rushed |
| Blacklist monitoring | Daily | 30% delivery drop overnight |
| Bounce processing | Real-time | Reputation damage |

**The Math:**
- Savings: $150 AUD/month
- Maintenance: 20+ hours/month engineering time
- Risk: Deliverability is existential for outreach platform
- **Verdict: Deliverability IS the product. Don't self-host.**

**Status:** ❌ PERMANENTLY REJECTED
**Governance Trace:** `[AGENTS.md §2 - Radical Honesty] → Capacity yes, wisdom no`

**Alternative Validated:** Forge Stack (InfraForge + WarmForge + Salesforge) — managed deliverability with automated DNS and integrated warmup network.

---

## 12. GOVERNANCE EVENTS

| Date | Event | Description |
|------|-------|-------------|
| 2026-02-04 | WF-001 | Waterfall Reliability Shift (Apollo SPOF elimination) |
| 2026-02-04 | WF-002 | Full System Re-Sync (Siege Waterfall doctrine) |
| 2026-02-04 | FCO-001 | Fixed-Cost Fortress Phase 1 (~$36/mo savings — Titan rejected) |
| 2026-02-05 | FORGE-001 | Forge Stack Validation (8-agent research, 15 competitors analyzed) |
| 2026-02-05 | FCO-002 | SDK Deprecation + Smart Prompts (~$385/mo savings, 70% margin target) |
| 2026-02-05 | FCO-003 | Apify Replacement — DIY GMB scraper (~$15/mo savings) |

---

## 13. ACTION ITEMS

### Immediate
- [x] Create Siege Waterfall engines
- [x] Update lead_pool.py with WF-001 fields
- [x] Deploy Proxy Waterfall engine
- [ ] Execute migration 055 in Supabase
- [ ] Register SMS alpha tags with Twilio Trust Hub

### Fixed-Cost Fortress
- [ ] Tag Prefect flows with `tier: bulk` / `tier: realtime`
- [ ] Provision AWS Spot instance for bulk processing

### Q1 2026
- [ ] Integrate DNCR SOAP API
- [ ] Build ABN Bulk Extract ingestion pipeline
- [ ] Test Kaspr free tier for AU mobile accuracy
- [ ] Evaluate Cognism for premium mobile data

---

*Signed: Elliot, CTO | Ratified: 2026-02-04*
