# Onboarding Flow — Agency OS

**Purpose:** Document the client onboarding process including ICP extraction, resource assignment, and post-onboarding setup.
**Status:** PARTIAL
**Last Updated:** 2026-01-21

---

## Overview

The onboarding flow is triggered when a new client signs up and provides their website URL. The system automatically extracts their Ideal Customer Profile (ICP) from their website, assigns platform resources based on their subscription tier, and sets up initial campaigns with AI-generated suggestions.

The flow consists of three main phases:
1. **ICP Extraction** — Scrape client website, extract ICP using AI, optionally enhance with SDK research
2. **Resource Assignment** — Allocate email domains, phone numbers, and other resources from the platform pool
3. **Post-Onboarding Setup** — Generate AI campaign suggestions, create draft campaigns, source leads from Apollo

---

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| **ICP Onboarding Flow** | `src/orchestration/flows/onboarding_flow.py` | Main Prefect flow for ICP extraction |
| **Post-Onboarding Flow** | `src/orchestration/flows/post_onboarding_flow.py` | Campaign generation and lead sourcing |
| **ICP Scraper Engine** | `src/engines/icp_scraper.py` | Website scraping with waterfall (Cheerio→Playwright→Camoufox) |
| **Client Intelligence Engine** | `src/engines/client_intelligence.py` | Multi-source client data scraping for SDK |
| **Campaign Suggester** | `src/engines/campaign_suggester.py` | AI-powered campaign suggestions |
| **ICP Discovery Agent** | `src/agents/icp_discovery_agent.py` | Pydantic AI agent for ICP extraction |
| **SDK ICP Agent** | `src/agents/sdk_agents/icp_agent.py` | Claude SDK agent for enhanced ICP |
| **Resource Assignment Service** | `src/services/resource_assignment_service.py` | Pool-to-client resource allocation |
| **Lead Allocator Service** | `src/services/lead_allocator_service.py` | Assign leads to campaigns |
| **Onboarding API** | `src/api/routes/onboarding.py` | REST endpoints for onboarding UI |
| **Client Model** | `src/models/client.py` | ICP fields stored on client record |

---

## Data Flow

### Phase 1: ICP Extraction

```
User submits website URL
        ↓
[POST /api/v1/onboarding/analyze]
        ↓
Create icp_extraction_jobs record (status: pending)
        ↓
Trigger Prefect: icp_onboarding_flow
        ↓
┌─────────────────────────────────────┐
│ Step 1: Scrape Website              │
│   - Validate URL (url_validator.py) │
│   - Cheerio scrape (Apify)          │
│   - Playwright fallback if needed   │
│   - Extract social links            │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Step 2: Basic ICP Extraction        │
│   - ICP Discovery Agent (Claude)    │
│   - Extract: industries, titles,    │
│     pain points, company sizes,     │
│     locations, services offered     │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Step 3: SDK Enhancement (if enabled)│
│   - Web search for additional data  │
│   - Research buying signals         │
│   - Build confidence score          │
│   - Cost: max $1.50 per extraction  │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Step 4: Client Intelligence Scrape  │
│   - LinkedIn company profile        │
│   - Twitter, Facebook, Instagram    │
│   - Trustpilot, Google reviews      │
│   - Extract proof points for SDK    │
└─────────────────────────────────────┘
        ↓
Save to icp_extraction_jobs (status: completed)
        ↓
Auto-apply ICP to clients table (if auto_apply=true)
        ↓
User reviews/confirms ICP in UI
        ↓
[POST /api/v1/onboarding/confirm]
        ↓
Mark icp_confirmed_at on clients table
```

### Phase 2: Resource Assignment

```
Payment confirmed (Stripe webhook)
        ↓
Trigger Prefect: resource_assignment_flow
        ↓
┌─────────────────────────────────────┐
│ Get tier allocations:               │
│   Ignition:  3 email domains, 1 phone│
│   Velocity:  5 email domains, 2 phones│
│   Dominance: 9 email domains, 3 phones│
│   (LinkedIn seats: 4/7/14 per tier) │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Select best resources from pool:    │
│   - Prioritize warm/healthy domains │
│   - Check availability status       │
│   - Skip LinkedIn (client-provided) │
└─────────────────────────────────────┘
        ↓
Create client_resources records (links pool→client)
        ↓
Update pool status to IN_USE
        ↓
Check buffer levels, alert if < 40%
```

### Phase 3: Post-Onboarding Setup

```
ICP confirmed
        ↓
Trigger Prefect: post_onboarding_setup_flow
        ↓
┌─────────────────────────────────────┐
│ Step 1: Verify ICP Ready            │
│   - Check industries, titles exist  │
│   - Get tier from client record     │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Step 2: Generate Campaign Suggestions│
│   - AI analyzes ICP + services      │
│   - Generates 3-5 campaign ideas    │
│   - Based on tier slots available   │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Step 3: Create Draft Campaigns      │
│   - Create campaigns as DRAFT status│
│   - Set allocation % per campaign   │
│   - Generate sequences (5 steps)    │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Step 4: Source Leads from Apollo    │
│   - Use ICP criteria for search     │
│   - Source tier-based lead count    │
│     Ignition: 1,250/month           │
│     Velocity: 2,250/month           │
│     Dominance: 4,500/month          │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│ Step 5: Assign Leads to Campaigns   │
│   - Distribute by allocation %      │
│   - Match lead attributes to ICP    │
└─────────────────────────────────────┘
        ↓
Update onboarding_status = 'completed'
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/onboarding/analyze` | POST | Submit website URL for ICP extraction |
| `/api/v1/onboarding/status/{job_id}` | GET | Check extraction job progress |
| `/api/v1/onboarding/result/{job_id}` | GET | Get extracted ICP profile |
| `/api/v1/onboarding/confirm` | POST | Confirm ICP and trigger post-onboarding |
| `/api/v1/clients/{id}/icp` | GET | Get client's current ICP profile |
| `/api/v1/clients/{id}/icp` | PUT | Update client's ICP profile (admin only) |

---

## Key Rules

1. **ICP Extraction is Async** — Always runs via Prefect flow, not inline with API request. Frontend polls for status.

2. **Auto-Apply Default** — ICP is automatically applied to client record but NOT marked as confirmed. User must explicitly confirm.

3. **SDK Enhancement Optional** — Controlled by `sdk_brain_enabled` setting. Adds ~$1.50 cost but improves ICP quality.

4. **Resource Assignment Trigger** — Only happens after payment confirmed (Stripe webhook), not during ICP extraction.

5. **LinkedIn Seats Client-Provided** — Unlike email domains and phone numbers, LinkedIn seats are not from the platform pool.

6. **Tier-Based Lead Sourcing** — Post-onboarding sources leads based on monthly tier quota, not a fixed amount.

7. **Campaigns Start as DRAFT** — AI-suggested campaigns are created as drafts. User must activate them.

---

## Configuration

| Setting | Default | Notes |
|---------|---------|-------|
| `sdk_brain_enabled` | True | Enable SDK enhancement for ICP |
| `auto_apply` | True | Auto-apply ICP to client record |
| `auto_activate_campaigns` | False | Keep campaigns as drafts |
| ICP extraction timeout | 15 min | Flow timeout for icp_onboarding_flow |
| Post-onboarding timeout | 10 min | Flow timeout for post_onboarding_setup_flow |

---

## Database Tables

### icp_extraction_jobs

Tracks async ICP extraction jobs.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `client_id` | UUID | Client being onboarded |
| `status` | text | pending, running, completed, failed |
| `website_url` | text | URL being analyzed |
| `current_step` | text | Current step name |
| `completed_steps` | int | Progress tracking |
| `total_steps` | int | Total steps (default 8) |
| `extracted_icp` | jsonb | Extracted ICP data |
| `error_message` | text | Error if failed |
| `started_at` | timestamp | When extraction started |
| `completed_at` | timestamp | When extraction finished |

### clients (ICP fields)

ICP data stored directly on client record.

| Column | Type | Purpose |
|--------|------|---------|
| `website_url` | text | Client's website |
| `company_description` | text | AI-extracted description |
| `services_offered` | text[] | Services they offer |
| `value_proposition` | text | Value prop |
| `icp_industries` | text[] | Target industries |
| `icp_company_sizes` | text[] | Target company sizes |
| `icp_locations` | text[] | Target locations |
| `icp_titles` | text[] | Target job titles |
| `icp_pain_points` | text[] | Target pain points |
| `als_weights` | jsonb | Custom ALS weights |
| `icp_extracted_at` | timestamp | When ICP was extracted |
| `icp_confirmed_at` | timestamp | When user confirmed ICP |
| `icp_extraction_job_id` | UUID | Link to extraction job |

---

## Scraper Waterfall Architecture

The ICP scraper uses a tiered fallback approach:

| Tier | Method | Use Case | Cost |
|------|--------|----------|------|
| 0 | URL Validation | Check URL accessibility | Free |
| 1 | Cheerio (Apify) | Static HTML sites | ~$0.01/page |
| 2 | Playwright (Apify) | JavaScript-rendered sites | ~$0.03/page |
| 3 | Camoufox | Anti-bot protected sites | ~$0.10/page |
| 4 | Manual Fallback | Sites that block all scrapers | N/A |

Each tier is tried in order until successful. The `tier_used` field on `ScrapedWebsite` tracks which tier succeeded.

---

## Cross-References

- [`../business/TIERS_AND_BILLING.md`](../business/TIERS_AND_BILLING.md) — Tier quotas and credit system
- [`../distribution/RESOURCE_POOL.md`](../distribution/RESOURCE_POOL.md) — Resource pool and allocation
- [`./ENRICHMENT.md`](./ENRICHMENT.md) — Lead enrichment after sourcing (to be created)
- [`../content/SDK_AND_PROMPTS.md`](../content/SDK_AND_PROMPTS.md) — SDK agent details
- [`../business/CAMPAIGNS.md`](../business/CAMPAIGNS.md) — Campaign lifecycle (to be created)

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
