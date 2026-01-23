# Frontend Design Index

**Purpose:** Navigation hub for building the Agency OS dashboard. Start here to find specs, components, and implementation guides.
**Last Updated:** 2026-01-23

---

## New Session? Start Here

When starting a new Claude session for frontend/dashboard work:

```
1. Point Claude to: C:\AI\Agency_OS\frontend\design\INDEX.md (this file)
2. Say: "Read this file and SPEC_ALIGNMENT.md, then tell me current status"
```

### Context Files (Read Order)

| # | File | Purpose | Priority |
|---|------|---------|----------|
| 1 | `frontend/design/INDEX.md` | This file - navigation hub | REQUIRED |
| 2 | `docs/architecture/frontend/SPEC_ALIGNMENT.md` | What's built vs not | REQUIRED |
| 3 | `docs/architecture/TODO.md` | Current phase, CEO decisions | IF NEEDED |
| 4 | `dashboard/OVERVIEW.md` | Design philosophy | IF BUILDING UI |

### Current Status (Update This)

**Last Session:** 2026-01-23
**Current Phase:** Phase I (Dashboard Redesign) — COMPLETE ✅ (10/10 done)
**Current Focus:** Audit Fixes (P0/P1 Critical)
**Blocking Issues:** NONE

**Dashboard Build Status:** COMPLETE ✅

**What's Done (Phase H + Phase I Complete):**
- ✅ All architecture docs created (Phases A-G complete)
- ✅ Design specs complete (OVERVIEW.md, campaigns.md, metrics.md)
- ✅ Item 40: Claude fact-check gate (`_fact_check_content()`)
- ✅ Item 41: Conservative SMART_EMAIL_PROMPT
- ✅ Item 42: Safe fallback template
- ✅ Item 43: Emergency Pause Button (migration 050, `/pause-all`, EmergencyPauseButton.tsx)
- ✅ Item 44: Daily Digest Email (DigestService, daily_digest_flow)
- ✅ Item 45: Live Activity Feed (endpoint, hook, LiveActivityFeed.tsx)
- ✅ Item 46: Content Archive page (/dashboard/archive)
- ✅ Item 47: Best Of Showcase (BestOfShowcase.tsx)
- ✅ Item 52: PrioritySlider component
- ✅ Item 53: CampaignPriorityPanel component
- ✅ Item 54: CampaignPriorityCard component
- ✅ Item 55: CampaignAllocationManager component
- ✅ Item 56: SequenceBuilder component (with edit functionality)
- ✅ Item 57: CampaignMetricsPanel component (meetings, show rate, active sequences)

**All endpoints and components complete.**

**What's Next:**
See `docs/architecture/TODO.md` for Audit Fixes (P0/P1 Critical)

---

## Quick Start

1. **Read design philosophy:** `dashboard/OVERVIEW.md`
2. **Check component specs:** `dashboard/campaigns.md`, `dashboard/metrics.md`
3. **Find technical details:** `docs/architecture/frontend/DASHBOARD.md`
4. **Track what's built:** `docs/architecture/frontend/SPEC_ALIGNMENT.md`

---

## Design Specs (This Folder)

| File | What It Covers | Use When |
|------|----------------|----------|
| [README.md](README.md) | Design system overview, workflow | Understanding the design-to-code process |
| [PLASMIC_WORKFLOW.md](PLASMIC_WORKFLOW.md) | Plasmic visual design collaboration workflow | CEO + Claude design iteration |
| [PLASMIC_SKILL.md](PLASMIC_SKILL.md) | Plasmic access, navigation, shortcuts | Quick reference for Plasmic tasks |
| [PLASMIC_DASHBOARD_AUDIT.md](PLASMIC_DASHBOARD_AUDIT.md) | Full dashboard feature audit for Plasmic | Building dashboard in Plasmic |
| [dashboard/OVERVIEW.md](dashboard/OVERVIEW.md) | Design philosophy, terminology, banned words | Starting any dashboard work |
| [dashboard/campaigns.md](dashboard/campaigns.md) | Priority sliders, auto-balance, states | Building campaign allocation UI |
| [dashboard/metrics.md](dashboard/metrics.md) | Metric tiers (T1-T4), formatting, empty states | Displaying KPIs and stats |
| [dashboard/mockups/](dashboard/mockups/) | Visual mockups (Plasmic exports) | Reference designs |
| [tokens/](tokens/) | Design tokens (future) | Colors, typography, spacing |

---

## Architecture Specs (docs/architecture/frontend/)

| File | What It Covers | Use When |
|------|----------------|----------|
| [TECHNICAL.md](../../docs/architecture/frontend/TECHNICAL.md) | Tech stack, React Query, hooks, API client | Understanding frontend patterns |
| [DASHBOARD.md](../../docs/architecture/frontend/DASHBOARD.md) | Routes, components, API contracts, wireframes | Building dashboard pages |
| [CAMPAIGNS.md](../../docs/architecture/frontend/CAMPAIGNS.md) | Campaign UI, priority system, sequences | Building campaign features |
| [LEADS.md](../../docs/architecture/frontend/LEADS.md) | Lead list, ALS display, activity timeline | Building lead pages |
| [SETTINGS.md](../../docs/architecture/frontend/SETTINGS.md) | ICP form, LinkedIn, emergency controls | Building settings pages |
| [SPEC_ALIGNMENT.md](../../docs/architecture/frontend/SPEC_ALIGNMENT.md) | What's built vs what's documented | Checking implementation status |

---

## Component Reference

### Existing Components (Ready to Use)

| Component | Location | Purpose |
|-----------|----------|---------|
| ActivityTicker | `components/dashboard/ActivityTicker.tsx` | Bloomberg-style scrolling feed |
| CapacityGauge | `components/dashboard/CapacityGauge.tsx` | Monthly usage visualization |
| CoPilotView | `components/dashboard/CoPilotView.tsx` | AI email co-pilot interface |
| meetings-widget | `components/dashboard/meetings-widget.tsx` | Upcoming meetings list |
| ALSScorecard | `components/leads/ALSScorecard.tsx` | ALS score with radar chart |
| KPICard | `components/admin/KPICard.tsx` | Metric display card (reusable) |
| **LiveActivityFeed** | `components/dashboard/LiveActivityFeed.tsx` | Real-time activity wrapper ✅ |
| **EmergencyPauseButton** | `components/dashboard/EmergencyPauseButton.tsx` | Pause all outreach ✅ |
| **BestOfShowcase** | `components/dashboard/BestOfShowcase.tsx` | Top-performing content ✅ |
| **Content Archive** | `app/dashboard/archive/page.tsx` | Searchable content history ✅ |
| **HeroMetricsCard** | `components/dashboard/HeroMetricsCard.tsx` | Meetings & show rate display ✅ |
| **OnTrackIndicator** | `components/dashboard/OnTrackIndicator.tsx` | Pace indicator (ahead/on track/behind) ✅ |
| **PrioritySlider** | `components/ui/slider.tsx` | Campaign priority adjustment ✅ |
| **CampaignPriorityPanel** | `components/campaigns/CampaignPriorityPanel.tsx` | Priority management panel ✅ |
| **CampaignPriorityCard** | `components/campaigns/CampaignPriorityCard.tsx` | Individual campaign priority ✅ |
| **SequenceBuilder** | `components/campaigns/SequenceBuilder.tsx` | Sequence step editor ✅ |
| **CampaignMetricsPanel** | `components/campaigns/CampaignMetricsPanel.tsx` | Campaign performance metrics ✅ |
| **CampaignTabs** | `components/campaigns/CampaignTabs.tsx` | Campaign detail tab navigation ✅ |

### Phase I Components (All Complete)

| Component | Spec Location | Status |
|-----------|---------------|--------|
| HeroMetricsCard | `DASHBOARD.md:258` | ✅ DONE |
| OnTrackIndicator | `DASHBOARD.md:380` | ✅ DONE |
| PrioritySlider | `DASHBOARD.md:286` | ✅ DONE |
| CampaignPriorityPanel | `DASHBOARD.md:318` | ✅ DONE |
| CampaignPriorityCard | `CAMPAIGNS.md:287` | ✅ DONE |
| CampaignAllocationManager | `CAMPAIGNS.md:311` | ✅ DONE |
| SequenceBuilder | `CAMPAIGNS.md:341` | ✅ DONE |
| CampaignMetricsPanel | `CAMPAIGNS.md:363` | ✅ DONE |
| CampaignTabs | `CAMPAIGNS.md:382` | ✅ DONE |

---

## API Endpoints Status

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `GET /clients/{id}/activities` | Activity feed | ✅ Done |
| `POST /clients/{id}/pause-all` | Emergency pause | ✅ Done |
| `POST /clients/{id}/resume-all` | Resume outreach | ✅ Done |
| `GET /clients/{id}/archive/content` | Content archive | ✅ Done |
| `GET /clients/{id}/best-of` | Best performers | ✅ Done |
| `GET /clients/{id}/dashboard-metrics` | Hero metrics data | ✅ Done |
| `POST /clients/{id}/campaigns/allocate` | Priority allocation | ✅ Done |

**All required endpoints complete.**

---

## Hooks Reference

### Existing Hooks

| Hook | File | Purpose | Status |
|------|------|---------|--------|
| useDashboardStats | `hooks/use-reports.ts` | Dashboard KPIs | ✅ Wired |
| **useDashboardMetrics** | `hooks/use-reports.ts` | Outcome-focused metrics | ✅ Wired |
| useActivityFeed | `hooks/use-reports.ts` | Activity feed | ✅ Wired |
| useALSDistribution | `hooks/use-reports.ts` | ALS tier breakdown | ✅ Wired |
| useContentArchive | `hooks/use-reports.ts` | Content archive | ✅ Wired |
| useBestOfShowcase | `hooks/use-reports.ts` | Best performers | ✅ Wired |
| useUpcomingMeetings | `hooks/use-meetings.ts` | Meeting calendar | ✅ Wired |
| useCampaigns | `hooks/use-campaigns.ts` | Campaign CRUD | ✅ Wired |
| useClient | `hooks/use-client.ts` | Client data | ✅ Wired |

### Phase I Hooks (All Complete)

| Hook | Endpoint | Status |
|------|----------|--------|
| useDashboardMetrics | `GET /clients/{id}/dashboard-metrics` | ✅ Done |
| useAllocateCampaigns | `POST /clients/{id}/campaigns/allocate` | ✅ Done |

---

## Design Rules (Non-Negotiable)

### Terminology

| Use This | NOT This | Reason |
|----------|----------|--------|
| "Meetings booked" | "Credits remaining" | Outcome-focused, not transactional |
| "Prospects in pipeline" | "Lead count" | We're not a lead vendor |
| "Priority" | "Lead allocation %" | Clients think in effort, not numbers |
| "Show rate" | "Lead budget" | Results, not commodities |

### Metric Tiers

| Tier | Visibility | Examples |
|------|------------|----------|
| T1 Hero | Always visible | Meetings booked, Show rate, On-track |
| T2 Campaign | Per campaign | Reply rate, Campaign meetings |
| T3 Activity | Proof of work | Activity feed, Active sequences |
| T4 Hidden | Internal only | Lead counts, Credits, Enrichment status |

### Priority Slider Rules

- **Min:** 10% per campaign
- **Max:** 80% per campaign
- **Total:** Must equal 100%
- **Auto-balance:** Adjusting one proportionally adjusts others

---

## Wireframes

### Dashboard Home Layout

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  +------------------------+  +------------------------+  |
|        |  | 12 Meetings Booked     |  | 85% Show Rate          |  |
| [Home] |  | On track               |  | +5% vs last month      |  |
| [Camp] |  +------------------------+  +------------------------+  |
| [Leads]|                                                          |
| [Reply]|  +--------------------------------------------------+    |
| [Reprt]|  | YOUR CAMPAIGNS                                    |    |
| [Setng]|  |                                                   |    |
|        |  | Tech Decision Makers (AI)   ●━━━━━━━━○──  40%    |    |
|        |  | Series A Startups (AI)      ○━━━━━●────  35%     |    |
|        |  | My Custom Campaign          ○━━━●──────  25%     |    |
|        |  |                                                   |    |
|        |  | Total: 100%          [ Confirm & Activate ]       |    |
|        |  +--------------------------------------------------+    |
|        |                                                          |
|        |  +----------------------------+  +---------------------+ |
|        |  | RECENT ACTIVITY       Live |  | UPCOMING MEETINGS   | |
|        |  | [Email] Sarah Chen opened  |  | Today 2:00 PM       | |
|        |  | [Reply] Mike Johnson reply |  | Tomorrow 10 AM      | |
|        |  +----------------------------+  +---------------------+ |
+------------------------------------------------------------------+
```

Full wireframes: `docs/architecture/frontend/DASHBOARD.md` Section 11

---

## Build Workflow

```
1. Find spec          → This INDEX.md → relevant spec file
2. Check alignment    → SPEC_ALIGNMENT.md (what's built)
3. Read component     → Spec Section 6 (Components to Create)
4. Build component    → Follow TypeScript interface from spec
5. Create hook        → If API needed, check Section 7/8
6. Test locally       → npm run dev
7. Update alignment   → Mark as implemented in SPEC_ALIGNMENT.md
```

---

## File Locations Summary

```
frontend/
├── design/                        <- YOU ARE HERE
│   ├── INDEX.md                   <- This file
│   ├── README.md                  <- Design system overview
│   └── dashboard/
│       ├── OVERVIEW.md            <- Design philosophy
│       ├── campaigns.md           <- Priority slider spec
│       └── metrics.md             <- Metric display rules
│
├── app/dashboard/                 <- Dashboard pages
├── components/dashboard/          <- Dashboard components
├── components/campaigns/          <- Campaign components
├── hooks/                         <- React Query hooks
└── lib/api/                       <- API client

docs/architecture/frontend/        <- Technical specs
├── DASHBOARD.md                   <- Dashboard architecture
├── CAMPAIGNS.md                   <- Campaign UI architecture
└── SPEC_ALIGNMENT.md              <- Implementation status
```

---

## Cross-References

| Need | Go To |
|------|-------|
| Design philosophy | `dashboard/OVERVIEW.md` |
| Technical architecture | `docs/architecture/frontend/DASHBOARD.md` |
| Implementation status | `docs/architecture/frontend/SPEC_ALIGNMENT.md` |
| Gap tracking | `docs/architecture/TODO.md` |
| Master architecture index | `docs/architecture/ARCHITECTURE_INDEX.md` |
