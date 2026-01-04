# PROGRESS.md — Agency OS Build Tracker

**Last Updated:** January 4, 2026
**Current Phase:** PHASE 17 - Launch Prerequisites
**Status:** Platform built (174/174), preparing for launch

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

**Platform Tasks:** 174/174 (100% complete)
**Launch Tasks:** 13/68 (19% complete)

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
| CRED-005 | Twilio account + phone number | 🔴 | P1 |
| CRED-006 | HeyReach API key + LinkedIn seats | 🔴 | P1 |
| CRED-007 | Vapi API key + phone number link | 🔴 | P1 |
| CRED-007a | ElevenLabs API key | 🔴 | P1 |
| CRED-008 | Lob API key | 🔴 | P2 |
| CRED-009 | DataForSEO credentials | 🟡 | P1 |

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
| Apollo | ⚠️ | Free plan - people/match needs upgrade |
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
| 4 | Resend API works | Can send | ⚠️ | Key restricted to send-only (intentional) |
| 5 | Anthropic API works | Can generate | ✅ | Claude response generated |
| 6 | Apollo API works | Can enrich | ❌ | Free plan - needs upgrade |
| 7 | Apify API works | Can scrape | ✅ | User: brawny_epitope |

**Pre-Flight Result:** 🟡 5/7 Pass, 1 Partial, 1 Blocked

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
| Pre-Flight | 7 | 5 | 🟡 |
| M1: Signup & Onboarding | 10 | 0 | 🔴 |
| M2: Campaign & Leads | 10 | 0 | 🔴 |
| M3: Email Send | 5 | 0 | 🔴 |
| M4: Reply Handling | 5 | 0 | 🔴 |
| M5: Dashboard Validation | 5 | 0 | 🔴 |
| M6: Admin Dashboard | 5 | 0 | 🔴 |
| **TOTAL** | **47** | **5** | 🟡 |

---

### Blockers Log

| ID | Milestone | Description | Severity | Fix | Status |
|----|-----------|-------------|----------|-----|--------|
| BLK-001 | Pre-Flight | Apollo free plan lacks `/people/match` API | HIGH | Upgrade Apollo or use alternative | 🔴 Open |

*(Fill in as blockers discovered during testing)*

---

### Test Session Log

| Date | Tester | Milestones | Passed | Failed | Blocked | Notes |
|------|--------|------------|--------|--------|---------|-------|
| 2026-01-04 | Claude | Pre-Flight | 5 | 0 | 1 | Apollo needs upgrade |

*(Add entry for each test session)*

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
| Twilio | https://www.twilio.com/try-twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | ⬜ |
| HeyReach | https://heyreach.io | `HEYREACH_API_KEY` | ⬜ |
| Vapi | https://vapi.ai | `VAPI_API_KEY`, `VAPI_PHONE_NUMBER_ID` | ⬜ |
| ElevenLabs | https://elevenlabs.io | `ELEVENLABS_API_KEY` | ⬜ |

### P2 - Future Channels

| Service | Sign Up | Env Var | Verified |
|---------|---------|---------|----------|
| Lob | https://dashboard.lob.com | `LOB_API_KEY` | ⬜ |

### Marketing Automation

| Service | Sign Up | Purpose | Verified |
|---------|---------|---------|----------|
| HeyGen | https://heygen.com | AI video generation | ⬜ |
| Serper | https://serper.dev | Google search API | ⬜ |
| Buffer | https://buffer.com | Social scheduling | ⬜ |

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
| ⬜ | Unchecked |
| ✅ | Verified |

---

**Quick Links:**
- [Project Blueprint](PROJECT_BLUEPRINT.md)
- [Completed Phases Archive](docs/progress/COMPLETED_PHASES.md)
- [Marketing Launch Plan](docs/marketing/MARKETING_LAUNCH_PLAN.md)
- [Conversion Skill](skills/conversion/CONVERSION_SKILL.md)
- [Live Test Config](tests/live/config.py)
