# Lead Pool Architecture — Agency OS

**Version:** 1.0  
**Created:** January 6, 2026  
**Status:** Ready for Implementation  
**Phase:** 24

---

## Executive Summary

Agency OS will operate a **centralised lead pool** where all leads are owned and controlled by the platform. Leads are exclusively assigned to one client only — no lead will ever be contacted by multiple agencies.

This solves three critical problems:
1. **No spam:** One lead = one agency, forever
2. **No wasted data:** We save everything from enrichment, use it forever
3. **No cross-campaign collisions:** Platform controls distribution, not clients

---

## Problem Statement

### Problem 1: Cross-Campaign Lead Collision

**Current state:** Clients can create multiple campaigns. Same lead can appear in multiple campaigns and get contacted via multiple channels simultaneously.

**Risk:** Lead gets email Monday, LinkedIn Tuesday, SMS Wednesday — feels spammed, marks as spam, reputation damaged.

### Problem 2: Cross-Client Lead Collision

**Current state:** Two clients targeting the same industry (e.g., construction marketing) could both reach out to the same lead.

**Risk:** Lead gets pitched by two competing agencies — confusing, annoying, unprofessional.

### Problem 3: Wasted Enrichment Data

**Current state:** Apollo provides 50+ fields per lead. We only store ~20 fields.

**Risk:** Missing valuable personalisation signals, re-scraping data we already have, can't deduplicate properly.

---

## Solution: Centralised Lead Pool with Exclusive Assignment

### Core Principles

| Principle | Rule |
|-----------|------|
| **Platform Owns Leads** | Agency OS finds, enriches, and owns all leads |
| **Exclusive Assignment** | One lead = one client, permanently |
| **We Control Distribution** | Allocator decides who gets which lead, not clients |
| **Full Data Capture** | Save everything from enrichment sources |
| **JIT Validation** | Check every lead before every send |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  PLATFORM LEAD POOL                      │
│                                                         │
│  All leads enriched and owned by Agency OS              │
│  - Full Apollo data (50+ fields)                        │
│  - DataForSEO metrics                                   │
│  - ICP-extracted insights                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │      ALLOCATOR        │
              │                       │
              │  Rules:               │
              │  - Match client ICP   │
              │  - Check exclusivity  │
              │  - Fair distribution  │
              └───────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Client A │    │ Client B │    │ Client C │
    │          │    │          │    │          │
    │ Assigned:│    │ Assigned:│    │ Assigned:│
    │ Sarah    │    │ Mike     │    │ Emma     │
    │ Tom      │    │ Lisa     │    │ James    │
    │ Jane     │    │ Paul     │    │ Rachel   │
    └──────────┘    └──────────┘    └──────────┘

Sarah will NEVER be assigned to Client B or C.
Once assigned, that lead belongs to that client.
```

---

## Data Model

### Table: `lead_pool` (NEW — Platform-Wide)

All leads exist here first. This is the master record.

```sql
CREATE TABLE lead_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- ===== UNIQUE IDENTIFIERS =====
    apollo_id TEXT UNIQUE,              -- Apollo's internal ID (primary dedup key)
    email TEXT NOT NULL,
    linkedin_url TEXT,
    
    -- ===== PERSON DATA =====
    first_name TEXT,
    last_name TEXT,
    title TEXT,
    seniority TEXT,                     -- c_suite, vp, director, manager, etc.
    linkedin_headline TEXT,             -- Rich personalisation signal
    photo_url TEXT,
    twitter_url TEXT,
    phone TEXT,
    personal_email TEXT,
    
    -- Person Location
    city TEXT,
    state TEXT,
    country TEXT,
    timezone TEXT,                      -- Calculated from location
    
    departments TEXT[],                 -- Marketing, Sales, etc.
    
    -- Employment History (full context)
    employment_history JSONB,           -- [{company, title, start_date, end_date, is_current}]
    current_role_start_date DATE,       -- Extracted for easy querying
    
    -- ===== ORGANISATION DATA =====
    company_name TEXT,
    company_domain TEXT,
    company_website TEXT,
    company_linkedin_url TEXT,
    company_description TEXT,           -- Apollo's short_description
    company_logo_url TEXT,
    
    -- Company Firmographics
    company_industry TEXT,
    company_employee_count INTEGER,
    company_revenue BIGINT,
    company_revenue_range TEXT,
    company_founded_year INTEGER,
    company_country TEXT,
    company_city TEXT,
    company_state TEXT,
    company_postal_code TEXT,
    
    -- Company Signals
    company_is_hiring BOOLEAN,
    company_latest_funding_date DATE,
    company_total_funding BIGINT,
    company_technologies TEXT[],        -- Tech stack
    company_keywords TEXT[],            -- Business keywords
    
    -- ===== ENRICHMENT METADATA =====
    email_status TEXT,                  -- verified, guessed, unavailable
    enrichment_source TEXT,             -- apollo, clay, apify
    enrichment_confidence FLOAT,
    enriched_at TIMESTAMPTZ,
    last_enriched_at TIMESTAMPTZ,
    
    -- DataForSEO Metrics
    dataforseo_domain_rank INTEGER,
    dataforseo_organic_traffic INTEGER,
    dataforseo_spam_score FLOAT,
    dataforseo_enriched_at TIMESTAMPTZ,
    
    -- ===== POOL STATUS =====
    pool_status TEXT DEFAULT 'available',  -- available, assigned, converted, bounced, unsubscribed
    
    -- Global flags (applies across all clients)
    is_bounced BOOLEAN DEFAULT FALSE,
    bounced_at TIMESTAMPTZ,
    is_unsubscribed BOOLEAN DEFAULT FALSE,
    unsubscribed_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_email_in_pool UNIQUE (email),
    CONSTRAINT unique_linkedin_in_pool UNIQUE (linkedin_url) 
);

-- Indexes
CREATE INDEX idx_pool_apollo_id ON lead_pool(apollo_id);
CREATE INDEX idx_pool_email ON lead_pool(email);
CREATE INDEX idx_pool_domain ON lead_pool(company_domain);
CREATE INDEX idx_pool_status ON lead_pool(pool_status);
CREATE INDEX idx_pool_industry ON lead_pool(company_industry);
CREATE INDEX idx_pool_country ON lead_pool(company_country);
CREATE INDEX idx_pool_employee_count ON lead_pool(company_employee_count);
CREATE INDEX idx_pool_email_status ON lead_pool(email_status);
CREATE INDEX idx_pool_technologies ON lead_pool USING GIN(company_technologies);
```

### Table: `lead_assignments` (NEW — Client Allocations)

Tracks which client owns which lead.

```sql
CREATE TABLE lead_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Links
    lead_pool_id UUID NOT NULL REFERENCES lead_pool(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    -- Assignment Details
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by TEXT DEFAULT 'allocator',  -- allocator, manual, import
    
    -- Status
    status TEXT DEFAULT 'active',  -- active, released, converted
    released_at TIMESTAMPTZ,
    release_reason TEXT,           -- client_cancelled, lead_request, manual
    
    -- Outcome Tracking
    converted_at TIMESTAMPTZ,
    conversion_type TEXT,          -- meeting_booked, deal_closed, etc.
    
    -- Contact History Summary
    first_contacted_at TIMESTAMPTZ,
    last_contacted_at TIMESTAMPTZ,
    total_touches INTEGER DEFAULT 0,
    channels_used channel_type[] DEFAULT '{}',
    
    -- Response Tracking
    has_replied BOOLEAN DEFAULT FALSE,
    replied_at TIMESTAMPTZ,
    reply_intent TEXT,             -- interested, not_interested, out_of_office, etc.
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- CRITICAL: One lead can only be assigned to one client
    CONSTRAINT unique_lead_assignment UNIQUE (lead_pool_id)
);

-- Indexes
CREATE INDEX idx_assignments_client ON lead_assignments(client_id);
CREATE INDEX idx_assignments_status ON lead_assignments(status);
CREATE INDEX idx_assignments_lead ON lead_assignments(lead_pool_id);
```

### Table: `lead_activities` (Updated)

Track all outreach activities against the pool lead.

```sql
-- Add reference to pool
ALTER TABLE activities ADD COLUMN lead_pool_id UUID REFERENCES lead_pool(id);
```

### Migration from Current `leads` Table

The existing `leads` table becomes a **campaign view** — it references the pool and assignment.

```sql
-- Add pool references to existing leads table
ALTER TABLE leads ADD COLUMN lead_pool_id UUID REFERENCES lead_pool(id);
ALTER TABLE leads ADD COLUMN assignment_id UUID REFERENCES lead_assignments(id);

-- Existing leads table now serves as "campaign_leads" 
-- linking campaigns to assigned pool leads
```

---

## Lead Lifecycle

### Stage 1: Enrichment (Lead enters pool)

```
Source (Apollo/Clay/Apify)
         │
         ▼
    ┌─────────────┐
    │ Dedupe Check │ ←── Does this email/Apollo ID exist?
    └─────────────┘
         │
    ┌────┴────┐
    ▼         ▼
  EXISTS    NEW
    │         │
    ▼         ▼
  Update    Insert
  enrichment into pool
```

### Stage 2: Assignment (Lead goes to client)

```
Client ICP Criteria
         │
         ▼
    ┌─────────────┐
    │ Pool Query  │ ←── Match industry, size, location, etc.
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ Exclusivity │ ←── Filter out already-assigned leads
    │   Check     │
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │   Assign    │ ←── Create lead_assignments record
    └─────────────┘
         │
         ▼
    Lead now belongs to this client ONLY
```

### Stage 3: Outreach (JIT Validation)

```
Campaign wants to contact lead
         │
         ▼
    ┌─────────────────────────────┐
    │      JIT VALIDATION         │
    │                             │
    │  ✓ Lead still assigned?     │
    │  ✓ Not bounced globally?    │
    │  ✓ Not unsubscribed?        │
    │  ✓ Not contacted recently?  │
    │  ✓ Not already replied?     │
    │  ✓ Rate limit OK?           │
    │  ✓ Warmup ready?            │
    └─────────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
  PASS      FAIL
    │         │
    ▼         ▼
  Send     Skip/Queue
```

### Stage 4: Outcomes

| Event | Action |
|-------|--------|
| Email bounces | Mark `lead_pool.is_bounced = true` — affects ALL future assignments |
| Lead replies "not interested" | Mark in assignment, cooling period |
| Lead replies "interested" | Route to Closer Engine |
| Lead converts | Mark `assignment.status = 'converted'`, lead stays with client forever |
| Lead requests removal | Mark `lead_pool.is_unsubscribed = true` — no one contacts again |
| Client cancels subscription | Mark `assignment.status = 'released'`, lead returns to pool |

---

## JIT Validation Rules

Before ANY outreach (email, SMS, LinkedIn, voice, mail), run these checks:

```python
async def jit_validate(lead_pool_id: UUID, client_id: UUID, channel: str) -> ValidationResult:
    """
    Just-in-time validation before any outreach.
    Returns pass/fail with reason.
    """
    
    pool_lead = await get_pool_lead(lead_pool_id)
    assignment = await get_assignment(lead_pool_id, client_id)
    
    # 1. POOL-LEVEL CHECKS (global blockers)
    
    if pool_lead.is_bounced:
        return Fail("bounced_globally", "Email has bounced — blocks all sends")
    
    if pool_lead.is_unsubscribed:
        return Fail("unsubscribed_globally", "Lead requested no contact")
    
    if pool_lead.email_status == "guessed" and channel == "email":
        return Fail("unverified_email", "Email not verified — high bounce risk")
    
    # 2. ASSIGNMENT-LEVEL CHECKS (client-specific)
    
    if not assignment or assignment.status != "active":
        return Fail("not_assigned", "Lead not assigned to this client")
    
    if assignment.has_replied:
        return Fail("already_replied", "Lead has replied — route to Closer")
    
    if assignment.status == "converted":
        return Fail("already_converted", "Lead already converted")
    
    # 3. TIMING CHECKS
    
    if assignment.last_contacted_at:
        days_since = (now() - assignment.last_contacted_at).days
        if days_since < 3:  # Minimum gap between touches
            return Fail("too_recent", f"Last contacted {days_since} days ago")
    
    # 4. CHANNEL-SPECIFIC CHECKS
    
    if channel in assignment.channels_used:
        # Already used this channel — check cooling
        last_use = await get_last_channel_use(assignment.id, channel)
        if (now() - last_use).days < 7:
            return Fail("channel_cooling", f"Used {channel} recently")
    
    # 5. RATE LIMITS
    
    if not await check_rate_limit(client_id, channel):
        return Fail("rate_limit", "Daily limit reached for this channel")
    
    # 6. WARMUP (email only)
    
    if channel == "email":
        if not await check_warmup_ready(client_id):
            return Fail("warmup_not_ready", "Email warmup incomplete")
    
    return Pass()
```

---

## Allocator Logic

### Fair Distribution Algorithm

When multiple clients target the same ICP criteria:

```python
async def allocate_leads(client_id: UUID, icp_criteria: dict, count: int) -> list[UUID]:
    """
    Allocate leads from pool to client.
    Ensures fair distribution across competing clients.
    """
    
    # 1. Find matching leads in pool
    available_leads = await query_pool(
        industry=icp_criteria.get("industry"),
        employee_min=icp_criteria.get("employee_min"),
        employee_max=icp_criteria.get("employee_max"),
        country=icp_criteria.get("country"),
        titles=icp_criteria.get("titles"),
        pool_status="available",  # Not yet assigned
        email_status="verified",  # Only verified emails
    )
    
    # 2. Exclude leads assigned to ANY client
    available_leads = [l for l in available_leads if not l.has_assignment]
    
    # 3. Score and rank by fit
    scored_leads = score_leads_for_client(available_leads, icp_criteria)
    
    # 4. Take top N
    selected = scored_leads[:count]
    
    # 5. Create assignments
    for lead in selected:
        await create_assignment(
            lead_pool_id=lead.id,
            client_id=client_id,
            assigned_by="allocator"
        )
        
        # Update pool status
        lead.pool_status = "assigned"
        await save(lead)
    
    return [l.id for l in selected]
```

---

## Data Capture: Full Apollo Fields

### Updated Apollo Transform

```python
def transform_apollo_response(person: dict) -> dict:
    """
    Transform Apollo response — CAPTURE EVERYTHING.
    """
    org = person.get("organization", {}) or {}
    
    # Extract full employment history
    employment_history = []
    for job in person.get("employment_history", []):
        employment_history.append({
            "company": job.get("organization_name"),
            "title": job.get("title"),
            "start_date": job.get("start_date"),
            "end_date": job.get("end_date"),
            "is_current": job.get("current", False),
        })
    
    return {
        # ===== IDENTIFIERS =====
        "apollo_id": person.get("id"),
        "email": person.get("email"),
        "email_status": person.get("email_status"),  # CRITICAL
        "linkedin_url": person.get("linkedin_url"),
        
        # ===== PERSON =====
        "first_name": person.get("first_name"),
        "last_name": person.get("last_name"),
        "title": person.get("title"),
        "seniority": person.get("seniority"),
        "linkedin_headline": person.get("headline"),
        "photo_url": person.get("photo_url"),
        "twitter_url": person.get("twitter_url"),
        "phone": extract_phone(person),
        "personal_email": extract_personal_email(person),
        
        # Person Location
        "city": person.get("city"),
        "state": person.get("state"),
        "country": person.get("country"),
        "departments": person.get("departments", []),
        
        # Employment
        "employment_history": employment_history,
        "current_role_start_date": employment_history[0].get("start_date") if employment_history else None,
        
        # ===== ORGANISATION =====
        "company_name": org.get("name"),
        "company_domain": org.get("primary_domain"),
        "company_website": org.get("website_url"),
        "company_linkedin_url": org.get("linkedin_url"),
        "company_description": org.get("short_description"),
        "company_logo_url": org.get("logo_url"),
        
        # Firmographics
        "company_industry": org.get("industry"),
        "company_employee_count": org.get("estimated_num_employees"),
        "company_revenue": org.get("revenue"),
        "company_revenue_range": org.get("revenue_range"),
        "company_founded_year": org.get("founded_year"),
        "company_country": org.get("country"),
        "company_city": org.get("city"),
        "company_state": org.get("state"),
        "company_postal_code": org.get("postal_code"),
        
        # Signals
        "company_is_hiring": org.get("is_hiring"),
        "company_latest_funding_date": org.get("latest_funding_date"),
        "company_total_funding": org.get("total_funding"),
        "company_technologies": org.get("technologies", []),
        "company_keywords": org.get("keywords", []),
        
        # Meta
        "enrichment_source": "apollo",
        "enrichment_confidence": calculate_confidence(person),
        "enriched_at": datetime.now(),
    }
```

---

## Implementation Tasks

### Phase 24: Lead Pool Architecture

| Task ID | Task | Priority | Estimate |
|---------|------|----------|----------|
| POOL-001 | Create `lead_pool` table migration | High | 2h |
| POOL-002 | Create `lead_assignments` table migration | High | 1h |
| POOL-003 | Add pool references to existing `leads` table | High | 1h |
| POOL-004 | Update Apollo integration to capture all fields | High | 3h |
| POOL-005 | Create Lead Pool service (CRUD operations) | High | 4h |
| POOL-006 | Create Allocator service (assignment logic) | High | 4h |
| POOL-007 | Implement JIT Validation service | High | 4h |
| POOL-008 | Update Scout Engine to write to pool first | High | 3h |
| POOL-009 | Update Scorer Engine to read from pool | Medium | 2h |
| POOL-010 | Update Content Engine to use new fields | Medium | 3h |
| POOL-011 | Update campaign lead assignment flow | High | 4h |
| POOL-012 | Add pool admin UI (view pool, manual assign) | Low | 4h |
| POOL-013 | Migrate existing leads to pool | Medium | 2h |
| POOL-014 | Add pool analytics (utilisation, assignment rate) | Low | 2h |
| POOL-015 | Write tests for pool operations | High | 4h |

**Total Estimate:** ~43 hours

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Lead changes jobs | Keep assigned — client might still want them |
| Client cancels mid-campaign | Leads released back to pool with "released" status |
| Same person, different email | Apollo ID dedupes — same Apollo ID = same person |
| Lead requests data deletion | Mark unsubscribed, anonymise PII, keep record for audit |
| Pool runs out of leads for criteria | Alert client, suggest broadening ICP criteria |
| Lead converts then job changes | Stays with client forever — they earned that conversion |

---

## Success Metrics

| Metric | Target | Why |
|--------|--------|-----|
| Lead collision rate | 0% | No lead should ever be contacted by two clients |
| Enrichment data utilisation | 100% | All fields from Apollo should be stored |
| JIT validation block rate | <5% | Most leads should pass pre-send checks |
| Pool utilisation | >60% | Most pooled leads should be assigned |
| Bounce rate | <3% | Only verified emails should be sent |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Apollo API | ✅ | Already integrated |
| Supabase | ✅ | Database ready |
| Existing leads table | ✅ | Will be migrated/extended |
| Scorer Engine | ✅ | Will need updates |
| Content Engine | ✅ | Will need updates |
| Allocator Engine | ✅ | Will need updates |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration corrupts existing leads | Low | High | Backup before migration, test on staging |
| Pool query performance | Medium | Medium | Proper indexes, query optimisation |
| Assignment conflicts (race condition) | Low | Medium | Database-level unique constraint |
| Client unhappy with lead allocation | Medium | Medium | Transparent algorithm, fair distribution |

---

## Appendix: Current vs New Field Coverage

### Apollo Person Fields

| Field | Currently Saved | New Pool |
|-------|-----------------|----------|
| id (apollo_id) | ❌ | ✅ |
| email | ✅ | ✅ |
| email_status | ❌ | ✅ |
| first_name | ✅ | ✅ |
| last_name | ✅ | ✅ |
| title | ✅ | ✅ |
| seniority | ❌ | ✅ |
| linkedin_url | ✅ | ✅ |
| headline | ❌ | ✅ |
| photo_url | ❌ | ✅ |
| twitter_url | ❌ | ✅ |
| phone | ✅ | ✅ |
| personal_email | ❌ | ✅ |
| city | ❌ | ✅ |
| state | ❌ | ✅ |
| country | ❌ | ✅ |
| departments | ❌ | ✅ |
| employment_history | Partial | ✅ Full |

### Apollo Organisation Fields

| Field | Currently Saved | New Pool |
|-------|-----------------|----------|
| name | ✅ | ✅ |
| primary_domain | ✅ | ✅ |
| website_url | ❌ | ✅ |
| linkedin_url | ❌ | ✅ |
| short_description | ❌ | ✅ |
| logo_url | ❌ | ✅ |
| industry | ✅ | ✅ |
| employee_count | ✅ | ✅ |
| revenue | ❌ | ✅ |
| revenue_range | ❌ | ✅ |
| founded_year | ✅ | ✅ |
| country | ✅ | ✅ |
| city | ❌ | ✅ |
| state | ❌ | ✅ |
| postal_code | ❌ | ✅ |
| is_hiring | ✅ | ✅ |
| latest_funding_date | ✅ | ✅ |
| total_funding | ❌ | ✅ |
| technologies | ❌ | ✅ |
| keywords | ❌ | ✅ |

**Coverage improvement: 20 fields → 40+ fields**

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| CEO/Founder | Dave | | |
| Technical Review | Claude | January 6, 2026 | ✅ |
