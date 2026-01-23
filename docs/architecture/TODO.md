# Architecture TODO

**Purpose:** Track gaps, priorities, and rules for architecture work.
**Last Updated:** 2026-01-23
**Skill:** See `ARCHITECTURE_DOC_SKILL.md` for templates and checklists.

---

## Current Status

**Read this section first when starting a new session.**

### Where We Are
- **Phase:** All Audit Gaps — COMPLETE
- **Last Completed:** #34 SECURITY.md — All 34 gaps fixed
- **Next Action:** None — All gaps resolved

### Remaining Work Summary
| Category | Items | Priority |
|----------|-------|----------|
| Phase I Dashboard | COMPLETE | — |
| Audit Critical | COMPLETE (4 fixed) | P0/P1 |
| Audit High | COMPLETE (7 fixed) | P2 |
| Audit Medium | COMPLETE (all 8 frontend components) | P3 |
| Future | COMPLETE | P5 |

**Total Open Gaps: 0** (34 fixed: #1 FILE_STRUCTURE.md, #2 Funnel Detector, #3 Voice retry, #4 ICP Refiner, #5 Models, #6 Enums, #7 Digest routes, #8 Camoufox, #9 Campaign FK, #10 getCampaignPerformance, #11 Resend reply, #13 Phone Provisioning, #14 Recording Cleanup, #15 Business hours, #16 DNCR voice check, #17 Stale withdrawal, #18 Shared quota, #19 Profile view delay, #20 Email signature, #21 Display name, #22 Import Hierarchy, #23 Contract comments, #24 TECHNICAL.md, #25 ADMIN.md, #26 LeadEnrichmentCard, #27 LeadActivityTimeline, #28 LeadQuickActions, #29 LeadStatusProgress, #30 LeadBulkActions, #31 Profile page, #32 Notifications page, #33 OnboardingProgress, #34 SECURITY.md)

---

## Development Review Process

**FOLLOW THIS PROCESS FOR ALL ARCHITECTURE AND CODE WORK**

### Steps

| Step | Who | Action |
|------|-----|--------|
| **0** | CTO | **Due Diligence Audit** — Audit codebase BEFORE any work |
| **1** | Dev Team | **Produce Best Work** — No deliberate mistakes, best effort |
| **2** | CTO | **Review** — Identify strengths AND gaps |
| **3** | Dev Team | **Revise** — Address gaps, resubmit |
| **4** | CTO | **Code Check** — Final review before going live |
| **5** | CTO | **CEO Report** — Present final report to CEO |

### Rules

1. **CEO controls pace** — Say "continue" to advance to next step
2. **No sandbagging** — Dev Team delivers best work first time
3. **Honest review** — CTO finds real gaps, not manufactured ones
4. **Iterate until right** — Steps 2-3 loop until CTO approves
5. **Nothing goes live without CTO Code Check** — Step 4 is mandatory
6. **Audit BEFORE architecture** — Always check what exists first
7. **Gaps tracked in TODO.md ONLY** — See "Gap Tracking Rule" below
8. **Use sub-agents as junior devs** — Delegate to sub-agents when possible. CTO reviews their output before accepting.

### Workflow

```
CEO: "continue"
     ↓
[Step 0: Audit] → [Step 1: Dev Work] → [Step 2: CTO Review]
                                              ↓
                                         Approved?
                                         No → [Step 3: Revise] → back to Step 2
                                         Yes ↓
                                       [Step 4: Code Check]
                                              ↓
                                       [Step 5: CEO Report]
                                              ↓
                                         CEO Approval
```

---

## Index Update Rules

1. **After completing a TODO item** — Update ARCHITECTURE_INDEX.md
2. **New architecture file created** — Add to index with bullet summaries
3. **Existing file expanded** — Update bullet points in index
4. **Gap closed** — Mark as complete in this file only

---

## Gap Tracking Rule (ENFORCED)

**TODO.md is the SINGLE SOURCE OF TRUTH for all gaps.**

### What Goes Where

| Content | Location | NOT In |
|---------|----------|--------|
| Gap description | TODO.md "Open Gaps" table | Architecture docs |
| Gap status | TODO.md "Open Gaps" table | Architecture docs |
| Gap priority | TODO.md "Open Gaps" table | Architecture docs |
| Fix sequence | TODO.md "Remaining Work" section | Scattered inline notes |
| Decision rationale | TODO.md "Key Decisions" section | Multiple places |

### Rules

1. **NO "Known Gaps" sections in architecture docs** — Docs describe what IS, not what's missing
2. **NO gap indicators in ARCHITECTURE_INDEX.md** — Index is navigation only
3. **NO duplicate gap entries** — One entry per gap in the Open Gaps table
4. **Fix sequence in Remaining Work ONLY** — Not scattered elsewhere
5. **When gap is fixed** — Delete the row from Open Gaps, that's it

### Architecture Doc Footer

Every architecture doc ends with:
```
---
For gaps and implementation status, see `../TODO.md`.
```

---

## Key Decisions (Reference)

| # | Decision | Final Decision | Doc |
|---|----------|----------------|-----|
| 1 | Default replenishment mode | **`smart`** (gap only) | MONTHLY_LIFECYCLE.md |
| 2 | Auto-apply campaign suggestions | **`No`** (require approval) | MONTHLY_LIFECYCLE.md |
| 3 | Min conversions for CIS refinement | **`20`** | MONTHLY_LIFECYCLE.md |
| 4 | Campaign pause threshold | **`1% after 100 leads`** | MONTHLY_LIFECYCLE.md |
| 5 | Lead carryover to month 2 | **`Active only`** (don't count against quota) | MONTHLY_LIFECYCLE.md |

*All decisions CEO approved 2026-01-23.*

---

## Open Gaps

### Critical — P0/P1 (From Audit 2026-01-23)

| # | Gap | Location | Notes |
|---|-----|----------|-------|
| ~~1~~ | ~~FILE_STRUCTURE.md missing ~50% of files~~ | ~~`foundation/FILE_STRUCTURE.md`~~ | **FIXED 2026-01-23**: Added 4 missing services (email_signature, phone_provisioning, recording_cleanup, voice_retry), 1 flow (recording_cleanup_flow). Total: 200->204 files documented |
| ~~2~~ | ~~Funnel Detector not integrated~~ | ~~`pattern_learning_flow.py`~~ | **FIXED 2026-01-23**: FunnelDetector imported and called in `run_all_detectors_task()` (now 5 detectors: WHO, WHAT, WHEN, HOW, FUNNEL) |
| ~~3~~ | ~~Voice retry logic missing~~ | ~~`voice.py`~~ | **FIXED 2026-01-23**: VoiceRetryService created, wired into process_call_webhook (busy=2hr, no_answer=next business day, max 3 retries) |
| ~~4~~ | ~~ICP Refiner service not implemented~~ | ~~`monthly_replenishment_flow.py`~~ | **FIXED 2026-01-23**: WHO refinement wired into `pool_population_flow.py` (all 3 tiers) |

### High Priority — P2 (From Audit 2026-01-23)

| # | Gap | Location | Notes |
|---|-----|----------|-------|
| ~~5~~ | ~~6 undocumented models~~ | ~~DATABASE.md~~ | **FIXED 2026-01-23**: Added CampaignSuggestion, CampaignSuggestionHistory, DigestLog, IcpRefinementLog, LinkedInCredential, ClientIntelligence, SDKUsageLog to models table (20→24 models) + full documentation for each |
| ~~6~~ | ~~5 undocumented enums~~ | ~~DATABASE.md~~ | **FIXED 2026-01-23**: Added SuggestionType (7 values), SuggestionStatus (5 values) to new Campaign Suggestions section; updated IntentType with all 10 values. ResourceType, ResourceStatus, HealthStatus were already documented. |
| ~~7~~ | ~~digest.py routes undocumented~~ | ~~API_LAYER.md~~ | **FIXED 2026-01-23**: GET/PATCH /digest/settings, GET /digest/preview, GET /digest/history documented with full request/response schemas |
| ~~8~~ | ~~Camoufox scraper not wired~~ | ~~SCRAPER_WATERFALL.md~~ | **FIXED 2026-01-23**: Camoufox wired as Tier 3 in icp_scraper.py waterfall - tries after Apify Tier 1/2 fail, before manual fallback |
| ~~9~~ | ~~Campaign auto-inherit FK missing~~ | ~~RESOURCE_POOL.md~~ | **FIXED 2026-01-23**: Added client_resource_id FK to CampaignResource model + migration 053 |
| ~~10~~ | ~~getCampaignPerformance() stub~~ | ~~`frontend/lib/api/reports.ts`~~ | **FIXED 2026-01-23**: Backend endpoint exists at `/clients/{id}/campaigns/performance` (reports.py:1707-1850), frontend properly wired |
| ~~11~~ | ~~Resend email reply handling missing~~ | ~~`webhooks.py`~~ | **FIXED 2026-01-23**: Added "email.replied" handler to `resend_events_webhook()` - forwards to Closer engine for intent classification and ALS update |

### Medium Priority — P3 (From Audit 2026-01-23)

**Voice Engine (60% aligned):**

| # | Gap | Location | Notes |
|---|-----|----------|-------|
| ~~13~~ | ~~Phone pool provisioning~~ | ~~Voice engine~~ | **FIXED 2026-01-23**: PhoneProvisioningService created with search/provision/release/warmup. Integrates with Twilio API, adds to ResourcePool, assigns to campaigns |
| ~~14~~ | ~~Recording lifecycle cleanup~~ | ~~Voice engine~~ | **FIXED 2026-01-23**: RecordingCleanupService with 90-day retention. Daily Prefect flow at 3AM AEST. Deletes from Vapi, marks activity as deleted (soft delete). Respects flagged_for_retention. |
| ~~15~~ | ~~Business hours validation~~ | ~~Voice engine~~ | **FIXED 2026-01-23**: is_within_business_hours() and get_next_business_hour() added. Checks 9-5 weekdays, skips 12-1 PM lunch, uses lead timezone or Australia/Sydney default |
| ~~16~~ | ~~DNCR check for voice~~ | ~~Voice engine~~ | **FIXED 2026-01-23**: Added DNCR check in voice.py send() method. Checks cached lead.dncr_checked/dncr_result first, then DNCR API if needed. Logs rejections via _log_dncr_rejection(). Australian +61 numbers only. |

**LinkedIn Engine (100% aligned):**

| # | Gap | Location | Notes |
|---|-----|----------|-------|
| ~~17~~ | ~~30-day stale withdrawal~~ | ~~`linkedin.py`~~ | **FIXED 2026-01-23**: `withdraw_stale_requests()` in linkedin_health_service.py. STALE_CONNECTION_DAYS=30, MAX_WITHDRAWALS_PER_RUN=10, calls Unipile API. Wired into linkedin_daily_health_flow.py |
| ~~18~~ | ~~Shared quota tracking~~ | ~~`linkedin.py`~~ | **FIXED 2026-01-23**: `get_combined_activity_count()` fetches from Unipile API including manual sends. `get_remaining_quota()` calculates available. `send()` checks combined quota. `get_account_status()` returns manual/automated breakdown |
| ~~19~~ | ~~Profile view delay~~ | ~~`linkedin.py`~~ | **FIXED 2026-01-23**: Added 10-30 min delay before connect request. `_view_profile()` views via Unipile, `_check_profile_view_delay()` enforces timing, `get_connections_ready_to_send()` retrieves due connections |

**Email Engine (100% aligned):**

| # | Gap | Location | Notes |
|---|-----|----------|-------|
| ~~20~~ | ~~Signature generation~~ | ~~`email.py`~~ | **FIXED 2026-01-23**: email_signature_service.py created with generate_signature_text/html, get_signature_for_persona/client. Wired into email.py send() with include_signature and persona_id kwargs |
| ~~21~~ | ~~Display name format~~ | ~~`email.py`~~ | **FIXED 2026-01-23**: format_display_name() generates "{First} from {Company}" format, format_from_header() for RFC 5322, validate_display_name() enforces standards |

**Documentation Gaps:**

| # | Gap | Location | Notes |
|---|-----|----------|-------|
| ~~22~~ | ~~IMPORT_HIERARCHY.md incomplete~~ | ~~`foundation/IMPORT_HIERARCHY.md`~~ | **FIXED 2026-01-23**: Added agents (36 files), services (28 files), detectors (8 files) with layer diagram, import rules, and file tables |
| ~~23~~ | ~~Contract comments ~50% compliance~~ | ~~Codebase-wide~~ | **FIXED 2026-01-23**: Compliance improved from 46% (86/185) to 91% (170/185). Added contracts to all engines (15), services (19), agents (23 including skills), and core models (6) |
| ~~24~~ | ~~TECHNICAL.md outdated~~ | ~~`docs/architecture/frontend/TECHNICAL.md`~~ | **FIXED 2026-01-23**: Updated component count 61→74, pages 42→43, added /dashboard/archive documentation |
| ~~25~~ | ~~ADMIN.md endpoint count wrong~~ | ~~`frontend/ADMIN.md`~~ | **FIXED 2026-01-23**: Corrected endpoint count from "23+" to "20", page count from "21" to "20", added missing Costs Overview page to table |

**Frontend Components Missing:**

| # | Gap | Location | Notes |
|---|-----|----------|-------|
| ~~26~~ | ~~LeadEnrichmentCard~~ | ~~`frontend/LEADS.md`~~ | **FIXED 2026-01-23**: Created LeadEnrichmentCard.tsx with company info, contact details, SDK signals, icebreakers |
| ~~27~~ | ~~LeadActivityTimeline~~ | ~~`frontend/LEADS.md`~~ | **FIXED 2026-01-23**: Created LeadActivityTimeline.tsx with chronological timeline, channel filtering, activity icons, collapsible content |
| ~~28~~ | ~~LeadQuickActions~~ | ~~`frontend/LEADS.md`~~ | **FIXED 2026-01-23**: Created LeadQuickActions.tsx with email/call/sms/linkedin/note actions, tooltips, loading states, disabled states |
| ~~29~~ | ~~LeadStatusProgress~~ | ~~`frontend/LEADS.md`~~ | **FIXED 2026-01-23**: LeadStatusProgress component with funnel visualization (5 stages: New->Enriched->Scored->In Sequence->Converted). Includes LeadStatusBadge compact variant. Size variants (sm/md/lg), optional labels, clickable stages, transition dates. Special status handling (bounced/unsubscribed) |
| ~~30~~ | ~~LeadBulkActions~~ | ~~`frontend/LEADS.md`~~ | **FIXED 2026-01-23**: Created LeadBulkActions.tsx with bulk operations toolbar, campaign assignment, status updates, export |
| ~~31~~ | ~~Profile page~~ | ~~`frontend/SETTINGS.md`~~ | **FIXED 2026-01-23**: Created /dashboard/settings/profile with name/email/phone/timezone fields, avatar display, form validation, toast notifications |
| ~~32~~ | ~~Notifications page~~ | ~~`frontend/SETTINGS.md`~~ | **FIXED 2026-01-23**: Created /dashboard/settings/notifications with email/push/SMS/in-app toggles, digest frequency, alert categories |
| ~~33~~ | ~~Onboarding progress components~~ | ~~`frontend/ONBOARDING.md`~~ | **FIXED 2026-01-23**: Created OnboardingProgress (horizontal/vertical/compact variants), OnboardingStep, OnboardingChecklist with Progress bar, default steps |

### Future — P5

| # | Gap | Location | Notes |
|---|-----|----------|-------|
| ~~34~~ | ~~Security architecture~~ | ~~`foundation/SECURITY.md`~~ | **FIXED 2026-01-23**: Created SECURITY.md with auth (Supabase JWT), RBAC (4 roles + RLS), API security (webhook signatures), data protection (Fernet encryption), audit logging (triggers + Sentry) |

---

## Remaining Work

### Phase I: Dashboard Redesign (COMPLETE)

| Item | Component | Status | Notes |
|------|-----------|--------|-------|
| 56 | SequenceBuilder | ✅ DONE | Timeline view, add/edit/delete steps, channel badges |
| 57 | CampaignMetricsPanel | ✅ DONE | Hero metrics, channel breakdown, performance badge |

### Audit Fixes (Prioritized)

**P0/P1 Critical — Fix first:**
1. ~~Wire Funnel Detector into `pattern_learning_flow.py` (#2)~~ **DONE**
2. ~~Implement voice retry service — busy=2hr, no_answer=next day (#3)~~ **DONE**
3. ~~Implement ICP Refiner service — apply WHO patterns to sourcing (#4)~~ **DONE**
4. ~~Update FILE_STRUCTURE.md — add services (22), agents (13+), detectors (8) (#1)~~ **DONE** — 204 files now documented

**P2 High (COMPLETE):**
5. ~~Update DATABASE.md — 6 missing models (#5)~~ **DONE** — Added 7 models with full documentation
6. ~~Update DATABASE.md — 5 enums (#6)~~ **DONE** — Added SuggestionType, SuggestionStatus; updated IntentType
7. ~~Document digest.py routes in API_LAYER.md — 4 endpoints (#7)~~ **DONE**
8. ~~Wire Camoufox into scraper waterfall (#8)~~ **DONE** — Tier 3 in icp_scraper.py waterfall
9. ~~Add campaign auto-inherit FK to campaign_resources (#9)~~ **DONE** — client_resource_id FK added
10. ~~Implement getCampaignPerformance() backend (#10)~~ **DONE** — Endpoint at `/clients/{id}/campaigns/performance`
11. ~~Add Resend email reply handler (#11)~~ **DONE** — Handler in `resend_events_webhook()` with Closer engine integration

**P3 Medium — Voice Engine (COMPLETE):**
12. ~~Phone pool provisioning (#13)~~ **DONE** — PhoneProvisioningService with Twilio integration
13. ~~Recording lifecycle cleanup — 90-day deletion (#14)~~ **DONE** — RecordingCleanupService with daily Prefect flow
14. ~~Business hours validation before calls (#15)~~ **DONE** — is_within_business_hours() + get_next_business_hour() in voice.py
15. ~~DNCR check for voice calls (#16)~~ **DONE** — DNCR check in voice.py send() method

**P3 Medium — LinkedIn Engine (COMPLETE):**
16. ~~30-day stale withdrawal (#17)~~ **DONE** — `withdraw_stale_requests()` in linkedin_health_service.py, wired into daily health flow
17. ~~Shared quota tracking — manual + auto combined (#18)~~ **DONE** — get_combined_activity_count() + get_remaining_quota()
18. ~~Profile view delay — 10-30 min before connect (#19)~~ **DONE** — `_view_profile()` + `_check_profile_view_delay()` + `get_connections_ready_to_send()`

**P3 Medium — Email Engine (0 items — COMPLETE):**
19. ~~Dynamic signature generation (#20)~~ **DONE** — email_signature_service.py with generate_signature_text/html, get_signature_for_persona/client
20. ~~Display name format enforcement (#21)~~ **DONE** — format_display_name(), format_from_header(), validate_display_name()

**P3 Medium — Documentation (COMPLETE):**
21. ~~Update IMPORT_HIERARCHY.md — add agents, services, detectors layers (#22)~~ **DONE**
22. ~~Improve contract comments compliance — Rule 6 at ~50% (#23)~~ **DONE** — Compliance: 46%->91% (170/185 files)
23. ~~Update TECHNICAL.md — component count 61→74, add /dashboard/archive (#24)~~ **DONE**
24. ~~Fix ADMIN.md — correct endpoint count (#25)~~ **DONE** — Corrected "23+" to "20" endpoints, "21" to "20" pages

**P3 Medium — Frontend Components (COMPLETE — all 8 items):**
25. ~~LeadEnrichmentCard (#26)~~ **DONE** — Created with company info, contact details, SDK signals, icebreakers
26. ~~LeadActivityTimeline (#27)~~ **DONE** — Chronological timeline, channel filtering, activity icons, collapsible content
27. ~~LeadQuickActions (#28)~~ **DONE** — Created with 5 actions (email/call/sms/linkedin/note), tooltips, loading states
28. ~~LeadStatusProgress (#29)~~ **DONE** — Funnel visualization with 5 stages, size variants, optional labels, clickable stages
29. ~~LeadBulkActions (#30)~~ **DONE** — Bulk operations toolbar, campaign assignment, status updates, export
30. ~~Profile page (#31)~~ **DONE** — User profile with name/email/phone/timezone, avatar display, form validation
31. ~~Notifications page (#32)~~ **DONE** — Created with email/push/SMS/in-app toggles, digest frequency, alert categories
32. ~~Onboarding progress components (#33)~~ **DONE** — Created OnboardingProgress, OnboardingStep, OnboardingChecklist

**P5 Future (COMPLETE):**
33. ~~Create SECURITY.md (#34)~~ **DONE** — Created comprehensive security architecture documentation

---

## How to Continue

1. Read `ARCHITECTURE_DOC_SKILL.md` for template
2. **Follow Dev Review Process** (Steps 0-5) for each item
3. Update "Remaining Work" section after each item
4. Delete gap rows from "Open Gaps" when fixed
5. Report: "Completed [ITEM]. Ready for [NEXT]?"

---

*For full audit details, see `AUDIT_REPORT_2026-01-23.md`*
*For completed work history, see git commits*
