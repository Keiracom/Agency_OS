# Phase 10: Deployment

**Status:** ✅ Complete  
**Tasks:** 8  
**Dependencies:** Phase 9 complete  
**Checkpoint:** CEO approval required (LAUNCH)

---

## Overview

Deploy the platform to production.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| DEP-001 | Railway config | 3-service deployment | `railway.toml` | M |
| DEP-002 | Vercel config | Frontend deployment | `vercel.json` | S |
| DEP-003 | Backend deploy | Deploy to Railway | N/A | M |
| DEP-004 | Frontend deploy | Deploy to Vercel | N/A | M |
| DEP-005 | Prefect deploy | Configure self-hosted | N/A | M |
| DEP-006 | Sentry setup | Error tracking | N/A | S |
| DEP-007 | Env vars | Production config | N/A | M |
| DEP-008 | E2E prod test | Test campaign end-to-end | N/A | L |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        VERCEL                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Next.js Frontend                        │   │
│  │              (Edge Functions)                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        RAILWAY                               │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ API Service │  │   Worker    │  │   Prefect   │        │
│  │  (FastAPI)  │  │  (Agent)    │  │  (Server)   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
       ┌──────┴──────┐               ┌────────┴────────┐
       │  Supabase   │               │     Upstash     │
       │ PostgreSQL  │               │     Redis       │
       │  Port 6543  │               │                 │
       └─────────────┘               └─────────────────┘
```

---

## Railway Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI backend |
| worker | — | Prefect agent |
| prefect | 4200 | Prefect server UI |

---

## Environment Variables

See `config/RAILWAY_ENV_VARS.txt` and `config/VERCEL_ENV_VARS.txt` for complete lists.

Key variables:
- `DATABASE_URL` — Supabase connection string (port 6543)
- `REDIS_URL` — Upstash Redis URL
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_ANON_KEY` — Supabase anonymous key
- `PREFECT_API_URL` — Prefect server URL

---

## Checkpoint 6 Criteria (LAUNCH)

- [ ] 3 Railway services running
- [ ] Vercel frontend deployed
- [ ] E2E test passes in production
- [ ] Sentry capturing errors
- [ ] All webhooks configured
- [ ] DNS configured
