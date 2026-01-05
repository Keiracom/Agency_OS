# Architecture Decisions — Agency OS

**Status:** LOCKED  
**Last Updated:** January 5, 2026

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
| numpy | >=1.24.0 | Statistical analysis |
| scipy | >=1.10.0 | Pattern optimization |
