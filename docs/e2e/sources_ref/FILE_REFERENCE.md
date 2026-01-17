# File Reference — E2E Testing

**Purpose:** Quick lookup for which files to check when debugging issues
**Source:** Extracted from skills/testing/*.md (Jan 11, 2026)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Vercel)                             │
│                     https://agency-os-liart.vercel.app                  │
│                                                                         │
│   /login → /auth/callback → /onboarding → /dashboard                   │
│                                                                         │
│   Key Files:                                                            │
│   - frontend/app/auth/callback/route.ts (auth redirect logic)          │
│   - frontend/app/onboarding/* (onboarding flow)                        │
│   - frontend/app/dashboard/* (main app)                                │
│   - frontend/lib/supabase.ts (Supabase client)                         │
│   - frontend/lib/api.ts (Backend API calls)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ API calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          BACKEND (Railway)                              │
│                https://agency-os-production.up.railway.app              │
│                                                                         │
│   /api/v1/health → Health check                                        │
│   /api/v1/clients/* → Client CRUD                                      │
│   /api/v1/campaigns/* → Campaign management                            │
│   /api/v1/leads/* → Lead operations                                    │
│   /api/v1/onboarding/* → Onboarding flow                               │
│                                                                         │
│   Key Files:                                                            │
│   - src/api/routes/*.py (API endpoints)                                │
│   - src/engines/*.py (Business logic)                                  │
│   - src/services/*.py (Data operations)                                │
│   - src/integrations/*.py (External APIs)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Database queries
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SUPABASE (Database)                             │
│                                                                         │
│   Core: clients, campaigns, leads, activities                          │
│   Phase 24: lead_pool, lead_assignments, conversation_threads,         │
│             email_events, meetings, deals                              │
│   Auth: Supabase Auth with JWT                                         │
│   RLS: Row-level security on all tables                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Files by Journey

### J0: Infrastructure Audit

| Component | Files |
|-----------|-------|
| Backend config | `src/config/settings.py` |
| Main app | `src/main.py` |
| Dockerfile | `Dockerfile` |
| Railway config | `.railway.toml`, `railway.json` |
| Prefect config | `src/orchestration/deployments.py` |

### J1: Authentication & Onboarding

| Component | Files |
|-----------|-------|
| Login UI | `frontend/app/(auth)/login/page.tsx` |
| Auth callback | `frontend/app/auth/callback/route.ts` |
| Supabase client | `frontend/lib/supabase.ts` |
| User provisioning | `supabase/migrations/016_auto_provision_client.sql` |
| Onboarding UI | `frontend/app/onboarding/page.tsx` |
| Manual entry | `frontend/app/onboarding/manual-entry/page.tsx` |
| Onboarding API | `src/api/routes/onboarding.py` |
| ICP scraper | `src/engines/icp_scraper.py` |
| Apify integration | `src/integrations/apify.py` |
| Camoufox scraper | `src/integrations/camoufox_scraper.py` |

### J2: Campaigns & Leads

| Component | Files |
|-----------|-------|
| Campaign pages | `frontend/app/dashboard/campaigns/*.tsx` |
| Campaign create | `frontend/app/dashboard/campaigns/new/page.tsx` |
| Campaign API | `src/api/routes/campaigns.py` |
| Lead pool service | `src/services/lead_pool_service.py` |
| Lead allocator | `src/services/lead_allocator_service.py` |
| Scorer engine | `src/engines/scorer.py` |
| Deep research | `src/engines/deep_research.py` |
| Content engine | `src/engines/content.py` |
| Apollo integration | `src/integrations/apollo.py` |

### J3: Outreach Engines

| Component | Files |
|-----------|-------|
| Email engine | `src/engines/email.py` |
| SMS engine | `src/engines/sms.py` |
| Voice engine | `src/engines/voice.py` |
| LinkedIn engine | `src/engines/linkedin.py` |
| Content engine | `src/engines/content.py` |
| JIT Validator | `src/services/jit_validator.py` |
| Salesforge integration | `src/integrations/salesforge.py` |
| Twilio integration | `src/integrations/twilio.py` |
| Vapi integration | `src/integrations/vapi.py` |
| HeyReach integration | `src/integrations/heyreach.py` |

### J4: Reply & Meeting

| Component | Files |
|-----------|-------|
| Webhook handlers | `src/api/routes/webhooks.py` |
| Reply analyzer | `src/services/reply_analyzer.py` |
| Thread service | `src/services/thread_service.py` |
| Closer engine | `src/engines/closer.py` |
| Deal service | `src/services/deal_service.py` |
| Meeting service | `src/services/meeting_service.py` |

### J5: Dashboard

| Component | Files |
|-----------|-------|
| Dashboard page | `frontend/app/dashboard/page.tsx` |
| Dashboard API | `src/api/routes/dashboard.py` |
| Dashboard hooks | `frontend/hooks/use-dashboard.ts` |

### J6: Admin

| Component | Files |
|-----------|-------|
| Admin layout | `frontend/app/admin/layout.tsx` |
| Admin pages | `frontend/app/admin/*.tsx` |
| Admin API | `src/api/routes/admin.py` |
| Admin hooks | `frontend/hooks/use-admin.ts` |
| Admin fetchers | `frontend/lib/api/admin.ts` |

---

## Key Integration Files

| Integration | File | What It Does |
|-------------|------|--------------|
| Apollo | `src/integrations/apollo.py` | Lead enrichment, people search |
| Apify | `src/integrations/apify.py` | Web scraping (Cheerio, Playwright) |
| Camoufox | `src/integrations/camoufox_scraper.py` | Anti-detection scraping |
| Salesforge | `src/integrations/salesforge.py` | Email sending |
| Resend | `src/integrations/resend.py` | Transactional email |
| Twilio | `src/integrations/twilio.py` | SMS sending |
| Vapi | `src/integrations/vapi.py` | Voice AI calls |
| HeyReach | `src/integrations/heyreach.py` | LinkedIn automation |
| Supabase | `src/integrations/supabase.py` | Database client |
| Redis | `src/integrations/redis.py` | Caching (Upstash) |
| Sentry | `src/integrations/sentry_utils.py` | Error tracking |

---

## Key Engine Files

| Engine | File | Layer | Purpose |
|--------|------|-------|---------|
| Scorer | `src/engines/scorer.py` | 3 | ALS scoring (85+ = Hot) |
| Content | `src/engines/content.py` | 3 | Generate email/SMS/voice content |
| Email | `src/engines/email.py` | 3 | Send emails via Salesforge |
| SMS | `src/engines/sms.py` | 3 | Send SMS via Twilio |
| Voice | `src/engines/voice.py` | 3 | Make calls via Vapi |
| LinkedIn | `src/engines/linkedin.py` | 3 | LinkedIn outreach via HeyReach |
| Deep Research | `src/engines/deep_research.py` | 3 | Hot lead research |
| ICP Scraper | `src/engines/icp_scraper.py` | 3 | Website → ICP extraction |
| Closer | `src/engines/closer.py` | 3 | Reply handling, meeting booking |

---

## Key Migration Files

| Migration | File | Purpose |
|-----------|------|---------|
| 002 | `002_clients_users_memberships.sql` | Core user/client tables |
| 003 | `003_campaigns.sql` | Campaign table |
| 012 | `012_client_icp_profile.sql` | ICP profile storage |
| 016 | `016_auto_provision_client.sql` | Auto-create client on signup |
| 018+ | Various CIS migrations | Lead pool, assignments, etc. |

---

## Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://agency-os-liart.vercel.app |
| Backend API | https://agency-os-production.up.railway.app |
| Health Check | https://agency-os-production.up.railway.app/api/v1/health |
| Prefect UI | https://prefect-server-production-f9b1.up.railway.app |
| Supabase | https://jatzvazlbusedwsnqxzr.supabase.co |
