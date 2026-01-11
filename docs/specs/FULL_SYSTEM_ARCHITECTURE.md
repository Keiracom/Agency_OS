# Agency OS — Complete System Architecture

**Version**: 2.0 (Merged)  
**Date**: December 26, 2025  
**Status**: Production Deployed + Architecture Extended  
**Classification**: Internal Technical Documentation

---

## Executive Summary

Agency OS is a unified client acquisition platform—a "Bloomberg Terminal for Client Acquisition"—designed for marketing agencies. This document merges:
1. **The existing implemented system** (Phases 1-12A complete, 122/141 tasks)
2. **Extended full architecture** for scaling and future phases

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Frontend Layer](#3-frontend-layer)
4. [Backend Layer](#4-backend-layer)
5. [Database Layer](#5-database-layer)
6. [Agent Architecture](#6-agent-architecture)
7. [Skills System](#7-skills-system)
8. [Orchestration Layer](#8-orchestration-layer)
9. [Channel Integrations](#9-channel-integrations)
10. [Data Pipeline](#10-data-pipeline)
11. [Observability](#11-observability)
12. [Security & Compliance](#12-security--compliance)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Future Phases](#14-future-phases)

---

## 1. System Overview

### 1.1 Production URLs

| Service | URL | Platform |
|---------|-----|----------|
| User Dashboard | https://agency-os-liart.vercel.app/dashboard | Vercel |
| Admin Dashboard | https://agency-os-liart.vercel.app/admin | Vercel |
| Backend API | https://agency-os-production.up.railway.app | Railway |
| Health Check | https://agency-os-production.up.railway.app/api/v1/health | Railway |
| Database | jatzvazlbusedwsnqxzr.supabase.co | Supabase |

### 1.2 Core Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Multi-tenancy** | Row-level security with tenant IDs (client_id) |
| **Decoupled execution** | Separate worker services for channel sending |
| **Agent-first** | AI agents handle ICP discovery, campaign generation, scoring |
| **Skills-based** | Modular, testable AI capabilities |
| **Batch-first orchestration** | Prefect-scheduled campaigns with event-triggered capabilities |
| **Webhook-first** | Primary reply processing via webhooks, schedules as safety nets |

### 1.3 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENCY OS PLATFORM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FRONTEND (Vercel)                           │   │
│  │  Next.js 14 • App Router • shadcn/ui • React Query • Supabase Auth  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      API GATEWAY (Railway)                          │   │
│  │           FastAPI • JWT Auth • Rate Limiting • Soft Delete          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────────┐    │
│  │   ENGINES   │          │   AGENTS    │          │   PREFECT       │    │
│  │  (11 Total) │          │ + SKILLS    │          │   ORCHESTRATOR  │    │
│  └─────────────┘          └─────────────┘          └─────────────────┘    │
│         │                          │                          │            │
│         └──────────────────────────┼──────────────────────────┘            │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       DATABASE (Supabase)                           │   │
│  │     PostgreSQL • RLS • Real-time • 13 Migrations Applied            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────────┐    │
│  │   EMAIL     │          │   SMS/VOICE │          │   LINKEDIN      │    │
│  │   Resend    │          │   Twilio    │          │   HeyReach      │    │
│  │   Postmark  │          │   Vapi      │          │                 │    │
│  └─────────────┘          └─────────────┘          └─────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

### 2.1 Locked Technology Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Workflow Orchestration** | Prefect (self-hosted on Railway) | Full control, no external dependency |
| **Agent Framework** | Pydantic AI | Type-safe validation, contract enforcement |
| **Backend Framework** | FastAPI on Railway | Async, fast, Python-native |
| **Frontend Framework** | Next.js 14 on Vercel | React, SSR, edge functions |
| **Database** | Supabase PostgreSQL (Port 6543) | RLS, real-time, auth included |
| **Authentication** | Supabase Auth | Built-in, no Clerk needed |
| **Cache** | Redis (Upstash) | Caching ONLY — Prefect handles orchestration |
| **AI Provider** | Anthropic Claude | Content, ICP, scoring |

### 2.2 Full Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 14, React 18, TypeScript | Web application |
| UI Components | shadcn/ui, Tailwind CSS | Design system |
| State Management | React Query, Zustand | Server/client state |
| Hosting (Frontend) | Vercel | Edge deployment, CDN |
| API | FastAPI | REST API |
| Hosting (Backend) | Railway | Container orchestration |
| Database | Supabase PostgreSQL | Primary data store |
| Cache | Redis (Upstash) | Caching, rate limiting |
| Orchestration | Prefect Cloud | Workflow scheduling |
| AI Runtime | Claude API (Anthropic) | Agent execution |
| Email Outbound | Resend | Email sending |
| Email Inbound | Postmark | Webhook processing |
| SMS | Twilio | SMS + DNCR check |
| Voice | Vapi + ElevenLabs | Voice AI |
| LinkedIn | HeyReach | Automation (17/day/seat) |
| Direct Mail | ClickSend | Physical mail (AU) |
| Enrichment | Apollo, Apify, Clay | Lead data |
| Scraping | Apify | Website content |
| Error Tracking | Sentry | Production monitoring |

### 2.3 Redis Usage Rules

**What Redis IS Used For:**
- Enrichment data cache (90-day TTL, versioned keys with v1 prefix)
- Rate limiting counters (resource-level, not client-level)
- AI spend tracking (daily circuit breaker)
- Session data

**What Redis IS NOT Used For:**
- Task queues (use Prefect)
- Background job processing (use Prefect)
- Workflow orchestration (use Prefect)

---

## 3. Frontend Layer

### 3.1 Application Structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── auth/callback/route.ts     # OAuth handler
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Dashboard home
│   │   ├── campaigns/
│   │   │   ├── page.tsx               # List
│   │   │   ├── [id]/page.tsx          # Detail
│   │   │   └── new/page.tsx           # Create (simplified)
│   │   ├── leads/
│   │   │   ├── page.tsx               # List with ALS filtering
│   │   │   └── [id]/page.tsx          # Detail with timeline
│   │   ├── reports/page.tsx
│   │   └── settings/
│   │       ├── page.tsx
│   │       └── icp/page.tsx           # ICP configuration
│   ├── admin/                         # Platform admin (20 pages)
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Command center
│   │   ├── revenue/page.tsx
│   │   ├── clients/
│   │   ├── costs/
│   │   ├── system/
│   │   └── compliance/
│   └── onboarding/page.tsx            # ICP extraction flow
├── components/
│   ├── ui/                            # shadcn components
│   ├── layout/                        # Sidebar, Header
│   ├── admin/                         # Admin-specific
│   └── campaigns/
│       └── permission-mode-selector.tsx
└── lib/
    └── supabase.ts                    # Type-safe client
```

### 3.2 Key Frontend Features

| Feature | Description |
|---------|-------------|
| **Permission Modes** | Autopilot (full AI), Co-Pilot (AI suggests, user approves), Manual |
| **ALS Tier Colors** | Hot (red), Warm (orange), Cool (blue), Cold (gray), Dead (black) |
| **React Query** | Server state management with caching |
| **Real-time** | Supabase subscriptions for live updates |
| **Admin Dashboard** | 20 pages for platform management |

### 3.3 Authentication Flow

1. User clicks "Sign in with Google" or enters email/password
2. Supabase Auth handles OAuth flow
3. Callback route (`/auth/callback/route.ts`) exchanges code for session
4. JWT stored in HTTP-only cookies
5. All API requests include JWT in Authorization header
6. Backend validates JWT and extracts user + client context via memberships

---

## 4. Backend Layer

### 4.1 Service Architecture

Railway hosts the FastAPI application as a single service with internal routing:

```
Railway Service: agency-os-production
├── API Routes (/api/v1/*)
├── Webhook Handlers (/api/v1/webhooks/*)
├── Admin Routes (/api/v1/admin/*)
└── Health Checks (/api/v1/health/*)
```

### 4.2 API Route Structure

```
/api/v1
├── /auth                      # Supabase Auth (handled by frontend)
├── /health
│   ├── GET /                  # Basic health
│   ├── GET /ready             # Readiness (DB, Redis, Prefect)
│   └── GET /live              # Liveness
├── /clients/{id}
│   ├── /campaigns             # CRUD + status management
│   ├── /leads                 # CRUD + enrichment + bulk
│   ├── /icp                   # ICP configuration
│   └── /resources             # Resources per campaign
├── /campaigns
│   ├── POST /generate         # Generate from ICP
│   ├── GET /templates         # List generated templates
│   └── POST /templates/{id}/launch
├── /onboarding
│   ├── POST /analyze          # Start ICP extraction
│   ├── GET /status/{job_id}   # Check progress
│   ├── GET /result/{job_id}   # Get extracted ICP
│   └── POST /confirm          # Confirm ICP
├── /reports                   # Analytics endpoints
├── /webhooks
│   ├── POST /postmark         # Email inbound/bounce/spam
│   ├── POST /twilio           # SMS inbound/status
│   ├── POST /heyreach         # LinkedIn replies
│   └── POST /dispatch         # Outbound to clients
└── /admin                     # Platform admin endpoints
    ├── GET /stats             # Command center KPIs
    ├── GET /clients           # All clients with health
    ├── GET /costs/ai          # AI spend breakdown
    └── GET /suppression       # Global suppression list
```

### 4.3 Middleware Stack

```python
# Execution order
app.use(corsMiddleware)              # 1. CORS
app.use(requestLoggerMiddleware)     # 2. Logging
app.use(authMiddleware)              # 3. JWT verification
app.use(clientContextMiddleware)     # 4. Extract client via memberships
app.use(rateLimitMiddleware)         # 5. Per-client rate limiting
app.use(softDeleteMiddleware)        # 6. deleted_at IS NULL check
```

### 4.4 Dependency Injection Pattern

All engines receive database sessions as arguments (Rule 11):

```python
# ❌ WRONG
class ScoutEngine:
    def __init__(self):
        self.db = AsyncSessionLocal()

# ✅ CORRECT
class ScoutEngine:
    async def enrich(self, db: AsyncSession, domain: str):
        ...
```

---

## 5. Database Layer

### 5.1 Migrations Applied (13 total)

| Migration | Purpose |
|-----------|---------|
| 001_foundation.sql | Enums, UUIDv7, helper functions |
| 002_clients_users_memberships.sql | Multi-tenant core |
| 003_campaigns.sql | Campaigns with allocation |
| 004_leads_suppression.sql | Leads, ALS fields, suppression |
| 005_activities.sql | Activity log with threading |
| 006_permission_modes.sql | Approval queue |
| 007_webhook_configs.sql | Webhook configurations |
| 008_audit_logs.sql | Audit trail triggers |
| 009_rls_policies.sql | Row-level security |
| 010_platform_admin.sql | Admin tables |
| 011_fix_user_insert_policy.sql | RLS INSERT fix |
| 012_client_icp_profile.sql | ICP fields + portfolio |
| 013_campaign_templates.sql | Generated campaign templates |

### 5.2 Core Tables

```sql
-- Clients (tenants)
clients (
    id UUID PRIMARY KEY,
    name TEXT,
    tier tier_type,  -- ignition, velocity, dominance
    subscription_status subscription_status,
    credits_remaining INTEGER,
    default_permission_mode permission_mode,
    -- ICP fields
    website_url TEXT,
    icp_industries TEXT[],
    icp_company_sizes TEXT[],
    als_weights JSONB,
    ...
)

-- Leads with ALS scoring
leads (
    id UUID PRIMARY KEY,
    client_id UUID REFERENCES clients,
    campaign_id UUID REFERENCES campaigns,
    email TEXT,
    -- ALS Score components
    als_score INTEGER,      -- 0-100
    als_tier TEXT,          -- hot, warm, cool, cold, dead
    als_data_quality INTEGER,
    als_authority INTEGER,
    als_company_fit INTEGER,
    als_timing INTEGER,
    als_risk INTEGER,
    ...
)

-- Activities with email threading
activities (
    id UUID PRIMARY KEY,
    client_id UUID,
    campaign_id UUID,
    lead_id UUID,
    channel channel_type,
    action TEXT,
    provider_message_id TEXT,  -- For In-Reply-To
    metadata JSONB,
    ...
)
```

### 5.3 Row-Level Security

```sql
-- All tenant-scoped tables use this pattern
CREATE POLICY tenant_isolation ON leads
    FOR ALL
    USING (
        client_id IN (
            SELECT client_id FROM memberships 
            WHERE user_id = auth.uid()
            AND accepted_at IS NOT NULL
        )
    );
```

---

## 6. Agent Architecture

### 6.1 Agents Implemented

| Agent | Purpose | Skills Used |
|-------|---------|-------------|
| **CMO Agent** | Campaign/lead orchestration decisions | - |
| **Content Agent** | Personalized copy generation | - |
| **Reply Agent** | Intent classification | - |
| **ICP Discovery Agent** | Extract ICP from website | 8 skills |
| **Campaign Generation Agent** | Generate campaigns from ICP | 3 skills |

### 6.2 Agent Base Class

```python
class BaseAgent:
    """
    Pydantic AI base with spend limiting.
    All agents track token/cost usage.
    """
    
    async def run(
        self,
        db: AsyncSession,
        input: BaseModel,
        context: AgentContext
    ) -> AgentResult:
        # Check budget before execution
        if not await self.check_budget(context.client_id):
            raise AIBudgetExceededError()
        
        # Execute with Claude API
        result = await self.execute(input)
        
        # Track costs
        await self.track_usage(context.client_id, result.tokens, result.cost)
        
        return result
```

---

## 7. Skills System

### 7.1 Skills Architecture

Skills are modular, testable AI capabilities that agents orchestrate:

```
src/agents/skills/
├── base_skill.py              # Base class + registry
├── website_parser.py          # Parse HTML → structured pages
├── service_extractor.py       # Find services offered
├── value_prop_extractor.py    # Find value proposition
├── portfolio_extractor.py     # Find client logos/cases
├── industry_classifier.py     # Classify industries
├── company_size_estimator.py  # Estimate team size
├── icp_deriver.py             # Derive ICP from portfolio
├── als_weight_suggester.py    # Suggest ALS weights
├── sequence_builder.py        # Build 6-touch sequence
├── messaging_generator.py     # Generate channel copy
└── campaign_splitter.py       # Handle multi-industry
```

### 7.2 Skill Base Class

```python
class BaseSkill(ABC, Generic[InputT, OutputT]):
    """
    Each skill is a focused, testable capability with:
    - name: Unique identifier
    - description: When to use this skill
    - Input: Pydantic model for input validation
    - Output: Pydantic model for output validation
    - system_prompt: Instructions for Claude
    """
    
    name: str
    description: str
    system_prompt: str
    
    class Input(BaseModel):
        pass
    
    class Output(BaseModel):
        pass
    
    @abstractmethod
    async def execute(
        self, 
        input: InputT, 
        anthropic: AnthropicClient
    ) -> SkillResult[OutputT]:
        pass
```

### 7.3 ICP Discovery Flow

```
User enters website URL
        │
        ▼
ICP Scraper Engine (data fetching only)
├── Apify: scrape website HTML
└── Apollo: LinkedIn company data
        │
        ▼
ICP Discovery Agent (orchestrates skills)
├── WebsiteParserSkill → structured pages
├── ServiceExtractorSkill → services
├── ValuePropExtractorSkill → value prop
├── PortfolioExtractorSkill → client logos
├── IndustryClassifierSkill → industries
├── ICPDeriverSkill → ICP pattern
└── ALSWeightSuggesterSkill → custom weights
        │
        ▼
User confirms/edits
        │
        ▼
Database populated + Scorer uses custom weights
```

### 7.4 Campaign Generation Flow

```
ICP Profile (confirmed)
        │
        ▼
Campaign Generation Agent
├── SequenceBuilderSkill
│   └── "Growth Engine" 6-touch sequence
│   └── Adaptive timing by industry
├── MessagingGeneratorSkill
│   └── Email (subject + body)
│   └── SMS (160 chars)
│   └── LinkedIn (connection + InMail)
│   └── Voice (talking points)
└── CampaignSplitterSkill
    └── Multi-industry handling
        │
        ▼
campaign_templates table
        │
        ▼
User reviews → Launch → campaigns table
```

---

## 8. Orchestration Layer

### 8.1 Prefect Flows

| Flow | Schedule | Purpose |
|------|----------|---------|
| campaign_flow | On-demand | Campaign activation |
| enrichment_flow | 0 2 * * * (safety net) | Daily enrichment |
| outreach_flow | Hourly 8-6 Mon-Fri (safety net) | Outreach execution |
| reply_recovery_flow | 0 */6 * * * | Safety net for missed webhooks |
| icp_onboarding_flow | On-demand | ICP extraction |

### 8.2 Prefect Tasks

All tasks enforce JIT validation (Rule 13):

```python
@task
async def send_email_task(lead_id: str, campaign_id: str):
    """
    JIT validation before every send:
    1. Client subscription active?
    2. Client has credits?
    3. Campaign not paused/deleted?
    4. Lead not bounced/unsubscribed?
    5. Rate limit not exceeded?
    """
    async with get_db_session() as db:
        # Validate all conditions
        if not await validate_send_conditions(db, lead_id, campaign_id):
            return TaskResult.skipped()
        
        # Execute send
        result = await email_engine.send(db, lead_id, campaign_id)
        return TaskResult.success(result)
```

### 8.3 Rate Limits

| Channel | Rate Limit | Enforced At |
|---------|------------|-------------|
| Email | 50/day/domain | Resource level |
| SMS | 100/day/number | Resource level |
| LinkedIn | 17/day/seat | Resource level |
| Voice | 50/day/number | Resource level |

---

## 9. Channel Integrations

### 9.1 The 11 Engines

| Engine | Purpose | Integration |
|--------|---------|-------------|
| **Scout** | Data enrichment | Apollo, Apify, Clay |
| **Scorer** | ALS calculation | Internal |
| **Allocator** | Channel assignment | Internal |
| **Email** | Email outreach | Resend |
| **SMS** | SMS outreach | Twilio |
| **LinkedIn** | LinkedIn outreach | HeyReach |
| **Voice** | Voice calls | Vapi + ElevenLabs |
| **Mail** | Direct mail | ClickSend |
| **Closer** | Reply handling | Internal + AI |
| **Content** | Copy generation | Anthropic |
| **Reporter** | Metrics aggregation | Internal |
| **ICP Scraper** | Website scraping | Apify |

### 9.2 Waterfall Enrichment

```
Tier 0: Check cache (v1: prefix, 90-day TTL)
    ├── Hit → Return cached data
    └── Miss → Continue
        │
        ▼
Tier 1: Apollo + Apify hybrid
    ├── Success → Cache and return
    └── Partial → Continue
        │
        ▼
Tier 2: Clay fallback (max 15% of batch)
    └── Final data or fail
```

### 9.3 Email Threading

All follow-up emails include `In-Reply-To` header for proper threading (Rule 18):

```python
# In Resend integration
headers = {
    "In-Reply-To": f"<{original_message_id}@agency-os.com>",
    "References": f"<{original_message_id}@agency-os.com>"
}
```

---

## 10. Data Pipeline

### 10.1 ALS (Agency Lead Score) Formula

| Component | Max Points | Factors |
|-----------|------------|---------|
| Data Quality | 20 | Email verified (8), phone (6), LinkedIn (4), personal email (2) |
| Authority | 25 | Owner/CEO (25), C-suite (22), VP (18), Director (15), Manager (7-10) |
| Company Fit | 25 | Industry match (10), employee count 5-50 (8), Australia (7) |
| Timing | 15 | New role <6mo (6), hiring (5), funded <12mo (4) |
| Risk | 15 | Deductions for bounced, unsubscribed, competitor, bad title |

### 10.2 Tier Assignment

| ALS Score | Tier | Channels Available |
|-----------|------|-------------------|
| 85-100 | Hot | Email, SMS, LinkedIn, Voice, Direct Mail |
| 60-84 | Warm | Email, LinkedIn, Voice |
| 35-59 | Cool | Email, LinkedIn |
| 20-34 | Cold | Email only |
| 0-19 | Dead | None (suppress) |

### 10.3 Lead Lifecycle

```
NEW → ENRICHED → SCORED → IN_SEQUENCE → CONVERTED
                                    ↘
                               UNSUBSCRIBED / BOUNCED / NOT_INTERESTED
```

---

## 11. Observability

### 11.1 Logging

- **Sentry**: Error tracking for both backend and frontend
- **Railway Logs**: API request/response logging
- **Prefect Cloud**: Flow execution monitoring

### 11.2 Key Metrics

| Metric | Location | Purpose |
|--------|----------|---------|
| API latency | Railway | Performance |
| Error rate | Sentry | Reliability |
| Flow status | Prefect | Orchestration health |
| AI spend | Database | Cost control |
| Channel deliverability | Activities table | Delivery tracking |

### 11.3 AI Spend Limiter

```python
# Daily budget check before any AI call
async def check_budget(client_id: str) -> bool:
    today_spend = await get_daily_ai_spend(client_id)
    daily_limit = await get_client_ai_limit(client_id)
    return today_spend < daily_limit
```

---

## 12. Security & Compliance

### 12.1 Authentication

- **Provider**: Supabase Auth
- **Methods**: Google OAuth, Email/Password
- **Session**: JWT in HTTP-only cookies
- **MFA**: Supported via Supabase

### 12.2 Authorization

- **RLS**: Row-level security on all tenant tables
- **Roles**: Owner, Admin, Member, Viewer
- **Platform Admin**: `is_platform_admin` flag on users table

### 12.3 Data Protection

- **Encryption**: TLS 1.3 in transit, AES-256 at rest (Supabase default)
- **Soft Delete**: All deletions set `deleted_at` timestamp (Rule 14)
- **Audit Trail**: `audit_logs` table with triggers

### 12.4 Email Compliance

- Australian Spam Act 2003
- US CAN-SPAM Act
- DNCR check for Australian SMS
- One-click unsubscribe headers
- Global suppression list

---

## 13. Deployment Architecture

### 13.1 Infrastructure

| Service | Platform | Configuration |
|---------|----------|---------------|
| Frontend | Vercel | Sydney region, security headers |
| Backend | Railway | Python 3.11, auto-scaling |
| Database | Supabase | PostgreSQL 15, RLS enabled |
| Cache | Upstash | Redis, serverless |
| Orchestration | Prefect Cloud | Self-hosted worker on Railway |

### 13.2 Environment Variables

**Railway (Backend):**
- DATABASE_URL
- SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET
- REDIS_URL
- ANTHROPIC_API_KEY
- PREFECT_API_URL (self-hosted on Railway, no API key needed)
- Integration keys (Apollo, Resend, Twilio, etc.)

**Vercel (Frontend):**
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY
- NEXT_PUBLIC_API_URL

### 13.3 Database Pooling

- **Application/Prefect**: Transaction Pooler (Port 6543)
- **Migrations**: Session Pooler (Port 5432)
- **Pool limits**: pool_size=5, max_overflow=10

---

## 14. Future Phases

### 14.1 Phase Status

| Phase | Status | Tasks |
|-------|--------|-------|
| 1-10 | ✅ Complete | 98/98 |
| 11 (ICP Discovery) | ✅ Complete | 18/18 |
| 12A (Campaign Gen Core) | ✅ Complete | 6/6 |
| 12B (Campaign Gen Enhancement) | ⏸️ Deferred | 0/2 |
| 13 (Frontend-Backend) | 🔴 Planned | 0/7 |
| 14 (Missing UI) | 🔴 Planned | 0/4 |
| 15 (Live UX Testing) | 🔴 Planned | 0/6 |

**Current Progress**: 122/141 tasks (87%)

### 14.2 Planned Work

**Phase 13: Frontend-Backend Connection**
- Replace mock data with real API calls
- Connect Dashboard, Leads, Campaigns, Reports pages
- Error/loading states

**Phase 14: Missing UI Features**
- Replies page (unified inbox)
- Meetings widget
- Credits badge
- Content visibility in Lead timeline

**Phase 15: Live UX Testing**
- Real API integration testing
- YOU as test lead receiving actual emails/SMS
- Dashboard verification with real data

### 14.3 Extended Architecture (Future)

For scaling beyond initial deployment:

**Voice AI Enhancement (Vapi)**
- Outbound AI cold calls
- Real-time conversation handling
- Call recording and transcription

**Direct Mail at Scale**
- Address verification
- Bulk postcard campaigns
- Delivery tracking

**Advanced Analytics**
- Revenue attribution
- Multi-touch attribution
- Cohort analysis

---

## Appendix A: Import Hierarchy (Enforced)

```
LAYER 1 (Bottom): src/models/
├── Pure Pydantic models + SQLAlchemy
├── NO imports from src/engines/
├── NO imports from src/orchestration/
└── CAN import from src/exceptions.py

LAYER 2: src/integrations/
├── External API wrappers
├── CAN import from src/models/
├── NO imports from src/engines/
└── NO imports from src/orchestration/

LAYER 3: src/engines/
├── Business logic
├── CAN import from src/models/
├── CAN import from src/integrations/
├── NO imports from other engines (pass data as args)
└── NO imports from src/orchestration/

LAYER 4 (Top): src/orchestration/
├── The glue layer
├── CAN import from everything below
└── Coordinates engines, never imported by them
```

---

## Appendix B: Critical Rules Summary

| Rule | Description |
|------|-------------|
| Rule 11 | Session passed as argument, never instantiated in engines |
| Rule 12 | Import hierarchy enforced |
| Rule 13 | JIT validation before every outreach |
| Rule 14 | Soft delete only (deleted_at IS NULL check) |
| Rule 15 | AI spend limiter on all Anthropic calls |
| Rule 16 | Cache versioning with v1 prefix |
| Rule 17 | Resource-level rate limits (not client-level) |
| Rule 18 | Email threading via In-Reply-To headers |
| Rule 20 | Webhook-first architecture (schedules are safety nets) |

---

## Appendix C: File Structure

```
C:\AI\Agency_OS\
├── src/
│   ├── api/
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── campaigns.py
│   │       ├── leads.py
│   │       ├── webhooks.py
│   │       ├── webhooks_outbound.py
│   │       ├── reports.py
│   │       ├── admin.py
│   │       ├── onboarding.py
│   │       └── campaign_generation.py
│   ├── models/
│   │   ├── base.py, client.py, user.py
│   │   ├── membership.py, campaign.py
│   │   ├── lead.py, activity.py
│   ├── integrations/
│   │   ├── supabase.py, redis.py
│   │   ├── apollo.py, apify.py, clay.py
│   │   ├── resend.py, postmark.py
│   │   ├── twilio.py, heyreach.py
│   │   ├── vapi.py, elevenlabs.py, clicksend.py
│   │   └── anthropic.py
│   ├── engines/
│   │   ├── base.py, scout.py, scorer.py
│   │   ├── allocator.py, email.py, sms.py
│   │   ├── linkedin.py, voice.py, mail.py
│   │   ├── closer.py, content.py
│   │   ├── reporter.py, icp_scraper.py
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── cmo_agent.py, content_agent.py
│   │   ├── reply_agent.py
│   │   ├── icp_discovery_agent.py
│   │   ├── campaign_generation_agent.py
│   │   └── skills/
│   │       ├── base_skill.py
│   │       ├── website_parser.py
│   │       ├── service_extractor.py
│   │       ├── value_prop_extractor.py
│   │       ├── portfolio_extractor.py
│   │       ├── industry_classifier.py
│   │       ├── company_size_estimator.py
│   │       ├── icp_deriver.py
│   │       ├── als_weight_suggester.py
│   │       ├── sequence_builder.py
│   │       ├── messaging_generator.py
│   │       └── campaign_splitter.py
│   └── orchestration/
│       ├── worker.py
│       ├── flows/
│       ├── tasks/
│       └── schedules/
├── frontend/
│   ├── app/
│   ├── components/
│   └── lib/
├── supabase/
│   └── migrations/ (13 files)
├── tests/
├── docs/
├── PROJECT_BLUEPRINT.md
├── PROGRESS.md
├── CLAUDE.md
├── DEPLOYMENT.md
└── railway.toml, vercel.json, prefect.yaml
```

---

**Document Version**: 2.0  
**Last Updated**: December 26, 2025  
**Maintainer**: Claude Code + CEO Oversight
