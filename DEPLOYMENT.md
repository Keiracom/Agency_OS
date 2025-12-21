# DEPLOYMENT.md — Agency OS Production Deployment Guide

**Version:** 1.0
**Last Updated:** December 21, 2025
**Phase:** 10 (Deployment)
**Tasks:** DEP-003, DEP-004, DEP-005, DEP-006, DEP-007, DEP-008

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Backend Deployment (Railway)](#backend-deployment-railway)
4. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
5. [Prefect Deployment](#prefect-deployment)
6. [Sentry Setup](#sentry-setup)
7. [Environment Variables](#environment-variables)
8. [E2E Production Test](#e2e-production-test)
9. [Post-Deployment Checklist](#post-deployment-checklist)

---

## Architecture Overview

Agency OS uses a 3-service architecture:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel        │     │   Railway       │     │   Railway       │
│   (Frontend)    │────▶│   (API)         │────▶│   (Worker)      │
│   Next.js 14    │     │   FastAPI       │     │   Prefect Agent │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         │                       ▼                       ▼
         │              ┌─────────────────┐     ┌─────────────────┐
         │              │   Supabase      │     │   Upstash       │
         └─────────────▶│   PostgreSQL    │     │   Redis         │
                        │   + Auth        │     │   (Cache)       │
                        └─────────────────┘     └─────────────────┘
```

---

## Prerequisites

Before deployment, ensure you have:

1. **Accounts:**
   - Railway account (railway.app)
   - Vercel account (vercel.com)
   - Supabase project (supabase.com)
   - Upstash Redis instance (upstash.com)
   - Sentry project (sentry.io)
   - Stripe account (stripe.com)

2. **API Keys:**
   - Anthropic (Claude API)
   - Apollo.io
   - Resend
   - Twilio
   - HeyReach
   - Synthflow
   - Lob

3. **CLI Tools:**
   ```bash
   npm install -g railway vercel
   ```

---

## Backend Deployment (Railway)

### DEP-003: Deploy API Service

1. **Connect Repository:**
   ```bash
   cd Agency_OS
   railway login
   railway link
   ```

2. **Create API Service:**
   ```bash
   railway service create api
   ```

3. **Configure Environment Variables:**
   - Go to Railway Dashboard → Project → api → Variables
   - Add all required environment variables (see [Environment Variables](#environment-variables))

4. **Deploy:**
   ```bash
   railway up
   ```

5. **Verify Health:**
   ```bash
   curl https://your-api.railway.app/api/v1/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "version": "3.0.0",
     "timestamp": "2025-12-21T00:00:00Z"
   }
   ```

### Create Worker Service

1. **Create Worker Service:**
   ```bash
   railway service create worker
   ```

2. **Configure Worker:**
   - Set Dockerfile path: `Dockerfile.prefect`
   - Set start command: `prefect agent start -q agency-os-queue`
   - Add same database/Redis environment variables

3. **Deploy Worker:**
   ```bash
   railway up --service worker
   ```

---

## Frontend Deployment (Vercel)

### DEP-004: Deploy Frontend

1. **Connect Repository:**
   ```bash
   cd Agency_OS
   vercel login
   vercel link
   ```

2. **Configure Project:**
   - Framework: Next.js
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`

3. **Set Environment Variables:**
   - Go to Vercel Dashboard → Project → Settings → Environment Variables
   - Add:
     ```
     NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
     NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
     NEXT_PUBLIC_API_URL=https://your-api.railway.app
     NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx
     ```

4. **Deploy:**
   ```bash
   vercel --prod
   ```

5. **Configure Domain:**
   - Add custom domain in Vercel Dashboard
   - Configure DNS records

---

## Prefect Deployment

### DEP-005: Configure Prefect

1. **Deploy Flows:**
   ```bash
   prefect deploy --all
   ```

2. **Verify Deployments:**
   ```bash
   prefect deployment ls
   ```

   Expected output:
   ```
   ┌──────────────────────────┬──────────────────┬─────────────┐
   │ Name                     │ Status           │ Schedule    │
   ├──────────────────────────┼──────────────────┼─────────────┤
   │ campaign-activation      │ READY            │ On-demand   │
   │ daily-enrichment         │ READY            │ 0 2 * * *   │
   │ hourly-outreach          │ READY            │ 0 8-18 * * 1-5 │
   │ reply-recovery           │ READY            │ 0 */6 * * * │
   │ daily-metrics            │ READY            │ 0 0 * * *   │
   └──────────────────────────┴──────────────────┴─────────────┘
   ```

3. **Start Agent (if not using Railway worker):**
   ```bash
   prefect agent start -q agency-os-queue
   ```

4. **Test Flow Execution:**
   ```bash
   prefect deployment run campaign-activation/default --param campaign_id=test-123
   ```

---

## Sentry Setup

### DEP-006: Configure Error Tracking

1. **Create Sentry Project:**
   - Go to sentry.io → Create Project
   - Platform: Python (FastAPI) for backend
   - Platform: Next.js for frontend

2. **Backend Integration:**

   The Sentry SDK is already configured in `src/api/main.py`:
   ```python
   import sentry_sdk

   sentry_sdk.init(
       dsn=settings.SENTRY_DSN,
       environment=settings.ENVIRONMENT,
       traces_sample_rate=0.1,  # 10% of transactions
       profiles_sample_rate=0.1,
   )
   ```

3. **Frontend Integration:**

   Add to `frontend/app/layout.tsx`:
   ```typescript
   import * as Sentry from "@sentry/nextjs";

   Sentry.init({
     dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
     environment: process.env.NODE_ENV,
     tracesSampleRate: 0.1,
   });
   ```

4. **Configure Alerts:**
   - Go to Sentry → Alerts → Create Alert Rule
   - Set up alerts for:
     - Error rate > 1%
     - Response time > 5s
     - Failed health checks

---

## Environment Variables

### DEP-007: Complete Environment Variable Reference

#### Backend (Railway API + Worker)

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `ENVIRONMENT` | Environment name | Yes | `production` |
| `SECRET_KEY` | JWT signing key | Yes | `your-256-bit-secret` |
| `DATABASE_URL` | Supabase PostgreSQL (port 6543) | Yes | `postgresql+asyncpg://...` |
| `SUPABASE_URL` | Supabase project URL | Yes | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase anon key | Yes | `eyJ...` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Yes | `eyJ...` |
| `REDIS_URL` | Upstash Redis URL | Yes | `rediss://...` |
| `ANTHROPIC_API_KEY` | Claude API key | Yes | `sk-ant-...` |
| `AI_DAILY_SPEND_LIMIT_AUD` | Daily AI budget | No | `50` |
| `APOLLO_API_KEY` | Apollo enrichment | Yes | `...` |
| `APIFY_API_KEY` | Apify scraping | Yes | `...` |
| `CLAY_API_KEY` | Clay enrichment | Yes | `...` |
| `RESEND_API_KEY` | Email sending | Yes | `re_...` |
| `POSTMARK_API_KEY` | Inbound webhooks | Yes | `...` |
| `TWILIO_ACCOUNT_SID` | Twilio account | Yes | `AC...` |
| `TWILIO_AUTH_TOKEN` | Twilio auth | Yes | `...` |
| `HEYREACH_API_KEY` | LinkedIn automation | Yes | `...` |
| `SYNTHFLOW_API_KEY` | Voice AI | Yes | `...` |
| `LOB_API_KEY` | Direct mail | Yes | `...` |
| `STRIPE_SECRET_KEY` | Stripe API | Yes | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhooks | Yes | `whsec_...` |
| `SENTRY_DSN` | Error tracking | Yes | `https://...@sentry.io/...` |
| `CORS_ORIGINS` | Allowed origins | Yes | `https://app.agency-os.com` |

#### Frontend (Vercel)

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL | Yes | `https://xxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | Yes | `eyJ...` |
| `NEXT_PUBLIC_API_URL` | Backend API URL | Yes | `https://api.agency-os.com` |
| `NEXT_PUBLIC_SENTRY_DSN` | Sentry frontend DSN | Yes | `https://...@sentry.io/...` |

---

## E2E Production Test

### DEP-008: Production Verification Checklist

Run these tests after deployment to verify everything works:

#### 1. Health Checks

```bash
# API Health
curl https://api.agency-os.com/api/v1/health
# Expected: {"status": "healthy", ...}

# API Readiness
curl https://api.agency-os.com/api/v1/health/ready
# Expected: {"status": "ready", "database": "connected", "redis": "connected"}
```

#### 2. Authentication Flow

```bash
# Test login
curl -X POST https://api.agency-os.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "..."}'
```

#### 3. Campaign Creation

```bash
# Create campaign (with auth token)
curl -X POST https://api.agency-os.com/api/v1/clients/{client_id}/campaigns \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E2E Test Campaign",
    "permission_mode": "co_pilot",
    "daily_limit": 10,
    "allocation_email": 60,
    "allocation_sms": 20,
    "allocation_linkedin": 20
  }'
```

#### 4. Lead Enrichment

```bash
# Create and enrich lead
curl -X POST https://api.agency-os.com/api/v1/clients/{client_id}/leads \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test.lead@company.io",
    "campaign_id": "{campaign_id}"
  }'

# Trigger enrichment
curl -X POST https://api.agency-os.com/api/v1/clients/{client_id}/leads/{lead_id}/enrich \
  -H "Authorization: Bearer {token}"
```

#### 5. Prefect Flow Execution

```bash
# Trigger campaign activation
prefect deployment run campaign-activation/default \
  --param campaign_id={campaign_id}

# Check flow status in Prefect UI
```

#### 6. Webhook Processing

Test inbound webhooks:

```bash
# Postmark inbound email simulation
curl -X POST https://api.agency-os.com/api/v1/webhooks/postmark/inbound \
  -H "Content-Type: application/json" \
  -d '{"From": "test@example.com", "TextBody": "Test reply"}'
```

#### 7. Frontend Verification

- [ ] Login page loads
- [ ] Can log in with valid credentials
- [ ] Dashboard loads with stats
- [ ] Can create a new campaign
- [ ] Can view campaign details
- [ ] Can view leads list
- [ ] Can view reports
- [ ] Settings page works

---

## Post-Deployment Checklist

### Immediate (Day 1)

- [ ] All health checks passing
- [ ] Authentication working
- [ ] Database migrations applied
- [ ] Redis cache connected
- [ ] Sentry receiving errors
- [ ] Prefect agent running
- [ ] All scheduled flows deployed

### First Week

- [ ] Monitor error rates in Sentry
- [ ] Check Prefect flow success rates
- [ ] Verify rate limits are enforced
- [ ] Test webhook processing
- [ ] Verify AI spend tracking
- [ ] Check credit deduction accuracy

### Ongoing

- [ ] Review Sentry alerts daily
- [ ] Monitor Prefect flow metrics
- [ ] Check Redis memory usage
- [ ] Review database query performance
- [ ] Monitor API response times

---

## Rollback Procedures

### API Rollback

```bash
# Railway
railway rollback --service api

# Or deploy specific commit
railway up --commit {commit_sha}
```

### Frontend Rollback

```bash
# Vercel
vercel rollback

# Or promote previous deployment
vercel promote {deployment_url}
```

### Database Rollback

```bash
# Supabase migrations
supabase db reset --linked

# Or apply specific migration
supabase migration repair --status reverted {migration_id}
```

---

## Support

For deployment issues:
1. Check Sentry for errors
2. Review Railway/Vercel logs
3. Check Prefect flow runs
4. Verify environment variables

---

## Verification Checklist

- [x] DEP-003: Backend deployment documented
- [x] DEP-004: Frontend deployment documented
- [x] DEP-005: Prefect deployment documented
- [x] DEP-006: Sentry setup documented
- [x] DEP-007: Environment variables documented
- [x] DEP-008: E2E production test checklist created
