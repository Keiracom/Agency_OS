# Phase 2.1 User Dashboard — Gap Analysis

**Date:** 2026-04-22
**Callsign:** scout
**Requested by:** Aiden (via TG relay)
**Method:** Verbatim file reads + grep across /home/elliotbot/clawd/Agency_OS/frontend/
**Status:** tentative — awaiting peer review

---

## Summary

The user dashboard is **~65% real, ~35% mock**. Auth (login/signup) and onboarding (4-step flow) are fully functional against Supabase. Core data pages (campaigns, leads, replies, archive, pipeline) use real API hooks. **Six areas are mock or stubbed:** (1) dashboard home — 4 of 9 panels import from mock-dashboard, (2) inbox — entirely mock, (3) reports — entirely mock, (4) billing — entirely mock with zero Stripe wiring, (5) settings hub — mock (though sub-pages profile/linkedin/notifications/icp are real), (6) lead detail timeline + inbox detail send handler. The onboarding flow is NOT a stub — all 4 steps persist to backend APIs. Campaign wizard steps 3-5 are "Coming Soon" placeholders.

---

## Q1: Every TODO and Mock Import

### Explicit TODO Comments

| File | Line | Verbatim TODO |
|------|------|---------------|
| `app/dashboard/page.tsx` | 29 | `// TODO: wire channel-orchestration when API exposes per-channel touch counts` |
| `app/dashboard/page.tsx` | 31 | `// TODO: wire smart-calling when voice AI call data API is available` |
| `app/dashboard/page.tsx` | 33 | `// TODO: wire what's-working insights (who-converts + best-channel-mix) when segment analytics API is available` |
| `app/dashboard/page.tsx` | 35 | `// TODO: wire activity-feed when activity stream API is available` |
| `app/dashboard/page.tsx` | 363 | `// TODO: wire activity-feed when activity stream API is available` (duplicate) |
| `app/dashboard/leads/[id]/page.tsx` | 231-232 | `TODO: wire timeline when getLeadActivities() is integrated into this page` |
| `app/dashboard/inbox/[id]/page.tsx` | 54-56 | `console.log` — `"In a real app, this would send the message via API"` |
| `app/dashboard/settings/icp/page.tsx` | 149 | `// Could poll for status using task_id from response` |
| `app/dashboard/settings/notifications/page.tsx` | 90-91 | `// Return defaults if endpoint not yet implemented` |
| `app/dashboard/settings/profile/page.tsx` | 302-308 | Avatar upload disabled — `"Avatar upload coming soon"` |

### Mock Data Imports

| File | Line(s) | Import Source | What's Mocked |
|------|---------|---------------|---------------|
| `app/dashboard/page.tsx` | 30 | `@/data/mock-dashboard` | `mockChannelOrchestration` |
| `app/dashboard/page.tsx` | 32 | `@/data/mock-dashboard` | `mockVoiceStats`, `mockRecentCalls` |
| `app/dashboard/page.tsx` | 34 | `@/data/mock-dashboard` | `mockInsights` |
| `app/dashboard/page.tsx` | 36 | `@/data/mock-dashboard` | `mockActivityFeed` |
| `app/dashboard/inbox/page.tsx` | 10 | `@/lib/mock/inbox-data` | `mockInboxMessages` |
| `app/dashboard/inbox/[id]/page.tsx` | 25-33 | `@/lib/mock/inbox-data` | `mockInboxMessages`, `mockDavidParkThread`, `mockDavidParkSMS`, `mockAISuggestions` |
| `app/dashboard/reports/page.tsx` | 10 | `@/lib/mock/reports-data` | `DateRange` type (all report components use mock internally) |
| `app/dashboard/settings/page.tsx` | 14-20 | `@/lib/mock/settings-data` | `mockUserProfile`, `mockIntegrations`, `mockNotifications`, `mockBillingInfo`, `mockTeamMembers`, `mockApiKeys` |
| `app/billing/page.tsx` | 20 | `@/data/mock-billing` | `mockCurrentPlan`, `mockPlanMetrics`, `mockUsageData`, `mockInvoices`, `mockPaymentMethod`, `mockAvailablePlans` |

---

## Q2: Per-Route Classification

### Route Status Table

| Route | Status | Detail |
|-------|--------|--------|
| `/dashboard` | **PARTIAL** | 5 of 9 panels real (`useDashboardV4()`): meetings hero, stats grid, hot prospects, week ahead, warm replies. 4 panels mock: channel orchestration, voice stats, insights, activity feed |
| `/dashboard/campaigns` | **REAL** | `useCampaigns()` hook → `/api/v1/campaigns?client_id={id}` |
| `/dashboard/campaigns/new` | **PARTIAL** | Steps 1-2 functional (form state), steps 3-5 render "Coming Soon" placeholder |
| `/dashboard/campaigns/[id]` | **REAL** | `useCampaign()` + `useApproveCampaign()` + `useRejectCampaign()` |
| `/dashboard/campaigns/approval` | **REAL** | `useCampaigns({ status: "pending_approval" })` + approve/reject mutations |
| `/dashboard/leads` | **REAL** | `useLeads()` hook with ALS scoring + real enrichment data |
| `/dashboard/leads/[id]` | **PARTIAL** | `useLeadDetail()` real. CommunicationTimeline empty — TODO at line 231-232 |
| `/dashboard/inbox` | **MOCK** | `mockInboxMessages` hardcoded array. No API integration |
| `/dashboard/inbox/[id]` | **MOCK** | Mock thread data. Send handler is `console.log` stub |
| `/dashboard/replies` | **REAL** | `useReplies()` hook with intent classification + pagination |
| `/dashboard/reports` | **MOCK** | All 10 report components render mock data. No analytics API wired |
| `/dashboard/archive` | **REAL** | `useContentArchive()` hook with real filtering |
| `/dashboard/pipeline` | **REAL** | `usePipelineStream()` — live SSE streaming, real-time prospect cards |
| `/dashboard/elliot` | **REAL** | `useTaskStats`, `useSignoffQueue`, `useRealtimeStatus` hooks. 4 tabs: Tasks, Sign-off, Knowledge, Costs |
| `/dashboard/settings` | **MOCK** | Hub page imports all mock: `mockUserProfile`, `mockIntegrations`, `mockNotifications`, `mockBillingInfo`, `mockTeamMembers`, `mockApiKeys` |
| `/dashboard/settings/profile` | **REAL** | Supabase auth + users table. Avatar upload disabled (coming soon) |
| `/dashboard/settings/linkedin` | **REAL** | Unipile OAuth connect/disconnect via `/api/v1/linkedin/connect` |
| `/dashboard/settings/notifications` | **REAL** | `/api/v1/clients/{id}/notifications/settings` — graceful fallback to defaults if 404 |
| `/dashboard/settings/icp` | **REAL** | GET/PUT `/api/v1/clients/{id}/icp` + reanalyze endpoint. Polling not implemented |
| `/billing` | **MOCK** | 100% mock. No Stripe SDK. No payment webhooks. No subscription management |

### Visual Summary

```
REAL (11 routes):
  campaigns, campaigns/[id], campaigns/approval, leads,
  replies, archive, pipeline, elliot,
  settings/profile, settings/linkedin, settings/notifications, settings/icp

PARTIAL (3 routes):
  dashboard (home), campaigns/new, leads/[id]

MOCK (5 routes):
  inbox, inbox/[id], reports, settings (hub), billing
```

---

## Q3: Missing Backend APIs

These are APIs referenced in dashboard TODOs that don't exist yet:

| Dashboard Panel | Expected API | TODO Reference |
|----------------|-------------|----------------|
| Channel Orchestration | Per-channel touch counts endpoint | `page.tsx:29` — "when API exposes per-channel touch counts" |
| Smart Calling / Voice Stats | Voice AI call data API | `page.tsx:31` — "when voice AI call data API is available" |
| What's Working / Insights | Segment analytics API (who-converts + best-channel-mix) | `page.tsx:33` — "when segment analytics API is available" |
| Activity Feed | Activity stream API | `page.tsx:35` — "when activity stream API is available" |
| Lead Timeline | `getLeadActivities()` | `leads/[id]/page.tsx:231` — "when getLeadActivities() is integrated" |
| Inbox Messages | Real message thread API | `inbox/[id]/page.tsx:54` — "In a real app, this would send the message via API" |
| Reports (all 10) | Analytics/reporting engine | No specific TODO — entire reports section uses mock data |
| Billing | Stripe integration + subscription API | No TODO — entire billing page is mock |

### Existing Next.js API Routes (for reference)

These middleware routes exist at `frontend/app/api/`:

```
/api/activity/            /api/campaigns/pause-all/
/api/channels/stats/      /api/dashboard/bloomberg/
/api/dashboard/stats/     /api/exit-preview/
/api/leads/counts/        /api/meetings/
/api/pipeline/stream/     /api/preview/
/api/replies/             /api/replies/[id]/send/
/api/reports/funnel/      /api/reports/meetings/
/api/reports/weekly/      /api/settings/icp/
/api/waitlist/
```

Note: `/api/activity/` exists but the dashboard activity feed TODO says it's not wired — route may exist but return incomplete data, or the dashboard panel expects a different shape.

---

## Q4: Onboarding Flow

**Verdict: FULLY FUNCTIONAL — NOT A STUB**

| Step | Route | What It Does | Backend Call | Persists? |
|------|-------|-------------|-------------|-----------|
| 1 | `/onboarding/crm` | HubSpot OAuth connection | `POST /api/v1/crm/connect/hubspot` | YES — OAuth flow |
| 2 | `/onboarding/linkedin` | LinkedIn/Unipile OAuth | `GET /api/v1/linkedin/connect` | YES — OAuth flow |
| 3 | `/onboarding/agency` | Website scrape + service confirmation | `POST /api/v1/onboarding/analyze` → poll `GET /api/v1/onboarding/result/{id}` → `POST /api/v1/onboarding/confirm` | YES — persists to Supabase |
| 4 | `/onboarding/service-area` | Metro/state/national selection | `POST /api/v1/onboarding/confirm` with `{ service_area, finalize: true }` | YES — finalizes + redirects to /dashboard |

All 4 steps make real API calls. Step 3 uses polling (3-second intervals) for async scrape results. Aiden's earlier assessment of "12-line stub" does not match — the onboarding flow is production-ready.

---

## Q5: Auth Wiring

**Verdict: FULLY FUNCTIONAL AGAINST SUPABASE AUTH**

| Component | File | Method | Status |
|-----------|------|--------|--------|
| Login (email/password) | `(auth)/login/LoginClient.tsx:33-36` | `supabase.auth.signInWithPassword()` | REAL |
| Login (Google OAuth) | `(auth)/login/LoginClient.tsx:69-74` | `supabase.auth.signInWithOAuth({ provider: "google" })` | REAL |
| Signup | `(auth)/signup/page.tsx:38-48` | `supabase.auth.signUp()` with `full_name`, `company_name` metadata | REAL |
| Dashboard guard | `dashboard/layout.tsx:24-28` | `getCurrentUser()` → redirect to /login if null | REAL |
| Onboarding check | `dashboard/layout.tsx:30-45` | `supabase.rpc("get_onboarding_status")` → redirect to /onboarding if needed | REAL |
| Membership check | `dashboard/layout.tsx:47-52` | `getUserMemberships()` → redirect to /onboarding if no active membership | REAL |

Auth is complete. No stubs. No mock.

---

## Q6: Billing + Stripe

**Verdict: 100% MOCK — ZERO STRIPE INTEGRATION**

`app/billing/page.tsx` lines 20-27:
```
import {
  mockCurrentPlan, mockPlanMetrics, mockUsageData,
  mockInvoices, mockPaymentMethod, mockAvailablePlans
} from "@/data/mock-billing";
```

Lines 40-55 — every billing component renders mock data:
- `<PlanHeroCard plan={mockCurrentPlan} metrics={mockPlanMetrics} />`
- `<UsageMeters usage={mockUsageData} resetDate="March 1, 2026" />`
- `<PaymentMethod paymentMethod={mockPaymentMethod} />`
- `<InvoiceTable invoices={mockInvoices} />`
- `<PlanComparison plans={mockAvailablePlans} />`
- `<UpgradeCTA />`

No Stripe SDK imports found anywhere in the frontend. No payment webhooks. No subscription management. No checkout flow.

---

## Recommended Close Sequence for Phase 2.1

Priority order based on user-facing impact and backend readiness:

### P0 — Dashboard Home Panels (4 mock panels to wire)

These block the primary user experience. Each depends on a backend API:

| Panel | Blocked By | Estimated Backend Work |
|-------|-----------|----------------------|
| 1. Activity Feed | Activity stream API (shape TBD) | Medium — `/api/activity/` route exists, may need reshape |
| 2. Channel Orchestration | Per-channel touch counts | Medium — aggregation query over campaign_activities |
| 3. What's Working / Insights | Segment analytics (who-converts, best-channel-mix) | Heavy — new analytics queries |
| 4. Smart Calling / Voice Stats | Voice AI call data API | Heavy — depends on Vapi/Telnyx integration depth |

### P1 — Inbox (fully mock)

| Item | Work |
|------|------|
| Inbox list | Replace `mockInboxMessages` with real message query (Resend + Unipile) |
| Inbox detail | Wire thread rendering to real message data |
| Send handler | Replace `console.log` with `/api/replies/[id]/send` (route exists) |

### P2 — Reports (fully mock)

All 10 report components need backend analytics. This is the heaviest lift — requires an analytics/reporting engine that doesn't exist yet. Defer unless Dave priorities it.

### P3 — Settings Hub

Replace mock imports in `settings/page.tsx` with real data. Sub-pages (profile, linkedin, notifications, icp) are already real — the hub page just needs to call the same APIs those sub-pages use.

### P4 — Remaining Gaps

| Item | Work | Priority |
|------|------|----------|
| Campaign wizard steps 3-5 | Build remaining wizard steps | Medium |
| Lead detail timeline | Wire `getLeadActivities()` | Low (page works without it) |
| Avatar upload | Implement Supabase storage upload | Low |
| ICP reanalyze polling | Add poll loop for task_id | Low |
| Billing + Stripe | Full Stripe integration | Defer — pre-revenue |

### P5 — Billing (defer)

Pre-revenue platform. Stripe integration is premature. Keep mock until first paying client is imminent.

---

## Sources

All findings from verbatim file reads of:
- `/home/elliotbot/clawd/Agency_OS/frontend/app/dashboard/**/*.tsx`
- `/home/elliotbot/clawd/Agency_OS/frontend/app/(auth)/**/*.tsx`
- `/home/elliotbot/clawd/Agency_OS/frontend/app/onboarding/**/*.tsx`
- `/home/elliotbot/clawd/Agency_OS/frontend/app/billing/page.tsx`
- `/home/elliotbot/clawd/Agency_OS/frontend/app/api/**/route.ts`
