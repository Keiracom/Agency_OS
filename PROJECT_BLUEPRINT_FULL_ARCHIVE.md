# PROJECT_BLUEPRINT.md — Agency OS v3.0

**Status:** APPROVED  
**Version:** 2.0 (with 20 architectural fixes)  
**Created:** December 20, 2025  
**Owner:** CEO  
**Purpose:** Single source of truth for Claude Code. Follow exactly. No improvisation.

---

## Document Control

| Item | Value |
|------|-------|
| Currency | AUD (Australian Dollars) |
| Primary Market | Australia |
| Scoring System | ALS (Agency OS Lead Score) |
| Auth Provider | Supabase Auth |
| Orchestration | Prefect (self-hosted on Railway) |
| Cache | Redis (caching ONLY, not task queues) |

---

# PART 1: ARCHITECTURE DECISIONS (LOCKED)

These decisions are final. Do not deviate.

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Workflow Orchestration** | Prefect (self-hosted on Railway) | Full control, no external dependency, runs alongside API |
| **Agent Framework** | Pydantic AI | Type-safe validation, contract enforcement |
| **Backend Framework** | FastAPI on Railway | Async, fast, Python-native |
| **Frontend Framework** | Next.js on Vercel | React, SSR, edge functions |
| **Database** | Supabase PostgreSQL (Port 6543 Transaction Pooler) | RLS, real-time, auth included |
| **Authentication** | Supabase Auth | Built-in, no Clerk needed |
| **Cache** | Redis (Upstash) | Caching ONLY — Prefect handles orchestration |
| **Task Queues** | Prefect | NOT Redis workers |
| **Error Tracking** | Sentry | Production monitoring, alerting |
| **Dev Tunnels** | ngrok | Local webhook development |
| **Voice AI** | Vapi + Twilio + ElevenLabs | Maximum control, high quality voice, low latency |

### What Redis IS Used For
- Enrichment data cache (90-day TTL, versioned keys)
- Rate limiting counters (resource-level, not client-level)
- AI spend tracking (daily circuit breaker)
- Session data

### What Redis IS NOT Used For
- Task queues (use Prefect)
- Background job processing (use Prefect)
- Workflow orchestration (use Prefect)

### Database Connection Rules
- **Application/Prefect:** Use Transaction Pooler (Port 6543)
- **Migrations:** Use Session Pooler (Port 5432)
- **Pool limits:** pool_size=5, max_overflow=10 per service

### Service Architecture
Three separate services (not one monolith):
1. **API Service** - FastAPI, handles HTTP requests
2. **Worker Service** - Prefect agent, processes background tasks
3. **Prefect Service** - Prefect server, orchestration UI

---

# PART 1B: PRICING & COST MODEL (LOCKED)

**Full specification:** `docs/specs/TIER_PRICING_COST_MODEL_v2.md`

These numbers are final. Do not deviate.

## Tier Pricing (AUD)

### Founding Member Pricing (50% off - 20 spots)

| Tier | Founding Price | Regular Price | Lead Pool | Max Campaigns | HeyReach Seats |
|------|----------------|---------------|-----------|---------------|----------------|
| **Ignition** | $1,250/mo | $2,500/mo | 1,250 | 5 | 1 |
| **Velocity** | $2,500/mo | $5,000/mo | 2,250 | 10 | 3 |
| **Dominance** | $3,750/mo | $7,500/mo | 4,500 | 20 | 5 |

### Tier Differentiation Rule

**IMPORTANT:** All tiers include ALL features. The ONLY differences between tiers are:
1. Lead pool (monthly prospect quota)
2. Max campaigns (simultaneous active campaigns)
3. HeyReach seats (LinkedIn automation capacity)

Every tier gets:
- Full 5-channel outreach (Email, LinkedIn, Voice AI, SMS, Direct Mail)
- Advanced Conversion Intelligence (WHO/WHAT/WHEN/HOW pattern detection)
- ALS scoring with learned weights
- ICP auto-discovery
- All support channels
- All reporting and insights
- API access

This keeps pricing simple: **pay for volume, not features**.

## COGS & Margins

| Tier | COGS | Gross Margin |
|------|------|--------------|
| Ignition | $666 | **73.4%** |
| Velocity | $1,323 | **66.9%** |
| Dominance | $2,502 | **66.6%** |

## Provider Costs (AUD, January 2026)

| Provider | Unit Cost | Notes |
|----------|-----------|-------|
| HeyReach | $122/seat | LinkedIn automation |
| Clay | $0.039-0.077/credit | Waterfall enrichment |
| Hunter.io | $0.023/email | Tier 1 enrichment |
| Vapi | $0.35/min | Voice AI (all-in) |
| Twilio SMS (AU) | $0.08/msg | Outbound SMS |
| ClickSend | $0.59/letter | Australian direct mail |
| Resend | $0.0009/email | Transactional email |

## Enrichment Strategy: Hybrid Clay Waterfall

- **Cold/Cool leads (65%):** Hunter.io direct — $0.02/lead
- **Warm/Hot leads (35%):** Clay full waterfall — $0.25-0.50/lead
- **Blended cost:** $0.13/lead

## Channel Access by ALS Score

| Channel | Cold (20-34) | Cool (35-59) | Warm (60-84) | Hot (85-100) |
|---------|--------------|--------------|--------------|--------------|
| Email | ✅ | ✅ | ✅ | ✅ |
| LinkedIn | ❌ | ✅ | ✅ | ✅ |
| Voice AI | ❌ | ❌ | ✅ | ✅ |
| SMS | ❌ | ❌ | ❌ | ✅ |
| Direct Mail | ❌ | ❌ | ❌ | ✅ |

---

# PART 2: COMPLETE FILE STRUCTURE

```
C:\AI\Agency_OS\
├── config/
│   ├── .env
│   └── .env.example
├── reference/
│   ├── MCP_REQUIREMENTS.md
│   ├── API_CREDENTIALS_CHECKLIST.md
│   ├── MASTER_SPEC_v3.1_old.md
│   ├── CMO_STRATEGIC_REVIEW_v2_old.md
│   └── AI_AGENT_FRAMEWORK_old.md
├── scripts/
│   ├── dev_tunnel.sh
│   └── update_webhook_urls.py
├── src/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       ├── campaigns.py
│   │       ├── leads.py
│   │       ├── webhooks.py
│   │       ├── webhooks_outbound.py
│   │       └── reports.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── models/                    # LAYER 1 (Bottom) - No engine imports
│   │   ├── __init__.py
│   │   ├── base.py               # SoftDeleteMixin, UUIDv7
│   │   ├── client.py
│   │   ├── user.py
│   │   ├── membership.py
│   │   ├── campaign.py
│   │   ├── lead.py
│   │   └── activity.py
│   ├── integrations/              # LAYER 2 - Can import models
│   │   ├── __init__.py
│   │   ├── supabase.py
│   │   ├── redis.py
│   │   ├── apollo.py
│   │   ├── apify.py
│   │   ├── clay.py
│   │   ├── resend.py
│   │   ├── postmark.py
│   │   ├── twilio.py
│   │   ├── heyreach.py
│   │   ├── vapi.py               # Voice AI orchestration (Vapi + Twilio + ElevenLabs)
│   │   ├── elevenlabs.py         # Voice synthesis
│   │   ├── deepgram.py           # Speech-to-text
│   │   ├── clicksend.py          # Australian direct mail
│   │   └── anthropic.py          # Includes spend limiter
│   ├── engines/                   # LAYER 3 - Can import models, integrations
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── scout.py
│   │   ├── scorer.py
│   │   ├── allocator.py
│   │   ├── email.py
│   │   ├── sms.py
│   │   ├── linkedin.py
│   │   ├── voice.py
│   │   ├── mail.py
│   │   ├── closer.py
│   │   ├── content.py
│   │   └── reporter.py
│   ├── orchestration/             # LAYER 4 (Top) - Can import everything
│   │   ├── __init__.py
│   │   ├── worker.py             # Prefect agent entrypoint
│   │   ├── flows/
│   │   │   ├── __init__.py
│   │   │   ├── campaign_flow.py
│   │   │   ├── enrichment_flow.py
│   │   │   ├── outreach_flow.py
│   │   │   └── reply_recovery_flow.py
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── enrichment_tasks.py
│   │   │   ├── scoring_tasks.py
│   │   │   ├── outreach_tasks.py
│   │   │   └── reply_tasks.py
│   │   └── schedules/
│   │       ├── __init__.py
│   │       └── scheduled_jobs.py
│   └── agents/
│       ├── __init__.py
│       ├── base_agent.py
│       ├── cmo_agent.py
│       ├── content_agent.py
│       └── reply_agent.py
├── frontend/
│   └── [Next.js structure - see Phase 8]
├── supabase/
│   └── migrations/
│       ├── 001_foundation.sql
│       ├── 002_clients_users_memberships.sql
│       ├── 003_campaigns.sql
│       ├── 004_leads_suppression.sql
│       ├── 005_activities.sql
│       ├── 006_permission_modes.sql
│       ├── 007_webhook_configs.sql
│       ├── 008_audit_logs.sql
│       └── 009_rls_policies.sql
├── tests/
│   └── [Test structure - see Phase 9]
├── .claude/
│   └── agents/
│       ├── devops-agent.md
│       ├── database-agent.md
│       ├── backend-agent.md
│       ├── engine-agent.md
│       ├── orchestration-agent.md
│       └── qa-agent.md
├── PROJECT_BLUEPRINT.md
├── PROGRESS.md
├── CLAUDE.md
├── requirements.txt
├── Dockerfile
├── Dockerfile.prefect
├── docker-compose.yml
├── railway.toml
├── vercel.json
├── prefect.yaml
└── README.md
```

### Import Hierarchy (ENFORCED)

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

# PART 3: BUILD PHASES WITH DEPENDENCIES

## PHASE 1: Foundation + DevOps
**Dependencies:** None  
**Checkpoint:** CEO approval required

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| DEV-001 | Dockerfile | Shared container image | `Dockerfile` | M |
| DEV-002 | Docker Compose | Local dev with 3 services | `docker-compose.yml` | M |
| DEV-003 | Dev tunnel script | ngrok for webhook testing | `scripts/dev_tunnel.sh` | S |
| DEV-004 | Webhook URL updater | Update Postmark/Twilio URLs | `scripts/update_webhook_urls.py` | S |
| DB-001 | Settings with pools | Pydantic settings, pool config | `src/config/settings.py` | M |
| DB-002 | Foundation migration | Enums, roles, base types | `supabase/migrations/001_foundation.sql` | M |
| DB-003 | Clients + Users + Memberships | Multi-tenant with team access | `supabase/migrations/002_clients_users_memberships.sql` | L |
| DB-004 | Campaigns migration | Campaigns with allocation | `supabase/migrations/003_campaigns.sql` | M |
| DB-005 | Leads + Suppression | Leads with compound uniqueness | `supabase/migrations/004_leads_suppression.sql` | L |
| DB-006 | Activities migration | Activity log with indexes | `supabase/migrations/005_activities.sql` | M |
| DB-007 | Permission modes | Autopilot/Co-Pilot/Manual | `supabase/migrations/006_permission_modes.sql` | S |
| DB-008 | Webhook configs | Client webhook endpoints | `supabase/migrations/007_webhook_configs.sql` | S |
| DB-009 | Audit logs | System audit trail | `supabase/migrations/008_audit_logs.sql` | M |
| DB-010 | RLS policies | Row-level security via memberships | `supabase/migrations/009_rls_policies.sql` | L |
| CFG-001 | Exceptions module | Custom exceptions | `src/exceptions.py` | S |
| INT-001 | Supabase integration | Async client with pool limits | `src/integrations/supabase.py` | M |
| INT-002 | Redis integration | Versioned cache, resource rate limits | `src/integrations/redis.py` | M |

## PHASE 2: Models & Schemas
**Dependencies:** Phase 1 complete  

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| MOD-001 | Base model | SoftDeleteMixin, UUIDv7 | `src/models/base.py` | M |
| MOD-002 | Client model | Client with subscription status | `src/models/client.py` | M |
| MOD-003 | User model | User profile | `src/models/user.py` | S |
| MOD-004 | Membership model | User-Client many-to-many | `src/models/membership.py` | M |
| MOD-005 | Campaign model | Campaign with allocation % | `src/models/campaign.py` | M |
| MOD-006 | Lead model | Lead with ALS fields | `src/models/lead.py` | L |
| MOD-007 | Activity model | Activity with message ID | `src/models/activity.py` | S |

## PHASE 3: Integrations
**Dependencies:** Phase 1 complete  
**Checkpoint:** CEO approval required

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| INT-003 | Apollo integration | Primary enrichment | `src/integrations/apollo.py` | M |
| INT-004 | Apify integration | Bulk scraping | `src/integrations/apify.py` | M |
| INT-005 | Clay integration | Premium fallback | `src/integrations/clay.py` | M |
| INT-006 | Resend integration | Email with threading | `src/integrations/resend.py` | M |
| INT-007 | Postmark integration | Inbound webhooks | `src/integrations/postmark.py` | M |
| INT-008 | Twilio integration | SMS + DNCR + Voice telephony | `src/integrations/twilio.py` | M |
| INT-009 | HeyReach integration | LinkedIn + proxy | `src/integrations/heyreach.py` | M |
| INT-010 | Vapi integration | Voice AI orchestration | `src/integrations/vapi.py` | L |
| INT-010a | ElevenLabs integration | Voice synthesis (TTS) | `src/integrations/elevenlabs.py` | M |
| INT-010b | Deepgram integration | Speech-to-text (STT) | `src/integrations/deepgram.py` | M |
| INT-011 | ClickSend integration | Australian direct mail | `src/integrations/clicksend.py` | M |
| INT-012 | Anthropic integration | AI with spend limiter | `src/integrations/anthropic.py` | L |

## PHASE 4: Engines (with tests)
**Dependencies:** Phase 2 + Phase 3 complete  
**Checkpoint:** CEO approval required

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| ENG-001 | Base engine | Abstract base, DI pattern | `src/engines/base.py` | M |
| ENG-002 | Scout engine + test | Enrichment waterfall | `src/engines/scout.py`, `tests/test_engines/test_scout.py` | L |
| ENG-003 | Scorer engine + test | ALS formula | `src/engines/scorer.py`, `tests/test_engines/test_scorer.py` | L |
| ENG-004 | Allocator engine + test | Channel + resource round-robin | `src/engines/allocator.py`, `tests/test_engines/test_allocator.py` | M |
| ENG-005 | Email engine + test | Email with threading | `src/engines/email.py`, `tests/test_engines/test_email.py` | M |
| ENG-006 | SMS engine + test | SMS with DNCR | `src/engines/sms.py`, `tests/test_engines/test_sms.py` | M |
| ENG-007 | LinkedIn engine + test | LinkedIn via HeyReach | `src/engines/linkedin.py`, `tests/test_engines/test_linkedin.py` | M |
| ENG-008 | Voice engine + test | Voice via Vapi + Twilio + ElevenLabs | `src/engines/voice.py`, `tests/test_engines/test_voice.py` | L |
| ENG-009 | Mail engine + test | Direct mail via Lob | `src/engines/mail.py`, `tests/test_engines/test_mail.py` | M |
| ENG-010 | Closer engine + test | Reply handling | `src/engines/closer.py`, `tests/test_engines/test_closer.py` | L |
| ENG-011 | Content engine + test | AI content generation | `src/engines/content.py`, `tests/test_engines/test_content.py` | M |
| ENG-012 | Reporter engine + test | Metrics aggregation | `src/engines/reporter.py`, `tests/test_engines/test_reporter.py` | M |

## PHASE 5: Orchestration (Prefect)
**Dependencies:** Phase 4 complete  
**Checkpoint:** CEO approval required

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| ORC-001 | Worker entrypoint | Prefect agent service | `src/orchestration/worker.py` | M |
| ORC-002 | Campaign flow + test | Campaign activation | `src/orchestration/flows/campaign_flow.py`, `tests/test_flows/test_campaign_flow.py` | M |
| ORC-003 | Enrichment flow + test | Daily enrichment with billing check | `src/orchestration/flows/enrichment_flow.py`, `tests/test_flows/test_enrichment_flow.py` | L |
| ORC-004 | Outreach flow + test | Hourly outreach | `src/orchestration/flows/outreach_flow.py`, `tests/test_flows/test_outreach_flow.py` | L |
| ORC-005 | Reply recovery flow | Safety net (6-hourly) | `src/orchestration/flows/reply_recovery_flow.py` | M |
| ORC-006 | Enrichment tasks | Prefect tasks with JIT checks | `src/orchestration/tasks/enrichment_tasks.py` | M |
| ORC-007 | Scoring tasks | Prefect tasks | `src/orchestration/tasks/scoring_tasks.py` | M |
| ORC-008 | Outreach tasks | Prefect tasks with JIT checks | `src/orchestration/tasks/outreach_tasks.py` | M |
| ORC-009 | Reply tasks | Prefect tasks | `src/orchestration/tasks/reply_tasks.py` | M |
| ORC-010 | Scheduled jobs | Cron schedules | `src/orchestration/schedules/scheduled_jobs.py` | M |
| ORC-011 | Prefect config | Deployment config | `prefect.yaml` | S |
| ORC-012 | Prefect Dockerfile | Server container | `Dockerfile.prefect` | S |

## PHASE 6: Agents (Pydantic AI)
**Dependencies:** Phase 5 complete  

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| AGT-001 | Base agent | Pydantic AI base | `src/agents/base_agent.py` | M |
| AGT-002 | CMO agent | Orchestration decisions | `src/agents/cmo_agent.py` | L |
| AGT-003 | Content agent | Copy generation | `src/agents/content_agent.py` | M |
| AGT-004 | Reply agent | Intent classification | `src/agents/reply_agent.py` | M |

## PHASE 7: API Routes (with tests)
**Dependencies:** Phase 6 complete  
**Checkpoint:** CEO approval required

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| API-001 | FastAPI app | Main app, middleware | `src/api/main.py` | M |
| API-002 | Dependencies | Auth via memberships | `src/api/dependencies.py` | M |
| API-003 | Health routes + test | Health check | `src/api/routes/health.py`, `tests/test_api/test_health.py` | S |
| API-004 | Campaign routes + test | CRUD (soft delete) | `src/api/routes/campaigns.py`, `tests/test_api/test_campaigns.py` | L |
| API-005 | Lead routes + test | CRUD + enrichment | `src/api/routes/leads.py`, `tests/test_api/test_leads.py` | L |
| API-006 | Webhook routes | Inbound (Postmark/Twilio) | `src/api/routes/webhooks.py` | M |
| API-007 | Outbound webhooks | Client dispatch + HMAC | `src/api/routes/webhooks_outbound.py` | M |
| API-008 | Report routes + test | Metrics | `src/api/routes/reports.py`, `tests/test_api/test_reports.py` | M |

## PHASE 8: Frontend
**Dependencies:** Phase 7 complete  
**Checkpoint:** CEO approval required

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| FE-001 | Next.js init | Initialize project | `frontend/package.json`, `frontend/next.config.js` | S |
| FE-002 | Tailwind + shadcn | Styling | `frontend/tailwind.config.js`, UI components | M |
| FE-003 | Supabase auth | Auth integration | `frontend/lib/supabase.ts` | M |
| FE-004 | Layout components | Header, sidebar, footer | `frontend/components/layout/*` | M |
| FE-005 | UI components | Core components | `frontend/components/ui/*` | M |
| FE-006 | Auth pages | Login, signup | `frontend/app/(auth)/*` | M |
| FE-007 | Dashboard home | Activity feed | `frontend/app/dashboard/page.tsx` | L |
| FE-008 | Campaign list | List campaigns | `frontend/app/dashboard/campaigns/page.tsx` | M |
| FE-009 | Campaign detail | Single campaign | `frontend/app/dashboard/campaigns/[id]/page.tsx` | L |
| FE-010 | New campaign | Create with permission mode | `frontend/app/dashboard/campaigns/new/page.tsx` | L |
| FE-011 | Lead list | List with ALS | `frontend/app/dashboard/leads/page.tsx` | M |
| FE-012 | Lead detail | Single lead | `frontend/app/dashboard/leads/[id]/page.tsx` | M |
| FE-013 | Reports page | Campaign metrics | `frontend/app/dashboard/reports/page.tsx` | L |
| FE-014 | Settings page | Client settings | `frontend/app/dashboard/settings/page.tsx` | M |
| FE-015 | Permission mode selector | Mode component | `frontend/components/campaigns/permission-mode-selector.tsx` | M |

## PHASE 9: Integration Testing
**Dependencies:** Phase 8 complete  

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| TST-001 | Test config | Pytest fixtures | `tests/conftest.py` | M |
| TST-002 | Mock fixtures | API response mocks | `tests/fixtures/*` | M |
| TST-003 | E2E flow test | Full enrichment → outreach | `tests/test_e2e/test_full_flow.py` | L |
| TST-004 | Billing integration test | Subscription checks | `tests/test_e2e/test_billing.py` | M |
| TST-005 | Rate limit test | Resource-level limits | `tests/test_e2e/test_rate_limits.py` | M |

## PHASE 10: Deployment
**Dependencies:** Phase 9 complete  
**Checkpoint:** CEO approval required (LAUNCH)

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| DEP-001 | Railway config | 3-service deployment | `railway.toml` | M |
| DEP-002 | Vercel config | Frontend deployment | `vercel.json` | S |
| DEP-003 | Backend deploy | Deploy to Railway | N/A | M |
| DEP-004 | Frontend deploy | Deploy to Vercel | N/A | M |
| DEP-005 | Prefect deploy | Configure self-hosted | N/A | M |
| DEP-006 | Sentry setup | Error tracking | N/A | S |
| DEP-007 | Env vars | Production config | N/A | M |
| DEP-008 | E2E prod test | Test campaign end-to-end | N/A | L |

---

# PART 4: TECHNOLOGY SPECIFICATIONS

## Python Dependencies (requirements.txt)

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.109.0 | Backend API |
| uvicorn | >=0.27.0 | ASGI server |
| pydantic | >=2.5.0 | Data models |
| pydantic-settings | >=2.1.0 | Environment config |
| python-dotenv | >=1.0.0 | Load .env |
| supabase | >=2.3.0 | Database client |
| sqlalchemy | >=2.0.0 | ORM |
| asyncpg | >=0.29.0 | Async Postgres |
| redis | >=5.0.0 | Cache client |
| httpx | >=0.26.0 | Async HTTP |
| anthropic | >=0.39.0 | Claude API |
| pydantic-ai | >=0.1.0 | Agent framework |
| prefect | >=3.0.0 | Workflow orchestration |
| tenacity | >=8.2.0 | Retry logic |
| python-jose | >=3.3.0 | JWT handling |
| resend | >=0.8.0 | Email sending |
| twilio | >=8.10.0 | SMS |
| apify-client | >=1.5.0 | Web scraping |
| uuid-extensions | >=0.1.0 | UUIDv7 support |
| sentry-sdk | >=1.39.0 | Error tracking |
| pytest | >=7.4.0 | Testing |
| pytest-asyncio | >=0.21.0 | Async tests |

---

# PART 5: DATABASE SCHEMA SPECIFICATIONS

## 001_foundation.sql

```sql
-- Enums
CREATE TYPE tier_type AS ENUM ('ignition', 'velocity', 'dominance');
CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'cancelled', 'paused');
CREATE TYPE membership_role AS ENUM ('owner', 'admin', 'member', 'viewer');
CREATE TYPE permission_mode AS ENUM ('autopilot', 'co_pilot', 'manual');
CREATE TYPE campaign_status AS ENUM ('draft', 'active', 'paused', 'completed');
CREATE TYPE lead_status AS ENUM ('new', 'enriched', 'scored', 'in_sequence', 'converted', 'unsubscribed', 'bounced');
CREATE TYPE channel_type AS ENUM ('email', 'sms', 'linkedin', 'voice', 'mail');
CREATE TYPE intent_type AS ENUM ('meeting_request', 'interested', 'question', 'not_interested', 'unsubscribe', 'out_of_office', 'auto_reply');

-- Helper function for RLS
CREATE OR REPLACE FUNCTION get_user_client_ids()
RETURNS SETOF UUID AS $$
    SELECT client_id 
    FROM memberships 
    WHERE user_id = auth.uid()
    AND accepted_at IS NOT NULL
$$ LANGUAGE sql SECURITY DEFINER STABLE;
```

## 002_clients_users_memberships.sql

```sql
-- Clients (tenants)
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    tier tier_type NOT NULL DEFAULT 'ignition',
    subscription_status subscription_status NOT NULL DEFAULT 'trialing',
    credits_remaining INTEGER NOT NULL DEFAULT 1250,
    credits_reset_at TIMESTAMPTZ,
    default_permission_mode permission_mode DEFAULT 'co_pilot',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete
);

-- Users (profile linked to auth.users)
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memberships (many-to-many with roles)
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    role membership_role NOT NULL DEFAULT 'member',
    invited_by UUID REFERENCES users(id),
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_membership UNIQUE (user_id, client_id)
);

-- Trigger: Create user profile on auth signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO users (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- Indexes
CREATE INDEX idx_memberships_user ON memberships(user_id);
CREATE INDEX idx_memberships_client ON memberships(client_id);
CREATE INDEX idx_clients_subscription ON clients(subscription_status);
```

## 004_leads_suppression.sql

```sql
-- Leads
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    email TEXT NOT NULL,
    phone TEXT,
    first_name TEXT,
    last_name TEXT,
    title TEXT,
    company TEXT,
    linkedin_url TEXT,
    domain TEXT,
    
    -- ALS Score components
    als_score INTEGER,
    als_tier TEXT,
    als_data_quality INTEGER,
    als_authority INTEGER,
    als_company_fit INTEGER,
    als_timing INTEGER,
    als_risk INTEGER,
    
    -- Organization data
    organization_industry TEXT,
    organization_employee_count INTEGER,
    organization_country TEXT,
    organization_founded_year INTEGER,
    organization_is_hiring BOOLEAN,
    organization_latest_funding_date DATE,
    employment_start_date DATE,
    
    -- Status
    status lead_status DEFAULT 'new',
    dncr_checked BOOLEAN DEFAULT FALSE,
    enrichment_source TEXT,
    enrichment_confidence FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- CRITICAL: Compound uniqueness per client
    CONSTRAINT unique_lead_per_client UNIQUE (client_id, email)
);

-- Global suppression (platform-wide)
CREATE TABLE global_suppression (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    reason TEXT NOT NULL,
    added_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_leads_client_email ON leads(client_id, email);
CREATE INDEX idx_leads_campaign ON leads(campaign_id);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_als ON leads(als_score DESC);
CREATE INDEX idx_suppression_email ON global_suppression(email);
```

## 005_activities.sql

```sql
CREATE TABLE activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    channel channel_type NOT NULL,
    action TEXT NOT NULL,
    provider_message_id TEXT,  -- For email threading
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CRITICAL: Composite indexes for performance
CREATE INDEX idx_activities_client_created ON activities(client_id, created_at DESC);
CREATE INDEX idx_activities_lead_created ON activities(lead_id, created_at DESC);
CREATE INDEX idx_activities_campaign_channel ON activities(campaign_id, channel, action);
CREATE INDEX idx_activities_thread ON activities(lead_id, channel, provider_message_id)
    WHERE provider_message_id IS NOT NULL;
```

---

# PART 6: THE 11 ENGINES SPECIFICATION

## ENGINE 01: Scout (Data Enrichment)

**Purpose:** Enrich leads with contact data using waterfall approach

**Dependency Injection Pattern:**
```python
class ScoutEngine:
    """
    RULE: Session passed by caller, never instantiated here.
    """
    
    async def enrich(
        self, 
        db: AsyncSession,  # Passed by caller
        domain: str, 
        client_id: str
    ) -> EnrichedLead:
        ...
```

**Waterfall Logic:**
- Tier 0: Check cache (versioned key, soft validation)
- Tier 1: Apollo + Apify hybrid
- Tier 2: Clay fallback (max 15% of batch)

**Validation Rules:**
- Minimum fields: email, first_name, last_name, company
- Confidence threshold: 0.70

## ENGINE 02: Scorer (ALS Calculation)

**ALS Formula (5 Components, 100 points max):**

| Component | Max Points | Description |
|-----------|------------|-------------|
| Data Quality | 20 | Email verified (8), phone (6), LinkedIn (4), personal email (2) |
| Authority | 25 | Owner/CEO (25), C-suite (22), VP (18), Director (15), Manager (7-10) |
| Company Fit | 25 | Industry (10), employee 5-50 (5), Australia (5), **DataForSEO (5)** |
| Timing | 15 | New role <6mo (6), hiring (5), funded <12mo (4) |
| Risk | 15 | Deductions for bounced, unsubscribed, competitor, bad title, **no web presence (-5)** |

### DataForSEO Integration (Verified Jan 4, 2026)

Marketing agency-specific scoring using SEO metrics. Assesses if agency "practices what they preach".

**APIs Used:**
- Labs API: `domain_rank_overview` ($0.01/request) - organic traffic, keyword rankings
- Backlinks API: `summary` ($0.02/request) - domain rank, backlinks, referring domains

**Company Fit Sub-Scoring (5 points from DataForSEO):**

| Signal | Points | Source | Threshold |
|--------|--------|--------|-----------|
| Domain Rank | 0-2 | Backlinks API | 0-150: 0, 151-500: 1, 501+: 2 |
| Organic Traffic (ETV) | 0-2 | Labs API | 0-200: 0, 201-1000: 1, 1001+: 2 |
| Top 10 Keywords | 0-1 | Labs API | >0 keywords in pos 1-10: 1 |

**Risk Deductions (from DataForSEO):**

| Signal | Deduction | Logic |
|--------|-----------|-------|
| No Domain Rank | -5 | No web presence = suspicious |
| No Organic Traffic | -3 | Doesn't practice what they preach |
| Spam Score >50 | -3 | Low quality backlinks |

**Cost per Lead:** ~$0.03 (both APIs combined)
**Caching:** 30-day TTL by domain (40% expected cache hit rate)

**Tier Assignment:**

| ALS Score | Tier | Channels |
|-----------|------|----------|
| 85-100 | Hot | Email, SMS, LinkedIn, Voice, Direct Mail |
| 60-84 | Warm | Email, LinkedIn, Voice |
| 35-59 | Cool | Email, LinkedIn |
| 20-34 | Cold | Email only |
| 0-19 | Dead | None (suppress) |

## ENGINE 04: Allocator (Channel + Resource Assignment)

**Resource-Level Rate Limiting:**
- LinkedIn: 17/day/seat
- Email: 50/day/domain
- SMS: 100/day/number

---

# PART 9: RULES FOR CLAUDE CODE

## Absolute Rules (1-10)

1. **Follow the blueprint exactly.** No improvisation.
2. **Never proceed past a checkpoint without CEO approval.**
3. **Never create duplicate systems.** (No Redis workers alongside Prefect)
4. **Never use mock data in production code.**
5. **Never leave incomplete implementations**
6. **Every file must have a contract comment at the top.**
7. **Every implementation must end with verification checklist.**
8. **Update PROGRESS.md after completing each task.**
9. **Before modifying external services, show command and wait for approval.**
10. **If blocked, report immediately with options. Do not guess.**

## Architectural Rules (11-20)

11. **Dependency Injection:** Engines accept `db: AsyncSession` as argument
12. **Import Hierarchy:** models → integrations → engines → orchestration
13. **JIT Validation:** All outreach tasks must check client/campaign/lead status
14. **Soft Deletes Only:** Never use hard DELETE
15. **AI Spend Limiter:** All Anthropic calls through spend limiter
16. **Cache Versioning:** All Redis keys include version prefix
17. **Resource-Level Rate Limits:** Rate limits per seat/domain/number
18. **Email Threading:** In-Reply-To headers for follow-ups
19. **Connection Pool Limits:** pool_size=5, max_overflow=10
20. **Webhook-First Architecture:** Cron jobs are safety nets only

---

# PART 10: CHECKPOINTS

## Checkpoint 1: After Phase 1 (Foundation + DevOps)
- [ ] Docker containers build and run
- [ ] All migrations applied successfully
- [ ] Supabase connection works (port 6543)
- [ ] Redis connection works
- [ ] RLS policies verified

## Checkpoint 2: After Phase 4 (Engines)
- [ ] All 12 engines implemented
- [ ] All engine tests pass
- [ ] Scout validation threshold working
- [ ] Spend limiter working
- [ ] Resource-level rate limits working

## Checkpoint 3: After Phase 5 (Orchestration)
- [ ] Prefect server running
- [ ] Worker connects to server
- [ ] Flows registered
- [ ] JIT validation in all tasks
- [ ] Billing checks in enrichment flow

## Checkpoint 4: After Phase 7 (API)
- [ ] All routes implemented
- [ ] Auth via memberships working
- [ ] Webhooks receive and process
- [ ] Soft deletes working

## Checkpoint 5: After Phase 8 (Frontend)
- [ ] All pages render
- [ ] Auth flow works
- [ ] Dashboard shows real-time data
- [ ] Permission mode selector works

## Checkpoint 6: After Phase 10 (Deployment) - LAUNCH
- [ ] 3 Railway services running
- [ ] Vercel frontend deployed
- [ ] E2E test passes
- [ ] Sentry capturing errors

---

# END OF PROJECT_BLUEPRINT.md

**Total Tasks:** 98  
**Checkpoints:** 6  

**Next Step:** CEO says "START PHASE 1" and Claude Code begins execution.


---

# PART 11: POST-LAUNCH PHASES

## PHASE 11: ICP Discovery System (Skills-Based Architecture)
**Dependencies:** Phase 10 complete (Production deployed)
**Purpose:** Automatically discover client ICP from their digital footprint using modular skills

### Overview

When a marketing agency signs up, they provide their website URL. The system:
1. Scrapes their website and digital presence
2. Uses modular skills to extract structured ICP data
3. Analyzes their existing clients to derive patterns
4. Auto-configures ALS weights for their specific ICP
5. User confirms or adjusts

### Skills Architecture

Skills are modular, testable capabilities that agents can use. Each skill:
- Has a single focused purpose
- Defines input/output schemas
- Contains its own system prompt
- Can be tested independently
- Can be reused across agents

```
src/agents/
├── base_agent.py              # Base class with skill loading
├── skills/
│   ├── __init__.py
│   ├── base_skill.py          # Skill base class + registry
│   ├── website_parser.py      # Parse raw HTML → structured pages
│   ├── service_extractor.py   # Find services offered
│   ├── value_prop_extractor.py # Find value proposition
│   ├── portfolio_extractor.py # Find client logos/case studies
│   ├── industry_classifier.py # Classify target industries
│   ├── company_size_estimator.py # Estimate team size
│   ├── icp_deriver.py         # Derive ICP from portfolio
│   └── als_weight_suggester.py # Suggest custom ALS weights
└── icp_discovery_agent.py     # Orchestrates skills
```

### Skill Base Class

**File:** `src/agents/skills/base_skill.py`

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pydantic import BaseModel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

class BaseSkill(ABC, Generic[InputT, OutputT]):
    """
    Base class for all agent skills.
    
    Each skill is a focused, testable capability with:
    - name: Unique identifier
    - description: When to use this skill
    - Input: Pydantic model for input validation
    - Output: Pydantic model for output validation
    - system_prompt: Instructions for Claude
    """
    
    name: str
    description: str
    
    class Input(BaseModel):
        pass
    
    class Output(BaseModel):
        pass
    
    system_prompt: str = ""
    
    @abstractmethod
    async def execute(
        self, 
        input: InputT, 
        anthropic: "AnthropicClient"
    ) -> OutputT:
        """Execute the skill and return structured output."""
        pass
    
    def validate_input(self, data: dict) -> InputT:
        """Validate input data against schema."""
        return self.Input(**data)
    
    def validate_output(self, data: dict) -> OutputT:
        """Validate output data against schema."""
        return self.Output(**data)


class SkillRegistry:
    """Registry for discovering and loading skills."""
    
    _skills: dict[str, BaseSkill] = {}
    
    @classmethod
    def register(cls, skill: BaseSkill):
        cls._skills[skill.name] = skill
    
    @classmethod
    def get(cls, name: str) -> BaseSkill:
        return cls._skills[name]
    
    @classmethod
    def all(cls) -> list[BaseSkill]:
        return list(cls._skills.values())
```

### ICP Discovery Skills

#### Skill 1: Website Parser
**File:** `src/agents/skills/website_parser.py`

| Attribute | Value |
|-----------|-------|
| name | `parse_website` |
| description | Extract structured content from raw website HTML |
| Input | `html: str, url: str` |
| Output | `pages: list[PageContent], company_name: str, navigation: list[str]` |

#### Skill 2: Service Extractor
**File:** `src/agents/skills/service_extractor.py`

| Attribute | Value |
|-----------|-------|
| name | `extract_services` |
| description | Identify services a marketing agency offers |
| Input | `pages: list[PageContent]` |
| Output | `services: list[str], confidence: float, source_pages: list[str]` |

#### Skill 3: Value Prop Extractor
**File:** `src/agents/skills/value_prop_extractor.py`

| Attribute | Value |
|-----------|-------|
| name | `extract_value_prop` |
| description | Find the agency's value proposition and key messaging |
| Input | `pages: list[PageContent]` |
| Output | `value_proposition: str, taglines: list[str], differentiators: list[str]` |

#### Skill 4: Portfolio Extractor
**File:** `src/agents/skills/portfolio_extractor.py`

| Attribute | Value |
|-----------|-------|
| name | `extract_portfolio` |
| description | Find client logos, case studies, testimonials |
| Input | `pages: list[PageContent]` |
| Output | `companies: list[PortfolioCompany], source: str` |

#### Skill 5: Industry Classifier
**File:** `src/agents/skills/industry_classifier.py`

| Attribute | Value |
|-----------|-------|
| name | `classify_industries` |
| description | Determine target industries from services and portfolio |
| Input | `services: list[str], portfolio: list[PortfolioCompany]` |
| Output | `industries: list[str], confidence: float` |

#### Skill 6: Company Size Estimator
**File:** `src/agents/skills/company_size_estimator.py`

| Attribute | Value |
|-----------|-------|
| name | `estimate_company_size` |
| description | Estimate agency team size from website and LinkedIn |
| Input | `about_page: PageContent, linkedin_data: Optional[LinkedInData]` |
| Output | `team_size: int, size_range: str, confidence: float` |

#### Skill 7: ICP Deriver
**File:** `src/agents/skills/icp_deriver.py`

| Attribute | Value |
|-----------|-------|
| name | `derive_icp` |
| description | Analyze portfolio companies to derive ICP pattern |
| Input | `enriched_portfolio: list[EnrichedCompany]` |
| Output | `icp_industries: list[str], icp_sizes: list[str], icp_locations: list[str], pattern_description: str` |

#### Skill 8: ALS Weight Suggester
**File:** `src/agents/skills/als_weight_suggester.py`

| Attribute | Value |
|-----------|-------|
| name | `suggest_als_weights` |
| description | Suggest custom ALS scoring weights based on ICP |
| Input | `icp_profile: ICPProfile` |
| Output | `weights: dict[str, int], reasoning: str` |

### Database Schema Updates

**Migration: 012_client_icp_profile.sql**

```sql
-- Add ICP fields to clients table
ALTER TABLE clients ADD COLUMN website_url TEXT;
ALTER TABLE clients ADD COLUMN company_description TEXT;
ALTER TABLE clients ADD COLUMN services_offered TEXT[];
ALTER TABLE clients ADD COLUMN years_in_business INTEGER;
ALTER TABLE clients ADD COLUMN team_size INTEGER;
ALTER TABLE clients ADD COLUMN value_proposition TEXT;
ALTER TABLE clients ADD COLUMN default_offer TEXT;

-- ICP Configuration
ALTER TABLE clients ADD COLUMN icp_industries TEXT[];
ALTER TABLE clients ADD COLUMN icp_company_sizes TEXT[];
ALTER TABLE clients ADD COLUMN icp_revenue_range TEXT;
ALTER TABLE clients ADD COLUMN icp_locations TEXT[];
ALTER TABLE clients ADD COLUMN icp_titles TEXT[];
ALTER TABLE clients ADD COLUMN icp_pain_points TEXT[];

-- Custom ALS weights (overrides defaults)
ALTER TABLE clients ADD COLUMN als_weights JSONB DEFAULT '{}';

-- ICP extraction status
ALTER TABLE clients ADD COLUMN icp_extracted_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN icp_extraction_source TEXT;
ALTER TABLE clients ADD COLUMN icp_confirmed_at TIMESTAMPTZ;

-- Discovered client logos/case studies
CREATE TABLE client_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    company_domain TEXT,
    company_industry TEXT,
    company_size TEXT,
    company_location TEXT,
    source TEXT,
    enriched_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_client_portfolio_client ON client_portfolio(client_id);
```

### ICP Discovery Agent

**File:** `src/agents/icp_discovery_agent.py`

```python
class ICPDiscoveryAgent(BaseAgent):
    """
    Orchestrates ICP extraction using modular skills.
    
    Flow:
    1. Scrape website (via ICP Scraper Engine)
    2. Parse content (WebsiteParserSkill)
    3. Extract agency info (ServiceExtractor, ValuePropExtractor)
    4. Find portfolio (PortfolioExtractor)
    5. Enrich portfolio companies (via Apollo)
    6. Derive ICP pattern (ICPDeriver)
    7. Suggest ALS weights (ALSWeightSuggester)
    """
    
    skills = [
        WebsiteParserSkill(),
        ServiceExtractorSkill(),
        ValuePropExtractorSkill(),
        PortfolioExtractorSkill(),
        IndustryClassifierSkill(),
        CompanySizeEstimatorSkill(),
        ICPDeriverSkill(),
        ALSWeightSuggesterSkill(),
    ]
    
    async def extract_icp(self, website_url: str) -> ICPProfile:
        # 1. Scrape raw content
        raw_html = await self.scraper.scrape_website(website_url)
        
        # 2. Parse website structure
        parsed = await self.use_skill("parse_website", 
            html=raw_html, 
            url=website_url
        )
        
        # 3. Extract agency info (parallel)
        services, value_prop, portfolio = await asyncio.gather(
            self.use_skill("extract_services", pages=parsed.pages),
            self.use_skill("extract_value_prop", pages=parsed.pages),
            self.use_skill("extract_portfolio", pages=parsed.pages),
        )
        
        # 4. Enrich portfolio companies
        enriched = await self.scraper.enrich_portfolio(portfolio.companies)
        
        # 5. Derive ICP from portfolio
        icp = await self.use_skill("derive_icp", 
            enriched_portfolio=enriched
        )
        
        # 6. Suggest ALS weights
        weights = await self.use_skill("suggest_als_weights",
            icp_profile=icp
        )
        
        return ICPProfile(
            services_offered=services.services,
            value_proposition=value_prop.value_proposition,
            portfolio_companies=portfolio.companies,
            icp_industries=icp.icp_industries,
            icp_company_sizes=icp.icp_sizes,
            icp_locations=icp.icp_locations,
            als_weights=weights.weights,
            ...
        )
```

### ICP Scraper Engine

**File:** `src/engines/icp_scraper.py`

**Purpose:** Coordinate scraping from multiple sources (not AI - just data fetching)

**Methods:**
- `scrape_website(url: str) -> str` - Raw HTML via Apify
- `scrape_linkedin(company_name: str) -> LinkedInData` - Company data via Apollo
- `enrich_portfolio(companies: list[PortfolioCompany]) -> list[EnrichedCompany]` - Enrich via Apollo

### API Endpoints

**File:** `src/api/routes/onboarding.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/onboarding/analyze` | POST | Submit website URL, trigger extraction |
| `/api/v1/onboarding/status/{job_id}` | GET | Check extraction progress |
| `/api/v1/onboarding/result/{job_id}` | GET | Get extracted ICP profile |
| `/api/v1/onboarding/confirm` | POST | User confirms/edits ICP |
| `/api/v1/clients/{id}/icp` | GET | Get client ICP profile |
| `/api/v1/clients/{id}/icp` | PUT | Update client ICP profile |

### Frontend Updates

**Onboarding Flow:** `frontend/app/onboarding/page.tsx`
1. User enters website URL
2. Loading state with progress steps
3. Display extracted ICP for confirmation
4. User edits if needed
5. Confirm → redirect to dashboard

**ICP Settings:** `frontend/app/dashboard/settings/icp/page.tsx`
- View/edit ICP configuration
- Re-run extraction
- Manual adjustments

**Create Campaign:** `frontend/app/dashboard/campaigns/new/page.tsx`
- Simplified: name, description, permission mode only
- Shows inherited ICP from client profile
- Link to edit ICP

### Phase 11 Tasks

| Task ID | Task Name | Description | Files to Create | Complexity |
|---------|-----------|-------------|-----------------|------------|
| ICP-001 | Database migration | Add ICP fields to clients | `supabase/migrations/012_client_icp_profile.sql` | M |
| ICP-002 | Skill base class | Base skill + registry | `src/agents/skills/base_skill.py` | M |
| ICP-003 | Website Parser Skill | Parse HTML → structured pages | `src/agents/skills/website_parser.py` | M |
| ICP-004 | Service Extractor Skill | Find agency services | `src/agents/skills/service_extractor.py` | M |
| ICP-005 | Value Prop Extractor Skill | Find value proposition | `src/agents/skills/value_prop_extractor.py` | M |
| ICP-006 | Portfolio Extractor Skill | Find client logos/cases | `src/agents/skills/portfolio_extractor.py` | M |
| ICP-007 | Industry Classifier Skill | Classify industries | `src/agents/skills/industry_classifier.py` | M |
| ICP-008 | Company Size Estimator Skill | Estimate team size | `src/agents/skills/company_size_estimator.py` | S |
| ICP-009 | ICP Deriver Skill | Derive ICP from portfolio | `src/agents/skills/icp_deriver.py` | L |
| ICP-010 | ALS Weight Suggester Skill | Suggest scoring weights | `src/agents/skills/als_weight_suggester.py` | M |
| ICP-011 | ICP Scraper Engine | Multi-source scraping | `src/engines/icp_scraper.py` | L |
| ICP-012 | ICP Discovery Agent | Orchestrate skills | `src/agents/icp_discovery_agent.py` | L |
| ICP-013 | Onboarding API routes | Extraction endpoints | `src/api/routes/onboarding.py` | M |
| ICP-014 | Onboarding flow | Prefect async flow | `src/orchestration/flows/onboarding_flow.py` | M |
| ICP-015 | Onboarding UI | Website input + confirm | `frontend/app/onboarding/page.tsx` | M |
| ICP-016 | ICP Settings page | View/edit ICP | `frontend/app/dashboard/settings/icp/page.tsx` | M |
| ICP-017 | Update Create Campaign | Simplified form | `frontend/app/dashboard/campaigns/new/page.tsx` | S |
| ICP-018 | Skill unit tests | Test each skill | `tests/test_skills/*.py` | M |

**Total New Tasks:** 18
**Phase 11 Checkpoint:** ICP extraction working end-to-end with all skills

### Checkpoint 7: After Phase 11 (ICP Discovery)
- [ ] All 8 skills implemented and tested
- [ ] ICP Scraper Engine fetches from website + LinkedIn
- [ ] ICP Discovery Agent orchestrates skills correctly
- [ ] Onboarding API endpoints work
- [ ] Prefect flow runs end-to-end
- [ ] Onboarding UI shows extraction progress
- [ ] User can confirm/edit ICP
- [ ] Create Campaign inherits ICP from client
- [ ] Custom ALS weights applied to scoring

---

## PHASE 12: Campaign Execution (Connect Live APIs)
*To be defined after Phase 11*

---

# UPDATED TOTALS

**Total Tasks:** 116 (98 original + 18 Phase 11)
**Checkpoints:** 7



---

## PHASE 16: Conversion Intelligence System
**Dependencies:** Phase 11 complete (ICP Discovery working)  
**Purpose:** Transform Agency OS from "dumb pipe" to learning platform that improves based on outcomes
**Specification Documents:** `docs/phase16/`

### Overview

The Conversion Intelligence System answers the billion-dollar question:
> "How do we 1) Find correct candidates to convert and 2) Convert those candidates into bookings?"

**Core Architecture Principle:**
- **ENGINES** execute deterministically (no AI)
- **AGENTS** decide using AI (Claude)
- **LEARNING** happens offline via statistical algorithms (Python + scipy)
- Claude CANNOT learn between conversations - all "learning" = database + scheduled jobs

### The Four Pattern Detectors

| Detector | Question | Output | Consumer |
|----------|----------|--------|----------|
| **WHO** | Which leads convert? | Optimized ALS weights | Scorer Engine |
| **WHAT** | Which content converts? | Effective messaging patterns | MessagingGeneratorSkill |
| **WHEN** | When do leads convert? | Optimal timing patterns | AllocatorEngine, SequenceBuilderSkill |
| **HOW** | Which channels convert? | Winning sequence patterns | AllocatorEngine, SequenceBuilderSkill |

### Database Schema (Migration 014)

```sql
-- Lead tracking
ALTER TABLE leads ADD COLUMN als_components JSONB;
ALTER TABLE leads ADD COLUMN als_weights_used JSONB;
ALTER TABLE leads ADD COLUMN scored_at TIMESTAMPTZ;

-- Activity tracking  
ALTER TABLE activities ADD COLUMN led_to_booking BOOLEAN DEFAULT FALSE;
ALTER TABLE activities ADD COLUMN content_snapshot JSONB;

-- Client learned weights
ALTER TABLE clients ADD COLUMN als_learned_weights JSONB;
ALTER TABLE clients ADD COLUMN als_weights_updated_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN conversion_sample_count INTEGER DEFAULT 0;

-- Pattern storage
CREATE TABLE conversion_patterns (
    id UUID PRIMARY KEY,
    client_id UUID REFERENCES clients(id),
    pattern_type TEXT CHECK (pattern_type IN ('who', 'what', 'when', 'how')),
    patterns JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    confidence FLOAT,
    computed_at TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    UNIQUE (client_id, pattern_type)
);

-- Pattern history
CREATE TABLE conversion_pattern_history (...);

-- Trigger: Mark converting touch
CREATE TRIGGER on_lead_converted;
```

### File Structure

```
src/
├── algorithms/
│   ├── who_detector.py       # Lead attribute analysis
│   ├── what_detector.py      # Content pattern analysis
│   ├── when_detector.py      # Timing pattern analysis
│   └── how_detector.py       # Channel sequence analysis
├── engines/
│   ├── content_utils.py      # Shared utilities
│   ├── scorer.py             # Modified: reads WHO patterns
│   ├── allocator.py          # Modified: reads WHEN/HOW patterns
│   ├── email.py              # Modified: stores content_snapshot
│   ├── sms.py                # Modified: stores content_snapshot
│   ├── linkedin.py           # Modified: stores content_snapshot
│   └── voice.py              # Modified: stores content_snapshot
├── orchestration/
│   └── flows/
│       ├── pattern_learning_flow.py   # Weekly batch learning
│       ├── pattern_health_flow.py     # Daily validation
│       └── pattern_backfill_flow.py   # Historical analysis
└── api/routes/
    └── patterns.py           # Pattern API endpoints
```

### Phase 16 Tasks (30 tasks, ~50.5 hours)

#### 16A: Data Capture + WHO Detector (8 tasks, ~12 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16A.1 | Create migration 014 | `migrations/014_conversion_intelligence.sql` | 1 |
| 16A.2 | Create ConversionPattern model | `src/models/conversion_patterns.py` | 0.5 |
| 16A.3 | Create WhoDetector class | `src/algorithms/who_detector.py` | 2.5 |
| 16A.4 | Implement conversion_rate_by analysis | `src/algorithms/who_detector.py` | 2 |
| 16A.5 | Implement weight optimization (scipy) | `src/algorithms/who_detector.py` | 3 |
| 16A.6 | Integrate with Scorer engine | `src/engines/scorer.py` | 1.5 |
| 16A.7 | Write unit tests | `tests/algorithms/test_who_detector.py` | 1.5 |
| 16A.8 | Integration tests | `tests/integration/test_who_integration.py` | 1 |

#### 16B: WHAT Detector (5 tasks, ~9 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16B.1 | Create WhatDetector class | `src/algorithms/what_detector.py` | 2.5 |
| 16B.2 | Implement pain point extraction | `src/algorithms/what_detector.py` | 1.5 |
| 16B.3 | Implement subject/CTA/angle analysis | `src/algorithms/what_detector.py` | 2 |
| 16B.4 | Integrate with MessagingGeneratorSkill | `src/agents/skills/messaging_generator.py` | 1.5 |
| 16B.5 | Write unit tests | `tests/algorithms/test_what_detector.py` | 1.5 |

#### 16C: WHEN Detector (4 tasks, ~7 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16C.1 | Create WhenDetector class | `src/algorithms/when_detector.py` | 2.5 |
| 16C.2 | Integrate with SequenceBuilderSkill | `src/agents/skills/sequence_builder.py` | 1.5 |
| 16C.3 | Integrate with AllocatorEngine | `src/engines/allocator.py` | 1.5 |
| 16C.4 | Write unit tests | `tests/algorithms/test_when_detector.py` | 1.5 |

#### 16D: HOW Detector (4 tasks, ~8 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16D.1 | Create HowDetector class | `src/algorithms/how_detector.py` | 3 |
| 16D.2 | Integrate with SequenceBuilderSkill | `src/agents/skills/sequence_builder.py` | 1.5 |
| 16D.3 | Integrate with AllocatorEngine | `src/engines/allocator.py` | 2 |
| 16D.4 | Write unit tests | `tests/algorithms/test_how_detector.py` | 1.5 |

#### 16E: Engine Modifications (5 tasks, ~8 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16E.1 | Create shared content_utils module | `src/engines/content_utils.py` | 1 |
| 16E.2 | Modify Email engine | `src/engines/email.py` | 1.5 |
| 16E.3 | Modify SMS + LinkedIn + Voice engines | `src/engines/sms.py`, `linkedin.py`, `voice.py` | 2 |
| 16E.4 | Modify Scorer engine | `src/engines/scorer.py` | 1.5 |
| 16E.5 | Modify Allocator engine | `src/engines/allocator.py` | 2 |

#### 16F: Prefect Flows (4 tasks, ~6.5 hours)

| Task | Description | File(s) | Hours |
|------|-------------|---------|-------|
| 16F.1 | Create pattern_learning_flow | `src/orchestration/flows/pattern_learning_flow.py` | 2 |
| 16F.2 | Create pattern_health_flow | `src/orchestration/flows/pattern_health_flow.py` | 1.5 |
| 16F.3 | Create pattern_backfill_flow | `src/orchestration/flows/pattern_backfill_flow.py` | 1.5 |
| 16F.4 | Create schedules + API endpoints | `schedules/`, `api/routes/patterns.py` | 1.5 |

### Schedules

| Flow | Schedule | Purpose |
|------|----------|---------|
| Pattern Learning | Sunday 2am UTC | Weekly batch learning for all clients |
| Pattern Health | Daily 6am UTC | Validation + alerts for pattern quality |
| Pattern Backfill | Manual | One-time historical data analysis |

### Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Booking rate | 3% | 5%+ |
| Time to conversion | ~14 days | <10 days |
| Touches to convert | 6 avg | <5 avg |
| Multi-channel lift | Unknown | Measured |

### Checkpoint 8: After Phase 16 (Conversion Intelligence)
- [ ] Migration 014 applied successfully
- [ ] All 4 detectors implemented and tested
- [ ] Engines capture content_snapshot on send
- [ ] Scorer uses learned weights from patterns
- [ ] Allocator uses WHEN/HOW patterns for scheduling
- [ ] Weekly pattern learning flow runs successfully
- [ ] Patterns visible in admin dashboard
- [ ] Pattern health alerts working

### Specification Documents

Full specifications in `docs/phase16/`:
- `PHASE_16_MASTER_INDEX.md` - Overview and build order
- `PHASE_16_CONVERSION_INTELLIGENCE_SPEC.md` - Data model + WHO Detector
- `PHASE_16B_WHAT_DETECTOR_SPEC.md` - Content pattern analysis
- `PHASE_16C_WHEN_DETECTOR_SPEC.md` - Timing pattern analysis
- `PHASE_16D_HOW_DETECTOR_SPEC.md` - Channel sequence analysis
- `PHASE_16E_ENGINE_MODIFICATIONS_SPEC.md` - Engine updates
- `PHASE_16F_PREFECT_FLOWS_SPEC.md` - Orchestration

### Dependencies (add to requirements.txt)

```
numpy>=1.24.0
scipy>=1.10.0
```

---

## PHASE 19: Email Infrastructure (InfraForge + Smartlead)
**Dependencies:** Phase 17 complete (API credentials collected)
**Purpose:** Programmatic email domain/mailbox provisioning and warmup for multi-tenant SaaS
**Decision Date:** January 4, 2026

### Architecture Decision: InfraForge + Smartlead (APPROVED)

After comprehensive API research comparing Instantly.ai, Mailforge/Infraforge, and Smartlead, the **InfraForge + Smartlead** architecture was selected as superior for Agency OS.

**Architecture Flow:**
```
Agency OS Platform
      │
      ├──► InfraForge API (Domain/Mailbox Provisioning)
      │    ├── Purchase domains programmatically
      │    ├── Create mailboxes programmatically  
      │    ├── Automated DNS (SPF, DKIM, DMARC)
      │    ├── Dedicated IPs per tenant ($99/month each)
      │    └── Pre-warmed infrastructure option
      │
      ├──► Smartlead API (Warmup + Sending + Campaigns)
      │    ├── Add email accounts via API (SMTP/IMAP)
      │    ├── Enable/configure warmup via API
      │    ├── Create campaigns via API
      │    ├── Webhooks for all events
      │    └── Monitor warmup stats via API
      │
      └──► Agency OS Bridge Code
           ├── Tenant provisioning workflow
           ├── Infrastructure orchestration
           └── Unified dashboard/reporting
```

### Why Not Instantly.ai?

| Factor | InfraForge + Smartlead | Instantly DFY |
|--------|------------------------|---------------|
| Domain Ownership | ✅ You own domains | ❌ Instantly retains ownership |
| Cost (100 tenants) | ~$1,500-1,800/month | ~$6,600-8,100/month |
| Tenant Isolation | ✅ Dedicated IPs | ⚠️ Shared infrastructure |
| Exit Strategy | ✅ Portable infrastructure | ❌ Platform lock-in |
| API Flexibility | ✅ Best-in-class for each function | ⚠️ Good but generalist |

### InfraForge API Capabilities

| Capability | API Support | Notes |
|------------|-------------|-------|
| Domain Purchase | ✅ Yes | Programmatic provisioning |
| Mailbox Creation | ✅ Yes | Automated at scale |
| DNS Setup | ✅ Automated | SPF, DKIM, DMARC auto-configured |
| Dedicated IPs | ✅ Yes | $99/month per IP via API |
| Multi-IP Provisioning | ✅ Yes | Distribute across multiple IPs |
| Pre-warmed Domains | ✅ Yes | Skip warmup period |
| Workspace Management | ✅ Yes | Per-tenant isolation |
| Real-time Monitoring | ✅ Yes | Deliverability dashboards |
| White-label | ✅ Yes | Custom branding available |

**InfraForge Pricing:**
- Mailbox slots: ~$3-4/mailbox/month (bulk: $1.67-2.50)
- Domain: ~$15-20/year
- Dedicated IP: $99/month
- SSL/Domain Masking: $2/domain/month

### Smartlead API Capabilities

| Capability | API Support | Endpoint |
|------------|-------------|----------|
| Create Email Account | ✅ Yes | `POST /api/v1/email-accounts/save` |
| Add SMTP/IMAP Credentials | ✅ Yes | Full credential support |
| Enable Warmup | ✅ Yes | `POST /api/v1/email-accounts/{id}/warmup` |
| Configure Warmup Settings | ✅ Yes | daily limit, rampup, reply rate |
| Get Warmup Stats | ✅ Yes | `GET /api/v1/email-accounts/{id}/warmup-stats` |
| Create Campaigns | ✅ Yes | `POST /api/v1/campaigns` |
| Add Leads | ✅ Yes | `POST /api/v1/campaigns/{id}/leads` |
| Webhooks | ✅ Yes | Full event support |
| Client Management | ✅ Yes | White-label sub-accounts |
| Campaign Analytics | ✅ Yes | Comprehensive stats |

**Smartlead API - Create Email Account Example:**
```json
POST /api/v1/email-accounts/save?api_key=${API_KEY}
{
  "id": null,
  "from_name": "John Smith",
  "from_email": "john@clientdomain.com",
  "user_name": "john@clientdomain.com",
  "password": "smtp_password",
  "smtp_host": "smtp.infraforge.ai",
  "smtp_port": 465,
  "imap_host": "imap.infraforge.ai",
  "imap_port": 993,
  "max_email_per_day": 50,
  "warmup_enabled": true,
  "total_warmup_per_day": 35,
  "daily_rampup": 2,
  "reply_rate_percentage": 38,
  "client_id": 123
}
```

**Smartlead Pricing:**
- Basic: $39/month (2,000 active leads, unlimited warmup)
- Pro: $94/month (30,000 active leads)
- Custom: $174/month (12M leads)
- Unlimited mailboxes on all plans

### Cost Model per Tier

**Per-Tenant Cost Comparison (Ignition Tier: 3 mailboxes, 2 domains)**

| Provider | Domains | Mailboxes | Warmup | Total/Month |
|----------|---------|-----------|--------|-------------|
| InfraForge + Smartlead | $3.33 | $9-12 | Included | ~$15-18 |
| Instantly DFY | $5.83 | $60-75 | Included | ~$66-81 |

**At Scale (100 tenants, 300 mailboxes):**
- InfraForge + Smartlead: ~$1,500-1,800/month
- Instantly DFY: ~$6,600-8,100/month

**Savings: 4-5x cheaper at scale**

### Tier Infrastructure Requirements

| Tier | Domains | Mailboxes | Dedicated IPs | Est. Monthly Cost |
|------|---------|-----------|---------------|-------------------|
| Ignition | 2 | 3 | 1 | ~$115 |
| Velocity | 3 | 6 | 1 | ~$140 |
| Dominance | 5 | 11 | 2 | ~$320 |

### Phase 19 Tasks

#### 19A: InfraForge Integration (5 tasks)

| Task ID | Description | File(s) | Status |
|---------|-------------|---------|--------|
| INF-001 | Request InfraForge API documentation/access | — | 🔴 |
| INF-002 | Create InfraForge integration client | `src/integrations/infraforge.py` | 🔴 |
| INF-003 | Implement domain provisioning | `src/integrations/infraforge.py` | 🔴 |
| INF-004 | Implement mailbox creation | `src/integrations/infraforge.py` | 🔴 |
| INF-005 | Implement DNS status monitoring | `src/integrations/infraforge.py` | 🔴 |

#### 19B: Smartlead Integration (6 tasks)

| Task ID | Description | File(s) | Status |
|---------|-------------|---------|--------|
| SML-001 | Set up Smartlead Pro account | — | 🔴 |
| SML-002 | Create Smartlead integration client | `src/integrations/smartlead.py` | 🔴 |
| SML-003 | Implement email account registration | `src/integrations/smartlead.py` | 🔴 |
| SML-004 | Implement warmup management | `src/integrations/smartlead.py` | 🔴 |
| SML-005 | Implement campaign API wrapper | `src/integrations/smartlead.py` | 🔴 |
| SML-006 | Implement webhook receiver | `src/api/routes/webhooks_smartlead.py` | 🔴 |

#### 19C: Bridge Orchestration (5 tasks)

| Task ID | Description | File(s) | Status |
|---------|-------------|---------|--------|
| BRG-001 | Create tenant provisioning flow | `src/orchestration/flows/email_provisioning_flow.py` | 🔴 |
| BRG-002 | Implement infrastructure orchestration | `src/engines/email_infrastructure.py` | 🔴 |
| BRG-003 | Create warmup monitoring dashboard | `frontend/app/admin/email-health/page.tsx` | 🔴 |
| BRG-004 | Database schema for email infrastructure | `supabase/migrations/017_email_infrastructure.sql` | 🔴 |
| BRG-005 | Tenant onboarding email setup | Update onboarding flow | 🔴 |

#### 19D: Testing & Validation (4 tasks)

| Task ID | Description | File(s) | Status |
|---------|-------------|---------|--------|
| TST-019-1 | InfraForge integration tests | `tests/integrations/test_infraforge.py` | 🔴 |
| TST-019-2 | Smartlead integration tests | `tests/integrations/test_smartlead.py` | 🔴 |
| TST-019-3 | End-to-end provisioning test | `tests/e2e/test_email_provisioning.py` | 🔴 |
| TST-019-4 | Warmup monitoring test | `tests/e2e/test_warmup_monitoring.py` | 🔴 |

**Total Phase 19 Tasks:** 20

### Database Schema (Migration 017)

```sql
-- Email infrastructure tracking
CREATE TABLE email_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    domain TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'infraforge',
    provider_domain_id TEXT,
    dns_status TEXT DEFAULT 'pending',
    spf_verified BOOLEAN DEFAULT FALSE,
    dkim_verified BOOLEAN DEFAULT FALSE,
    dmarc_verified BOOLEAN DEFAULT FALSE,
    dedicated_ip TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    UNIQUE(client_id, domain)
);

CREATE TABLE email_mailboxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    domain_id UUID NOT NULL REFERENCES email_domains(id),
    email TEXT NOT NULL,
    persona_name TEXT,
    provider TEXT NOT NULL DEFAULT 'infraforge',
    provider_mailbox_id TEXT,
    smartlead_account_id INTEGER,
    smtp_host TEXT,
    smtp_port INTEGER,
    imap_host TEXT,
    imap_port INTEGER,
    warmup_enabled BOOLEAN DEFAULT FALSE,
    warmup_status TEXT DEFAULT 'inactive',
    warmup_score INTEGER,
    daily_send_limit INTEGER DEFAULT 50,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    warmup_started_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    UNIQUE(client_id, email)
);

CREATE TABLE warmup_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mailbox_id UUID NOT NULL REFERENCES email_mailboxes(id),
    recorded_at DATE NOT NULL,
    sent_count INTEGER DEFAULT 0,
    received_count INTEGER DEFAULT 0,
    spam_count INTEGER DEFAULT 0,
    reputation_score FLOAT,
    UNIQUE(mailbox_id, recorded_at)
);

CREATE INDEX idx_email_domains_client ON email_domains(client_id);
CREATE INDEX idx_email_mailboxes_client ON email_mailboxes(client_id);
CREATE INDEX idx_email_mailboxes_domain ON email_mailboxes(domain_id);
CREATE INDEX idx_warmup_stats_mailbox ON warmup_stats(mailbox_id);
```

### Tenant Provisioning Flow

```python
async def provision_tenant_email_infrastructure(
    tenant_id: str, 
    tier: str
) -> ProvisioningResult:
    """
    End-to-end email infrastructure provisioning.
    
    Flow:
    1. Calculate requirements based on tier
    2. Purchase domains via InfraForge API
    3. Create mailboxes via InfraForge API  
    4. Wait for DNS propagation
    5. Register mailboxes in Smartlead
    6. Enable warmup in Smartlead
    7. Store metadata in Agency OS database
    8. Return provisioning status
    """
    
    # Tier requirements
    requirements = {
        'ignition': {'domains': 2, 'mailboxes': 3, 'ips': 1},
        'velocity': {'domains': 3, 'mailboxes': 6, 'ips': 1},
        'dominance': {'domains': 5, 'mailboxes': 11, 'ips': 2},
    }
    
    req = requirements[tier]
    
    # Step 1: Provision infrastructure (InfraForge)
    domains = await infraforge.purchase_domains(count=req['domains'])
    mailboxes = await infraforge.create_mailboxes(
        domains=domains,
        count_per_domain=req['mailboxes'] // req['domains']
    )
    
    # Step 2: Wait for DNS (polling with timeout)
    await wait_for_dns_propagation(domains, timeout_minutes=30)
    
    # Step 3: Register in Smartlead
    for mailbox in mailboxes:
        smartlead_id = await smartlead.create_email_account(
            from_name=mailbox.persona_name,
            from_email=mailbox.email,
            smtp_host=mailbox.smtp_host,
            smtp_port=mailbox.smtp_port,
            imap_host=mailbox.imap_host,
            imap_port=mailbox.imap_port,
            password=mailbox.password,
            warmup_enabled=True,
            total_warmup_per_day=35,
            daily_rampup=2,
            reply_rate_percentage=38
        )
        mailbox.smartlead_account_id = smartlead_id
    
    # Step 4: Store in database
    await store_email_infrastructure(tenant_id, domains, mailboxes)
    
    return ProvisioningResult(
        success=True,
        domains=domains,
        mailboxes=mailboxes,
        estimated_warmup_complete=datetime.now() + timedelta(days=14)
    )
```

### API Documentation Links

- **InfraForge:** Contact for API docs (enterprise focus) - https://infraforge.ai
- **Smartlead:** https://api.smartlead.ai/reference
- **Instantly:** https://developer.instantly.ai/api/v2 (NOT USED - for reference only)

### Research Documents

Full comparison research documented in:
- `docs/research/INFRAFORGE_SMARTLEAD_VS_INSTANTLY_COMPARISON.md`

### Checkpoint 9: After Phase 19 (Email Infrastructure)
- [ ] InfraForge API access obtained
- [ ] Smartlead Pro account configured
- [ ] InfraForge integration client working
- [ ] Smartlead integration client working
- [ ] Domain provisioning working end-to-end
- [ ] Mailbox creation working end-to-end
- [ ] Warmup enabled and monitoring working
- [ ] Webhook receiver processing Smartlead events
- [ ] Tenant provisioning flow complete
- [ ] Email health dashboard showing warmup stats

---

## Phase 20: Platform Intelligence (Post-Launch)

**Purpose:** Cross-client learning system that aggregates conversion patterns across the platform, enabling new clients to benefit from collective learnings on day 1.

**Trigger:** Activate when 10+ clients have 50+ conversions each (~Month 4-6)

**Decision Date:** January 4, 2026

### Why This Matters

**Current State (Phase 16 - Per-Client Learning):**
```
Client A learns → Benefits Client A only
Client B learns → Benefits Client B only
New Client C → Starts from default weights (no advantage)
```

**With Platform Intelligence:**
```
Client A conversions → Platform aggregates
Client B conversions → Platform aggregates  
New Client C → Inherits platform-learned weights on Day 1
```

### Data Acquisition Strategy: Hybrid Approach

**Problem:** Conversion outcome data isn't sold anywhere. Companies like Apollo, 6sense, Artisan guard this as their competitive moat.

**Solution:** Build our own data co-op from founding customers.

#### Phase 1: Seed with Industry Benchmarks (Immediate)

Create `src/intelligence/platform_priors.py` with industry-standard weights derived from public research (Ruler Analytics, First Page Sage, Martal 2025):

```python
# Industry benchmark priors - used until platform has enough data
PLATFORM_PRIORS = {
    "als_weights": {
        "data_quality": 0.15,   # Less important than originally assumed
        "authority": 0.30,      # Title matters significantly in B2B
        "company_fit": 0.25,    # Size/industry alignment + DataForSEO signals
        "timing": 0.20,         # Intent signals critical for conversion
        "risk": 0.10,           # Reduced weight on negatives
    },
    "timing_patterns": {
        "best_days": ["Tuesday", "Wednesday", "Thursday"],
        "best_hours": [9, 10, 14, 15],  # 9-10am, 2-3pm local time
        "avoid_periods": ["Monday 8-10am", "Friday 3-5pm"],
    },
    "content_patterns": {
        "optimal_subject_length": {"min": 4, "max": 8},    # words
        "optimal_body_length": {"min": 50, "max": 125},    # words
        "personalization_lift": 1.26,                       # 26% improvement
        "question_in_subject_lift": 1.15,                   # 15% improvement
    },
    "channel_patterns": {
        "email_first_sequence_rate": 0.67,      # 67% of winning sequences start email
        "linkedin_touch_lift": 1.35,             # 35% lift when LinkedIn included
        "voice_touch_lift": 1.85,                # 85% lift when voice included (costly)
        "optimal_touches_before_convert": 4,     # Average touches to conversion
    },
    "source": "Industry benchmarks - Ruler Analytics, First Page Sage, Martal Group 2025",
    "confidence": 0.5,  # Low confidence until platform data validates
}
```

#### Phase 2: Data Co-op Agreement (Launch)

Add to founding customer terms:

> "By using Agency OS, you agree that anonymized, aggregated conversion patterns 
> (not individual lead data or personally identifiable information) may be used 
> to improve the platform for all users. This includes patterns such as optimal 
> send times, effective message lengths, and channel sequence performance."

#### Phase 3: Platform Learning (Month 4+)

Once 10+ clients have 50+ conversions each:
- Aggregate learned weights across all clients
- Weight contributions by sample size (more data = more influence)
- Optionally cluster by industry segment if patterns diverge
- New clients inherit platform priors instead of default weights

### Database Schema (Migration 018)

```sql
-- Platform-wide aggregated patterns
CREATE TABLE platform_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('who', 'what', 'when', 'how', 'weights')),
    industry_segment TEXT,  -- NULL = global, or 'saas', 'real_estate', etc.
    patterns JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    contributing_clients INTEGER NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Only one active pattern per type/segment combination
    CONSTRAINT unique_platform_pattern UNIQUE (pattern_type, industry_segment)
);

-- Platform-wide optimized weights
CREATE TABLE platform_weights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    weight_type TEXT NOT NULL CHECK (weight_type IN ('global', 'industry')),
    industry_segment TEXT,  -- NULL for global
    weights JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    contributing_clients INTEGER NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    baseline_correlation FLOAT,
    optimized_correlation FLOAT,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_platform_weights UNIQUE (weight_type, industry_segment)
);

-- Track which clients opted into data sharing
ALTER TABLE clients ADD COLUMN IF NOT EXISTS data_sharing_consent BOOLEAN DEFAULT TRUE;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS data_sharing_consented_at TIMESTAMPTZ;

-- Indexes
CREATE INDEX idx_platform_patterns_type ON platform_patterns(pattern_type);
CREATE INDEX idx_platform_patterns_segment ON platform_patterns(industry_segment);
CREATE INDEX idx_platform_weights_type ON platform_weights(weight_type);
```

### Phase 20 Tasks

#### 20A: Platform Priors (5 tasks)

| Task ID | Description | File(s) | Status |
|---------|-------------|---------|--------|
| PLT-001 | Create platform_priors module with industry benchmarks | `src/intelligence/platform_priors.py` | 🔴 |
| PLT-002 | Add data sharing consent to client model | `src/models/client.py` | 🔴 |
| PLT-003 | Create consent capture in onboarding | `frontend/app/onboarding/page.tsx` | 🔴 |
| PLT-004 | Database migration for platform tables | `supabase/migrations/018_platform_intelligence.sql` | 🔴 |
| PLT-005 | Create platform_patterns model | `src/models/platform_patterns.py` | 🔴 |

#### 20B: Platform Learning Engine (6 tasks)

| Task ID | Description | File(s) | Status |
|---------|-------------|---------|--------|
| PLT-006 | Create platform pattern aggregator | `src/intelligence/platform_aggregator.py` | 🔴 |
| PLT-007 | Create platform weight optimizer | `src/intelligence/platform_weight_optimizer.py` | 🔴 |
| PLT-008 | Implement industry clustering (optional) | `src/intelligence/industry_clustering.py` | 🔴 |
| PLT-009 | Monthly platform learning flow | `src/orchestration/flows/platform_learning_flow.py` | 🔴 |
| PLT-010 | Platform learning scheduler | `src/orchestration/schedules/scheduled_jobs.py` | 🔴 |
| PLT-011 | Admin dashboard: platform insights | `frontend/app/admin/platform-intelligence/page.tsx` | 🔴 |

#### 20C: Scorer Integration (4 tasks)

| Task ID | Description | File(s) | Status |
|---------|-------------|---------|--------|
| PLT-012 | Modify Scorer to use weight fallback hierarchy | `src/engines/scorer.py` | 🔴 |
| PLT-013 | Add platform weights lookup | `src/engines/scorer.py` | 🔴 |
| PLT-014 | Add weight source tracking to leads | `src/models/lead.py` | 🔴 |
| PLT-015 | Unit tests for fallback hierarchy | `tests/test_engines/test_scorer_platform.py` | 🔴 |

#### 20D: Testing & Validation (3 tasks)

| Task ID | Description | File(s) | Status |
|---------|-------------|---------|--------|
| TST-020-1 | Platform aggregator tests | `tests/intelligence/test_platform_aggregator.py` | 🔴 |
| TST-020-2 | Weight fallback tests | `tests/intelligence/test_weight_fallback.py` | 🔴 |
| TST-020-3 | End-to-end platform learning test | `tests/e2e/test_platform_learning.py` | 🔴 |

**Total Phase 20 Tasks:** 18

### Weight Fallback Hierarchy

When scoring a lead, the Scorer engine will use this priority:

```python
async def _get_weights(self, db: AsyncSession, client_id: UUID) -> dict:
    """
    Weight fallback hierarchy:
    1. Client learned weights (if confidence > 0.7 and sample >= 50)
    2. Industry-specific platform weights (if client's industry has enough data)
    3. Global platform weights (aggregated from all clients)
    4. Platform priors (industry benchmarks from research)
    5. Default weights (hardcoded fallback)
    """
    
    # 1. Try client's own learned weights
    client_weights = await self._get_client_learned_weights(db, client_id)
    if client_weights and client_weights.confidence > 0.7:
        return client_weights.weights, "client_learned"
    
    # 2. Try industry-specific platform weights
    client_industry = await self._get_client_industry(db, client_id)
    if client_industry:
        industry_weights = await self._get_platform_weights(db, client_industry)
        if industry_weights and industry_weights.confidence > 0.6:
            return industry_weights.weights, "platform_industry"
    
    # 3. Try global platform weights
    global_weights = await self._get_platform_weights(db, industry=None)
    if global_weights and global_weights.confidence > 0.5:
        return global_weights.weights, "platform_global"
    
    # 4. Use platform priors (industry benchmarks)
    from src.intelligence.platform_priors import PLATFORM_PRIORS
    return PLATFORM_PRIORS["als_weights"], "platform_priors"
```

### Monthly Platform Learning Flow

```python
@flow(
    name="monthly_platform_learning",
    description="Aggregate learnings across all clients monthly",
    log_prints=True,
)
async def monthly_platform_learning_flow() -> dict:
    """
    Monthly aggregation of conversion patterns across platform.
    
    Steps:
    1. Get all clients with data_sharing_consent=True
    2. Filter to clients with 50+ conversions
    3. Aggregate WHO/WHAT/WHEN/HOW patterns
    4. Weight by sample size (more data = more influence)
    5. Optionally cluster by industry
    6. Compute platform-wide optimal weights
    7. Store in platform_patterns / platform_weights tables
    """
    pass
```

### Activation Criteria

Platform Intelligence activates when:
- ✅ 10+ clients with `data_sharing_consent = TRUE`
- ✅ Combined 500+ conversions across consenting clients
- ✅ At least 3 clients have individually learned weights

### Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| New client time-to-value | -2 months | Days to first conversion vs baseline |
| New client first-month conversion rate | +20% | Compare to clients before platform learning |
| Platform weight confidence | >0.7 | Sample size and correlation improvement |
| Cross-client pattern consistency | >60% | Agreement on top patterns across clients |

### Checkpoint 10: After Phase 20 (Platform Intelligence)

- [ ] Platform priors seeded with industry benchmarks
- [ ] Data sharing consent captured in onboarding
- [ ] Platform pattern aggregation working
- [ ] Platform weight optimization working
- [ ] Scorer using weight fallback hierarchy
- [ ] Admin dashboard showing platform insights
- [ ] New clients inheriting platform weights
- [ ] Monthly learning flow scheduled and running

### Related Documents

- Phase 16: Conversion Intelligence (per-client learning)
- `src/detectors/weight_optimizer.py` - Per-client scipy optimization
- `src/orchestration/flows/pattern_learning_flow.py` - Weekly client learning

---

# UPDATED TOTALS

**Total Tasks:** 184 (146 original + 20 Phase 19 + 18 Phase 20)
**Checkpoints:** 10

