# Enrichment Flow — Agency OS

**Purpose:** Document the lead enrichment pipeline including waterfall architecture, SDK enhancement, and pool operations.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-21

---

## Overview

The enrichment system uses a three-tier waterfall architecture to progressively enrich leads using Apollo, Apify, and Clay integrations. Hot leads (ALS 85+) receive additional SDK-powered deep research. The system operates in two modes:

1. **Daily Batch Enrichment** — Processes NEW leads with JIT billing validation
2. **Assignment Enrichment** — Full LinkedIn + personalization pipeline for allocated leads

Enrichment is a prerequisite for channel allocation—leads cannot be contacted until enriched and scored.

---

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| Daily Batch Flow | `src/orchestration/flows/enrichment_flow.py` | Batch enrichment with billing checks |
| Assignment Flow | `src/orchestration/flows/lead_enrichment_flow.py` | Full pipeline per assignment |
| Scout Engine | `src/engines/scout.py` | Three-tier waterfall logic |
| Apollo Integration | `src/integrations/apollo.py` | Tier 1 primary enrichment |
| Apify Integration | `src/integrations/apify.py` | LinkedIn scraping + fallback |
| Clay Integration | `src/integrations/clay.py` | Tier 2 premium fallback |
| SDK Enrichment Agent | `src/agents/sdk_agents/enrichment_agent.py` | Hot lead deep research |
| Lead Model | `src/models/lead.py` | Enrichment field storage |
| Lead Pool Model | `src/models/lead_pool.py` | Pool enrichment fields |

---

## Data Flow

### Daily Batch Enrichment Flow

```
Query leads (status=NEW, billing valid)
        ↓
Batch leads by client
        ↓
For each batch:
    ┌─────────────────────────────────────┐
    │ SCOUT.enrich_batch()                │
    │   └─ For each lead:                 │
    │       ├─ Check Redis cache (Tier 0) │
    │       ├─ Apollo enrich (Tier 1)     │
    │       ├─ Apify supplement (if gaps) │
    │       └─ Clay fallback (Tier 2)     │
    │          (max 15% of batch)         │
    └─────────────────────────────────────┘
        ↓
Score leads (ALS calculation)
        ↓
┌─────────────────────────────────────┐
│ For Hot leads (ALS >= 85):          │
│   ├─ Check SDK eligibility signals  │
│   └─ If signals: SDK deep research  │
└─────────────────────────────────────┘
        ↓
Allocate channels by ALS tier
        ↓
Deduct 1 credit per enriched lead
```

### Assignment Enrichment Flow

```
Get assignment + pool lead data
        ↓
┌─────────────────────────────────────┐
│ SCOUT.enrich_linkedin_for_assignment│
│   ├─ Apify person profile + 5 posts │
│   └─ Apify company profile + 5 posts│
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Claude Personalization Analysis     │
│   ├─ Extract pain points            │
│   ├─ Generate icebreaker hooks      │
│   └─ Recommend best channel         │
└─────────────────────────────────────┘
        ↓
Score lead (ALS with LinkedIn boost)
        ↓
┌─────────────────────────────────────┐
│ For Hot leads (ALS >= 85):          │
│   ├─ SDK enrichment (if signals)    │
│   ├─ SDK email generation (all Hot) │
│   └─ SDK voice KB (all Hot)         │
└─────────────────────────────────────┘
        ↓
Update assignment with all data
```

---

## Three-Tier Waterfall Architecture

| Tier | Source | When Used | Cost | Coverage |
|------|--------|-----------|------|----------|
| 0 | Redis Cache | Always checked first | Free | Variable |
| 1 | Apollo | Primary enrichment | 1 credit | ~70% |
| 1.5 | Apify | LinkedIn supplement if Apollo incomplete | ~$0.01-0.05 | +15% |
| 2 | Clay | Fallback if Tier 1 fails | Premium | +10% |

### Tier Progression Rules

1. **Cache First** — Check Redis with version prefix (`v1`)
2. **Apollo Primary** — Lookup by email, LinkedIn URL, or name+domain
3. **Apify Supplement** — If Apollo missing LinkedIn data, scrape profile
4. **Clay Budget** — Max 15% of batch can fall back to Clay
5. **Validation Gate** — 0.70 confidence required to accept enrichment

### Required Fields

Enrichment must provide:
- `email` (verified)
- `first_name`
- `last_name`
- `company`

Without these, lead remains unenriched.

---

## SDK Enrichment (Hot Leads)

### Eligibility

Hot leads (ALS >= 85) with at least ONE trigger (tiered approach, any one qualifies):

**Phase 4 Tiered Triggers (Primary):**

| Trigger | Condition | Why SDK Helps |
|---------|-----------|---------------|
| Sparse Data | data completeness < 50% | Fill gaps via web search |
| Enterprise | `company_employee_count` >= 500 | Press coverage likely exists |
| Executive Title | CEO, Founder, VP, Director, Head of | Speaking engagements, podcasts |
| Recent Funding | `company_latest_funding_date` < 90 days | Press releases, investor news |

**Legacy Signals (also checked):**

| Signal | Condition |
|--------|-----------|
| Actively Hiring | `company_open_roles` >= 3 |
| Tech Stack Match | `tech_stack_match_score` > 0.8 |
| LinkedIn Engaged | `linkedin_engagement_score` > 70 |
| Referral Source | `source` == "referral" |

**Key insight:** SDK enrichment only valuable when Google search results exist. Average mid-market contacts have no press/podcast coverage.

### SDK Output Structure

```python
EnrichmentOutput:
    funding: FundingInfo (amount, date, investors, round)
    hiring: HiringInfo (total_roles, sales_roles, key_positions)
    recent_news: list[NewsItem]
    pain_points: list[str]  # Specific to company
    personalization_hooks: list[str]
    competitor_intel: CompetitorIntel
    conversation_starters: list[str]
```

### SDK Cost Controls

| Agent | Max Cost (AUD) | Max Turns |
|-------|----------------|-----------|
| Enrichment | $1.50 | 8 |
| Email | $0.50 | 3 |
| Voice KB | $2.00 | 3 |

---

## Apollo Integration

### Lookup Methods

1. **Email** — Direct email match (highest confidence)
2. **LinkedIn URL** — Profile URL lookup
3. **Name + Domain** — Fuzzy match by name and company domain

### Fields Captured (50+)

| Category | Fields |
|----------|--------|
| Contact | email, phone, first_name, last_name, title, linkedin_url, personal_email |
| Organization | company, domain, industry, employee_count, website, description |
| Hiring | is_hiring, open_roles (sales/engineering/etc) |
| Funding | latest_funding_date, funding_stage, total_funding, investors |
| Location | city, state, country, timezone |
| Email Status | verified, guessed, invalid, catch_all |

### Email Status Handling

Apollo returns `email_status`:
- **verified** — Safe to email
- **guessed** — Risky, may bounce
- **invalid** — Do not email
- **catch_all** — May work, proceed with caution

Email engine should check status before sending to reduce bounces.

---

## Apify Integration

### LinkedIn Person Scraping

| Field | Description |
|-------|-------------|
| headline | Current role/tagline |
| about | Bio summary |
| experience | Last 5 roles |
| education | Schools/degrees |
| skills | Top 10 skills |
| posts | Last 5 posts with engagement |

### LinkedIn Company Scraping

| Field | Description |
|-------|-------------|
| name | Company name |
| description | About section |
| industry | Industry category |
| specialties | Focus areas |
| employee_count | Company size |
| founded_year | Year founded |
| posts | Last 5 company posts |

### Fallback Tiers (Internal to Apify)

1. **Cheerio** — Static HTML, fast, ~60% success
2. **Playwright** — JS rendering, ~80% success

Returns `needs_fallback=True` if both fail.

---

## Pool Operations

### search_and_populate_pool()

```
Apollo ICP search (industries, titles, locations)
        ↓
For each result:
    ├─ Check global suppression
    ├─ Check client suppression
    ├─ Check domain suppression
    └─ Insert into lead_pool (ON CONFLICT skip)
        ↓
Return population stats
```

### enrich_to_pool()

Single-lead enrichment into pool with all 50+ Apollo fields.

### Suppression Tables

| Table | Purpose |
|-------|---------|
| global_suppression | Platform-wide blacklist |
| client_suppression | Client-specific do-not-contact |
| domain_suppression | Competitor/blocked domains |

---

## Key Rules

1. **Waterfall Order** — Always follow: Cache → Apollo → Apify → Clay
2. **Clay Budget** — Never exceed 15% of batch for Clay fallback
3. **Confidence Threshold** — Reject enrichment below 0.70 confidence
4. **JIT Billing** — Check `credits_remaining > 0` before enriching
5. **SDK Eligibility** — Hot (85+) AND at least one priority signal
6. **Soft Deletes** — All queries check `deleted_at IS NULL`
7. **Cache Versioning** — Use `v1` prefix for safe invalidation

---

## Configuration

| Setting | Default | Notes |
|---------|---------|-------|
| `enrichment_confidence_threshold` | 0.70 | Min confidence to accept |
| `clay_max_budget_percent` | 0.15 | Max batch % for Clay |
| `sdk_enrichment_max_cost` | $1.50 | Per-lead cap |
| `sdk_enrichment_max_turns` | 8 | Agent turn limit |
| `linkedin_posts_to_scrape` | 5 | Posts per profile |
| `cache_version_prefix` | v1 | Redis key prefix |

---

## Billing Model

| Operation | Cost | Deducted When |
|-----------|------|---------------|
| Lead enrichment | 1 credit | After successful enrichment |
| Apollo search | Included | N/A (platform cost) |
| Clay fallback | Included | N/A (platform cost) |
| SDK enhancement | Tracked separately | Logged to `sdk_cost_aud` |

Credits deducted via `deduct_client_credits_task()` after enrichment completes.

---

## Cross-References

- [`../business/TIERS_AND_BILLING.md`](../business/TIERS_AND_BILLING.md) — Credit system and quotas
- [`../business/SCORING.md`](../business/SCORING.md) — ALS calculation and tiers
- [`./ONBOARDING.md`](./ONBOARDING.md) — Initial lead sourcing
- [`./OUTREACH.md`](./OUTREACH.md) — Channel execution after enrichment (to be created)
- [`../content/SDK_AND_PROMPTS.md`](../content/SDK_AND_PROMPTS.md) — SDK agent details

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
