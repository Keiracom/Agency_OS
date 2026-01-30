# Agency OS Architecture Map

**Created:** January 30, 2025  
**Purpose:** Comprehensive system architecture reference for Agency OS  
**Status:** Baseline Documentation

---

## Executive Summary

Agency OS is an AI-powered lead generation and outreach automation platform targeting Australian marketing agencies. It uses a multi-channel approach (email, LinkedIn, SMS, voice, direct mail) with intelligent lead scoring (ALS - Agency Lead Score) to prioritize and personalize outreach.

**Currency:** AUD  
**Primary Market:** Australia  
**Orchestration:** Prefect (self-hosted on Railway)  
**Database:** Supabase PostgreSQL  

---

## 1. API Integrations

### 1.1 Lead Enrichment

| API | Purpose | Cost Estimate | Data Provided |
|-----|---------|---------------|---------------|
| **Apollo.io** | Primary lead enrichment (Tier 1) | ~$0.05-0.10/lead | 50+ fields: email, phone, title, company firmographics, employment history, funding data, hiring signals |
| **Apify** | Web scraping waterfall (Tiers 1-2) | ~$0.25-0.50/1k pages | Website content for ICP extraction, LinkedIn profile data, social posts |
| **DataForSEO** | SEO metrics enrichment | ~$0.03/lead (Labs: $0.01 + Backlinks: $0.02) | Domain rank, organic traffic, keyword rankings, backlinks, spam score |
| **Clay** | Fallback enrichment (Tier 3) | Higher cost, 15% max usage | Additional enrichment when Apollo fails |
| **Serper** | Web search | ~$0.001/search | Google search results for research |

### 1.2 Email Sending

| API | Purpose | Cost Estimate | Notes |
|-----|---------|---------------|-------|
| **Salesforge** | Primary cold email (warmed mailboxes) | Per-mailbox subscription | Works with WarmForge-warmed domains; threading support |
| **Resend** | Transactional email (backup) | ~$0.001/email | Simple email sending, not for cold outreach |
| **Postmark** | Transactional (unused?) | Per-email pricing | Server token configured but appears secondary |

**Email Infrastructure Stack:**
- **InfraForge:** Domain provisioning
- **WarmForge:** Mailbox warmup
- **Salesforge:** Sending through warmed mailboxes

### 1.3 LinkedIn Automation

| API | Purpose | Cost Estimate | Notes |
|-----|---------|---------------|-------|
| **Unipile** | LinkedIn automation (primary) | ~70-85% cheaper than HeyReach | Connection requests, messages, profile data; 80-100 connections/day limit |
| **HeyReach** | *DEPRECATED* | — | Replaced by Unipile |

**LinkedIn Limits (configurable):**
- Connection requests: 80-100/day per account
- Messages: 100-150/day per account
- Business hours: 8am-6pm
- Weekend reduction: 50% Sat, 0% Sun

### 1.4 SMS & Phone

| API | Purpose | Cost Estimate | Notes |
|-----|---------|---------------|-------|
| **ClickSend** | SMS for Australia (primary) | Per-message AU rates | Native Australian provider; also supports direct mail |
| **Twilio** | Voice calls ONLY (via Vapi) | Per-minute telephony | NOT used for SMS in AU market |
| **DNCR (ACMA)** | Do Not Call Register compliance | Per-wash pricing | Australian regulatory compliance |

### 1.5 Voice AI Stack

| API | Purpose | Cost Estimate | Notes |
|-----|---------|---------------|-------|
| **Vapi** | Voice AI orchestration | Per-call + per-minute | Orchestrates STT → LLM → TTS |
| **ElevenLabs** | Text-to-Speech synthesis | Per-character | High-quality voice synthesis |
| **Twilio** | Telephony backbone | Per-minute | Provides phone numbers for Vapi |

**Voice Call Limits:**
- Business hours: 9am-5pm (skip 12-1pm lunch)
- Weekdays only (Mon-Fri)
- Max 50 calls/day/phone number

### 1.6 AI/LLM

| API | Purpose | Cost Estimate | Notes |
|-----|---------|---------------|-------|
| **Anthropic Claude** | All AI tasks | Daily budget limit enforced | Sonnet for most tasks, Haiku for classification |
| **SDK Brain** | Agentic AI wrapper | Per-call limits (default $2 AUD/call) | Wraps Claude with cost control, caching, turn limits |

**AI Spend Limits (daily, per tier):**
- Ignition: $50 AUD
- Velocity: $100 AUD  
- Dominance: $200 AUD

**Model Pricing (AUD, Jan 2026):**
- Claude Sonnet 4: $4.65/1M input, $23.25/1M output
- Claude Haiku: $1.24/1M input, $6.20/1M output

### 1.7 Infrastructure

| Service | Purpose | Notes |
|---------|---------|-------|
| **Supabase** | Database + Auth | PostgreSQL on AP-Southeast-1 |
| **Redis (Upstash)** | Caching ONLY | Not for task queues |
| **Prefect** | Workflow orchestration | Self-hosted on Railway |
| **Railway** | Backend hosting | FastAPI backend |
| **Vercel** | Frontend hosting | Next.js dashboard |
| **Sentry** | Error tracking | Exception monitoring |
| **Stripe** | Billing | Subscriptions and payments |

### 1.8 Calendar/CRM

| API | Purpose | Notes |
|-----|---------|-------|
| **Cal.com** | Meeting scheduling | Primary calendar integration |
| **Calendly** | Meeting scheduling | Alternative/backup |

---

## 2. Core Business Flows

### 2.1 Lead Enrichment Waterfall

```
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: Apollo Enrichment (Primary)                       │
│  • 50+ fields captured                                      │
│  • Email verification status                                │
│  • Company firmographics                                    │
│  • Employment history                                       │
│  SUCCESS → Stage 2 | FAIL → Clay fallback (max 15%)         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: LinkedIn Person Scrape (Apify)                    │
│  • Profile data                                             │
│  • Recent posts (personalization signals)                   │
│  • Connections/activity                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3: LinkedIn Company Scrape (Apify)                   │
│  • Company profile                                          │
│  • Company posts                                            │
│  • Employee count verification                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4: Claude Analysis                                   │
│  • Pain point identification                                │
│  • Personalization hooks                                    │
│  • Relevance scoring                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 5: ALS Scoring (Agency Lead Score)                   │
│  • Data Quality (20 pts)                                    │
│  • Authority (25 pts)                                       │
│  • Company Fit (25 pts)                                     │
│  • Timing (15 pts)                                          │
│  • Risk (15 pts)                                            │
│  HOT LEAD (85+) → SDK deep enrichment                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Website Scraping Waterfall

```
Tier 0: URL Validation → FREE, <2s
    ↓
Tier 1: Apify Cheerio (Static) → $0.25/1k pages, ~60% success
    ↓ (if fail)
Tier 2: Apify Playwright (JS) → $0.50/1k pages, ~80% success
    ↓ (if fail)
Tier 3: Camoufox + Residential Proxy → $0.02-0.05/page, ~95% success
    ↓ (if fail)
Tier 4: Manual Fallback → User intervention
```

### 2.3 ALS Score Tiers → Channel Eligibility

| Tier | Score | Channels Available |
|------|-------|-------------------|
| **Hot** | 85-100 | Email, SMS, LinkedIn, Voice, Mail |
| **Warm** | 60-84 | Email, LinkedIn, Voice |
| **Cool** | 35-59 | Email, LinkedIn |
| **Cold** | 20-34 | Email only |
| **Dead** | <20 | None (do not contact) |

### 2.4 Outreach Sequence Flow

```
┌─────────────────────────────────────────────────────────────┐
│  HOURLY OUTREACH FLOW (Prefect)                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  JIT VALIDATION (Before every outreach)                     │
│  • Client subscription active?                              │
│  • Client has credits?                                      │
│  • Campaign active?                                         │
│  • Lead not suppressed/bounced/converted?                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  RESOURCE ALLOCATION                                        │
│  • Email: Assign warmed mailbox from pool                   │
│  • LinkedIn: Assign account from seat pool                  │
│  • Phone: Assign provisioned number                         │
│  • Rate limit check per resource                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  CHANNEL EXECUTION (Parallel by channel)                    │
│  • Email: Salesforge with threading                         │
│  • LinkedIn: Unipile (profile view → delay → connect)       │
│  • SMS: ClickSend (DNCR check first)                        │
│  • Voice: Vapi (business hours only)                        │
│  • Mail: ClickSend direct mail                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ACTIVITY LOGGING                                           │
│  • Content snapshot for learning                            │
│  • Credit deduction                                         │
│  • Next step scheduling                                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.5 Lead Pool Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PLATFORM LEAD POOL (Centralized)                           │
│  • All leads enriched once, stored globally                 │
│  • De-duplication via Apollo ID                             │
│  • Status: available → assigned → converted/released        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  CLIENT ASSIGNMENT                                          │
│  • Exclusive assignment to one client                       │
│  • Assignment expires if not contacted                      │
│  • Released leads return to pool                            │
│  • Converted leads stay with client                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Data Model (Key Supabase Tables)

### 3.1 Core Entities

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   clients   │────<│  campaigns  │────<│    leads    │
└─────────────┘     └─────────────┘     └─────────────┘
      │                                        │
      │             ┌─────────────┐            │
      └────────────>│ memberships │            │
                    └─────────────┘            │
      ┌─────────────┐                          │
      │    users    │<─────────────────────────┘
      └─────────────┘
```

### 3.2 Table Descriptions

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `clients` | Tenant/customer accounts | tier, subscription_status, credits_remaining, stripe_customer_id |
| `users` | User profiles (linked to Supabase Auth) | email, timezone, notification preferences |
| `memberships` | Team membership (user↔client) | role (owner/admin/member/viewer) |
| `campaigns` | Outreach campaigns | status, permission_mode, ICP criteria, sequence config |
| `leads` | Leads assigned to clients/campaigns | ALS score, status, enrichment data, sequence position |
| `lead_pool` | Platform-wide lead repository | Apollo data, email status, assignment status |
| `lead_assignments` | Lead↔Client exclusive assignments | assignment_status, assignment dates |
| `activities` | All outreach activities logged | channel, content_snapshot, outcome |
| `client_intelligence` | Client proof points and intelligence | testimonials, case studies, ratings, differentiators |
| `client_personas` | Client ICP definitions | target industries, titles, company sizes |
| `resource_pool` | Email/phone/LinkedIn resources | resource type, health status, daily limits |
| `linkedin_seats` | LinkedIn account pool | account_id, daily_limit, warmup_status |
| `linkedin_connections` | LinkedIn connection tracking | profile_viewed_at, connection_status |
| `conversion_patterns` | What content/timing converts | learned patterns for optimization |
| `suppression_list` | Global/client suppression | email, domain, reason |

### 3.3 Key Enums

```sql
tier_type: ignition | velocity | dominance
subscription_status: trialing | active | past_due | cancelled | paused
lead_status: new | enriched | scored | in_sequence | converted | unsubscribed | bounced
channel_type: email | sms | linkedin | voice | mail
permission_mode: autopilot | co_pilot | manual
campaign_status: draft | active | paused | completed
pool_status: available | assigned | converted | bounced | unsubscribed | invalid
```

---

## 4. Pain Points & Inefficiencies

### 4.1 Cost Concerns

| Issue | Impact | Recommendation |
|-------|--------|----------------|
| **Dual email verification** | Apollo provides email_status, but may need secondary verification for older leads | Consider periodic re-verification for stale leads only |
| **LinkedIn scraping redundancy** | Apify scrapes LinkedIn, Apollo also has LinkedIn data | Consolidate LinkedIn data source; use Apollo first, Apify for fresh signals only |
| **Clay fallback at 15%** | Clay is expensive; used when Apollo fails | Investigate Apollo failure patterns; may reduce Clay usage |
| **DataForSEO Backlinks API** | $100/mo minimum after trial | Evaluate ROI; may be overkill for basic lead scoring |

### 4.2 Architectural Concerns

| Issue | Impact | Recommendation |
|-------|--------|----------------|
| **HeyReach still in codebase** | Deprecated but code remains | Full removal to prevent confusion; Unipile is the replacement |
| **Resend vs Salesforge overlap** | Two email integrations | Clarify: Salesforge for cold, Resend for transactional only |
| **Multiple calendar integrations** | Cal.com and Calendly both configured | Pick one primary; reduce maintenance burden |
| **SDK Brain cost per-call limit** | $2 AUD default may be too low for complex tasks | Monitor failures; consider task-specific limits |

### 4.3 Operational Gaps

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **No Prospeo integration** | Email finder mentioned in requirements but not implemented | Apollo handles email finding; Prospeo may be unnecessary |
| **Cloudflare bypass reliance** | Tier 3 Camoufox needed for 30-50% of AU sites | Monitor Tier 3 usage; optimize for cost |
| **DNCR caching at 24 hours** | Numbers can be added to DNCR quickly | Consider shorter TTL or real-time check for high-value leads |
| **Voice AI business hours only** | Limits call volume | Consider voicemail/async follow-up for after-hours |

### 4.4 Data Quality Concerns

| Issue | Impact | Recommendation |
|-------|--------|----------------|
| **Lead pool deduplication by Apollo ID only** | Leads from non-Apollo sources may duplicate | Add email-based dedup as secondary |
| **Stale enrichment data** | Leads enriched months ago may have outdated info | Implement `stale_lead_refresh_flow` on schedule |
| **Email status 'guessed' tier** | Apollo guessed emails have higher bounce risk | Weight 'guessed' emails lower in scoring; verify before high-touch channels |

### 4.5 Redundant Patterns

| Pattern | Location | Issue |
|---------|----------|-------|
| **Two enrichment flows** | `enrichment_flow.py` + `lead_enrichment_flow.py` | Clarify purpose; potential consolidation |
| **Multiple scraper actors** | Cheerio, Playwright, Camoufox | Necessary waterfall but complex debugging |
| **SDK agent complexity** | Multiple SDK agents (enrichment, email, voice KB) | Consider unified agent interface |

---

## 5. Cost Model Summary

### 5.1 Per-Lead Cost Estimate

| Stage | Low Estimate | High Estimate |
|-------|--------------|---------------|
| Apollo enrichment | $0.05 | $0.10 |
| Apify LinkedIn scrape | $0.01 | $0.05 |
| DataForSEO | $0.03 | $0.03 |
| AI analysis | $0.01 | $0.05 |
| **Total enrichment** | **$0.10** | **$0.23** |

### 5.2 Per-Outreach Cost Estimate

| Channel | Cost per Touch |
|---------|---------------|
| Email (Salesforge) | ~$0.01-0.05 |
| LinkedIn (Unipile) | ~$0.02-0.05 |
| SMS (ClickSend) | ~$0.05-0.10 |
| Voice (Vapi) | ~$0.10-0.50/minute |
| Direct Mail | ~$1.50-3.00 |

### 5.3 Monthly Infrastructure

| Service | Estimated Cost |
|---------|---------------|
| Railway (backend) | $20-50 |
| Vercel (frontend) | $0-20 |
| Supabase | $25-100 |
| Redis (Upstash) | $0-20 |
| DataForSEO | $100+ (after trial) |
| Apify | Usage-based |

---

## 6. File Structure Reference

```
Agency_OS/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── config/           # Settings, tier config
│   ├── engines/          # Business logic (scout, scorer, content, email, linkedin, sms, voice, mail)
│   ├── integrations/     # External API clients
│   ├── intelligence/     # Platform learning
│   ├── models/           # SQLAlchemy models
│   ├── orchestration/    # Prefect flows and tasks
│   ├── services/         # Business services
│   └── utils/            # Helpers
├── agents/               # AI agent definitions
├── skills/               # Skill implementations
├── supabase/
│   └── migrations/       # 53 migration files
├── frontend/             # Next.js dashboard
├── tests/                # Test suite
└── docs/                 # Specifications
```

---

## 7. Key Prefect Flows

| Flow | Schedule | Purpose |
|------|----------|---------|
| `outreach_flow` | Hourly | Execute scheduled outreach across channels |
| `lead_enrichment_flow` | On-demand | Enrich assigned leads |
| `enrichment_flow` | Daily | Batch enrichment with billing checks |
| `campaign_flow` | On-demand | Campaign activation/deactivation |
| `pool_population_flow` | On-demand | Populate lead pool from Apollo searches |
| `daily_pacing_flow` | Daily | Manage daily send volumes |
| `daily_digest_flow` | Daily | Generate client activity digests |
| `pattern_learning_flow` | Weekly | Learn from conversion patterns |
| `stale_lead_refresh_flow` | Weekly | Re-enrich old leads |
| `dncr_rewash_flow` | Monthly | Re-check DNCR compliance |
| `recording_cleanup_flow` | Daily | Clean old voice recordings |
| `crm_sync_flow` | Hourly | Sync leads to client CRMs |

---

## 8. Import Hierarchy (Enforced)

```
Layer 4: src/orchestration/  → Can import ALL below
Layer 3: src/engines/        → models, integrations only
Layer 2: src/integrations/   → models only
Layer 1: src/models/         → exceptions only
```

**Rule:** Never import upward. Engines cannot import from orchestration.

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-01-30 | Elliot (Audit) | Initial architecture map |
