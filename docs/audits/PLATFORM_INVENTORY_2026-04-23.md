# Platform Inventory — 2026-04-23

**Scope:** read-only survey of every feature surface in Agency OS (frontend routes, backend routes, services, models, integrations, migrations, tests). No code changes.

**Methodology:**
- `find frontend/app -name "page.tsx"` for route enumeration
- `ls src/api/routes`, `src/services`, `src/models`, `src/integrations` for backend layers
- `grep -n "mock\|hardcoded\|placeholder\|from.*data/mock"` per file to detect non-wired data
- `grep "createBrowserClient\|supabase\|useQuery"` per hook to detect real data wiring
- Wire-state reported per the 6 categories defined at the bottom

---

## Summary

| Metric | Count | Notes |
|---|---|---|
| Frontend `page.tsx` routes | **65** | across `/`, `(auth)`, `(marketing)`, `admin/`, `billing`, `campaigns`, `dashboard/`, `leads`, `onboarding/`, `replies`, `reports`, `settings`, `welcome`, dev showcases |
| Backend route files | 25 (content) | `src/api/routes/` (plus `__init__.py`) |
| Backend endpoints (total @router decorators) | **~186** | top 5 files: `admin.py` 20, `campaigns.py` 26, `webhooks.py` 17, `customers.py` 15, `crm.py` 14 |
| Backend services | 56 | `src/services/` |
| Backend models | 30 | `src/models/` |
| Integrations | 38 | `src/integrations/` — mix of live clients, compatibility shims, deprecated-kept-for-import-compat |
| Supabase migrations | 115 | `supabase/migrations/` |
| Top-level migrations | 26 | `migrations/` (legacy + directive-ratified) |
| Alembic migrations | 9 | `alembic/versions/` |
| Python tests | 183 | `tests/**/test_*.py` |
| Frontend tests | 2 | `frontend/lib/__tests__/` (`provider-labels.test.ts` new in PR #393, `useLiveActivityFeed.test.ts` legacy) |

---

## Feature Surfaces

Each row maps a user-visible or API-visible surface to its frontend and backend touchpoints with an honest wire-state call-out.

| # | Surface | Feature | Frontend Files | Backend Files | Wire State | Gap |
|---|---|---|---|---|---|---|
| 1 | Marketing | Landing page | `app/page.tsx` | — | FRONTEND-ONLY | Static copy, no backend needed |
| 2 | Marketing | About | `app/(marketing)/about/page.tsx` | — | FRONTEND-ONLY | Static |
| 3 | Marketing | How it works | `app/(marketing)/how-it-works/page.tsx` | — | FRONTEND-ONLY | Static |
| 4 | Marketing | Pricing | `app/(marketing)/pricing/page.tsx` | — | FRONTEND-ONLY | Static |
| 5 | Auth | Login | `app/(auth)/login/page.tsx` | Supabase Auth | PROD-WIRED | Uses `@supabase/ssr` |
| 6 | Auth | Signup | `app/(auth)/signup/page.tsx` | Supabase Auth | PROD-WIRED | — |
| 7 | Onboarding | Welcome gate | `app/welcome/page.tsx`, `app/onboarding/page.tsx` | `api/routes/onboarding.py` (8 endpoints), `services/onboarding_gate_service.py` | PROD-WIRED | Full gate flow |
| 8 | Onboarding | Agency profile | `app/onboarding/agency/page.tsx` | `api/routes/onboarding.py` | PROD-WIRED | — |
| 9 | Onboarding | Service area | `app/onboarding/service-area/page.tsx` | `api/routes/onboarding.py` | PROD-WIRED | — |
| 10 | Onboarding | CRM import | `app/onboarding/crm/page.tsx` | `services/customer_import_service.py`, `services/mock_crm_service.py` | PARTIAL | `mock_crm_service.py` named-mock; prod CRM path via `services/crm_push_service.py` |
| 11 | Onboarding | LinkedIn connect | `app/onboarding/linkedin/page.tsx` | `api/routes/linkedin.py` (4 endpoints), `services/linkedin_*` | PROD-WIRED | Unipile + Heyreach shims live |
| 12 | Dashboard | Home (Command Center) | `app/dashboard/page.tsx` (replaces legacy v3 on main) | `hooks/use-dashboard-v4.ts`, `lib/useLiveActivityFeed.ts`, `lib/hooks/useDashboardStats.ts` | PARTIAL | **12 `mock-dashboard` imports** (ChannelOrchestration, VoiceStats, RecentCalls, Insights, ActivityFeed) — flagged as `// TODO: wire…` |
| 13 | Dashboard | Elliot chat | `app/dashboard/elliot/page.tsx` | `hooks/use-elliot.ts` | PROD-WIRED | Backend chat endpoint |
| 14 | Dashboard | Pipeline (Kanban + Table) | `app/dashboard/pipeline/page.tsx` (post PR #385) | `lib/hooks/usePipelineData.ts` — queries `business_universe`, `cis_outreach_outcomes`, `scheduled_touches` | PROD-WIRED | No mocks; realtime subscribed in PR #393 |
| 15 | Dashboard | Meetings week view | `app/dashboard/meetings/page.tsx` (PR #385), `components/dashboard/MeetingsCalendar.tsx`, `MeetingBriefing.tsx` | `lib/hooks/useMeetingsData.ts` — queries `activities`, `business_universe` | PROD-WIRED | — |
| 16 | Dashboard | Activity timeline | `app/dashboard/activity/page.tsx`, `components/dashboard/ActivityFeedFull.tsx` (PR #388) | `lib/useLiveActivityFeed.ts`, direct query on `cis_outreach_outcomes` | PROD-WIRED | Realtime subscribed |
| 17 | Dashboard | Approval queue | `app/dashboard/approval/page.tsx`, `components/dashboard/ApprovalQueue.tsx` (PR #389) | `lib/hooks/useApprovalQueue.ts` (queries `scheduled_touches`), `api/routes/approvals.py` (4 endpoints) | PARTIAL | Queue reads live; mutations POST `/api/v1/outreach/approval` (frontend) vs backend `/api/v1/approvals/clients/{id}/{id}/{action}` — URL mismatch, follow-up |
| 18 | Dashboard | Prospect drawer | `components/dashboard/ProspectDrawer.tsx` (PR #388, enhanced PR #391) | `lib/hooks/useProspectDetail.ts` — joins 4 Supabase tables | PROD-WIRED | VR sub-score columns optional |
| 19 | Dashboard | Outreach timeline | `components/dashboard/OutreachTimeline.tsx` (PR #391) | `lib/hooks/useOutreachTimeline.ts` — pure transform over `useProspectDetail` | PROD-WIRED | Pause/Skip/Accelerate POSTs stub endpoint |
| 20 | Dashboard | VR grade popover | `components/dashboard/VRGradePopover.tsx` (PR #391) | Reads `business_universe.vr_*` columns with fallback | PARTIAL | VR sub-score columns may not exist in every deployment |
| 21 | Dashboard | Attention cards | `components/dashboard/AttentionCards.tsx` | `lib/hooks/useAttentionItems.ts` | PROD-WIRED | Real queries against multiple tables |
| 22 | Dashboard | Hero strip (BDR stats) | `components/dashboard/HeroStrip.tsx` | `lib/hooks/useDashboardStats.ts` — realtime in PR #393 | PROD-WIRED | — |
| 23 | Dashboard | Funnel bar | `components/dashboard/FunnelBar.tsx` | `lib/hooks/useFunnelData.ts` | PROD-WIRED | — |
| 24 | Dashboard | Kill switch (global pause) | `components/dashboard/KillSwitch.tsx` (PR #389) | — | FRONTEND-ONLY | Backend endpoint `/api/v1/outreach/kill-switch` is a stub — needs implementation |
| 25 | Dashboard | Nav sidebar | `components/dashboard/DashboardNav.tsx` (PR #395) | — | FRONTEND-ONLY | Static nav |
| 26 | Dashboard | Campaigns list | `app/dashboard/campaigns/page.tsx` | `api/routes/campaigns.py` (26 endpoints), `hooks/use-campaigns.ts` | PROD-WIRED | — |
| 27 | Dashboard | Campaign detail | `app/dashboard/campaigns/[id]/page.tsx` | `api/routes/campaigns.py` | PROD-WIRED | — |
| 28 | Dashboard | Campaign wizard (new) | `app/dashboard/campaigns/new/page.tsx`, `components/dashboard/CampaignWizard.tsx` | `api/routes/campaign_generation.py` (6 endpoints) | PARTIAL | Wizard wired; GPT generation step may stub |
| 29 | Dashboard | Campaign approval | `app/dashboard/campaigns/approval/page.tsx` | `api/routes/campaigns.py` | PROD-WIRED | — |
| 30 | Dashboard | Inbox list | `app/dashboard/inbox/page.tsx` | `hooks/use-replies.ts`, `api/routes/replies.py` (3 endpoints) | PARTIAL | 5 mock references; some fields hardcoded |
| 31 | Dashboard | Inbox thread | `app/dashboard/inbox/[id]/page.tsx` | `api/routes/replies.py` | PARTIAL | — |
| 32 | Dashboard | Replies (legacy inbox) | `app/dashboard/replies/page.tsx` | `hooks/use-replies.ts` | PROD-WIRED | No mocks |
| 33 | Dashboard | Leads list | `app/dashboard/leads/page.tsx` | `hooks/use-leads.ts`, `api/routes/leads.py` (12 endpoints) | PARTIAL | 2 mock refs — partial hardcoding |
| 34 | Dashboard | Lead detail | `app/dashboard/leads/[id]/page.tsx` | `hooks/use-lead-detail.ts` | PROD-WIRED | — |
| 35 | Dashboard | Archive | `app/dashboard/archive/page.tsx` | — | MOCK | 5 mock refs; archive UI only |
| 36 | Dashboard | Reports | `app/dashboard/reports/page.tsx`, `components/dashboard/ReportsView.tsx` | `api/routes/reports.py` (14 endpoints), `hooks/use-reports.ts` | PARTIAL | 1 mock ref in page; ReportsView has mocks |
| 37 | Dashboard | Settings index | `app/dashboard/settings/page.tsx` | — | PROD-WIRED | Navigational only |
| 38 | Dashboard | Settings — ICP | `app/dashboard/settings/icp/page.tsx` | `hooks/useICPAutoPopulate.ts`, `hooks/use-icp-job.ts`, `services/icp_filter_service.py`, `services/who_refinement_service.py` | PROD-WIRED | — |
| 39 | Dashboard | Settings — LinkedIn | `app/dashboard/settings/linkedin/page.tsx` | `api/routes/linkedin.py`, `hooks/use-linkedin.ts`, `api/routes/unipile.py` (5 endpoints) | PROD-WIRED | — |
| 40 | Dashboard | Settings — Notifications | `app/dashboard/settings/notifications/page.tsx` | — | FRONTEND-ONLY | Backend notification prefs storage missing |
| 41 | Dashboard | Settings — Profile | `app/dashboard/settings/profile/page.tsx` | Supabase user table | PROD-WIRED | — |
| 42 | Admin | Admin home (KPI) | `app/admin/page.tsx` | `api/routes/admin.py` (20 endpoints), `hooks/use-admin.ts` | PROD-WIRED | — |
| 43 | Admin | Activity stream | `app/admin/activity/page.tsx` | `hooks/use-activity-feed.ts` | PROD-WIRED | — |
| 44 | Admin | Campaigns overview | `app/admin/campaigns/page.tsx` | `api/routes/campaigns.py`, `api/routes/admin.py` | PROD-WIRED | — |
| 45 | Admin | Clients list | `app/admin/clients/page.tsx` | `api/routes/customers.py` (15 endpoints), `api/routes/admin.py` | PROD-WIRED | — |
| 46 | Admin | Client detail | `app/admin/clients/[id]/page.tsx` | `api/routes/customers.py` | PROD-WIRED | — |
| 47 | Admin | Compliance overview | `app/admin/compliance/page.tsx` | — | MOCK | 14 mock refs in page — no backend compliance route wired |
| 48 | Admin | Compliance — bounces | `app/admin/compliance/bounces/page.tsx` | — | MOCK | 9 mock refs |
| 49 | Admin | Compliance — suppression | `app/admin/compliance/suppression/page.tsx` | `services/suppression_service.py`, `pipeline/suppression_manager.py` | PARTIAL | 6 mock refs; backend exists but not queried |
| 50 | Admin | Costs overview | `app/admin/costs/page.tsx` | — | MOCK | 10 mock refs |
| 51 | Admin | Costs — AI breakdown | `app/admin/costs/ai/page.tsx` | `services/sdk_usage_service.py`, `models/sdk_usage_log.py` | PROD-WIRED | 0 mock refs; backend usage log exists |
| 52 | Admin | Costs — channels | `app/admin/costs/channels/page.tsx` | — | MOCK | 6 mock refs |
| 53 | Admin | Leads (admin) | `app/admin/leads/page.tsx` | `api/routes/leads.py` | MOCK | 6 mock refs — `mockLeads` hardcoded array used for filtering |
| 54 | Admin | Replies (admin) | `app/admin/replies/page.tsx` | `api/routes/replies.py` | MOCK | 7 mock refs |
| 55 | Admin | Revenue | `app/admin/revenue/page.tsx` | `api/routes/billing.py` (4 endpoints) | MOCK | 17 mock refs — richest admin mock surface; needs revenue rollup backend |
| 56 | Admin | Settings | `app/admin/settings/page.tsx` | — | PROD-WIRED | 0 mock refs; minimal content |
| 57 | Admin | Settings — users | `app/admin/settings/users/page.tsx` | — | MOCK | 6 mock refs |
| 58 | Admin | System overview | `app/admin/system/page.tsx` | — | MOCK | 14 mock refs |
| 59 | Admin | System — errors | `app/admin/system/errors/page.tsx` | Sentry | MOCK | 6 mock refs — Sentry integration exists at `@sentry/nextjs` but route reads local mocks |
| 60 | Admin | System — queues | `app/admin/system/queues/page.tsx` | — | MOCK | 7 mock refs — Prefect backend exists but not queried |
| 61 | Admin | System — rate limits | `app/admin/system/rate-limits/page.tsx` | `services/rate_limit_manager.py`, `services/send_limiter.py` | MOCK | 6 mock refs; backend limiters exist |
| 62 | Platform | Billing page | `app/billing/page.tsx`, `components/dashboard/BillingPage.tsx` | `api/routes/billing.py` (4 endpoints), `integrations/stripe.py` | PROD-WIRED | Stripe integration live |
| 63 | Platform | Campaigns (top-level) | `app/campaigns/page.tsx` | `api/routes/campaigns.py` | PROD-WIRED | — |
| 64 | Platform | Leads (top-level) | `app/leads/page.tsx`, `app/leads/[id]/page.tsx` | `api/routes/leads.py` | PROD-WIRED | — |
| 65 | Platform | Replies (top-level) | `app/replies/page.tsx` | `api/routes/replies.py` | PROD-WIRED | — |
| 66 | Platform | Reports (top-level) | `app/reports/page.tsx` | `api/routes/reports.py` | PROD-WIRED | — |
| 67 | Platform | Settings (top-level) | `app/settings/page.tsx` | — | FRONTEND-ONLY | Thin wrapper, delegates to dashboard |
| 68 | Dev | Gallery showcase | `app/gallery/page.tsx` | — | FRONTEND-ONLY | Dev showcase only |
| 69 | Dev | Logo showcase | `app/logo-showcase/page.tsx` | — | FRONTEND-ONLY | Dev showcase |
| 70 | Dev | Showroom | `app/showroom/page.tsx` | — | FRONTEND-ONLY | Dev showcase |
| 71 | Dev | Plasmic host | `app/plasmic-host/page.tsx` | Plasmic | FRONTEND-ONLY | Plasmic embed |
| 72 | Backend | Approval workflow | — (see #17) | `api/routes/approvals.py` (4 ops: approve/reject/defer/edit), `models/approval.py` | BACKEND-ONLY | URL mismatch with frontend |
| 73 | Backend | Outreach webhooks | — | `api/routes/outreach_webhooks.py` (3: salesforge/unipile/elevenagents) | BACKEND-ONLY | Wired to CadenceDecisionTree; HMAC verified via `src/security/webhook_sigs.py` |
| 74 | Backend | Outbound webhooks | — | `api/routes/webhooks_outbound.py` (6 endpoints) | BACKEND-ONLY | For webhook-outbound event delivery |
| 75 | Backend | Provider webhooks | — | `api/routes/webhooks.py` (17 endpoints) | BACKEND-ONLY | Per-provider inbound handlers |
| 76 | Backend | Meetings API | — (see #15) | `api/routes/meetings.py` (1 endpoint), `services/meeting_service.py` | BACKEND-ONLY | Single endpoint; frontend reads directly from DB |
| 77 | Backend | Pool (capacity) | — | `api/routes/pool.py` (3 endpoints), `services/domain_pool_manager.py` | BACKEND-ONLY | No frontend surface |
| 78 | Backend | Cycles | — | `api/routes/cycles.py` (2 endpoints), `services/cycle_calendar.py`, `models/cycle.py` | BACKEND-ONLY | Monthly cycle lifecycle |
| 79 | Backend | Digest | — | `api/routes/digest.py` (4 endpoints), `services/digest_service.py`, `models/digest_log.py` | BACKEND-ONLY | — |
| 80 | Backend | Internal (service-to-service) | — | `api/routes/internal.py` (4 endpoints) | BACKEND-ONLY | Cross-service auth |
| 81 | Backend | CRM push | — | `api/routes/crm.py` (14 endpoints), `services/crm_push_service.py` | BACKEND-ONLY | Multi-CRM; `services/mock_crm_service.py` for dev |
| 82 | Backend | Patterns (pattern-learning) | — | `api/routes/patterns.py` (7 endpoints), `services/who_refinement_service.py`, `models/conversion_patterns.py` | BACKEND-ONLY | — |
| 83 | Backend | Health | — | `api/routes/health.py` (3 endpoints) | BACKEND-ONLY | Probe/healthz |
| 84 | Backend | Tiers | — | `api/routes/tiers.py` (1 endpoint) | BACKEND-ONLY | — |
| 85 | Integrations | Salesforge | `lib/provider-labels.ts` scrub | `integrations/salesforge.py` | PROD-WIRED | Real HTTP; `Sent via Salesforge` → `Sent via Email` |
| 86 | Integrations | Unipile | `lib/provider-labels.ts` scrub | `integrations/unipile.py`, `services/unipile_service.py` | PROD-WIRED | Real OAuth flow |
| 87 | Integrations | ElevenAgents | `lib/provider-labels.ts` scrub | `integrations/elevenagets_client.py` | PROD-WIRED | Voice AI live |
| 88 | Integrations | Vapi (alt voice) | — | `integrations/vapi.py` | PROD-WIRED | Kept alongside ElevenAgents |
| 89 | Integrations | ElevenLabs (TTS) | — | `integrations/elevenlabs.py` | PROD-WIRED | — |
| 90 | Integrations | Telnyx (phone) | — | `integrations/telnyx_client.py`, `services/phone_provisioning_service.py` | PROD-WIRED | — |
| 91 | Integrations | Twilio | — | `integrations/twilio.py` | PROD-WIRED | — |
| 92 | Integrations | Stripe | see #62 | `integrations/stripe.py` | PROD-WIRED | Billing |
| 93 | Integrations | Supabase | every hook | `integrations/supabase.py`, `lib/supabase.ts` | PROD-WIRED | Primary data store |
| 94 | Integrations | Redis | — | `integrations/redis.py` | PROD-WIRED | Queue |
| 95 | Integrations | Sentry | — | `@sentry/nextjs` in frontend | PROD-WIRED | Error tracking |
| 96 | Integrations | Anthropic (Claude) | — | `integrations/anthropic.py`, `integrations/sdk_brain.py` | PROD-WIRED | Sequence generation, Elliot chat |
| 97 | Integrations | OpenAI (GPT-4o-mini) | — | used inline in `src/outreach/reply_intent.py` | PROD-WIRED | Reply classifier escalation |
| 98 | Integrations | DataForSEO | — | `integrations/dataforseo.py` | PROD-WIRED | Enrichment DM tier |
| 99 | Integrations | Bright Data (GMB + LinkedIn) | — | `integrations/bright_data_client.py`, `brightdata_client.py` | PROD-WIRED | Waterfall tiers |
| 100 | Integrations | Leadmagic | — | `integrations/leadmagic.py` | PROD-WIRED | Email + mobile tiers |
| 101 | Integrations | Prospeo | — | `integrations/contactout_client.py` sibling | PROD-WIRED | Historical alt contact finder |
| 102 | Integrations | ContactOut | — | `integrations/contactout_client.py` | PROD-WIRED | Phone tier |
| 103 | Integrations | ABN (Australian Business Register) | — | `integrations/abn_client.py` | PROD-WIRED | Pipeline T1 |
| 104 | Integrations | DNCR (Do Not Call Registry) | — | `integrations/dncr.py`, `integrations/dncr_client.py` | PROD-WIRED | TCP compliance |
| 105 | Integrations | Serper | — | `integrations/serper.py` | PROD-WIRED | SERP Maps / LinkedIn discovery |
| 106 | Integrations | Heyreach (legacy LinkedIn) | — | `integrations/heyreach.py` | DEPRECATED-SHIM | Replaced by Unipile; kept for import-compat |
| 107 | Integrations | Postmark | — | `integrations/postmark.py` | PROD-WIRED | Transactional email |
| 108 | Integrations | GoHighLevel | — | `integrations/gohighlevel.py` | PROD-WIRED | CRM push |
| 109 | Integrations | HeyGen | — | `integrations/heygen.py` | PROD-WIRED | AI video |
| 110 | Integrations | Warmforge (email warmup) | — | `integrations/warmforge.py` | PROD-WIRED | Mailbox warmup |
| 111 | Integrations | InfraForge | — | `integrations/infraforge.py` | PROD-WIRED | Domain + DNS provisioning |
| 112 | Integrations | Camoufox (scraper) | — | `integrations/camoufox_scraper.py`, `integrations/httpx_scraper.py` | PROD-WIRED | Tier-3 scraping |
| 113 | Integrations | Buffer | — | `integrations/buffer.py` | PROD-WIRED | Social posting |
| 114 | Integrations | Twitter | — | `integrations/twitter.py` | PROD-WIRED | Social signals |
| 115 | Integrations | YouTube | — | `integrations/youtube.py` | PROD-WIRED | Social signals |
| 116 | Integrations | Ads Transparency | — | `integrations/ads_transparency.py` | PROD-WIRED | Ad signal enrichment |
| 117 | Integrations | Circuit breaker (cross-cutting) | — | `integrations/circuit_breaker.py` | PROD-WIRED | Per-provider failure isolation |
| 118 | Integrations | Siege Waterfall orchestration | — | `integrations/siege_waterfall.py`, pipeline files | PROD-WIRED | Agency OS proprietary |
| 119 | Orchestration | Hourly cadence flow | — | `orchestration/flows/hourly_cadence_flow.py` (PR #381) | BACKEND-ONLY | Prefect-scheduled |
| 120 | Orchestration | Daily decider flow | — | `orchestration/flows/daily_decider_flow.py` (PR #383) | BACKEND-ONLY | — |
| 121 | Orchestration | Fire scheduled actions flow | — | `orchestration/flows/fire_scheduled_actions_flow.py` | BACKEND-ONLY | Legacy sibling |
| 122 | Orchestration | Monthly cycle close | — | `orchestration/flows/*` (PR #390 ORION) | BACKEND-ONLY | State transitions + event emit + next-cycle trigger |
| 123 | Safety | Timing engine | — | `outreach/safety/timing_engine.py` | BACKEND-ONLY | AU public-holiday schedule |
| 124 | Safety | Compliance guard | — | `outreach/safety/compliance_guard.py` | BACKEND-ONLY | SPAM Act + TCP + DNCR + suppression |
| 125 | Safety | Rate limiter / send pacer | — | `outreach/safety/rate_limiter.py` (ORION), `services/send_limiter.py`, `services/rate_limit_manager.py` | BACKEND-ONLY | — |
| 126 | Safety | LinkedIn account state | — | `outreach/safety/linkedin_account_state.py` (PR #392 ORION) | BACKEND-ONLY | Dispatcher LinkedIn DM gate |
| 127 | Safety | Webhook signatures | — | `security/webhook_sigs.py` | BACKEND-ONLY | Per-provider HMAC |

---

## Wire-State Categories

- **PROD-WIRED** — Frontend queries real Supabase/API; backend returns real data.
- **PARTIAL** — Frontend exists but uses some mock data, OR backend exists but frontend doesn't call it, OR stub endpoint on one side.
- **MOCK** — Frontend renders but all data is hardcoded / mock.
- **BACKEND-ONLY** — Backend endpoint exists, no frontend surface.
- **FRONTEND-ONLY** — Frontend UI exists, no backend (static or stub endpoint).
- **MISSING** — Neither frontend nor backend.
- **DEPRECATED-SHIM** — Kept in tree for import-compatibility; replaced by newer integration.

---

## Key Gaps Identified (MOCK surfaces ranked by mock-ref density)

| Rank | Surface | Mock refs | Needed backend |
|---|---|---|---|
| 1 | Admin → Revenue | 17 | revenue rollup endpoint + views |
| 2 | Admin → Compliance overview | 14 | compliance status aggregator |
| 3 | Admin → System overview | 14 | prefect + supabase health aggregator |
| 4 | Dashboard → Home (mock-dashboard imports) | 12 | channel orchestration, voice stats, recent calls, insights, activity feed counts |
| 5 | Admin → Costs (overview) | 10 | cost rollup over sdk_usage + per-channel spend |
| 6 | Admin → Compliance bounces | 9 | bounce events aggregator |
| 7 | Admin → System queues | 7 | Prefect deployment + run status query |
| 8 | Admin → Replies | 7 | admin-scoped replies query |
| 9 | Admin → Leads | 6 | admin-scoped leads query |
| 10 | Admin → Suppression | 6 | suppression list admin view (backend `services/suppression_service.py` exists) |
| 11 | Admin → Costs channels | 6 | per-channel spend endpoint |
| 12 | Admin → System errors | 6 | Sentry proxy or webhook ingestion |
| 13 | Admin → System rate-limits | 6 | expose rate_limit_manager state |
| 14 | Admin → Settings users | 6 | user admin CRUD |
| 15 | Dashboard → Archive | 5 | archived-lead list endpoint |
| 16 | Dashboard → Inbox | 5 | full inbox wire (partial live) |
| 17 | Dashboard → Settings → Notifications | 0 refs; pure frontend | notification-prefs schema + CRUD |
| 18 | Dashboard → Kill switch | n/a | `/api/v1/outreach/kill-switch` stub |
| 19 | Approval URL mismatch | n/a | frontend POSTs `/api/v1/outreach/approval`; backend serves `/api/v1/approvals/clients/{id}/{id}/{action}` |

---

## Methodology Notes

- "Mock refs" = grep count of `mock|hardcoded|placeholder` per file. A low count does not guarantee PROD-WIRED (may just not match the keywords); a high count is a strong MOCK signal.
- Hooks in `frontend/lib/hooks/` are the newer convention (9 hooks); `frontend/hooks/` (20+ hooks) is the older convention. Both are live.
- "Backend endpoints ~186" is an `@router.*` count and includes overloads and alt-paths.
- Frontend tests at 2 is the current total after PR #393 added `provider-labels.test.ts`; Vitest install is blocked pending a separate fix to a pre-existing transitive-dep resolver error.
