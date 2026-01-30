---
name: agency-os
description: Internal knowledge about Agency OS - our multi-channel client acquisition SaaS for Australian marketing agencies. Use for architecture, database, deployments, and operational context.
metadata: {"clawdbot":{"emoji":"🏢"}}
---

# Agency OS - Internal System Knowledge

**"The Bloomberg Terminal for Client Acquisition"**

Multi-channel automated outreach SaaS targeting Australian marketing agencies ($2.5K-$7.5K/month).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│   Next.js Dashboard (Vercel) - elliot-dashboard.vercel.app     │
├─────────────────────────────────────────────────────────────────┤
│                          BACKEND                                │
│   FastAPI + Pydantic AI (Railway)                              │
│   Project ID: fef5af27-a022-4fb2-996b-cad099549af9             │
├─────────────────────────────────────────────────────────────────┤
│                       ORCHESTRATION                             │
│   Prefect (Self-hosted on Railway)                             │
│   prefect-server-production-f9b1.up.railway.app                │
├─────────────────────────────────────────────────────────────────┤
│                        DATA LAYER                               │
│   Supabase PostgreSQL (AP-Southeast-1 Singapore)               │
│   jatzvazlbusedwsnqxzr.supabase.co                             │
│   Redis (Upstash) - clever-stag-35095.upstash.io               │
└─────────────────────────────────────────────────────────────────┘
```

### Import Hierarchy (STRICT)
```
models → integrations → engines → orchestration
```
Never import upward.

## Key Database Tables

### Core Entities
| Table | Purpose |
|-------|---------|
| `leads` | Individual prospects with contact info, ALS score |
| `companies` | Organizations linked to leads |
| `campaigns` | Outreach campaigns with settings and targeting |

### Email System
| Table | Purpose |
|-------|---------|
| `email_sequences` | Multi-step email sequences |
| `email_sends` | Individual send records with tracking |
| `email_templates` | Reusable email content |

### Data & Intelligence
| Table | Purpose |
|-------|---------|
| `enrichment_data` | Apollo/Prospeo enrichment results |
| `elliot_knowledge` | AI assistant knowledge base |
| `elliot_signoff_queue` | Items pending Dave's approval |

### ML & Scoring
| Table | Purpose |
|-------|---------|
| `meetings` | Booked meetings (conversion events) |
| `deals` | Closed deals for attribution |
| `conversion_patterns` | ML model training data |
| `icp_refinement_log` | ICP changes with reasoning |

## Core Flows

### 1. Lead Pipeline
```
Import → Enrichment → WHO/WHAT/WHEN/HOW Detection → ALS Scoring → Campaign Assignment
```

**ALS (Agency Lead Score) Thresholds:**
- **85+** = Hot (priority outreach)
- **70-84** = Warm (standard sequence)
- **<70** = Nurture (long-term drip)

### 2. Email Sequence Execution
```
Campaign triggers → Sequence selected → Steps scheduled → Salesforge sends → Tracking captured
```

### 3. LinkedIn Automation (Unipile)
```
Lead identified → Connection request → Message sequence → Reply monitoring
```

### 4. Voice AI (Vapi)
```
Hot lead detected → Call scheduled → Vapi executes → Recording stored → Outcome logged
```

## API Integrations

### Outreach Channels
| Channel | Primary Tool | Purpose |
|---------|--------------|---------|
| Cold Email | Salesforge | Sending + warmup ecosystem |
| Transactional Email | Resend | System notifications |
| LinkedIn | Unipile | Connection + messaging automation |
| SMS | Twilio / ClickSend | Text outreach |
| Voice | Vapi + ElevenLabs | AI phone calls |

### Data & Enrichment
| Service | Purpose |
|---------|---------|
| Apollo | Lead/company enrichment (primary) |
| Prospeo | Email finding/verification |
| DataForSEO | SEO data for scoring |
| Apify | Web scraping workflows |

### Infrastructure
| Service | Purpose |
|---------|---------|
| InfraForge | Domain infrastructure |
| WarmForge | Email warmup |
| Anthropic | AI (primary LLM) |
| OpenRouter | AI (fallback) |

## Repositories

| Repo | Purpose | Deploy |
|------|---------|--------|
| `Keiracom/Agency_OS` | FastAPI backend | Railway (auto from main) |
| `elliot-dashboard` | Next.js frontend | Vercel (auto-deploy) |
| `elliot-mobile` | Expo React Native app | EAS Build |

**GitHub User:** `Keiracom` (full R/W access)

## Deployment

### Backend (Railway)
```bash
# Auto-deploys from main branch
# Manual deploy via Railway CLI:
railway up
```

### Frontend (Vercel)
```bash
# Auto-deploys from main branch
# Preview deployments on PRs
```

### Mobile (Expo)
```bash
# Build preview APK
eas build --platform android --profile preview

# Expo account: elliotdave
```

### Database Migrations
```bash
# Via Supabase CLI or direct SQL
# Migrations stored in: src/migrations/
```

## Environment Configuration

### Production
- **Backend:** Railway production environment
- **Frontend:** Vercel production
- **Database:** Supabase production instance
- **Region:** AP-Southeast-1 (Singapore)

### Local Development
```bash
# Load env
source ~/.config/agency-os/.env

# Start backend
uvicorn src.main:app --reload

# Start frontend
cd elliot-dashboard && npm run dev
```

## Common Operations

### Check Service Health
```bash
# Supabase
curl -H "apikey: $SUPABASE_ANON_KEY" "$SUPABASE_URL/rest/v1/"

# Prefect
curl "$PREFECT_API_URL/health"

# Salesforge
curl -H "Authorization: Bearer $SALESFORGE_API_KEY" "$SALESFORGE_API_URL/health"
```

### View Logs
```bash
# Railway logs
railway logs

# Prefect flow runs
# Via Prefect UI at prefect-server-production-f9b1.up.railway.app
```

### Generate Codebase Context
```bash
# For sub-agent context injection
./scripts/yek-context.sh agency-os 100K    # Backend src/
./scripts/yek-context.sh frontend 50K      # Frontend src/
```

## Key Files Reference

| Path | Purpose |
|------|---------|
| `src/detectors/` | WHO/WHAT/WHEN/HOW ML models |
| `src/engines/` | Core business logic |
| `src/orchestration/` | Prefect flow definitions |
| `src/integrations/` | External API clients |
| `src/models/` | Pydantic models & DB schemas |

## Design Language (STRICT)

### Banned Terms
- "Leads" → Use **"Prospects"** or **"Opportunities"**
- "Credits" → Subscription model, no credits
- Any commodity language

### Dashboard Principles
- Show customer metrics, not operator metrics
- Every element answers: "Is this working?", "How well?", "What should I do next?"
- Emotions: Confidence, excitement, validation — NOT anxiety, confusion, overwhelm

## Business Context

**Target:** Australian marketing agencies ($30K-$300K MRR)

**Pricing Tiers (AUD/month):**
- Ignition: $2,500
- Velocity: $5,000
- Dominance: $7,500

**Differentiators:**
1. Australian market specialist
2. Outcome-focused (show rate, not activity)
3. Agency B2B model (not direct sales)
4. Meetings-as-a-service positioning

---

*For detailed current state, see: `projects/agency-os/CONTEXT.md`*
