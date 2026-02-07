# MASTER EXECUTION PLAN — Agency OS Launch

**Generated:** 2026-02-06 02:05 UTC
**Source:** 5 research audits + tonight's fixes
**Target:** Launch-ready product

---

## EXECUTIVE SUMMARY

**Current State:** 85% complete. Core platform built. Siege Waterfall wired. Margins healthy (72-77%).

**Blockers to Launch:**
1. 40 E2E tests remaining (Phase 21)
2. Email infrastructure buffer (0 warmed domains)
3. Unipile 401 error (LinkedIn broken)
4. **Dashboard not wired to backend** (0 API calls in frontend)

**Timeline:** 2-3 weeks to launch-ready

---

## COMPLETED TONIGHT (2026-02-06)

| Task | Status |
|------|--------|
| hunter.py integration | ✅ Created |
| proxycurl.py integration | ✅ Created |
| Siege Waterfall wired to scout.py | ✅ Done |
| Siege Waterfall wired to icp_scraper.py | ✅ Done |
| SDK docs deprecated (FCO-002) | ✅ 6 files |
| Velocity price → $4,000 | ✅ 21 files |
| SMS extended to Warm tier | ✅ Code + config |
| 7 integration specs created | ✅ Done |
| Railway token fixed | ✅ Working |
| Margin recalculation | ✅ All tiers 70%+ |

---

## PHASE 1: LAUNCH BLOCKERS (Week 1)

### 1.1 E2E Tests (Phase 21) — CRITICAL PATH

**Current:** 7/47 tests passing
**Remaining:** 40 tests
**Estimate:** 20 hours

| Journey | Tests | Status |
|---------|-------|--------|
| J0: Signup | 3 | 🟡 Partial |
| J1: Onboarding | 5 | 🟡 Partial |
| J2: Lead Enrichment | 8 | 🔴 Not started |
| J3: Campaign Creation | 6 | 🔴 Not started |
| J4: Outreach Execution | 10 | 🔴 Not started |
| J5: Reply Handling | 8 | 🔴 Not started |
| J6: Reporting | 7 | 🔴 Not started |

**Action:** Spawn E2E-TESTER agents to work through journeys systematically.

### 1.2 Email Infrastructure — CRITICAL

**Current State:**
- Warmed domains: 0
- Warmed mailboxes: ~3
- Required for launch: 10+ domains, 30+ mailboxes

**Actions:**
1. Purchase 10 domains via InfraForge (~$100)
2. Create 3 mailboxes per domain (30 total)
3. Start WarmForge warmup (14-21 days)

**Timeline:** Start ASAP — warmup takes 2-3 weeks

### 1.3 Unipile 401 Error — HIGH

**Impact:** LinkedIn outreach completely broken
**Action:** Debug auth, refresh credentials, or escalate to Unipile support
**Estimate:** 1-2 hours

### 1.4 Dashboard Wiring — CRITICAL

**Current State:** Frontend has 0 API calls. Using mock/static data.

**Impact:** Customer can't see real data — meetings, leads, campaigns.

**Pages to Wire:**

| Page | API Endpoint | Priority |
|------|-------------|----------|
| Dashboard Home | `/api/v1/clients/{id}/stats` | P0 |
| Campaigns List | `/api/v1/campaigns` | P0 |
| Campaign Detail | `/api/v1/campaigns/{id}` | P0 |
| Leads List | `/api/v1/leads` | P0 |
| Lead Detail | `/api/v1/leads/{id}` | P1 |
| Reports | `/api/v1/reports/metrics` | P1 |
| Settings | `/api/v1/clients/{id}` | P2 |
| Inbox/Replies | `/api/v1/replies` | P1 |

**Actions:**
1. Create API hooks in `frontend/src/hooks/`
2. Replace mock data with real API calls
3. Add loading states and error handling
4. Test each page with real data

**Estimate:** 8-12 hours

---

## PHASE 2: QUALITY GATES (Week 2)

### 2.1 Migration 055 ✅ COMPLETE

**File:** `055_waterfall_enrichment_architecture.sql`
**Action:** Apply to production Supabase
**Status:** ✅ Done (2026-02-06)

### 2.2 Dead Code Cleanup ✅ COMPLETE

| File | Action | Status |
|------|--------|--------|
| apollo.py | Add deprecation warning (keep as fallback) | ✅ |
| apify.py | Add deprecation warning (keep as fallback) | ✅ |
| heyreach.py | Remove from reply_tasks | ✅ |
| resend.py | Delete (zero imports) | ✅ |
| sentry_utils.py | Delete (Sentry in main.py) | ✅ |

**Status:** ✅ Done (2026-02-06)

### 2.3 Remaining TODOs

| Location | TODO | Priority |
|----------|------|----------|
| voice_agent_telnyx.py:565 | Deepgram STT | P2 (post-launch) |

### 2.4 AU Phone Numbers

**Required:** 10 Telnyx AU mobile numbers
**Action:** Dave to provision via Telnyx dashboard
**Cost:** ~$10/mo per number

---

## PHASE 3: DOCUMENTATION (Ongoing)

### 3.1 Completed Tonight
- ✅ SIEGE_WATERFALL.md
- ✅ KASPR.md
- ✅ ABN_CLIENT.md
- ✅ GMB_SCRAPER.md
- ✅ UNIPILE.md
- ✅ SALESFORGE.md
- ✅ WARMFORGE.md

### 3.2 Still Needed
- [ ] SERVICE_INDEX.md (35 services)
- [ ] ENGINE_INDEX.md updates (5 engines)
- [ ] HUNTER.md spec
- [ ] PROXYCURL.md spec

**Estimate:** 2 hours (can run parallel)

---

## PHASE 4: LAUNCH PREP (Week 3)

### 4.1 First Customer Checklist

| Item | Status |
|------|--------|
| Signup flow works | 🟡 Needs E2E |
| Onboarding completes | 🟡 Needs E2E |
| Lead enrichment runs | 🟡 Needs E2E |
| Campaign sends email | 🟡 Needs E2E |
| Replies detected | 🟡 Needs E2E |
| Dashboard shows data | 🟡 Needs E2E |
| Billing works | 🔴 Not tested |

### 4.2 Marketing Readiness

| Asset | Status |
|-------|--------|
| Landing page | ✅ Built |
| Pricing page | ✅ Built |
| Demo video | 🔴 Not created |
| Onboarding video | 🔴 Not created |

### 4.3 Founding 20 Campaign

**Target:** 20 founding customers at 50% off
**Channel:** LinkedIn DMs + Email
**Prerequisite:** All E2E tests passing

---

## EXECUTION TIMELINE

```
Week 1 (Feb 6-12):
├── Day 1-2: Dashboard wiring (P0 pages)
├── Day 3-4: E2E tests J0-J2 (16 tests)
├── Day 5-7: E2E tests J3-J4 (16 tests)
├── PARALLEL: Start domain warmup
├── PARALLEL: Fix Unipile 401
└── PARALLEL: Dashboard wiring (P1 pages)

Week 2 (Feb 13-19):
├── Day 1: Migration 055 + dead code cleanup
├── Day 2-3: Fix any E2E failures
├── Day 4-5: Documentation completion
└── Day 6-7: End-to-end manual testing

Week 3 (Feb 20-26):
├── Day 1-2: Billing integration testing
├── Day 3-4: Demo/onboarding videos
├── Day 5: Final QA pass
├── Day 6: Soft launch (internal)
└── Day 7: Founding 20 outreach begins
```

---

## RESOURCE ALLOCATION

### Elliot (Main Agent)
- Strategic decisions
- Code review
- Dave communication
- Blocker resolution

### Sub-Agents
- E2E-TESTER: Run test journeys
- DOC-WRITER: Create missing specs
- CODE-FIXER: Dead code cleanup
- INFRA-MONITOR: Check deployments

---

## DECISIONS NEEDED FROM DAVE

| Decision | Options | Impact |
|----------|---------|--------|
| Domain purchase budget | $100-200 | 10-20 domains |
| Telnyx AU numbers | 5 vs 10 | Voice capacity |
| Demo video approach | Loom vs HeyGen | Marketing asset |
| Launch date target | Feb 26 vs Mar 5 | Founding 20 timing |

---

## RISKS

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Warmup takes longer than 21 days | Medium | Start immediately |
| Unipile can't be fixed | Low | Fall back to manual LinkedIn |
| E2E tests reveal major bugs | Medium | Buffer time in Week 2 |
| First customer finds edge case | High | Have Dave as first "customer" |

---

## SUCCESS CRITERIA

**Launch Ready When:**
1. ✅ All 47 E2E tests pass
2. ✅ 10+ domains warmed (deliverability >95%)
3. ✅ LinkedIn outreach working
4. ✅ One full customer journey completed manually
5. ✅ Billing accepts payment

---

## DAILY STANDUP FORMAT

Each morning, Elliot reports:
1. **Yesterday:** What got done
2. **Today:** What's planned
3. **Blockers:** What needs Dave
4. **Metrics:** E2E pass rate, warmup progress

---

*Plan generated from: DOCS_AUDIT, CODE_AUDIT, GAP_AUDIT, INFRA_AUDIT, FINANCE_AUDIT*
*Last updated: 2026-02-06 02:05 UTC*
