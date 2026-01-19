# PROGRESS.md — Agency OS Roadmap & Status

**Last Updated:** January 20, 2026
**Current Phase:** 21 (E2E Testing)
**Next Milestone:** Complete E2E journeys J1-J6 live

---

## STATUS AT A GLANCE

| Area | Status | Blocker |
|------|--------|---------|
| Platform Build | ✅ 174/174 | — |
| CIS Data (Phase 24) | ✅ 66/66 | — |
| Email Infra | ✅ Warmup ends Jan 20 | — |
| E2E Testing | 🟡 Restructuring | Defining sub-tasks |
| First Customer | 🔴 | E2E + warmup |

---

## ROADMAP

| Phase | Name | Status | Spec |
|-------|------|--------|------|
| 1-16 | Core Platform | ✅ | `docs/progress/COMPLETED_PHASES.md` |
| 17 | Launch Prerequisites | ✅ | `docs/phases/PHASE_17_LAUNCH_PREREQ.md` |
| 18 | Email Infrastructure | ✅ | Salesforge/Warmforge ecosystem |
| 19 | Scraper Waterfall | ✅ | `docs/specs/integrations/SCRAPER_WATERFALL.md` |
| 20 | UI Wiring | ✅ | ALS > 85 → Deep Research trigger |
| 21 | E2E Testing | 🟡 | See below |
| 22 | Marketing Automation | 📋 | `docs/phases/PHASE_22_MARKETING_AUTO.md` |
| 23 | Platform Intelligence | 📋 | `docs/phases/PHASE_23_PLATFORM_INTEL.md` |
| 24 | CIS Data Architecture | ✅ | `docs/phases/PHASE_24_LEAD_POOL.md` |

**Legend:** ✅ Complete | 🟡 In Progress | 📋 Planned | 🔴 Blocked

---

## CURRENT FOCUS: Phase 21 (E2E Testing)

**Goal:** Comprehensive system validation before launch
**Master Tracker:** `docs/e2e/E2E_MASTER.md`
**Instructions:** `docs/e2e/E2E_INSTRUCTIONS.md`

### Journey Status

| Journey | Name | Status | Sub-Tasks |
|---------|------|--------|-----------|
| J0 | Infrastructure & Wiring Audit | 🔴 Defining | Pending |
| J1 | Signup & Onboarding | 🔴 Defining | 15 draft |
| J2 | Campaign & Leads | 🔴 Not Started | — |
| J3 | Outreach Execution | 🔴 Not Started | — |
| J4 | Reply & Meeting | 🔴 Not Started | — |
| J5 | Dashboard Validation | 🔴 Not Started | — |
| J6 | Admin Dashboard | 🔴 Not Started | — |

### What Changed

Previous E2E approach only tested "does it work?" — now we test:
- **Part A:** Code & wiring verification (is it implemented correctly?)
- **Part B:** Live execution test (does it actually work?)

This catches issues like Prefect pointing to Cloud instead of self-hosted.

**Next Actions:**
1. Define J0 sub-tasks (Infrastructure Audit) — runs FIRST
2. Define J1-J6 sub-tasks with CEO review
3. Execute J0 → J1 → J2 → J3 → J4 → J5 → J6 in order

### E2E Documentation

| File | Purpose |
|------|---------|
| `docs/e2e/E2E_MASTER.md` | Status dashboard |
| `docs/e2e/E2E_INSTRUCTIONS.md` | Execution protocol |
| `docs/e2e/E2E_TASK_BREAKDOWN.md` | What we're really testing |
| `docs/e2e/J0_INFRASTRUCTURE.md` | Infrastructure audit |
| `docs/e2e/J1_ONBOARDING.md` - `J6_ADMIN.md` | Journey specs |
| `docs/e2e/ISSUES_FOUND.md` | Problems discovered |
| `docs/e2e/FIXES_APPLIED.md` | Changes made |

---

## BLOCKERS

| Blocker | Impact | ETA |
|---------|--------|-----|
| Mailbox warmup | Can't send cold email at volume | Jan 20, 2026 |

---

## ACTION ITEMS

- [ ] Set TEST_MODE env vars in Railway
- [ ] Subscribe to Salesforge Pro by Jan 11
- [ ] Run E2E journey J1 live
- [ ] Fix ISS-001: Update SCHEMA_OVERVIEW.md with migrations 018-031

---

## KEY URLS

| Service | URL |
|---------|-----|
| Frontend | https://agency-os-liart.vercel.app |
| Backend | https://agency-os-production.up.railway.app |
| Admin | https://agency-os-liart.vercel.app/admin |
| Health | https://agency-os-production.up.railway.app/api/v1/health |

---

## TEST CONFIGURATION

| Field | Value |
|-------|-------|
| Test Agency | Sparro Digital |
| Website | https://sparro.com.au |
| Industry | Digital Marketing / Performance Marketing |
| Location | Melbourne, Australia |
| Tier | Velocity ($5,000/mo) |
| Test Email | david.stephens@keiracom.com |
| Test Phone | +61457543392 |
| Test LinkedIn | https://www.linkedin.com/in/david-stephens-8847a636a/ |
| E2E Budget | $60 AUD |

> Full E2E plan: `docs/e2e/E2E_TEST_PLAN.md`

**TEST_MODE Environment Variables (set in Railway):**
```
TEST_MODE=true
TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com
TEST_SMS_RECIPIENT=+61457543392
TEST_VOICE_RECIPIENT=+61457543392
TEST_LINKEDIN_RECIPIENT=https://www.linkedin.com/in/david-stephens-8847a636a/
TEST_DAILY_EMAIL_LIMIT=15
```

---

## PREFECT CONFIGURATION

**Prefect Server (Self-Hosted on Railway):**
- **Dashboard:** https://prefect-server-production-f9b1.up.railway.app/dashboard
- **API:** https://prefect-server-production-f9b1.up.railway.app/api
- **Work Pool:** `agency-os-pool` (type: process, status: READY)
- **Work Queue:** `agency-os-queue`

**Required Railway Environment Variable:**
```
PREFECT_API_URL=https://prefect-server-production-f9b1.up.railway.app/api
```

## PREFECT FLOWS STATUS

| Flow | Deployment Name | Status |
|------|-----------------|--------|
| icp_onboarding_flow | onboarding-flow | ✅ Active |
| pool_population | pool-population-flow | ✅ Active |
| daily_enrichment | enrichment-flow | ⏸️ Paused |
| campaign_activation | campaign-flow | ✅ Active |
| hourly_outreach | outreach-flow | ⏸️ Paused |
| intelligence_research | intelligence-flow | ✅ Active |
| trigger_lead_research | lead-research-flow | ✅ Active |
| single_client_pattern_learning | client-pattern-learning-flow | ✅ Active |
| weekly_pattern_learning | pattern-learning-flow | ⏸️ Paused |
| pool_campaign_assignment | pool-assignment-flow | ✅ Active |
| reply_recovery | reply-recovery-flow | ⏸️ Paused |
| pattern_backfill | pattern-backfill-flow | ✅ Active |
| single_client_backfill | client-backfill-flow | ✅ Active |
| pool_daily_allocation | pool-daily-allocation-flow | ⏸️ Paused |
| icp_reextract_flow | icp-reextract-flow | ✅ Active |
| lead_enrichment | enrichment-waterfall-flow | ✅ Active |
| batch_lead_enrichment | batch-enrichment-flow | ✅ Active |

**Total:** 17 deployments (12 active, 5 paused)

---

## PHASE 24 STATUS (CIS Data)

| Sub-Phase | Tasks | Status |
|-----------|-------|--------|
| 24A: Lead Pool | 15 | ✅ |
| 24A+: LinkedIn Enrichment | 8 | ✅ |
| 24B: Content Tracking | 7 | ✅ |
| 24C: Email Engagement | 7 | ✅ |
| 24D: Conversation Threading | 8 | ✅ |
| 24E: Downstream Outcomes | 7 | ✅ |
| 24F: CRM Push | 12 | ✅ |
| 24G: Customer Import | 10 | ✅ |
| 24H: LinkedIn Connection | 10 | 📋 |
| **Total** | **84** | **74/84** |

---

## PHASE 37 STATUS (Lead/Campaign Architecture) ✅

**Goal:** Simplify lead ownership model - leads owned directly via lead_pool.client_id

| Task | Status | Notes |
|------|--------|-------|
| Create TIER_CONFIG constant | ✅ | `src/config/tiers.py` |
| Fix tier numbers in tests | ✅ | Velocity=2250, Dominance=4500 |
| Add client_id/campaign_id to lead_pool | ✅ | Migration 037 |
| Add campaign_type/lead_allocation to Campaign | ✅ | Migration 038 |
| Update scorer.py to write to lead_pool | ✅ | Direct ownership model |
| Update lead_allocator_service.py | ✅ | Sets client_id on lead_pool |
| Update pool_assignment_flow.py | ✅ | Uses lead_pool_ids |
| Create campaign suggestion engine | ✅ | `src/engines/campaign_suggester.py` |
| Add post-onboarding lead sourcing | ✅ | `src/orchestration/flows/post_onboarding_flow.py` |

**Architecture Decision:**
- One lead = one client = ONE campaign (at a time)
- `lead_pool.client_id = NULL` → available for sourcing
- `lead_pool.client_id = UUID` → owned by that client
- ALS scores stored directly in `lead_pool` table

**New Files Created:**
- `src/engines/campaign_suggester.py` - AI campaign suggestions from ICP
- `src/orchestration/flows/post_onboarding_flow.py` - Post-onboarding setup flow

**API Endpoints Added:**
- `GET /clients/{client_id}/campaigns/suggestions` - Get AI campaign suggestions
- `POST /clients/{client_id}/campaigns/suggestions/create` - Create campaigns from suggestions

---

## SDK INTEGRATION FOR HOT LEADS ✅

**Goal:** Use Claude Agent SDK for hyper-personalized outreach to Hot leads (ALS 85+)

| Task | Status | Notes |
|------|--------|-------|
| Create sdk_eligibility.py | ✅ | Gate functions for SDK eligibility |
| Create enrichment_agent.py | ✅ | SDK deep research with web_search/web_fetch |
| Create email_agent.py | ✅ | SDK personalized email generation |
| Create voice_kb_agent.py | ✅ | SDK voice knowledge base generation |
| Add agent type configs to sdk_brain.py | ✅ | enrichment, email, voice_kb configs |
| Integrate SDK in scout.py | ✅ | SDK enrichment for Hot leads with signals |
| Integrate SDK in content.py | ✅ | SDK email for ALL Hot leads |
| Integrate SDK in voice.py | ✅ | SDK voice KB for ALL Hot leads |

**Architecture:**
- SDK Enrichment: Hot leads (ALS >= 85) WITH at least one priority signal (~20% of Hot)
- SDK Email: ALL Hot leads (100% of Hot = ~10% of total)
- SDK Voice KB: ALL Hot leads (100% of Hot = ~10% of total)

**Priority Signals (for SDK Enrichment):**
1. Recent funding (< 90 days)
2. Actively hiring (3+ roles)
3. Tech stack match > 80%
4. LinkedIn engagement > 70
5. Referral source
6. Employee count sweet spot (50-500)

**Cost Per Hot Lead:**
| Agent | Max Cost | Typical Cost |
|-------|----------|--------------|
| Enrichment | $1.50 | ~$1.00-1.21 |
| Email | $0.50 | ~$0.20-0.25 |
| Voice KB | $2.00 | ~$1.50-1.79 |

**Files Created:**
- `src/agents/sdk_agents/sdk_eligibility.py`
- `src/agents/sdk_agents/enrichment_agent.py`
- `src/agents/sdk_agents/email_agent.py`
- `src/agents/sdk_agents/voice_kb_agent.py`

---

## EMAIL INFRASTRUCTURE

**Stack:** InfraForge (domains) → Warmforge (warmup) → Salesforge (sending)

| Domain | Mailboxes | Warmup Status |
|--------|-----------|---------------|
| agencyxos-growth.com | 2 | Warming |
| agencyxos-reach.com | 2 | Warming |
| agencyxos-leads.com | 2 | Warming |

**Ready Date:** Jan 20, 2026
**Action Required:** Subscribe to Salesforge Pro by Jan 11 ($48/mo)

---

## PRICING SUMMARY

| Tier | Price | Margin | Leads |
|------|-------|--------|-------|
| Ignition | $2,500 | 73.4% | 1,250 |
| Velocity | $5,000 | 73.5% | 2,250 |
| Dominance | $7,500 | 66.6% | 4,500 |

→ Full model: `docs/specs/TIER_PRICING_COST_MODEL_v2.md`

---

## WHAT "DONE" LOOKS LIKE

Before first paying customer:

### Infrastructure Ready
- [x] All API credentials collected and configured
- [ ] Health checks pass for all integrations
- [ ] Production database seeded with test data
- [ ] Error monitoring active (Sentry)

### End-to-End Flow Works
- [ ] Signup → Onboarding → ICP extraction completes
- [ ] Campaign creation with AI content generation works
- [ ] Real email sent and received in inbox
- [ ] Reply handling and intent classification works
- [ ] Dashboard shows accurate real-time data
- [ ] Admin panel shows platform-wide metrics

---

## RECENT SESSIONS

> Full history: `docs/progress/SESSION_LOG.md`

### Jan 11, 2026
- Replaced Resend with Salesforge as primary email provider
- Created `src/integrations/salesforge.py` with SalesforgeClient
- Updated `src/engines/email.py` to use SalesforgeClient
- Fixed webhook endpoints for correct EmailEventsService usage
- Preserves Warmforge mailbox warmup progress

### Jan 10, 2026
- Phase 24A+ LinkedIn Enrichment Waterfall implemented (8 tasks)
- PersonalizationAnalysisSkill for Claude pain point analysis
- LinkedIn scoring boost integrated into scorer engine (max +10 points)

### Jan 9, 2026
- Portfolio Fallback Discovery implemented (ICP-FALLBACK-001, ICP-FALLBACK-002)
- Fixed Apify Google Search flattening

### Jan 8, 2026
- Documentation audit & cleanup
- Logging protocol implemented

### Jan 7, 2026
- TEST_MODE deployed
- E2E code review complete (J1-J6 pass)
- All 15 Prefect flows operational

### Jan 6, 2026
- Phase 18 Email Infrastructure complete
- Phase 24 CIS Data complete (66 tasks)

---

## QUICK REFERENCE

| Need | Location |
|------|----------|
| **E2E Testing** | `docs/e2e/E2E_MASTER.md` |
| E2E Instructions | `docs/e2e/E2E_INSTRUCTIONS.md` |
| Completed phases | `docs/progress/COMPLETED_PHASES.md` |
| Session history | `docs/progress/SESSION_LOG.md` |
| Known issues | `docs/progress/ISSUES.md` |
| Architecture decisions | `docs/architecture/DECISIONS.md` |
| Phase specs | `docs/phases/PHASE_INDEX.md` |
| Import rules | `docs/architecture/IMPORT_HIERARCHY.md` |
| Database schema | `docs/specs/database/SCHEMA_OVERVIEW.md` |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| 🔴 | Not Started / Blocked |
| 🟡 | In Progress |
| ✅ | Complete |
| 📋 | Planned (Post-Launch) |
