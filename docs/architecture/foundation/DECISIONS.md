# Architecture Decisions — Agency OS

**Status:** LOCKED
**Last Updated:** January 22, 2026

These decisions are final. Do not deviate.

---

## Core Technology Stack

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
| **Email** | Salesforge | Multi-mailbox orchestration, warm-up, deliverability |
| **SMS** | ClickSend | Australian company (Perth), native AU support, DNCR compliant |
| **LinkedIn** | Unipile | API-based automation, migrated from HeyReach |
| **Direct Mail** | ClickSend | Australian company, letters + postcards |

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

## Redis Usage Rules

### What Redis IS Used For
- Enrichment data cache (90-day TTL, versioned keys)
- Rate limiting counters (resource-level, not client-level)
- AI spend tracking (daily circuit breaker)
- Session data

### What Redis IS NOT Used For
- Task queues (use Prefect)
- Background job processing (use Prefect)
- Workflow orchestration (use Prefect)

---

## Database Connection Rules

- **Application/Prefect:** Use Transaction Pooler (Port 6543)
- **Migrations:** Use Session Pooler (Port 5432)
- **Pool limits:** pool_size=5, max_overflow=10 per service

---

## Service Architecture

Three separate services (not one monolith):

1. **API Service** - FastAPI, handles HTTP requests
2. **Worker Service** - Prefect agent, processes background tasks
3. **Prefect Service** - Prefect server, orchestration UI

---

## Prefect Server Configuration

**Self-Hosted on Railway (NOT Prefect Cloud)**

| Component | URL |
|-----------|-----|
| Dashboard | https://prefect-server-production-f9b1.up.railway.app/dashboard |
| API | https://prefect-server-production-f9b1.up.railway.app/api |
| Work Pool | `agency-os-pool` |
| Work Queue | `agency-os-queue` |

**Required Environment Variable (Railway API Service):**
```
PREFECT_API_URL=https://prefect-server-production-f9b1.up.railway.app/api
```

**API Routes Triggering Prefect Flows:**
- `POST /onboarding/analyze` → `icp_onboarding_flow/onboarding-flow`
- `POST /onboarding/confirm` → `pool_population/pool-population-flow`
- `POST /pool/populate` → `pool_population/pool-population-flow`
- `POST /patterns/trigger` → `single_client_pattern_learning/client-pattern-learning-flow`
- `POST /campaigns/{id}/enrich` → `daily_enrichment/enrichment-flow`

---

## Python Dependencies

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
| httpx | >=0.26.0 | Async HTTP (Salesforge, etc.) |
| anthropic | >=0.39.0 | Claude API |
| pydantic-ai | >=0.1.0 | Agent framework |
| prefect | >=3.0.0 | Workflow orchestration |
| tenacity | >=8.2.0 | Retry logic |
| python-jose | >=3.3.0 | JWT handling |
| twilio | >=8.10.0 | Voice calls (via Vapi) - NOT for SMS |
| clicksend | REST API | SMS + Direct Mail (Australia) |
| apify-client | >=1.5.0 | Web scraping |
| uuid-extensions | >=0.1.0 | UUIDv7 support |
| sentry-sdk | >=1.39.0 | Error tracking |
| pytest | >=7.4.0 | Testing |
| pytest-asyncio | >=0.21.0 | Async tests |
| numpy | >=1.24.0 | Statistical analysis |
| scipy | >=1.10.0 | Pattern optimization |
