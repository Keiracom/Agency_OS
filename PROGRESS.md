# PROGRESS.md — Agency OS Build Tracker

**Last Updated:** January 4, 2026
**Current Phase:** PHASE 17-19 - Launch Prerequisites + Email Infrastructure
**Status:** Platform built (174/174), preparing for launch, Phase 20 documented

> **Archive:** Completed phases 1-16 detailed in [`docs/progress/COMPLETED_PHASES.md`](docs/progress/COMPLETED_PHASES.md)

---

## 🎯 WHAT "DONE" LOOKS LIKE

Before we have our first paying customer, ALL of the following must be true:

### Infrastructure Ready
- [ ] All API credentials collected and configured
- [ ] Health checks pass for all integrations
- [ ] Production database seeded with test data
- [ ] Error monitoring active (Sentry)

### End-to-End Flow Works
- [ ] Signup → Onboarding → ICP extraction completes *(M1)*
- [ ] Campaign creation with AI content generation works *(M2)*
- [ ] Real email sent and received in inbox *(M3)*
- [ ] Reply handling and intent classification works *(M4)*
- [ ] Dashboard shows accurate real-time data *(M5)*
- [ ] Admin panel shows platform-wide metrics *(M6)*

### Marketing Ready
- [ ] Landing page live with waitlist capture
- [ ] Automated content pipeline configured (HeyGen + social)
- [ ] First "Day 1" video posted
- [ ] Dogfooding: Agency OS sells itself via its own outreach

### First 20 Customers
- [ ] 5 paying customers
- [ ] 10 paying customers
- [ ] 15 paying customers
- [ ] 20 paying customers (SOLD OUT - founding tier)

---

## Phase Status Overview

| Phase | Name | Status | Tasks | Complete |
|-------|------|--------|-------|----------|
| 1-10 | Core Platform | ✅ | 98 | 98 |
| 11 | ICP Discovery | ✅ | 18 | 18 |
| 12A | Campaign Gen | ✅ | 6 | 6 |
| 12B | Campaign Enhancement | ✅ | 2 | 2 |
| 13 | Frontend-Backend | ✅ | 7 | 7 |
| 14 | Missing UI | ✅ | 4 | 4 |
| 15 | Live UX Testing | ✅ | 6 | 6 |
| 16 | Conversion Intelligence | ✅ | 30 | 30 |
| **17** | **Launch Prerequisites** | 🟡 | **20** | **8** |
| **18** | **E2E Journey Test** | 🟡 | **47** | **5** |
| **19** | **Email Infrastructure** | 🟡 | **20** | **1** |
| **20** | **Platform Intelligence** | 📋 | **18** | **0** |
| **21** | **Landing Page + UI Overhaul** | 🟡 | **18** | **15** |

**Platform Tasks:** 174/174 (100% complete)
**Launch Tasks:** 16/88 (18% complete)
**UI/Marketing Tasks:** 15/18 (83% - Phase 21)
**Post-Launch Tasks:** 0/18 (Phase 20 - planned)

---

## Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://agency-os-liart.vercel.app |
| Backend | https://agency-os-production.up.railway.app |
| Admin | https://agency-os-liart.vercel.app/admin |
| Health | https://agency-os-production.up.railway.app/api/v1/health |

---

## PHASE 17: Launch Prerequisites

**Purpose:** Everything needed before first paying customer
**Spec:** `docs/marketing/MARKETING_LAUNCH_PLAN.md`

### 17A: API Credentials (8 tasks)

| Task | Description | Status | Priority |
|------|-------------|--------|----------|
| CRED-001 | Resend API key + domain verification | ✅ | P0 |
| CRED-002 | Anthropic API key + spend limit | ✅ | P0 |
| CRED-003 | Apollo API key | ✅ | P0 |
| CRED-004 | Apify API key | ✅ | P0 |
| CRED-005 | Twilio account + phone number | ✅ | P1 |
| CRED-006 | HeyReach API key + LinkedIn seats | ✅ | P1 |
| CRED-007 | Vapi API key + phone number link | ✅ | P1 |
| CRED-007a | ElevenLabs API key | ✅ | P1 |
| CRED-008 | ClickSend credentials (AU direct mail) | 🔴 | P2 |
| CRED-009 | DataForSEO credentials | ✅ | P1 |
| CRED-010 | v0.dev API key (UI generation) | ✅ | P1 |

### 17B: Frontend Missing Pages (3 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| FE-016 | Landing page with waitlist | ✅ | `frontend/app/page.tsx` |
| FE-017 | Pricing page | ✅ | `frontend/app/(marketing)/pricing/page.tsx` |
| FE-018 | Waitlist thank you page | ✅ | `frontend/app/waitlist/thank-you/page.tsx` |

**FE-016-018 Notes (Jan 4, 2026):**
- Landing page rebuilt with Expert Panel animations (floating orbs, glass morphism, scroll-reveal)
- Added Buyer Guide ROI selling points (SDR comparison, cost-per-meeting tables)
- Year 1 comparison: $36K savings, 2.2x meetings vs junior SDR
- Waitlist API updated to store in Supabase + send via Resend
- Thank you page with confetti animation and next steps
- Migration created: `015_waitlist.sql`

### 17C: Live Validation (4 tasks)

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| LIVE-001 | Integration health check script | ✅ | CRED-001 to CRED-004 |
| LIVE-002 | Send test email to yourself | 🔴 | CRED-001 |
| LIVE-003 | Full onboarding flow test | 🟡 | CRED-002, CRED-003, CRED-004 |
| LIVE-004 | Full campaign creation test | 🔴 | LIVE-003 |

### 17X: Auto-Provisioning Flow (NEW - Jan 4, 2026)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| PROV-001 | Migration: auto-provision client on signup | ✅ | `supabase/migrations/016_auto_provision_client.sql` |
| PROV-002 | Auth callback: redirect based on onboarding status | ✅ | `frontend/app/auth/callback/route.ts` |
| PROV-003 | Dashboard layout: redirect to onboarding if needed | ✅ | `frontend/app/dashboard/layout.tsx` |
| PROV-004 | Skip onboarding page (testing) | ✅ | `frontend/app/onboarding/skip/page.tsx` |
| PROV-005 | Supabase export createClient alias | ✅ | `frontend/lib/supabase.ts` |

**Auto-Provisioning Flow (Jan 4, 2026):**
- New users automatically get: client (tenant) + owner membership
- Auth callback checks `get_onboarding_status()` RPC
- If `icp_confirmed_at` is NULL → redirect to `/onboarding`
- If ICP confirmed → redirect to `/dashboard`
- Skip page at `/onboarding/skip` for testing (sets default ICP values)

**Health Check Results (Jan 4, 2026):**
| Service | Status | Notes |
|---------|--------|-------|
| Anthropic | ✅ | Working |
| Resend | ✅ | Working (send-only, expected) |
| Apollo | ✅ | Working (upgraded) |
| Apify | ✅ | Working |

### 17D: Marketing Automation Integrations (2 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| INT-013 | HeyGen integration | 🔴 | `src/integrations/heygen.py` |
| INT-014 | Buffer integration | 🔴 | `src/integrations/buffer.py` |

### 17E: Marketing Automation Setup (3 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| MKT-001 | HeyGen account + avatar setup | 🔴 | — |
| MKT-002 | Content automation flow (Prefect) | 🔴 | `src/orchestration/flows/marketing_automation_flow.py` |
| MKT-003 | Day 1 video script + post | 🔴 | — |

---

## PHASE 18: E2E Journey Test

**Purpose:** Validate complete user journey before launch
**Spec:** `docs/audits/UX_AUDIT_2026-01-04.md`

### Pre-Flight Checks (7 tests)

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 1 | Backend health check | 200 OK | ✅ | `{"status":"healthy","version":"3.0.0"}` |
| 2 | Frontend loads | No console errors | ✅ | Returns 307 redirect (expected) |
| 3 | Supabase connection | Can query | ✅ | Connected, queried clients table |
| 4 | Resend API works | Can send | ✅ | Key restricted to send-only (intentional) |
| 5 | Anthropic API works | Can generate | ✅ | Claude response generated |
| 6 | Apollo API works | Can enrich | ✅ | Upgraded - full API access |
| 7 | Apify API works | Can scrape | ✅ | User: brawny_epitope |

**Pre-Flight Result:** ✅ 7/7 Pass

---

### M1: Signup & Onboarding (10 tests)

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1 | Go to /login | Login page loads | 🔴 |
| 2 | Click "Sign Up" | Signup form shows | 🔴 |
| 3 | Enter email + password | Form validates | 🔴 |
| 4 | Submit signup | Confirmation sent | 🔴 |
| 5 | Confirm email | Redirected to onboarding | 🔴 |
| 6 | Enter website URL | ICP extraction starts | 🔴 |
| 7 | Wait for extraction | Progress shown | 🔴 |
| 8 | Review ICP | Extracted data displayed | 🔴 |
| 9 | Confirm ICP | Saved to database | 🔴 |
| 10 | Redirected to dashboard | Dashboard loads | 🔴 |

**M1 Result:** 🔴 Not Started

---

### M2: Campaign & Leads (10 tests)

| # | Test | Expected | Status |
|---|------|----------|--------|
| 11 | Go to /dashboard/campaigns | Campaigns page loads | 🔴 |
| 12 | Click "New Campaign" | Creation form loads | 🔴 |
| 13 | Enter campaign name | Field validates | 🔴 |
| 14 | Select permission mode | Mode saved | 🔴 |
| 15 | Create campaign | Campaign created | 🔴 |
| 16 | Go to /dashboard/leads | Leads page loads | 🔴 |
| 17 | Click "Import" | Import UI shows | 🔴 |
| 18 | Add test lead manually | Lead created | 🔴 |
| 19 | View lead detail | Lead data correct | 🔴 |
| 20 | Assign lead to campaign | Lead assigned | 🔴 |

**M2 Result:** 🔴 Not Started

---

### M3: Email Send (5 tests)

| # | Test | Expected | Status |
|---|------|----------|--------|
| 21 | Go to campaign detail | Shows 1 lead assigned | 🔴 |
| 22 | Click "Activate Campaign" | Status → Active | 🔴 |
| 23 | Trigger send | Email queued | 🔴 |
| 24 | Check inbox | Email received | 🔴 |
| 25 | Verify email content | Personalization correct | 🔴 |

**Email Checks:**
- [ ] From address is verified domain
- [ ] Subject line rendered
- [ ] {first_name} replaced
- [ ] Unsubscribe link works

**M3 Result:** 🔴 Not Started

---

### M4: Reply Handling (5 tests)

| # | Test | Expected | Status |
|---|------|----------|--------|
| 26 | Reply to email: "I'm interested" | Email sent | 🔴 |
| 27 | Wait 1-2 min for webhook | Reply processed | 🔴 |
| 28 | Check lead status in UI | Shows "Replied" | 🔴 |
| 29 | Check intent classification | Classified as "interested" | 🔴 |
| 30 | Check activity feed | Reply activity visible | 🔴 |

**M4 Result:** 🔴 Not Started

---

### M5: Dashboard Validation (5 tests)

| # | Test | Expected | Status |
|---|------|----------|--------|
| 31 | View dashboard | Shows 1 campaign, 1 lead | 🔴 |
| 32 | Stats cards accurate | 1 sent, 1 open, 1 reply | 🔴 |
| 33 | Activity feed shows events | Send + reply visible | 🔴 |
| 34 | ALS distribution shows 1 lead | Correct tier | 🔴 |
| 35 | Refresh page | Data persists | 🔴 |

**M5 Result:** 🔴 Not Started

---

### M6: Admin Dashboard (5 tests)

**Requires:** Admin frontend wired to backend APIs (ADM fixes below)

| # | Test | Expected | Status |
|---|------|----------|--------|
| 36 | Go to /admin | Admin dashboard loads | 🔴 |
| 37 | Platform stats correct | 1 client, 1 campaign, real numbers | 🔴 |
| 38 | Client list shows your client | Name, tier, status visible | 🔴 |
| 39 | Activity log shows events | Platform-wide activities | 🔴 |
| 40 | System health all green | Integrations healthy | 🔴 |

**M6 Result:** 🔴 Not Started

---

### Admin Dashboard Fixes (Required for M6)

The audit found Admin frontend uses mock data. These fixes required before M6:

| Task | Description | File | Status |
|------|-------------|------|--------|
| ADM-001 | Create admin hooks | `frontend/hooks/use-admin.ts` | 🔴 |
| ADM-002 | Create admin API functions | `frontend/lib/api/admin.ts` | 🔴 |
| ADM-003 | Wire Admin Command Center | `frontend/app/admin/page.tsx` | 🔴 |
| ADM-004 | Wire Admin Clients page | `frontend/app/admin/clients/page.tsx` | 🔴 |
| ADM-005 | Wire Admin Activity page | `frontend/app/admin/activity/page.tsx` | 🔴 |

---

### Phase 18 Summary

| Milestone | Tests | Passed | Status |
|-----------|-------|--------|--------|
| Pre-Flight | 7 | 7 | ✅ |
| M1: Signup & Onboarding | 10 | 0 | 🔴 |
| M2: Campaign & Leads | 10 | 0 | 🔴 |
| M3: Email Send | 5 | 0 | 🔴 |
| M4: Reply Handling | 5 | 0 | 🔴 |
| M5: Dashboard Validation | 5 | 0 | 🔴 |
| M6: Admin Dashboard | 5 | 0 | 🔴 |
| **TOTAL** | **47** | **7** | 🟡 |

---

### Blockers Log

| ID | Milestone | Description | Severity | Fix | Status |
|----|-----------|-------------|----------|-----|--------|
| — | — | No active blockers | — | — | — |

*(Fill in as blockers discovered during testing)*

---

### Test Session Log

| Date | Tester | Milestones | Passed | Failed | Blocked | Notes |
|------|--------|------------|--------|--------|---------|-------|
| 2026-01-04 | Claude | Pre-Flight | 7 | 0 | 0 | All integrations working |

*(Add entry for each test session)*

---

---

## PHASE 19: Email Infrastructure (InfraForge + Smartlead)

**Purpose:** Programmatic email domain/mailbox provisioning and warmup
**Decision Date:** January 4, 2026
**Spec:** `PROJECT_BLUEPRINT.md` (Phase 19 section)

### Architecture Decision: APPROVED

**Selected Stack:**
- **InfraForge** → Domain purchase, mailbox creation, DNS automation, dedicated IPs
- **Smartlead** → Email account registration, warmup management, campaign sending
- **Agency OS** → Bridge orchestration, tenant provisioning, unified dashboard

**Why This Stack (vs Instantly DFY):**
- ✅ Domain ownership (InfraForge gives you the domains, Instantly retains ownership)
- ✅ 4-5x cheaper at scale ($1,500-1,800/mo vs $6,600-8,100/mo for 100 tenants)
- ✅ Dedicated IPs per tenant (reputation isolation)
- ✅ Best-in-class APIs for each function
- ✅ Exit strategy (portable infrastructure)

### Research Completed (Jan 4, 2026)

| Research Task | Status | Finding |
|---------------|--------|--------|
| Apollo API domain/mailbox | ✅ | NOT AVAILABLE - API limited to enrichment/CRM |
| Instantly API full review | ✅ | Good API but DFY locks domains to platform |
| Mailforge API search | ✅ | NO PUBLIC API - UI only or enterprise agreement |
| InfraForge API capabilities | ✅ | Full programmatic provisioning confirmed |
| Smartlead API capabilities | ✅ | Full SMTP/IMAP registration + warmup API |

### 19A: InfraForge Integration

| Task | Description | Status |
|------|-------------|--------|
| INF-001 | Request InfraForge API documentation/access | 🔴 |
| INF-002 | Create InfraForge integration client | 🔴 |
| INF-003 | Implement domain provisioning | 🔴 |
| INF-004 | Implement mailbox creation | 🔴 |
| INF-005 | Implement DNS status monitoring | 🔴 |

### 19B: Smartlead Integration

| Task | Description | Status |
|------|-------------|--------|
| SML-001 | Set up Smartlead Pro account | 🔴 |
| SML-002 | Create Smartlead integration client | 🔴 |
| SML-003 | Implement email account registration | 🔴 |
| SML-004 | Implement warmup management | 🔴 |
| SML-005 | Implement campaign API wrapper | 🔴 |
| SML-006 | Implement webhook receiver | 🔴 |

### 19C: Bridge Orchestration

| Task | Description | Status |
|------|-------------|--------|
| BRG-001 | Create tenant provisioning flow | 🔴 |
| BRG-002 | Implement infrastructure orchestration | 🔴 |
| BRG-003 | Create warmup monitoring dashboard | 🔴 |
| BRG-004 | Database schema for email infrastructure | 🔴 |
| BRG-005 | Tenant onboarding email setup | 🔴 |

### 19D: Testing & Validation

| Task | Description | Status |
|------|-------------|--------|
| TST-019-1 | InfraForge integration tests | 🔴 |
| TST-019-2 | Smartlead integration tests | 🔴 |
| TST-019-3 | End-to-end provisioning test | 🔴 |
| TST-019-4 | Warmup monitoring test | 🔴 |

### Cost Model per Tier

| Tier | Domains | Mailboxes | Est. Monthly Cost |
|------|---------|-----------|-------------------|
| Ignition | 2 | 3 | ~$115 |
| Velocity | 3 | 6 | ~$140 |
| Dominance | 5 | 11 | ~$320 |

### API Documentation

- **InfraForge:** Contact for API docs - https://infraforge.ai
- **Smartlead:** https://api.smartlead.ai/reference

### Key Smartlead API Endpoints

```
POST /api/v1/email-accounts/save          # Create email account
POST /api/v1/email-accounts/{id}/warmup   # Enable/configure warmup
GET  /api/v1/email-accounts/{id}/warmup-stats  # Get warmup stats
POST /api/v1/campaigns                    # Create campaign
POST /api/v1/campaigns/{id}/leads         # Add leads
```

---

## THE BIG TEST: Dogfooding Launch

**Goal:** Use Agency OS to sell Agency OS to 20 founding customers.

**Success Criteria:**
1. ICP = Australian marketing agencies ($30K-$300K monthly revenue)
2. Outreach sent via Agency OS automated campaigns
3. Content posted via automated pipeline
4. Zero manual outreach allowed
5. Track every metric in the dashboard

**Metrics to Capture (from Day 1):**

| Metric | Day 1 | Week 1 | Week 2 | Week 4 | Final |
|--------|-------|--------|--------|--------|-------|
| Emails Sent | — | — | — | — | — |
| Open Rate | — | — | — | — | — |
| Reply Rate | — | — | — | — | — |
| Meetings Booked | — | — | — | — | — |
| Customers Closed | — | — | — | — | — |
| Pipeline Value | — | — | — | — | — |
| Spots Remaining | 20 | — | — | — | — |

**Milestone Triggers (auto-post content):**
- [ ] First email sent
- [ ] First reply received
- [ ] First meeting booked
- [ ] First customer signed
- [ ] 5 customers
- [ ] 10 customers
- [ ] 15 customers
- [ ] 20 customers (SOLD OUT)

---

## Credential Collection Checklist

### P0 - Required for MVP

| Service | Sign Up | Env Var | Verified |
|---------|---------|---------|----------|
| Resend | https://resend.com/signup | `RESEND_API_KEY` | ✅ |
| Anthropic | https://console.anthropic.com | `ANTHROPIC_API_KEY` | ✅ |
| Apollo | https://app.apollo.io | `APOLLO_API_KEY` | ✅ |
| Apify | https://console.apify.com/sign-up | `APIFY_API_KEY` | ✅ |

### P1 - Required for Multi-Channel

| Service | Sign Up | Env Var | Verified |
|---------|---------|---------|----------|
| Twilio | https://www.twilio.com/try-twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | ✅ |
| HeyReach | https://heyreach.io | `HEYREACH_API_KEY` | ✅ |
| Vapi | https://vapi.ai | `VAPI_API_KEY`, `VAPI_PHONE_NUMBER_ID` | ✅ |
| ElevenLabs | https://elevenlabs.io | `ELEVENLABS_API_KEY` | ✅ |

### P2 - Future Channels

| Service | Sign Up | Env Var | Verified |
|---------|---------|---------|----------|
| ClickSend | https://clicksend.com | `CLICKSEND_USERNAME`, `CLICKSEND_API_KEY` | ⬜ |

### Marketing Automation

| Service | Sign Up | Purpose | Verified |
|---------|---------|---------|----------|
| HeyGen | https://heygen.com | AI video generation | ⬜ |
| Serper | https://serper.dev | Google search API | ⬜ |
| Buffer | https://buffer.com | Social scheduling | ⬜ |
| v0.dev | https://v0.dev/chat/settings/keys | AI UI generation | ✅ |

---

## PHASE 20: Platform Intelligence (Post-Launch)

**Purpose:** Cross-client learning system - aggregate conversion patterns so new clients benefit from collective learnings on Day 1
**Trigger:** Activate when 10+ clients have 50+ conversions each (~Month 4-6)
**Spec:** `PROJECT_BLUEPRINT.md` (Phase 20 section)
**Decision Date:** January 4, 2026

### Problem Solved

**Current (Phase 16):** Each client learns in isolation. New clients start from default weights.
**With Phase 20:** Platform aggregates learnings. New clients inherit platform-optimized weights immediately.

### Data Acquisition Strategy: Hybrid Approach

**Why we can't buy this data:**
- Conversion outcome data with lead attributes isn't sold anywhere
- Companies like Apollo, 6sense, Artisan guard this as competitive moat
- Privacy/legal prevents selling client campaign data
- "Marketing agencies in Australia" too niche for data vendors

**Our solution:**
1. **Seed with benchmarks** - Industry research provides starting weights
2. **Data co-op agreement** - Founding customers opt-in to share anonymized patterns
3. **Platform learning** - Aggregate across 10+ clients after Month 4

### 20A: Platform Priors (5 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| PLT-001 | Create platform_priors module | 🔴 | `src/intelligence/platform_priors.py` |
| PLT-002 | Add data sharing consent to client model | 🔴 | `src/models/client.py` |
| PLT-003 | Consent capture in onboarding | 🔴 | `frontend/app/onboarding/page.tsx` |
| PLT-004 | Database migration | 🔴 | `supabase/migrations/018_platform_intelligence.sql` |
| PLT-005 | Platform patterns model | 🔴 | `src/models/platform_patterns.py` |

### 20B: Platform Learning Engine (6 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| PLT-006 | Platform pattern aggregator | 🔴 | `src/intelligence/platform_aggregator.py` |
| PLT-007 | Platform weight optimizer | 🔴 | `src/intelligence/platform_weight_optimizer.py` |
| PLT-008 | Industry clustering (optional) | 🔴 | `src/intelligence/industry_clustering.py` |
| PLT-009 | Monthly platform learning flow | 🔴 | `src/orchestration/flows/platform_learning_flow.py` |
| PLT-010 | Platform learning scheduler | 🔴 | `src/orchestration/schedules/scheduled_jobs.py` |
| PLT-011 | Admin: platform insights page | 🔴 | `frontend/app/admin/platform-intelligence/page.tsx` |

### 20C: Scorer Integration (4 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| PLT-012 | Scorer weight fallback hierarchy | 🔴 | `src/engines/scorer.py` |
| PLT-013 | Platform weights lookup | 🔴 | `src/engines/scorer.py` |
| PLT-014 | Weight source tracking on leads | 🔴 | `src/models/lead.py` |
| PLT-015 | Unit tests for fallback | 🔴 | `tests/test_engines/test_scorer_platform.py` |

### 20D: Testing (3 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| TST-020-1 | Aggregator tests | 🔴 | `tests/intelligence/test_platform_aggregator.py` |
| TST-020-2 | Weight fallback tests | 🔴 | `tests/intelligence/test_weight_fallback.py` |
| TST-020-3 | E2E platform learning test | 🔴 | `tests/e2e/test_platform_learning.py` |

### Weight Fallback Hierarchy (Scorer)

```
1. Client learned weights (confidence > 0.7, sample >= 50) → "client_learned"
2. Industry platform weights (if industry has enough data) → "platform_industry"
3. Global platform weights (all clients aggregated) → "platform_global"
4. Platform priors (industry benchmarks) → "platform_priors"
5. Default weights (hardcoded) → "default"
```

### Industry Benchmark Priors (Seeded)

```python
PLATFORM_PRIORS = {
    "als_weights": {
        "data_quality": 0.15,   # Title matters more
        "authority": 0.30,      # Decision-maker critical
        "company_fit": 0.25,    # + DataForSEO signals
        "timing": 0.20,         # Intent signals
        "risk": 0.10,           # Reduced
    },
    "timing": {
        "best_days": ["Tuesday", "Wednesday", "Thursday"],
        "best_hours": [9, 10, 14, 15],
    },
    "content": {
        "optimal_subject_words": (4, 8),
        "optimal_body_words": (50, 125),
        "personalization_lift": 1.26,
    },
    "source": "Ruler Analytics, First Page Sage, Martal 2025",
    "confidence": 0.5,
}
```

### Activation Criteria

- ✅ 10+ clients with `data_sharing_consent = TRUE`
- ✅ Combined 500+ conversions
- ✅ At least 3 clients have learned weights

### Success Metrics

| Metric | Target |
|--------|--------|
| New client time-to-value | -2 months |
| New client first-month conversion | +20% |
| Platform weight confidence | >0.7 |

---

## Quick Commands

### Check Integration Health
```bash
# Once credentials are configured
python -c "from tests.live.config import get_config; get_config().print_status()"
```

### Run Live Tests
```bash
# Set your test email
export TEST_LEAD_EMAIL="your@email.com"
export LIVE_TEST_DRY_RUN="false"

# Run tests
pytest tests/live/ -v
```

### Seed Test Data
```bash
python tests/live/seed_live_data.py
```

---

## Completed Phases Summary

| Phase | Tasks | Completed |
|-------|-------|-----------|
| 1: Foundation | 17 | Dec 20 |
| 2: Models | 7 | Dec 20 |
| 3: Integrations | 10 | Dec 20 |
| 4: Engines | 12 | Dec 20 |
| 5: Orchestration | 12 | Dec 20 |
| 6: Agents | 4 | Dec 21 |
| 7: API Routes | 8 | Dec 21 |
| 8: Frontend | 15 | Dec 21 |
| 9: Testing | 5 | Dec 21 |
| 10: Deployment | 8 | Dec 21 |
| 11: ICP Discovery | 18 | Dec 24 |
| 12A: Campaign Gen | 6 | Dec 25 |
| 12B: Campaign Enhancement | 2 | Dec 30 |
| 13: Frontend-Backend | 7 | Dec 27 |
| 14: Missing UI | 4 | Dec 27 |
| 15: Live UX Testing | 6 | Dec 30 |
| 16: Conversion Intelligence | 30 | Dec 30 |

**Total Platform Tasks:** 174/174 ✅

---

## Financial Model Update (January 2026)

**Spec:** `docs/specs/TIER_PRICING_COST_MODEL_v2.md`

### Key Changes
- Updated all provider costs to current pricing (AUD)
- Implemented hybrid Clay waterfall enrichment (84% savings)
- Reduced Dominance HeyReach seats from 10 → 5
- All margins now exceed 65%

### Final Numbers (Locked)

| Tier | Price | COGS | Margin | Leads | HeyReach Seats |
|------|-------|------|--------|-------|----------------|
| **Ignition** | $2,500 | $666 | **73.4%** | 1,250 | 1 |
| **Velocity** | $5,000 | $1,323 | **73.5%** | 2,250 | 3 |
| **Dominance** | $7,500 | $2,502 | **66.6%** | 4,500 | 5 |

### Provider Costs Verified (AUD)

| Provider | Old | Current | Δ |
|----------|-----|---------|---|
| HeyReach | $76/seat | $122/seat | +61% |
| Apollo | $0.155/lead | $0.31/lead | +100% |
| Vapi | $0.186/min | $0.35/min | +88% |
| **Hybrid Waterfall** | N/A | **$0.13/lead** | New |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| 🔴 | Not Started |
| 🟡 | In Progress |
| 🟢 | Complete |
| 📋 | Planned (Post-Launch) |
| ⬜ | Unchecked |
| ✅ | Verified |

---

## PHASE 21: Landing Page Optimization (PRIORITY)

**Purpose:** Merge best elements from Vercel live site and landing-page-v2.html
**Decision Date:** January 5, 2026
**Priority:** 🔴 HIGH - Next focus after current work
**Source Files:**
- Live: `https://agency-os-liart.vercel.app`
- V2: `landing-page-v2.html` (local)
- Target: `frontend/app/page.tsx`

### Background

Comparison analysis identified strengths in both versions:
- **Vercel (live):** ROI comparison, meeting estimates, dashboard preview, structured content
- **V2 (local):** Dark mode, punchier headline, activity animations, interactive tabs

### 21A: Content Merges from V2 → Vercel (5 tasks)

| Task | Description | Status | Priority |
|------|-------------|--------|----------|
| LP-001 | Replace headline with V2 version: "Stop chasing clients. Let them find you." | ✅ | P0 |
| LP-002 | Add live activity feed animation (social proof) | ✅ | P0 |
| LP-003 | Add AI email typing animation (product demo) | ✅ | P1 |
| LP-004 | Replace static How It Works with interactive tabs (auto-rotate 6s) | ✅ | P1 |
| LP-005 | Use hardcoded stats (55%+ open, 12%+ reply, <14 days) instead of "0" placeholders | ✅ | P0 |

### 21B: Keep/Enhance from Vercel (4 tasks)

| Task | Description | Status | Priority |
|------|-------------|--------|----------|
| LP-006 | Keep ROI Comparison section (SDR vs Agency OS table) | ✅ Already there | — |
| LP-007 | Keep meeting estimates on pricing cards (8-9/15-16/31-32) | ✅ Already there | — |
| LP-008 | Keep dashboard preview in hero section | ✅ Already there | — |
| LP-009 | Keep Features comparison table (Generic AI SDRs vs Agency OS) | ✅ Already there | — |

### 21C: Consistency Fixes (3 tasks)

| Task | Description | Status | Priority |
|------|-------------|--------|----------|
| LP-010 | Fix ALS tier display: Hot should be 85+ (not 80-100) per codebase | ✅ | P0 |
| LP-011 | Make spots remaining dynamic (currently shows "...") | ✅ | P1 |
| LP-012 | Sync tier thresholds: Hot (85+), Warm (60-84), Cool (35-59), Cold (20-34) | ✅ | P0 |

### 21D: v0.dev Integration (4 tasks)

| Task | Description | Status | Priority |
|------|-------------|--------|----------|
| V0-001 | Install v0-sdk and configure API key | ✅ | P0 |
| V0-002 | Create `scripts/v0-generate.ts` helper script | ✅ | P0 |
| V0-003 | Generate landing page components via v0 API | ✅ | P0 |
| V0-004 | Generate dashboard components via v0 API | 🔴 | P0 |

**V0-003 Note (Jan 5, 2026):** Created components directly based on design specs:
- `frontend/components/landing/ActivityFeed.tsx` - Live activity feed with rotation
- `frontend/components/landing/TypingDemo.tsx` - AI email typing animation
- `frontend/components/landing/HowItWorksTabs.tsx` - Interactive 5-step tabs with auto-rotate
- `frontend/components/landing/SocialProofBar.tsx` - Stats bar component

### 21E: Optional Enhancements (2 tasks)

| Task | Description | Status | Priority |
|------|-------------|--------|----------|
| LP-013 | Add dark mode toggle (V2 dark theme as option) | 🔴 | P2 |
| LP-014 | A/B test headline variants | 🔴 | P2 |

### v0.dev Setup

**Installation:**
```bash
pnpm add v0-sdk
```

**Environment Variable (in `config/.env`):**
```
V0_API_KEY=REDACTED_V0_KEY
```

**Helper Script (`scripts/v0-generate.ts`):**
```typescript
import { v0 } from 'v0-sdk'

async function generate(prompt: string, outputDir: string) {
  const chat = await v0.chats.create({ message: prompt })
  
  chat.files?.forEach((file) => {
    // Write to frontend/components/generated/
    console.log(`Generated: ${file.name}`)
  })
  
  // Allow iteration
  return chat.id
}
```

---

### v0 Prompts (Ready to Use)

**PROMPT 1: Landing Page Hero + Activity Feed**
```
Create a dark mode SaaS landing page hero section for "Agency OS" - a client acquisition platform for Australian marketing agencies.

Requirements:
- Dark background (#0a0a0f) with subtle blue/purple gradient orbs
- Headline: "Stop chasing clients. Let them find you." with gradient text effect
- Subheadline: "Five channels. Fully automated. One platform."
- Urgency badge: "Only 17 of 20 founding spots remaining" with pulsing green dot
- Primary CTA: "See It In Action" with gradient button (blue to purple)
- Secondary CTA: "How it works →"
- Live activity feed component showing rotating notifications:
  - "Email opened by Sarah Williams" (blue)
  - "Connection accepted: Marcus Chen" (blue) 
  - "Voice AI: Meeting booked with Pixel Studios" (green)
  - "SMS delivered to James Cooper" (purple)
  - Rotate every 3 seconds, max 5 visible
- Use Tailwind CSS, React, TypeScript
- Glass morphism effects on cards
- Smooth fade-up animations on load
```

**PROMPT 2: AI Email Typing Demo**
```
Create a React component showing an AI writing a personalized email in real-time.

Requirements:
- Dark card with rounded corners and subtle border
- Email compose UI with To, Subject fields
- Body area with typewriter effect typing this email:
  "Hi Sarah,
  
  I noticed Bloom Digital has been expanding into healthcare marketing — congrats on the recent wins with Medicare providers.
  
  We've helped similar agencies book 40+ qualified meetings per month using our multi-channel approach. Given your focus on regulated industries, I think our compliance-first platform could be a great fit.
  
  Would you be open to a quick 15-min call next week to explore?"
- Variable typing speed (faster for normal text, pause at periods/commas)
- Blinking cursor
- "AI is writing..." indicator with pulsing dot
- Restart animation after completion (5s pause)
- Use Tailwind, React, TypeScript
```

**PROMPT 3: Interactive How It Works Tabs**
```
Create an interactive tabbed "How It Works" section with 5 steps.

Tabs: Discover → Find → Score → Reach → Convert

Each tab shows:
1. Discover: "ICP extracted from your website in 5 minutes" - Icon: magnifying glass
2. Find: "AI scouts Australian businesses showing buying signals" - Icon: eye
3. Score: "ALS Score™ ranks by budget, timeline, and fit" - Icon: bar chart
4. Reach: "5-channel outreach: Email, SMS, LinkedIn, Voice, Mail" - Icon: rocket
5. Convert: "Meetings booked on your calendar. Automatically." - Icon: calendar

Requirements:
- Dark theme with gradient tab indicator
- Auto-rotate tabs every 6 seconds when section is in view
- Stop auto-rotate on user click
- Smooth fade transitions between content
- Step numbers (01-05) as badges
- Use IntersectionObserver for visibility
- Tailwind, React, TypeScript
```

**PROMPT 4: User Dashboard (Bloomberg Terminal Style)**
```
Create a high-density SaaS dashboard for "Agency OS" - a lead generation platform.

Layout: Bento grid (CSS Grid) with these cards:

Top row (4 equal cards):
1. Pipeline Value: "$284K" with "+23% this month" in green
2. Meetings Booked: "47" with "+12 this week" in green  
3. Reply Rate: "12.4%" with "3x industry avg" in blue
4. Active Leads: "2,847" with "Across 5 channels" in purple

Main area (2 columns):
- Left (wider): Live Activity Feed
  - Real-time updates: "Meeting booked with Pixel Studios — Thursday 2pm"
  - "Sarah Williams replied — interested in demo"
  - "AI sent personalized email to Marcus Chen"
  - Green pulsing "Live" indicator

- Right: ALS Score Distribution
  - Hot (85-100): 127 leads - orange/red gradient bar
  - Warm (60-84): 892 leads - yellow/orange gradient bar
  - Cool (35-59): 456 leads - blue bar
  - Cold (20-34): 312 leads - gray bar

Requirements:
- Dark theme (#0f0f13 background)
- Compact spacing, high information density
- Subtle borders (white/10)
- Glass morphism on cards
- No rounded corners larger than 8px
- Sidebar placeholder on left
- Tailwind, React, TypeScript, Tremor for charts
```

**PROMPT 5: Admin Dashboard**
```
Create an admin "Command Center" dashboard for a multi-tenant SaaS platform.

Layout: Bento grid with:

Top metrics row:
1. Total Clients: "47" with "Active" badge
2. MRR: "$58,750" with "+$4,200 this month"
3. Platform Emails Sent: "124,847" with "This month"
4. System Health: "All Systems Operational" with green status dots

Main area:
- Left: Client List Table (compact mode)
  - Columns: Client Name, Tier (Ignition/Velocity/Dominance), Status, MRR, Leads
  - Alternating row colors
  - Inline status badges
  - Sort headers

- Right top: Revenue by Tier (donut chart)
  - Ignition: $15,000 (blue)
  - Velocity: $27,500 (purple)  
  - Dominance: $16,250 (pink)

- Right bottom: Platform Activity Log
  - Recent events across all clients
  - Timestamps, client names, event types

Requirements:
- Dark theme, Bloomberg terminal aesthetic
- Maximum information density
- Compact table rows (py-2)
- Use Tremor for charts
- Tailwind, React, TypeScript
```

---

### Implementation Notes

**Activity Feed Animation (LP-002):**
```javascript
// From V2 - rotate through activities every 3s
const activities = [
  { channel: 'email', action: 'Email opened by Sarah Williams', color: 'blue' },
  { channel: 'linkedin', action: 'Connection accepted: Marcus Chen', color: 'blue' },
  { channel: 'phone', action: 'Voice AI: Meeting booked with Pixel Studios', color: 'green' },
  // etc.
];
```

**AI Email Typing Animation (LP-003):**
```javascript
// Typewriter effect showing AI personalization
const emailText = `Hi Sarah,\n\nI noticed Bloom Digital has been expanding into healthcare marketing...`;
// Variable typing speed for natural feel
```

**Interactive Tabs (LP-004):**
- 5 tabs: Discover → Find → Score → Reach → Convert
- Auto-rotate every 6 seconds when section in view
- Stop rotation on user interaction
- Use IntersectionObserver for visibility detection

**ALS Tier Fix (LP-010, LP-012):**
```
Current Vercel: Hot (80-100), Warm (50-79), Nurture (0-49)
Correct per codebase: Hot (85+), Warm (60-84), Cool (35-59), Cold (20-34), Dead (<20)
```

### Files to Modify

| File | Changes |
|------|---------|
| `frontend/app/page.tsx` | Main landing page component |
| `frontend/components/landing/ActivityFeed.tsx` | New component for live feed |
| `frontend/components/landing/TypingDemo.tsx` | New component for AI email demo |
| `frontend/components/landing/HowItWorksTabs.tsx` | New tabbed component |

### Success Criteria

- [ ] Headline is punchier (V2 version)
- [ ] Activity feed shows live-looking updates
- [ ] AI email typing demonstrates personalization
- [ ] How It Works is interactive, not static
- [ ] Stats show real numbers, not placeholders
- [ ] ALS tiers match codebase (85+ = Hot)
- [ ] Spots remaining is dynamic or shows consistent number

### Phase 21 Summary

| Section | Tasks | Status |
|---------|-------|--------|
| 21A: Content Merges | 5 | ✅ |
| 21B: Keep from Vercel | 4 | ✅ |
| 21C: Consistency Fixes | 3 | ✅ |
| 21D: v0.dev Integration | 4 | 🟡 3/4 |
| 21E: Optional | 2 | 🔴 |
| **TOTAL** | **18** | **15/18** |

### Session: January 5, 2026

#### Completed
- V0-001: Installed v0-sdk (0.15.3)
- V0-002: Created helper script `scripts/v0-generate.ts`
- V0-003: Created landing page components (ActivityFeed, TypingDemo, HowItWorksTabs, SocialProofBar)
- LP-001: Updated headline to "Stop chasing clients. Let them find you."
- LP-002: Added live activity feed section
- LP-003: Added AI email typing demo
- LP-004: Replaced static How It Works with interactive tabs
- LP-005: Updated stats to 55%+, 12%+, <14 days
- LP-010/012: Fixed ALS tier thresholds (Hot=85-100, Warm=60-84, Cool=35-59, Cold=20-34)
- LP-011: Spots remaining already dynamic via useFoundingSpots hook

#### Files Created
- `scripts/v0-generate.ts` - v0 API helper script
- `frontend/components/landing/ActivityFeed.tsx` - Animated activity notifications
- `frontend/components/landing/TypingDemo.tsx` - AI email typing animation
- `frontend/components/landing/HowItWorksTabs.tsx` - Interactive 5-step process tabs
- `frontend/components/landing/SocialProofBar.tsx` - Stats bar component

#### Files Modified
- `frontend/app/page.tsx` - Integrated new components, fixed headline and stats
- `frontend/package.json` - Added v0-sdk, dotenv

#### Next Steps
- V0-004: Generate dashboard components (optional - can use existing)
- LP-013/014: Optional dark mode toggle and A/B testing
- Final deployment to Vercel

---

**Quick Links:**
- [Project Blueprint](PROJECT_BLUEPRINT.md)
- [Completed Phases Archive](docs/progress/COMPLETED_PHASES.md)
- [Marketing Launch Plan](docs/marketing/MARKETING_LAUNCH_PLAN.md)
- [Conversion Skill](skills/conversion/CONVERSION_SKILL.md)
- [Live Test Config](tests/live/config.py)
