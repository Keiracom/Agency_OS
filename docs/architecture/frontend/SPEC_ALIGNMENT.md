# Frontend Specification Alignment Report

**Purpose:** Documents where frontend specs are located and tracks alignment between architecture documentation and actual implementation.
**Last Audited:** 2026-01-23
**Status:** ALIGNMENT IMPROVING - Dashboard metrics pipeline complete

---

## Two-Tier Tracking System

This file is **Tier 2 (Implementation-Level)** tracking. It works alongside TODO.md:

| Tier | File | Tracks | Granularity |
|------|------|--------|-------------|
| **Tier 1** | `TODO.md` | WHAT to build (features, phases) | Feature/initiative |
| **Tier 2** | `SPEC_ALIGNMENT.md` (this file) | HOW to build (components, endpoints) | File/function |

**Rule:** No duplication. TODO.md has one line per feature. This file has the implementation breakdown.

### TODO.md Phase H Cross-Reference

| TODO.md Item | Feature | Implementation Details (This File) |
|--------------|---------|-----------------------------------|
| Item 40 | Claude fact-check gate | Backend only (not frontend) |
| Item 41 | Conservative SMART_EMAIL_PROMPT | Backend only (not frontend) |
| Item 42 | Safe fallback template | Backend only (not frontend) |
| **Item 43** | Emergency Pause Button | EmergencyPauseButton + POST /pause-all + usePauseOutreach ✅ |
| Item 44 | Daily Digest Email | Backend only (not frontend) |
| **Item 45** | Live Activity Feed | LiveActivityFeed + GET /activities + useActivityFeed ✅ |
| **Item 46** | Content Archive page | `/dashboard/archive` + GET /archive/content ✅ |
| **Item 47** | Best Of Showcase | BestOfShowcase + GET /best-of + useBestOfShowcase ✅ |

---

## Dependency Chain (Build Order)

**Dashboard build is BLOCKED until backend endpoints exist.**

### Phase 1: Backend Gaps (Fix First)

These must be built before dashboard components can function:

| Priority | Endpoint | Blocks | TODO.md | Status |
|----------|----------|--------|---------|--------|
| **P0** | Items 40-42 (fact-check system) | Brand safety for all outreach | Items 40-42 | IN PROGRESS |
| **P1** | `POST /clients/{id}/pause-all` | EmergencyPauseButton | Item 43 | ✅ COMPLETE |
| **P1** | `GET /clients/{id}/activities` | LiveActivityFeed, ActivityTicker | Item 45 | ✅ COMPLETE |
| **P1** | `GET /clients/{id}/dashboard-metrics` | HeroMetricsCard, OnTrackIndicator | *Spec-defined* | ✅ COMPLETE |

### Phase 2: Dashboard Components (Unblocked After Phase 1)

Once endpoints exist, these can be built:

| Component | Depends On | Can Build After |
|-----------|------------|-----------------|
| HeroMetricsCard | `GET /dashboard-metrics` | ✅ IN PROGRESS |
| OnTrackIndicator | `GET /dashboard-metrics` | Phase 1 complete |
| EmergencyPauseButton | `POST /pause` | Phase 1 complete |
| LiveActivityFeed | `GET /activities` | Phase 1 complete |
| PrioritySlider | `POST /campaigns/allocate` | Phase 1 complete |
| CampaignPriorityCard | `POST /campaigns/allocate` | Phase 1 complete |
| CampaignAllocationManager | `POST /campaigns/allocate` | Phase 1 complete |

### Phase 3: Secondary Components (No Blocking Dependencies)

These can be built anytime (use existing endpoints):

| Component | Uses | Status |
|-----------|------|--------|
| CampaignMetricsPanel | Existing campaign data | Can build now |
| CampaignTabs | Existing campaign data | Can build now |
| SequenceBuilder | Existing sequence data | Can build now |

### Dependency Diagram

```
TODO.md Items 40-42 (fact-check)
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ BACKEND ENDPOINTS (Phase 1)                            │
├────────────────────────────────────────────────────────┤
│ POST /clients/{id}/pause-all      → Item 43 ✅         │
│ GET /clients/{id}/activities      → Item 45 ✅         │
│ GET /clients/{id}/archive/content → Item 46 ✅         │
│ GET /clients/{id}/best-of         → Item 47 ✅         │
│ GET /clients/{id}/dashboard-metrics → Spec-defined ✅  │
│ POST /clients/{id}/campaigns/allocate → Spec-defined   │
└────────────────────────────────────────────────────────┘
         │
         ▼ (unblocks)
┌────────────────────────────────────────────────────────┐
│ FRONTEND COMPONENTS (Phase 2)                          │
├────────────────────────────────────────────────────────┤
│ EmergencyPauseButton              → Item 43 ✅         │
│ LiveActivityFeed                  → Item 45 ✅         │
│ BestOfShowcase                    → Item 47 ✅         │
│ HeroMetricsCard (IN PROGRESS), OnTrackIndicator        │
│ PrioritySlider, CampaignPriorityCard                  │
│ CampaignAllocationManager                              │
└────────────────────────────────────────────────────────┘
         │
         ▼ (unblocks)
┌────────────────────────────────────────────────────────┐
│ DASHBOARD PAGES (Phase 3)                              │
├────────────────────────────────────────────────────────┤
│ /dashboard (redesigned)                                │
│ /dashboard/campaigns (with priority sliders)           │
│ /dashboard/archive (Item 46) ✅                        │
└────────────────────────────────────────────────────────┘
```

---

## Where to Find Specs

### Primary Location

**All frontend specifications are in:** `C:\AI\Agency_OS\docs\architecture\frontend\`

| Document | Purpose | Pages/Components Covered |
|----------|---------|--------------------------|
| `INDEX.md` | Navigation hub | Links to all frontend docs |
| `TECHNICAL.md` | Tech stack, patterns, API client | Next.js 14, React Query, Shadcn/ui |
| `DASHBOARD.md` | Client dashboard architecture | 11 pages, 6 components to create |
| `CAMPAIGNS.md` | Campaign management UI | 3 routes, 6 components to create |
| `LEADS.md` | Lead list/detail UI | 2 routes, ALS tier display |
| `SETTINGS.md` | Configuration pages | 5 routes, ICP/LinkedIn management |
| `ONBOARDING.md` | Onboarding flow | 4 pages, ICP extraction |
| `ADMIN.md` | Admin panel | 21 pages, platform management |

### Design Specs (Visual/UX)

**Location:** `C:\AI\Agency_OS\frontend\design\`

| Document | Purpose |
|----------|---------|
| `README.md` | Design system overview, workflow |
| `dashboard/OVERVIEW.md` | Design philosophy, terminology rules |
| `dashboard/campaigns.md` | Priority slider UI spec, states |
| `dashboard/metrics.md` | Metric tiers (T1-T4), formatting |

### Gap Tracking

**Location:** `C:\AI\Agency_OS\docs\architecture\TODO.md`

- Master gap tracker with 47 items
- Implementation status for all features
- Priority assignments (P1-P4)
- Phase tracking (A-H)

---

## Architecture Folder Structure

```
C:\AI\Agency_OS\docs\architecture\
├── ARCHITECTURE_INDEX.md          <- START HERE (master navigation)
├── ARCHITECTURE_DOC_SKILL.md      <- Templates for creating docs
├── TODO.md                        <- Gap tracking (SINGLE SOURCE OF TRUTH)
│
├── foundation/                    <- LOCKED: Core rules
│   ├── INDEX.md
│   ├── DECISIONS.md              <- Tech stack choices
│   ├── IMPORT_HIERARCHY.md       <- Layer import rules
│   ├── RULES.md                  <- Development protocol
│   ├── FILE_STRUCTURE.md         <- Project layout (135+ files)
│   ├── API_LAYER.md              <- FastAPI routes, auth
│   └── DATABASE.md               <- 22 SQLAlchemy models
│
├── business/                      <- Pricing, scoring, campaigns
│   ├── INDEX.md
│   ├── TIERS_AND_BILLING.md      <- Subscription tiers, credits
│   ├── SCORING.md                <- ALS formula, thresholds
│   ├── CIS.md                    <- Conversion Intelligence
│   └── CAMPAIGNS.md              <- Campaign lifecycle (backend)
│
├── distribution/                  <- Channel specifications
│   ├── INDEX.md
│   ├── EMAIL.md                  <- Salesforge integration
│   ├── SMS.md                    <- ClickSend, DNCR
│   ├── VOICE.md                  <- Vapi, ElevenLabs
│   ├── LINKEDIN.md               <- Unipile automation
│   ├── MAIL.md                   <- Direct mail (spec only)
│   ├── RESOURCE_POOL.md          <- Shared resources
│   └── SCRAPER_WATERFALL.md      <- Web scraping tiers
│
├── flows/                         <- End-to-end data flows
│   ├── INDEX.md
│   ├── ONBOARDING.md             <- ICP extraction flow
│   ├── ENRICHMENT.md             <- Apollo->Apify->Clay
│   ├── OUTREACH.md               <- Multi-channel execution
│   ├── MEETINGS_CRM.md           <- Meeting lifecycle, CRM push
│   ├── MONTHLY_LIFECYCLE.md      <- Month 2+ operations
│   ├── AUTOMATION_DEFAULTS.md    <- Default sequences
│   └── REPLY_HANDLING.md         <- Intent classification
│
├── content/                       <- SDK & content generation
│   ├── INDEX.md
│   └── SDK_AND_PROMPTS.md        <- Smart Prompts, SDK agents
│
├── process/                       <- Development workflow
│   ├── INDEX.md
│   └── DEV_REVIEW.md             <- 5-step review process
│
└── frontend/                      <- UI ARCHITECTURE (THIS SECTION)
    ├── INDEX.md
    ├── TECHNICAL.md
    ├── DASHBOARD.md
    ├── CAMPAIGNS.md
    ├── LEADS.md
    ├── SETTINGS.md
    ├── ONBOARDING.md
    ├── ADMIN.md
    └── SPEC_ALIGNMENT.md         <- THIS FILE
```

---

## Alignment Status

### Routes: FULLY ALIGNED

All documented routes exist in the codebase.

| Category | Documented | Implemented | Status |
|----------|------------|-------------|--------|
| Dashboard pages | 11 | 11 | MATCH |
| Admin pages | 22 | 22 | MATCH |
| Onboarding pages | 4 | 4 | MATCH |
| Auth pages | 3 | 3 | MATCH |
| Marketing pages | 3 | 3 | MATCH |
| **Total** | **43** | **44** | MATCH |

### Components: MISALIGNED

**17 components documented but NOT implemented.**

#### Dashboard Components (from DASHBOARD.md Section 6)

| Component | Spec Line | Expected File | TODO.md Item | Status |
|-----------|-----------|---------------|--------------|--------|
| HeroMetricsCard | 258-276 | `components/dashboard/HeroMetricsCard.tsx` | *Spec-defined* | IN PROGRESS |
| PrioritySlider | 286-308 | `components/dashboard/PrioritySlider.tsx` | *Spec-defined* | NOT IMPLEMENTED |
| CampaignPriorityPanel | 318-336 | `components/dashboard/CampaignPriorityPanel.tsx` | *Spec-defined* | NOT IMPLEMENTED |
| LiveActivityFeed | 338-358 | `components/dashboard/LiveActivityFeed.tsx` | **Item 45** | NOT IMPLEMENTED |
| EmergencyPauseButton | 360-378 | `components/dashboard/EmergencyPauseButton.tsx` | **Item 43** | NOT IMPLEMENTED |
| OnTrackIndicator | 380-399 | `components/dashboard/OnTrackIndicator.tsx` | *Spec-defined* | NOT IMPLEMENTED |

#### Campaign Components (from CAMPAIGNS.md Section 6)

| Component | Spec Line | Expected File | TODO.md Item | Status |
|-----------|-----------|---------------|--------------|--------|
| PrioritySlider | 242-285 | `components/campaigns/PrioritySlider.tsx` | *Spec-defined* | NOT IMPLEMENTED |
| CampaignPriorityCard | 287-309 | `components/campaigns/CampaignPriorityCard.tsx` | *Spec-defined* | NOT IMPLEMENTED |
| CampaignAllocationManager | 311-339 | `components/campaigns/CampaignAllocationManager.tsx` | *Spec-defined* | NOT IMPLEMENTED |
| SequenceBuilder | 341-361 | `components/campaigns/SequenceBuilder.tsx` | *Spec-defined* | NOT IMPLEMENTED |
| CampaignMetricsPanel | 363-380 | `components/campaigns/CampaignMetricsPanel.tsx` | *Spec-defined* | NOT IMPLEMENTED |
| CampaignTabs | 382-400 | `components/campaigns/CampaignTabs.tsx` | *Spec-defined* | NOT IMPLEMENTED |

**Legend:**
- **Item XX** = Linked to TODO.md Phase H item
- *Spec-defined* = Implementation detail from architecture spec (no TODO.md entry needed)

#### Existing Components (Implemented)

| Component | Location | Documented |
|-----------|----------|------------|
| ActivityTicker | `components/dashboard/ActivityTicker.tsx` | DASHBOARD.md:227 |
| CapacityGauge | `components/dashboard/CapacityGauge.tsx` | DASHBOARD.md:228 |
| CoPilotView | `components/dashboard/CoPilotView.tsx` | DASHBOARD.md:229 |
| meetings-widget | `components/dashboard/meetings-widget.tsx` | DASHBOARD.md:226 |
| permission-mode-selector | `components/campaigns/permission-mode-selector.tsx` | CAMPAIGNS.md:215 |
| ALSScorecard | `components/leads/ALSScorecard.tsx` | DASHBOARD.md:235 |

### Hooks: PARTIALLY ALIGNED

#### Implemented Hooks

| Hook | File | Query Key | Status |
|------|------|-----------|--------|
| useDashboardStats | `hooks/use-reports.ts` | `["dashboard-stats", clientId]` | IMPLEMENTED |
| useActivityFeed | `hooks/use-reports.ts` | `["activity-feed", clientId, limit]` | STUB (returns []) |
| useALSDistribution | `hooks/use-reports.ts` | `["als-distribution", clientId]` | IMPLEMENTED |
| useCampaignPerformance | `hooks/use-reports.ts` | `["campaign-performance", ...]` | STUB |
| useChannelMetrics | `hooks/use-reports.ts` | `["channel-metrics", ...]` | STUB |
| useDailyActivity | `hooks/use-reports.ts` | `["daily-activity", ...]` | IMPLEMENTED |
| useUpcomingMeetings | `hooks/use-meetings.ts` | `["meetings", ...]` | IMPLEMENTED |

#### Implemented Hooks (Dashboard Metrics)

| Hook | Endpoint | Purpose | TODO.md Item | Status |
|------|----------|---------|--------------|--------|
| useDashboardMetrics | `GET /clients/{id}/dashboard-metrics` | T1 Hero metrics | *Spec-defined* | ✅ COMPLETE |

#### Missing Hooks (from DASHBOARD.md Section 7)

| Hook | Endpoint | Purpose | TODO.md Item | Priority |
|------|----------|---------|--------------|----------|
| useLiveActivity | WebSocket or polling | Real-time activity | **Item 45** | P1 |
| usePauseOutreach | `POST /clients/{id}/pause` | Emergency pause | **Item 43** | P1 |
| useCampaignPriorities | `GET /clients/{id}/campaigns` | Campaign priorities | *Spec-defined* | P2 |
| useUpdatePriorities | `PATCH /campaigns/priorities` | Batch update | *Spec-defined* | P2 |

### API Endpoints: PARTIALLY COMPLETE

#### Completed Backend Endpoints

| Endpoint | Purpose | TODO.md Item | Status | Spec Location |
|----------|---------|--------------|--------|---------------|
| `GET /api/v1/clients/{id}/dashboard-metrics` | Hero metrics (meetings, show rate) | *Spec-defined* | ✅ COMPLETE | DASHBOARD.md:455 |
| `GET /api/v1/clients/{id}/activities` | Activity feed | **Item 45** | ✅ COMPLETE | DASHBOARD.md:456 |
| `POST /api/v1/clients/{id}/pause-all` | Emergency pause outreach | **Item 43** | ✅ COMPLETE | DASHBOARD.md:457 |

#### Missing Backend Endpoints

| Endpoint | Purpose | TODO.md Item | Priority | Spec Location |
|----------|---------|--------------|----------|---------------|
| `PATCH /api/v1/campaigns/priorities` | Batch update priorities | *Spec-defined* | P2 | DASHBOARD.md:458 |
| `POST /api/v1/campaigns/activate` | Activate with priorities | *Spec-defined* | P2 | DASHBOARD.md:459 |
| `POST /api/v1/clients/{id}/campaigns/allocate` | Campaign allocation | *Spec-defined* | P1 | CAMPAIGNS.md:470 |
| `GET /api/v1/campaigns/{id}/activities` | Campaign activity feed | *Spec-defined* | P2 | CAMPAIGNS.md:471 |

---

## Code Quality Issues

### 1. Campaign Detail Page Uses Placeholder Data

**File:** `frontend/app/dashboard/campaigns/[id]/page.tsx`
**Line:** 14-42

```typescript
// Placeholder data - would be fetched based on id
const campaign = {
  id: "1",
  name: "Tech Startups Q1 2025",
  // ... hardcoded values
}
```

**Should use:**
```typescript
const { data: campaign, isLoading } = useCampaign(id);
```

### 2. Activity Feed Returns Empty Array

**File:** `frontend/hooks/use-reports.ts`
**Function:** `useActivityFeed`

The hook exists but the API endpoint may not be implemented, resulting in empty data.

### 3. React Query Stale Times Mismatch

**Documented (DASHBOARD.md:431-437):**
- campaigns: 60 * 1000 (1 minute)

**Actual (use-campaigns.ts:47):**
- campaigns: 30 * 1000 (30 seconds)

---

## Implementation Priority (Dependency-Based)

### Phase 1: Backend Endpoints (BLOCKING - Do First)

| # | Item | Type | TODO.md | Status |
|---|------|------|---------|--------|
| 1 | Items 40-42 (fact-check system) | Backend | Items 40-42 | IN PROGRESS |
| 2 | `POST /clients/{id}/pause-all` | Endpoint | Item 43 | ✅ COMPLETE |
| 3 | `GET /clients/{id}/activities` | Endpoint | Item 45 | ✅ COMPLETE |
| 4 | `GET /clients/{id}/dashboard-metrics` | Endpoint | *Spec-defined* | ✅ COMPLETE |
| 5 | `POST /clients/{id}/campaigns/allocate` | Endpoint | *Spec-defined* | NOT STARTED |

### Phase 2: Frontend Hooks (After Phase 1)

| # | Item | Depends On | Status |
|---|------|------------|--------|
| 6 | useDashboardMetrics | Endpoint #4 | ✅ COMPLETE |
| 7 | usePauseOutreach | Endpoint #2 | NOT STARTED |
| 8 | useLiveActivity | Endpoint #3 | NOT STARTED |
| 9 | useAllocateCampaigns | Endpoint #5 | NOT STARTED |

### Phase 3: Dashboard Components (After Phase 2)

| # | Item | Depends On | Status |
|---|------|------------|--------|
| 10 | HeroMetricsCard | Hook #6 | IN PROGRESS |
| 11 | OnTrackIndicator | Hook #6 | NOT STARTED |
| 12 | EmergencyPauseButton | Hook #7 | NOT STARTED |
| 13 | LiveActivityFeed | Hook #8 | NOT STARTED |
| 14 | PrioritySlider | Hook #9 | NOT STARTED |
| 15 | CampaignPriorityCard | Hook #9 | NOT STARTED |
| 16 | CampaignAllocationManager | Hook #9 | NOT STARTED |

### Phase 4: Non-Blocking Components (Can Build Anytime)

| # | Item | Uses Existing | Status |
|---|------|---------------|--------|
| 17 | CampaignMetricsPanel | useCampaign | NOT STARTED |
| 18 | CampaignTabs | useCampaign | NOT STARTED |
| 19 | SequenceBuilder | useCampaignSequences | NOT STARTED |

---

## Summary Statistics

| Metric | Documented | Implemented | Alignment |
|--------|------------|-------------|-----------|
| Frontend Docs | 8 | 8 | 100% |
| Routes | 43 | 44 | 100% |
| Dashboard Components | 10 | 4 (+1 in progress) | 50% |
| Campaign Components | 7 | 1 | 14% |
| Hooks (Dashboard) | 12 | 8 | 67% |
| API Endpoints | 7 total | 3 complete | 43% |
| **Overall Alignment** | - | - | **~60%** |

---

## How to Use This Document

### For Developers

1. **Before building a component:** Check if it's documented in the relevant spec file
2. **Find component specs:** Look in `DASHBOARD.md` or `CAMPAIGNS.md` Section 6
3. **Find API contracts:** Look in spec file Section 8 ("API Gaps")
4. **Check implementation status:** Use this alignment report

### For Project Managers

1. **Track progress:** Compare implemented vs documented
2. **Prioritize work:** Use P1-P4 priority list above
3. **Estimate effort:** 17 components + 7 endpoints + 5 hooks = ~29 items

### For New Team Members

1. **Start here:** `docs/architecture/ARCHITECTURE_INDEX.md`
2. **Understand frontend:** Read `frontend/TECHNICAL.md`
3. **Check gaps:** Read this file (`SPEC_ALIGNMENT.md`)
4. **Track work:** Check `TODO.md`

---

## Cross-References

| Need | Location |
|------|----------|
| Master navigation | `docs/architecture/ARCHITECTURE_INDEX.md` |
| Gap tracking | `docs/architecture/TODO.md` |
| Frontend tech stack | `docs/architecture/frontend/TECHNICAL.md` |
| Dashboard spec | `docs/architecture/frontend/DASHBOARD.md` |
| Campaign UI spec | `docs/architecture/frontend/CAMPAIGNS.md` |
| Design philosophy | `frontend/design/dashboard/OVERVIEW.md` |
| Metrics display rules | `frontend/design/dashboard/metrics.md` |

---

## Audit History

| Date | Auditor | Findings |
|------|---------|----------|
| 2026-01-23 | Claude (3 parallel agents) | Initial audit: 50% alignment, 17 missing components |
| 2026-01-23 | Claude | Dashboard metrics pipeline complete: endpoint + hook + API function. HeroMetricsCard in progress. ~60% alignment |

---

For implementation status updates, see `../TODO.md`.
