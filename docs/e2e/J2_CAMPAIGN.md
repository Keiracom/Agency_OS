# J2: Campaign & Leads Journey

**Status:** 🟡 Sub-tasks Defined (Pending CEO Approval)
**Priority:** P1 — After onboarding, campaigns drive everything
**Depends On:** J1 Complete
**Last Updated:** January 11, 2026
**Sub-Tasks:** 12 groups, 54 individual checks

---

## Overview

Tests campaign creation, lead sourcing from Apollo, ALS scoring, pool assignment, and content generation.

**User Journey:**
```
/dashboard/campaigns → New Campaign → Configure → Activate → Leads Assigned → Scored → Content Generated
```

**Key Finding from Code Review:**
⚠️ **Campaign detail page uses HARDCODED MOCK DATA** (`frontend/app/dashboard/campaigns/[id]/page.tsx` lines 14-42). This MUST be fixed before E2E testing.

---

## Sub-Tasks

### J2.1 — Campaign List Page
**Purpose:** Verify campaign list displays real data from API.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.1.1 | Read `frontend/app/dashboard/campaigns/page.tsx` — verify `useCampaigns` hook | Load `/dashboard/campaigns`, check network tab |
| J2.1.2 | Verify API endpoint `GET /api/v1/campaigns` exists in `campaigns.py` | Confirm campaigns list renders |
| J2.1.3 | Check status filter implementation (active/paused/draft/completed) | Click each filter, verify response |
| J2.1.4 | Check search functionality wiring | Search for campaign name |
| J2.1.5 | Verify channel allocation bar displays correctly | Check bar colors match allocations |

**Pass Criteria:**
- [ ] Campaign list loads from API (not mock data)
- [ ] Status filters work correctly
- [ ] Search filters work correctly
- [ ] Channel allocation bar displays accurately

<!-- E2E_SESSION_BREAK: J2.1 complete. Next: J2.2 Create Campaign Form -->

---

### J2.2 — Create Campaign Form
**Purpose:** Verify campaign creation flow with simplified fields.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.2.1 | Read `frontend/app/dashboard/campaigns/new/page.tsx` — verify `useCreateCampaign` hook | Navigate to `/dashboard/campaigns/new` |
| J2.2.2 | Verify ICP is fetched via `GET /api/v1/clients/{id}/icp` | Check ICP industries/titles display |
| J2.2.3 | Verify form fields: name (required), description (optional), permission_mode | Fill form, check validation |
| J2.2.4 | Check channel allocation is NOT in form (system determines) | Verify no channel inputs |
| J2.2.5 | Verify POST `/api/v1/campaigns` in `campaigns.py` creates campaign | Submit form, verify 201 response |
| J2.2.6 | Verify campaign created with status='draft' | Check DB for new campaign |

**Campaign Creation Fields (ICP-008 Simplified):**
```
Required: name
Optional: description, permission_mode (default: co_pilot)
System Determined: channel allocation, targeting (from ICP)
```

**Pass Criteria:**
- [ ] Form only has name, description, permission_mode
- [ ] ICP is displayed but not editable (link to settings)
- [ ] Campaign created successfully
- [ ] Redirects to campaign list after creation

<!-- E2E_SESSION_BREAK: J2.2 complete. Next: J2.3 Campaign Detail Page -->

---

### J2.3 — Campaign Detail Page
**Purpose:** Verify campaign detail displays real data.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.3.1 | Read `frontend/app/dashboard/campaigns/[id]/page.tsx` — **VERIFY DATA SOURCE** | Navigate to `/dashboard/campaigns/{id}` |
| J2.3.2 | ⚠️ **CRITICAL:** Check if using mock data (lines 14-42) or real API | Check network tab for API call |
| J2.3.3 | Verify GET `/api/v1/campaigns/{id}` returns campaign with metrics | Test endpoint directly |
| J2.3.4 | Verify activate/pause buttons call correct endpoints | Click activate/pause |
| J2.3.5 | Verify lead list shows real leads | Check leads section |

**⚠️ KNOWN ISSUE:**
```typescript
// lines 14-42 in [id]/page.tsx
const campaign = {
  id: "1",
  name: "Tech Startups Q1 2025",
  status: "active",
  // ... HARDCODED MOCK DATA
};
```

**Pass Criteria:**
- [ ] **Page fetches real campaign data** (FIX REQUIRED)
- [ ] Stats (total leads, contacted, replied) accurate
- [ ] Activate/Pause buttons work
- [ ] Lead list loads from API

<!-- E2E_SESSION_BREAK: J2.3 complete. Next: J2.4 Campaign Activation Flow -->

---

### J2.4 — Campaign Activation Flow
**Purpose:** Verify campaign activation triggers Prefect flow.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.4.1 | Read `src/api/routes/campaigns.py` — find activate endpoint | Locate POST `/campaigns/{id}/activate` |
| J2.4.2 | Verify activation triggers `campaign_flow` in Prefect | Check Prefect deployment exists |
| J2.4.3 | Read `src/orchestration/flows/campaign_flow.py` — verify JIT validation | Check validation steps |
| J2.4.4 | Verify campaign status updates to 'active' | Check DB after activation |
| J2.4.5 | Verify webhook triggers flow OR API triggers flow | Test both trigger methods |

**Campaign Flow Steps (from `campaign_flow.py`):**
1. Load campaign and client
2. JIT validation (ICP, sequences, sender profiles)
3. Check lead availability
4. Trigger pool assignment if needed
5. Update campaign status

**Pass Criteria:**
- [ ] Activation triggers Prefect flow
- [ ] JIT validation runs (fails if missing requirements)
- [ ] Campaign status changes to 'active'
- [ ] Activity logged

<!-- E2E_SESSION_BREAK: J2.4 complete. Next: J2.5 Lead Pool Population -->

---

### J2.5 — Lead Pool Population
**Purpose:** Verify Apollo search populates the platform-wide lead pool.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.5.1 | Read `src/orchestration/flows/pool_population_flow.py` | Identify flow tasks |
| J2.5.2 | Read `src/integrations/apollo.py` — verify `search_people_for_pool` | Check Apollo API calls |
| J2.5.3 | Verify 3-tier waterfall: Apollo → Clay → Direct Scraping | Check tier fallback logic |
| J2.5.4 | Read `src/services/lead_pool_service.py` — verify `create_or_update` | Check dedup by email |
| J2.5.5 | Verify `lead_pool` table receives enriched data | Query table after flow |
| J2.5.6 | Verify email_status captured from Apollo (CRITICAL for bounce prevention) | Check email_status field |

**Pool Population Waterfall:**
```
Tier 1: Apollo People Search
Tier 2: Clay Enrichment (if Apollo fails)
Tier 3: Direct Scraping (if both fail)
```

**Pass Criteria:**
- [ ] Pool population flow runs via Prefect
- [ ] Apollo integration returns enriched leads
- [ ] Leads stored in `lead_pool` with 50+ fields
- [ ] Email deduplication works (same email = update)
- [ ] email_status field captured

<!-- E2E_SESSION_BREAK: J2.5 complete. Next: J2.6 Lead Pool Assignment -->

---

### J2.6 — Lead Pool Assignment
**Purpose:** Verify leads are assigned from pool to clients exclusively.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.6.1 | Read `src/orchestration/flows/pool_assignment_flow.py` | Identify assignment logic |
| J2.6.2 | Read `src/services/lead_allocator_service.py` — verify `allocate_leads` | Check ICP matching |
| J2.6.3 | Verify `lead_assignments` table stores client-lead relationships | Query table |
| J2.6.4 | Verify exclusivity: one lead = one client (pool_status changes) | Check pool_status update |
| J2.6.5 | Verify campaign_id linked to assignment | Check assignment record |
| J2.6.6 | Verify assignment creates entry in `leads` table for client | Check leads table |

**Exclusivity Model:**
```sql
-- lead_pool.pool_status changes from 'available' to 'assigned'
-- lead_assignments links pool lead to client
-- Client's leads table gets copy of lead data
```

**Pass Criteria:**
- [ ] Assignment flow runs via Prefect
- [ ] ICP criteria used for matching
- [ ] Lead marked as assigned (not available to others)
- [ ] lead_assignments record created
- [ ] Client's leads table populated

<!-- E2E_SESSION_BREAK: J2.6 complete. Next: J2.7 ALS Scoring Engine -->

---

### J2.7 — ALS Scoring Engine
**Purpose:** Verify ALS scoring formula and tier assignment.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.7.1 | Read `src/engines/scorer.py` — verify 5-component formula | Check scoring constants |
| J2.7.2 | Verify tier thresholds: Hot=85+, Warm=60-84, Cool=35-59, Cold=20-34, Dead<20 | Check TIER_* constants |
| J2.7.3 | Verify `score_lead` method calculates all components | Run scoring on test lead |
| J2.7.4 | Verify `score_pool_lead` works for pool-first scoring | Score pool lead |
| J2.7.5 | Verify learned weights from conversion patterns (Phase 16) | Check `_get_learned_weights` |
| J2.7.6 | Verify buyer signal boost (Phase 24F) | Check `_get_buyer_boost` |
| J2.7.7 | Verify LinkedIn engagement boost (Phase 24A+) | Check `_get_linkedin_boost` |

**ALS Formula (VERIFIED from scorer.py):**
| Component | Max Points | Formula |
|-----------|------------|---------|
| Data Quality | 20 | Email verified (8) + Phone (6) + LinkedIn (4) + Personal email (2) |
| Authority | 25 | Based on title seniority (owner/CEO = 25, VP = 18, etc.) |
| Company Fit | 25 | Industry match (10) + Employee count (8) + Country (7) |
| Timing | 15 | New role (6) + Hiring (5) + Recent funding (4) |
| Risk | 15 | Base 15 minus deductions (bounced -10, unsubscribed -15, etc.) |

**Tier Thresholds (VERIFIED):**
- Hot: **85-100** (NOT 80!)
- Warm: 60-84
- Cool: 35-59
- Cold: 20-34
- Dead: 0-19

**Pass Criteria:**
- [ ] All 5 components calculated correctly
- [ ] Hot threshold is 85 (not 80)
- [ ] Tier determines available channels
- [ ] Buyer/LinkedIn boosts applied when applicable
- [ ] Scores stored in lead record

<!-- E2E_SESSION_BREAK: J2.7 complete. Next: J2.8 Deep Research (Hot Leads) -->

---

### J2.8 — Deep Research (Hot Leads)
**Purpose:** Verify deep research triggers for hot leads.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.8.1 | Verify deep research trigger at ALS >= 85 | Check trigger condition |
| J2.8.2 | Read `/api/v1/leads/{id}/research` endpoint | Test endpoint |
| J2.8.3 | Verify LinkedIn scraping for person/company | Check Apify integration |
| J2.8.4 | Verify icebreaker generation | Check AI call for icebreakers |
| J2.8.5 | Verify research data stored in lead_assignments | Check research_data field |

**Pass Criteria:**
- [ ] Deep research triggers automatically at 85+ score
- [ ] LinkedIn profile scraped
- [ ] Icebreakers generated
- [ ] Research data stored for content personalization

<!-- E2E_SESSION_BREAK: J2.8 complete. Next: J2.9 Content Generation -->

---

### J2.9 — Content Generation
**Purpose:** Verify AI generates personalized content for sequences.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.9.1 | Read `src/engines/content.py` — verify `generate_email` | Check AI prompt structure |
| J2.9.2 | Verify spend limiter integration (Rule 15) | Check `anthropic.complete` call |
| J2.9.3 | Verify `generate_email_for_pool` for pool-first content | Test pool method |
| J2.9.4 | Verify SMS, LinkedIn, Voice generation methods exist | Check other generators |
| J2.9.5 | Verify personalization uses lead data (name, company, title) | Check lead_data in prompt |
| J2.9.6 | Verify JSON response parsing (subject + body) | Check response handling |

**Content Types:**
- Email: subject (50 chars) + body (150 words)
- SMS: 160 chars max
- LinkedIn: Connection note or message
- Voice: Call script

**Pass Criteria:**
- [ ] Content engine generates personalized content
- [ ] AI spend tracked via limiter
- [ ] All 4 channels supported
- [ ] Response properly parsed

<!-- E2E_SESSION_BREAK: J2.9 complete. Next: J2.10 Campaign Sequences -->

---

### J2.10 — Campaign Sequences
**Purpose:** Verify sequence step creation and management.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.10.1 | Read POST `/campaigns/{id}/sequences` endpoint | Check sequence creation |
| J2.10.2 | Verify sequence_steps table schema | Check step_number, channel, delay_days |
| J2.10.3 | Verify step templates linked to sequences | Check template_id relationship |
| J2.10.4 | Verify sequence ordering (step_number) | Create multi-step sequence |
| J2.10.5 | Verify channel-specific sequence validation | Check channel requirements |

**Pass Criteria:**
- [ ] Sequences can be created for campaigns
- [ ] Multiple steps with delays supported
- [ ] Templates can be attached to steps
- [ ] Channel validation applied

<!-- E2E_SESSION_BREAK: J2.10 complete. Next: J2.11 Campaign Metrics -->

---

### J2.11 — Campaign Metrics
**Purpose:** Verify campaign metrics are calculated correctly.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.11.1 | Verify `total_leads` count in campaign response | Check API response |
| J2.11.2 | Verify `leads_contacted` count | Check activity-based count |
| J2.11.3 | Verify `leads_replied` count | Check reply detection |
| J2.11.4 | Verify `reply_rate` calculation (replied/contacted) | Verify percentage |
| J2.11.5 | Verify metrics update in real-time | Make activity, check update |

**Pass Criteria:**
- [ ] All metrics calculated from activities table
- [ ] Metrics reflect real data
- [ ] Reply rate percentage accurate

<!-- E2E_SESSION_BREAK: J2.11 complete. Next: J2.12 Campaign Edge Cases -->

---

### J2.12 — Campaign Edge Cases
**Purpose:** Test error handling and edge conditions.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2.12.1 | Create campaign without ICP configured | Should warn but allow |
| J2.12.2 | Activate campaign with no leads | Should fail validation |
| J2.12.3 | Activate campaign with no sequences | Should fail or warn |
| J2.12.4 | Duplicate campaign name | Check uniqueness constraint |
| J2.12.5 | Campaign with 0% allocation (all channels) | Check validation |
| J2.12.6 | Pause mid-sequence | Verify sequence state preservation |

**Pass Criteria:**
- [ ] Appropriate validation errors returned
- [ ] No silent failures
- [ ] State preserved on pause

<!-- E2E_SESSION_BREAK: J2 JOURNEY COMPLETE. Next: J2B Enrichment -->

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Campaign API | `src/api/routes/campaigns.py` | 1240 | ✅ VERIFIED |
| Leads API | `src/api/routes/leads.py` | 1082 | ✅ VERIFIED |
| Campaign Flow | `src/orchestration/flows/campaign_flow.py` | 378 | ✅ VERIFIED |
| Pool Population Flow | `src/orchestration/flows/pool_population_flow.py` | 774 | ✅ VERIFIED |
| Pool Assignment Flow | `src/orchestration/flows/pool_assignment_flow.py` | 678 | ✅ VERIFIED |
| Scorer Engine | `src/engines/scorer.py` | 1428 | ✅ VERIFIED |
| Content Engine | `src/engines/content.py` | 200+ | ✅ VERIFIED |
| Apollo Integration | `src/integrations/apollo.py` | 761 | ✅ VERIFIED |
| Lead Pool Service | `src/services/lead_pool_service.py` | 100+ | ✅ VERIFIED |
| Lead Allocator Service | `src/services/lead_allocator_service.py` | 100+ | ✅ VERIFIED |
| Campaign List (FE) | `frontend/app/dashboard/campaigns/page.tsx` | 257 | ✅ Real Data |
| New Campaign (FE) | `frontend/app/dashboard/campaigns/new/page.tsx` | 314 | ✅ Real API |
| Campaign Detail (FE) | `frontend/app/dashboard/campaigns/[id]/page.tsx` | 220 | ⚠️ **MOCK DATA** |

---

## Completion Criteria

All checks must pass:

- [ ] **J2.1** Campaign list loads from API with filters
- [ ] **J2.2** Campaign creation works (simplified form)
- [ ] **J2.3** Campaign detail shows real data **(REQUIRES FIX)**
- [ ] **J2.4** Activation triggers Prefect flow
- [ ] **J2.5** Pool population via Apollo works
- [ ] **J2.6** Lead assignment with exclusivity works
- [ ] **J2.7** ALS scoring accurate (Hot = 85+)
- [ ] **J2.8** Deep research triggers for hot leads
- [ ] **J2.9** Content generation works with AI
- [ ] **J2.10** Sequences can be created
- [ ] **J2.11** Metrics accurate
- [ ] **J2.12** Edge cases handled gracefully

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ Campaign API is comprehensive (1240 lines)
2. ✅ Scorer engine has correct Hot threshold (85, not 80)
3. ✅ Pool architecture fully implemented
4. ✅ Apollo integration captures 50+ fields
5. ⚠️ **Campaign detail page uses mock data — MUST FIX**
6. ✅ Prefect flows properly defined for all campaign operations

**Pre-requisite Fix Before Testing:**
The campaign detail page (`frontend/app/dashboard/campaigns/[id]/page.tsx`) must be updated to fetch real campaign data via API instead of using hardcoded mock data.

---

## Notes

**Why Lead Pool First:**
Phase 24A introduced pool-first architecture. Leads are enriched and stored in platform-wide pool BEFORE assignment. This enables:
- Lead deduplication across clients
- Exclusive assignment (no double-selling)
- Better enrichment (done once, used many times)
- CIS pattern learning at platform level
