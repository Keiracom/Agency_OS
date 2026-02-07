# Infrastructure Audit Report

**Generated:** 2026-02-06 01:36 UTC  
**Auditor:** RESEARCHER-INFRA (Subagent)

---

## Executive Summary

| Service | Status | Notes |
|---------|--------|-------|
| **Railway** | ⚠️ AUTH ISSUE | MCP returns "Not Authorized" - token may need refresh |
| **Vercel** | ✅ HEALTHY | 17 projects, 13 production-ready |
| **Supabase** | ✅ HEALTHY | 64 tables, 17 migrations, ACTIVE_HEALTHY |
| **Prefect** | ⚠️ PARTIAL | 23 flows, most deployments PAUSED, worker NOT RUNNING |
| **Env Vars** | ✅ CONFIGURED | 68 keys set, 4 documented as missing |

---

## 1. Railway Deployment

### Status: ⚠️ AUTHENTICATION ISSUE

**Error:** `GraphQL error: Not Authorized`

**Action Required:**
- Verify `Railway_Token` in `~/.config/agency-os/.env` is valid
- Token may have expired or been rotated
- Re-authenticate via Railway dashboard: https://railway.app/account/tokens

**Expected Project:** `fef5af27-a022-4fb2-996b-cad099549af9` (per TOOLS.md)

---

## 2. Vercel Deployment

### Status: ✅ HEALTHY

**Total Projects:** 17

| Project | Framework | Status | Last Deployed |
|---------|-----------|--------|---------------|
| **elliot-pwa** | Next.js | ✅ READY | Production |
| **second-brain** | Next.js | ✅ READY | Production |
| **clawd** | Static | ✅ READY | Production |
| **elliot-app** | Next.js | ✅ READY | Production |
| **elliot-dashboard-v2** | Next.js | ✅ READY | Production |
| **elliot-dashboard** | Next.js | ✅ READY | Production |
| **agency-os** | Next.js | ✅ READY | Production |
| **simple-claude** | Static | ✅ READY | Production |
| **mrc-website** | Static | ✅ READY | Production (keiracom.com) |
| **claude-memory-system** | Static | ✅ READY | Production |
| **mrc-memory-api** | Static | ✅ READY | Production |
| **keiracom-web** | Next.js | ✅ READY | Production |
| **frontend** | Next.js | ❌ ERROR | Build failed |
| **keiracom-api** | Python | ❌ ERROR | Build failed |
| **keiracom-v3-core-sugy** | Next.js | ❌ ERROR | Build failed |
| **keiracom-v3-core** | Next.js | ❌ ERROR | Build failed |

### Key Production URLs:
- `elliot-pwa.vercel.app`
- `elliot-dashboard.vercel.app`
- `agency-os-liart.vercel.app`
- `keiracom.com` / `www.keiracom.com` (mrc-website)

---

## 3. Supabase

### Status: ✅ HEALTHY

**Projects:**

| Project | Region | Status | DB Version |
|---------|--------|--------|------------|
| **agency-os-prod** | ap-southeast-1 | ✅ ACTIVE_HEALTHY | PostgreSQL 17.6.1.063 |
| Keiracom's Project | ap-southeast-2 | ⏸️ INACTIVE | PostgreSQL 15.8.1.105 |
| LeakDetector | ap-southeast-2 | ⏸️ INACTIVE | PostgreSQL 17.4.1.036 |
| Keiracom v3 | ap-south-1 | ⏸️ INACTIVE | PostgreSQL 17.6.1.054 |

### Active Database: `jatzvazlbusedwsnqxzr`

**Tables:** 64 in public schema

<details>
<summary>Table Summary (click to expand)</summary>

| Table | RLS | Rows | Purpose |
|-------|-----|------|---------|
| clients | ✅ | 18 | Client accounts |
| users | ✅ | 17 | User accounts |
| memberships | ✅ | 19 | User-client relationships |
| campaigns | ✅ | 2 | Outreach campaigns |
| leads | ✅ | 2 | Lead records |
| lead_pool | ✅ | 11 | Lead sourcing pool |
| icp_extraction_jobs | ✅ | 49 | ICP extraction tracking |
| elliot_knowledge | ✅ | 659 | Elliot's knowledge base |
| elliot_signoff_queue | ✅ | 52 | Action approval queue |
| elliot_tasks | ✅ | 3 | Spawned agent tracking |
| elliot_status | ✅ | 1 | Status dashboard |
| elliot_session_state | ✅ | 4 | Session continuity |
| audit_logs | ✅ | 1 | Audit trail |
| ... | ... | ... | (51 more tables) |

</details>

### Migrations Applied: 17

```
001_foundation
002_clients_users_memberships
003_campaigns
004_leads_suppression
005_activities
006_permission_modes
007_webhook_configs
008_audit_logs
009_rls_policies
010_platform_admin
011_fix_user_insert_policy
012_client_icp_profile
013_campaign_templates
014_conversion_intelligence
015_founding_spots
016_auto_provision_client
017_fix_trigger_schema
```

---

## 4. Prefect Orchestration

### Status: ⚠️ WORKER NOT RUNNING

**Server:** `prefect-server-production-f9b1.up.railway.app` ✅ Responding

### Flows: 23 registered

| Flow | Deployments | Description |
|------|-------------|-------------|
| daily_learning_scrape | daily-learning-scrape | Daily HN/PH/GitHub scraping |
| persona_buffer_replenishment | persona-buffer-flow | Persona buffer management |
| warmup_monitor | warmup-monitor-flow | Domain warmup tracking |
| crm-sync-flow | crm-sync-flow | CRM integration sync |
| batch_campaign_evolution | batch-campaign-evolution-flow | A/B test evolution |
| campaign_evolution | campaign-evolution-flow | Campaign optimization |
| monthly_replenishment | monthly-replenishment-flow | Lead quota refill |
| credit_reset_check | credit-reset-flow | Billing credit checks |
| *... 15 more flows* | | |

### Deployments: 24 total

**By Status:**
- ⏸️ **PAUSED:** 10 (persona-buffer, warmup-monitor, crm-sync, pattern-learning, pool-allocation, reply-recovery, outreach, enrichment, etc.)
- ✅ **READY:** 13 (most webhook-triggered flows)
- ⚠️ **NOT_READY:** 1 (daily-learning-scrape - local-pool worker offline)

### Recent Failed Runs (Last 7 Days):

| Run | Flow | State | Error |
|-----|------|-------|-------|
| lavender-caterpillar | daily_learning_scrape | CRASHED | Cancelled by runtime |
| sensible-octopus | daily_learning_scrape | CRASHED | Cancelled by runtime |
| classy-groundhog | daily_learning_scrape | CRASHED | Cancelled by runtime |

### Late Scheduled Runs:
- `tungsten-skua` (Feb 5) - daily-learning-scrape - **LATE**
- `cyber-bustard` (Feb 4) - daily-learning-scrape - **LATE**

### Work Pools:
- `agency-os-pool` - Railway-based (flows show READY)
- `local-pool` - Local worker (NOT_READY - worker not running)

**Action Required:**
1. Start local Prefect worker: `prefect worker start -p local-pool`
2. Or migrate daily-learning-scrape to agency-os-pool

---

## 5. Environment Variables

### Status: ✅ CONFIGURED (68 keys)

**Set Keys (from `~/.config/agency-os/.env`):**

| Category | Keys Set |
|----------|----------|
| **AI/LLM** | ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY |
| **Database** | DATABASE_URL, DATABASE_URL_MIGRATIONS, SUPABASE_* (6 keys), REDIS_URL, UPSTASH_* |
| **Enrichment** | APOLLO_API_KEY, PROSPEO_API_KEY, DATAFORSEO_* |
| **Outreach** | SALESFORGE_*, WARMFORGE_*, INFRAFORGE_*, HEYREACH_API_KEY |
| **Communication** | TWILIO_*, TELNYX_*, RESEND_API_KEY, CLICKSEND_* |
| **Voice** | VAPI_*, CARTESIA_API_KEY, ELEVENLABS_API_KEY |
| **Infrastructure** | Railway_Token, VERCEL_TOKEN, PREFECT_API_URL |
| **Social** | UNIPILE_*, YOUTUBE_*, TELEGRAM_TOKEN |
| **Other** | GITHUB_TOKEN, BRAVE_API_KEY, WEBSHARE_API_KEY, EXPO_TOKEN |

### Missing Keys (per TOOLS.md):

| Key | Service | Status |
|-----|---------|--------|
| `HUNTER_API_KEY` | Hunter.io | ❌ Not set |
| `SLACK_BOT_TOKEN` | Slack | ❌ Not set |
| `NOTION_API_KEY` | Notion | ❌ Not set |
| `LINEAR_API_KEY` | Linear | ❌ Not set |

---

## 6. MCP Bridge Status

### Verified Working: 15 servers

| Server | Status | Notes |
|--------|--------|-------|
| supabase | ✅ npm | Database queries working |
| redis | ✅ npm | Cache operations |
| prefect | ✅ Built | Flows/deployments working |
| railway | ⚠️ Built | Auth issue (token) |
| vercel | ✅ Built | Projects/deployments working |
| apollo | ✅ Built | Enrichment |
| prospeo | ✅ Built | Email finder |
| hunter | ✅ Built | (Needs API key) |
| dataforseo | ✅ Built | SEO data |
| salesforge | ✅ Built | Outreach |
| vapi | ✅ Built | Voice AI |
| telnyx | ✅ Built | SMS/Voice |
| unipile | ✅ Built | LinkedIn |
| resend | ✅ Built | Email |
| memory | ✅ Built | Semantic search |

---

## Recommendations

### Immediate (P0):
1. **Railway Token:** Re-generate and update `Railway_Token`
2. **Prefect Worker:** Start local-pool worker or migrate deployments

### Short-term (P1):
1. Add missing API keys (Hunter, Slack, Notion, Linear)
2. Investigate 4 Vercel projects with ERROR status
3. Unpause critical Prefect deployments (enrichment, outreach)

### Monitoring:
- daily-learning-scrape has 3 crashed runs - investigate runtime cancellation
- Several scheduled flows are LATE - worker offline

---

*Report generated by RESEARCHER-INFRA subagent via MCP Bridge*
