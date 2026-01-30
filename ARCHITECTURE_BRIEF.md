# Agency OS Architecture Briefing

**Document Type:** Executive Architecture Overview  
**Last Updated:** 2026-01-28  
**Status:** Complete System (310+ tasks across 24 phases)

---

## Executive Summary

Agency OS is a **multi-tenant B2B lead generation SaaS platform** that automates the entire sales development process: lead sourcing, enrichment, scoring, multi-channel outreach, reply handling, meeting booking, and CRM push. It learns from conversion outcomes via a Conversion Intelligence System (CIS) to continuously improve targeting, timing, and messaging.

**Target Market:** Australian B2B agencies  
**Business Model:** Tiered subscriptions based on lead volume  
**Key Differentiator:** AI-powered personalization + multi-channel orchestration at scale

---

## 1. System Overview

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js / Vercel)                 │
│    Client Dashboard | Admin Panel | Onboarding | Marketing Pages   │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │ REST API
┌─────────────────────────────────▼──────────────────────────────────┐
│                        BACKEND (FastAPI / Railway)                  │
│  API Routes | Auth (Supabase JWT) | Multi-tenancy | WebSockets     │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  ORCHESTRATION│       │    ENGINES      │       │  INTEGRATIONS   │
│   (Prefect)   │       │ (Business Logic)│       │ (External APIs) │
│ Self-hosted   │       │                 │       │                 │
│ on Railway    │       │ Scout, Scorer,  │       │ Apollo, Apify   │
│               │       │ Allocator,      │       │ Salesforge,     │
│ Flows, Tasks, │       │ Content, Email, │       │ Vapi, Unipile   │
│ Schedules     │       │ Voice, LinkedIn │       │ ClickSend, etc  │
└───────────────┘       └─────────────────┘       └─────────────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────────┐
│                      DATA LAYER                                     │
│  PostgreSQL (Supabase) | Redis (Upstash) | RLS Multi-tenancy       │
└────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 14 (App Router), React Query, Shadcn/ui | Client dashboard, Admin panel |
| **Backend** | FastAPI, Python 3.11+, Pydantic | REST API, business logic |
| **Orchestration** | Prefect (self-hosted on Railway) | Workflow automation, scheduling |
| **AI Framework** | Pydantic AI, Claude (Anthropic) | Content generation, agents |
| **Database** | Supabase PostgreSQL (ap-southeast-1) | Primary data store, RLS |
| **Cache** | Redis (Upstash) | Caching, rate limiting |
| **Hosting** | Railway (backend), Vercel (frontend) | Deployment, scaling |

---

## 2. Core Components

### 2.1 Lead Pool & Assignment

| Component | Purpose |
|-----------|---------|
| **Lead Pool** | Platform-wide repository of all leads with 50+ enrichment fields |
| **Lead Assignments** | Exclusive assignment—one lead can only belong to ONE client |
| **JIT Validation** | Pre-send checks before any outreach (bounced, unsubscribed, rate limits) |

**Key Rule:** No lead is ever contacted by two different agencies.

### 2.2 Engines (Business Logic Layer)

| Engine | Function |
|--------|----------|
| **Scout** | Lead enrichment via 3-tier waterfall (Apollo → Apify → Clay) |
| **Scorer** | ALS (Agency Lead Score) calculation (0-100 scale) |
| **Allocator** | Channel assignment, timing optimization, resource round-robin |
| **Content** | AI-powered email/SMS/LinkedIn/voice content generation |
| **Email** | Salesforge integration, domain rotation, threading |
| **Voice** | Vapi + ElevenLabs integration, call scheduling |
| **LinkedIn** | Unipile integration, connection tracking |
| **SMS** | ClickSend integration, DNCR compliance |
| **Closer** | Reply intent classification, objection handling |

### 2.3 Conversion Intelligence System (CIS)

**5 Detectors** analyze conversion data to optimize future campaigns:

| Detector | Analysis |
|----------|----------|
| **WHO** | Which lead attributes convert (title, industry, company size) |
| **WHAT** | Which content patterns work (subject lines, CTAs, pain points) |
| **WHEN** | Optimal timing (day, hour, touch sequence) |
| **HOW** | Channel effectiveness by lead tier |
| **FUNNEL** | Downstream outcomes (show rate, deal velocity, win rate) |

**Output:** Weekly pattern learning updates ALS weights, targeting recommendations, and content suggestions.

### 2.4 Resource Pool

Platform-managed infrastructure assigned to clients on signup:

| Resource | Allocation (per tier) | Limit |
|----------|----------------------|-------|
| **Email Domains** | 3 / 5 / 9 | 50/day/domain |
| **Phone Numbers** | 1 / 2 / 3 | Voice: 50/day, SMS: 100/day |
| **LinkedIn Seats** | 4 / 7 / 14 | 17-20 connections/day/seat |

---

## 3. Data Flow

### 3.1 Complete Lead Journey

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. ONBOARDING                                                       │
│    Client submits website → ICP extracted via Claude → Resources    │
│    assigned → AI suggests campaigns → Leads sourced from Apollo     │
└─────────────────────────────────────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. ENRICHMENT                                                       │
│    Apollo (Tier 1) → Apify LinkedIn (Tier 1.5) → Clay (Tier 2)     │
│    → Score (ALS) → SDK deep research if Hot (85+)                   │
└─────────────────────────────────────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. OUTREACH (Hourly Flow)                                           │
│    JIT Validation → Content Generation → Channel Execution          │
│    Email → Voice → LinkedIn → SMS (5-step sequence, 12+ days)       │
└─────────────────────────────────────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. REPLY HANDLING                                                   │
│    Intent Classification → Auto-response or Human Handoff           │
│    → ALS Update → CIS Pattern Learning                              │
└─────────────────────────────────────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. MEETINGS & CRM                                                   │
│    Booking → Confirmation → Reminders → Outcome Tracking            │
│    → Deal Creation → One-way CRM Push (HubSpot/Pipedrive/Close)     │
└─────────────────────────────────────────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. MONTHLY LIFECYCLE (Month 2+)                                     │
│    Credit Reset → CIS Refinement → Lead Replenishment               │
│    → Campaign Optimization Suggestions                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Sequence Steps (Default 5-Step Cadence)

| Step | Day | Channel | Fallback |
|------|-----|---------|----------|
| 1 | 0 | Email | — |
| 2 | 3 | Voice | Email |
| 3 | 5 | LinkedIn | Skip |
| 4 | 8 | Email | — |
| 5 | 12 | SMS | Email |

---

## 4. Integration Points

### 4.1 External Service Map

| Category | Service | Purpose | Cost Model |
|----------|---------|---------|------------|
| **Data** | Apollo | B2B lead enrichment | ~$0.02/lead |
| **Data** | Apify | Web scraping (LinkedIn, websites) | ~$0.01-0.05/page |
| **Data** | Clay | Premium enrichment fallback | ~$0.04-0.08/credit |
| **Data** | DataForSEO | SEO signals for scoring | ~$0.03/domain |
| **Email** | Salesforge | Cold email sending | $48/month |
| **Email** | Warmforge | Email warmup | Free with Salesforge |
| **Email** | InfraForge | Domain/mailbox provisioning | Variable |
| **Email** | Resend | Transactional email | ~$0.001/email |
| **Voice** | Vapi | Voice AI orchestration | $0.35/minute |
| **Voice** | ElevenLabs | Text-to-speech | Per character |
| **Voice** | Twilio | Telephony infrastructure | Per minute |
| **SMS** | ClickSend | SMS (Australian, DNCR compliant) | $0.08/message |
| **LinkedIn** | Unipile | LinkedIn automation API | Per seat/month |
| **Mail** | ClickSend | Direct mail (Australian) | $0.59/letter |
| **AI** | Anthropic | Claude (content, agents) | Per token |
| **Database** | Supabase | PostgreSQL + Auth + Realtime | Per usage |
| **Cache** | Upstash | Redis (rate limits, caching) | Per request |

### 4.2 Webhook Integrations

| Source | Events |
|--------|--------|
| Stripe | subscription.*, invoice.*, payment.* |
| Salesforge | email.sent, email.opened, email.replied, email.bounced |
| Resend | email.replied, email.bounced |
| Vapi | call.completed, call.recording.ready |
| Unipile | connection.accepted, message.received |
| Calendly | invitee.created, invitee.canceled |

---

## 5. Key Concepts

### 5.1 ALS (Agency Lead Score) — 0-100 Scale

| Component | Max Points | Weight |
|-----------|------------|--------|
| Data Quality | 20 | 15% |
| Authority | 25 | 30% |
| Company Fit | 25 | 25% |
| Timing | 15 | 20% |
| Risk | 15 (deductions) | 10% |

### 5.2 ALS Tiers → Channel Access

| Tier | Score | Email | LinkedIn | Voice | SMS | Mail |
|------|-------|-------|----------|-------|-----|------|
| **Hot** | 85-100 | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Warm** | 60-84 | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Cool** | 35-59 | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Cold** | 20-34 | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Dead** | <20 | ❌ | ❌ | ❌ | ❌ | ❌ |

**Critical:** Hot threshold is **85**, not 80. SMS/Voice are premium channels reserved for high-quality leads.

### 5.3 Subscription Tiers

| Tier | Price/Month | Leads/Month | Campaigns | Daily Outreach |
|------|-------------|-------------|-----------|----------------|
| Ignition | $2,500 AUD | 1,250 | 5 (3 AI + 2 custom) | 50 |
| Velocity | $5,000 AUD | 2,250 | 10 (6 AI + 4 custom) | 100 |
| Dominance | $7,500 AUD | 4,500 | 20 (12 AI + 8 custom) | 200 |

**Founding discount:** 50% off, locked for life if subscription maintained.

### 5.4 SDK vs Smart Prompts

| Scenario | Approach | Rationale |
|----------|----------|-----------|
| Standard leads (ALS < 85) | Smart Prompts | Use enriched data already paid for |
| Hot leads (ALS ≥ 85) | SDK Agents | Worth extra cost for personalization |
| Reply/objection handling | SDK Agents | Requires real-time reasoning |
| Meeting prep | SDK Agents | Deep research for booked meetings |

**Cost Impact:** SDK everywhere = ~$250/month. Smart Prompts default = ~$65/month (75% savings).

---

## 6. Critical Paths

### 6.1 New Client Activation (Day 0-3)

```
1. Signup → Payment confirmed via Stripe webhook
2. ICP extraction → Scrape website, Claude analyzes
3. Resource assignment → 3-9 domains, 1-3 phones from pool
4. Campaign suggestions → AI generates 3-5 segment ideas
5. Lead sourcing → Apollo search based on ICP
6. Warmup check → Email domains need 14-21 days warmup
7. First outreach → Day 14+ (after domain warmup)
```

### 6.2 Hourly Outreach Cycle

```
1. Query leads (status=IN_SEQUENCE, client active, credits > 0)
2. Group by channel
3. JIT validate each lead
4. Check rate limits (resource-level, not client-level)
5. Generate content (Smart Prompt or SDK for Hot)
6. Execute send via provider
7. Log activity with content snapshot (for CIS learning)
```

### 6.3 Meeting Conversion Path

```
Lead replied with "interested"
    → Closer engine classifies intent
    → Auto-response or human handoff
    → Calendly link sent
    → Meeting booked
    → Confirmation + reminder emails
    → Show/no-show tracked
    → Deal created if positive outcome
    → CRM push (HubSpot/Pipedrive/Close)
```

---

## 7. Gotchas & Non-Obvious Details

### 7.1 Architecture Gotchas

| Topic | Gotcha | Why It Matters |
|-------|--------|----------------|
| **Rate limits** | Per-resource, not per-client | 50/day/domain, not 50/day/client. Clients share resource capacity. |
| **Redis usage** | Caching ONLY, not task queues | Prefect handles all orchestration. Don't use Redis for background jobs. |
| **Hot threshold** | ALS 85, not 80 | Common mistake. Hot leads get SDK, all premium channels. |
| **Import hierarchy** | 4 strict layers | Models → Integrations → Engines → Orchestration. No backwards imports. |
| **Soft deletes** | Never hard DELETE | All tables use `deleted_at` timestamp. Data retention requirement. |
| **Connection pooling** | Port 6543 for app | Transaction pooler. Port 5432 only for migrations. |
| **LinkedIn seats** | Client-provided | Unlike domains/phones, LinkedIn seats aren't from platform pool. |

### 7.2 Operational Gotchas

| Topic | Gotcha | Impact |
|-------|--------|--------|
| **Domain warmup** | 14-21 days | New clients can't send email immediately. Plan ahead. |
| **Email threading** | Uses In-Reply-To headers | Follow-ups must reference original message ID. |
| **DNCR compliance** | Australian numbers only | Must check Do Not Call Register before SMS/voice to +61. |
| **LinkedIn daily limits** | 17-20 safe, max 80-100 | Conservative defaults to avoid account flags. |
| **Profile view delay** | 10-30 min before connect | LinkedIn connection requests need prior profile view. |
| **Stale data refresh** | 7 days trigger | Leads scheduled for outreach get Apify refresh if data > 7 days old. |

### 7.3 Business Logic Gotchas

| Topic | Gotcha | Consequence |
|-------|--------|-------------|
| **Credit deduction** | On enrichment, not sourcing | Credits consumed when lead is successfully enriched. |
| **Channel cooldown** | 5 days same channel | Can't email same lead twice within 5 days. |
| **Touch cooldown** | 2 days any channel | Minimum 2 days between any touches to same lead. |
| **CIS minimum** | 20 conversions | Pattern learning only runs for clients with 20+ conversions (90 days). |
| **Campaign allocation** | Must sum to 100% | Constraint enforced at database level. |
| **One CRM per client** | Not multiple | Each client can connect exactly one CRM integration. |

### 7.4 SDK/AI Gotchas

| Topic | Gotcha | Optimization |
|-------|--------|--------------|
| **SDK eligibility** | Tiered, not all Hot | Only sparse data, executives, enterprise, or recently funded get SDK enrichment. |
| **AI spend limiter** | Daily cap enforced | Default $100 AUD/day across all AI calls. |
| **Prompt caching** | Use cached_tokens field | Track cache hit rate for cost optimization. |
| **Priority weighting** | HIGH fields marked with ★ | AI prompts weight recent funding, hiring, pain points higher. |

---

## 8. Database Schema Overview

### Core Tables (24 models)

| Table | Purpose | Key Relationships |
|-------|---------|-------------------|
| `clients` | Tenant organizations | → users, campaigns, leads |
| `users` | User accounts (Supabase Auth) | → memberships |
| `memberships` | User-Client with roles | Many-to-many |
| `campaigns` | Outreach campaigns | → leads, sequences, resources |
| `campaign_sequences` | Multi-step sequences | Belongs to campaign |
| `leads` | Campaign-assigned leads | → activities, pool |
| `lead_pool` | Platform lead repository | 50+ enrichment fields |
| `activities` | Outreach activity log | Content snapshots for CIS |
| `conversion_patterns` | CIS learned patterns | WHO/WHAT/WHEN/HOW/FUNNEL |
| `resource_pool` | Platform resources | Domains, phones |
| `client_resources` | Client-resource assignments | Exclusive allocation |
| `meetings` | Meeting lifecycle | → deals |
| `deals` | Pipeline tracking | → CRM push |
| `client_crm_configs` | CRM connections | HubSpot/Pipedrive/Close |

### Multi-tenancy

- All tenant-scoped tables include `client_id` FK
- Row Level Security (RLS) enabled
- Compound unique constraints within tenant scope

---

## 9. Phase Summary

| Phase Range | Focus | Status |
|-------------|-------|--------|
| 1-10 | Core platform (98 tasks) | ✅ Complete |
| 11-16 | Post-deploy features (48 tasks) | ✅ Complete |
| 17-21 | Launch prep (72 tasks) | ✅ Complete |
| 22-23 | Marketing automation, Platform intel | 📋 Post-launch |
| 24A-G | CIS data gaps (66 tasks) | ✅ Complete |
| 24H | LinkedIn connection | 📋 Planned |

**Total:** ~310 tasks, ~243 hours estimated

---

## 10. Quick Reference

### API Base URLs

| Environment | URL |
|-------------|-----|
| Production API | `https://agency-os-api.up.railway.app` |
| Prefect Dashboard | `https://prefect-server-production-f9b1.up.railway.app/dashboard` |
| Frontend | Vercel (custom domain) |

### Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Database connection |
| `SUPABASE_ANON_KEY` | Client-side auth |
| `PREFECT_API_URL` | Orchestration server |
| `SALESFORGE_API_KEY` | Email sending |
| `VAPI_API_KEY` | Voice AI |
| `UNIPILE_API_KEY` | LinkedIn automation |

### Important Files

| Path | Purpose |
|------|---------|
| `src/config/tiers.py` | Tier definitions, ALS thresholds, channel access |
| `src/services/jit_validator.py` | Pre-send validation rules |
| `src/engines/smart_prompts.py` | Content generation with priority weighting |
| `src/detectors/*.py` | CIS detector implementations |
| `docs/architecture/TODO.md` | Gap tracking (currently 0 open gaps) |

---

## Summary

Agency OS is a comprehensive B2B lead generation platform with:

1. **Automated lead lifecycle** from sourcing to CRM push
2. **Multi-channel orchestration** (email, voice, LinkedIn, SMS, mail)
3. **AI-powered personalization** via Smart Prompts and SDK agents
4. **Conversion Intelligence** that learns and optimizes continuously
5. **Platform-managed resources** for reliable, compliant outreach
6. **Strict multi-tenancy** with exclusive lead assignment

The architecture prioritizes cost efficiency (Smart Prompts over SDK), compliance (DNCR, email warmup), and continuous improvement (CIS weekly learning cycles).

---

*Document generated from Agency OS architecture documentation.*
*For detailed specs, see `/home/elliotbot/clawd/Agency_OS/docs/architecture/`*
