# Architecture TODO

**Purpose:** Track gaps, priorities, and rules for architecture work.
**Last Updated:** 2026-01-22
**Skill:** See `ARCHITECTURE_DOC_SKILL.md` for templates and checklists.

---

## Current Status (Session Resumption)

**Read this section first when starting a new session.**

### Where We Are
- **Phase:** Phase D — Code Fixes — IN PROGRESS
- **Last Completed:** Item 18 (Campaign evolution agents)
- **Next Action:** Item 19-23 (remaining code fixes), Phase E (METRICS.md), Phase F (Frontend UI docs), or Phase H (Transparency)

### Key Decisions Made
1. **47 total items** — 12 docs created, 3 verified, 6 docs to create, 10 to verify, 11 code fixes, 8 transparency features
2. **Two scraper systems** — ICP scraper (onboarding) vs Lead enrichment (Apollo→Apify→Clay)
3. **METRICS.md** combines Analytics + Spend Control (Phase E)
4. **SDK_AND_PROMPTS.md** — Expand existing, don't create new SMART_PROMPTS.md
5. **ADMIN.md** — Moved to `frontend/ADMIN.md` (spans backend + frontend)
6. **Hybrid approach** — Document area, then fix related P1/P2 issues in that area
7. **Credit reset** — Fixed immediately (P0)
8. **Post-onboarding flow** — Defer fix until after CAMPAIGNS.md. Reason: `pool_population_flow` and `post_onboarding_setup_flow` overlap on lead sourcing. Need ENRICHMENT.md + CAMPAIGNS.md context to choose between: (A) replace pool_population entirely, (B) skip sourcing if done, (C) keep flows separate.
9. **Content hallucination risk** — Claude can hallucinate facts not in source data. Solution: Claude fact-check gate (~$0.01/email) + conservative prompt + safe fallback
10. **Client transparency** — Automated outreach stays automated, but client sees everything via: Emergency Pause, Daily Digest, Live Feed, Archive, Best Of Showcase

### Doc Creation Order (Reconciled)
```
Phase A (Core Flows) — 5 docs:
  1. flows/ONBOARDING.md      ✓ CREATED
  2. flows/ENRICHMENT.md      ✓ CREATED
  3. flows/OUTREACH.md        ✓ CREATED
  4. flows/MEETINGS_CRM.md    ✓ CREATED
  5. business/CIS.md          ✓ CREATED

Phase B (Business & Infrastructure) — 4 docs:
  6. business/CAMPAIGNS.md           ✓ CREATED
  7. foundation/API_LAYER.md         ✓ CREATED
  8. foundation/DATABASE.md          ✓ CREATED
  9. distribution/SCRAPER_WATERFALL.md ✓ CREATED

Phase C (Process) — 1 doc + 1 frontend:
  10. process/FRONTEND.md     ✓ CREATED (moved to frontend/TECHNICAL.md)
  11. frontend/ADMIN.md       ✓ CREATED

Expand existing (not new doc):
  - content/SDK_AND_PROMPTS.md — add Smart Prompts content

Phase D (Code Fixes) — remaining items after docs:
  - DNCR wiring, LinkedIn warmup, daily pacing

Phase E (Nice to Have) — 1 doc:
  12. business/METRICS.md (Analytics + Spend Control combined)

Phase F (Frontend UI Docs) — 5 docs:
  13. frontend/DASHBOARD.md   — Client dashboard, KPIs, reports
  14. frontend/CAMPAIGNS.md   — Campaign list, detail, sequences
  15. frontend/LEADS.md       — Lead list, detail, ALS display
  16. frontend/SETTINGS.md    — ICP, LinkedIn, client settings
  17. frontend/ONBOARDING.md  — Onboarding flow pages

Then: Verify 13 existing docs (Phase G)
```

### How to Continue
1. Read `ARCHITECTURE_DOC_SKILL.md` for template
2. **Follow Dev Review Process for EACH file** (Steps 0-5)
3. Create doc, then fix related P1/P2 issues in that area
4. Update this "Current Status" section after each doc
5. Mark completed in "Next Actions" section below

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
| Gap description | TODO.md "Identified Gaps" table | Architecture docs |
| Gap status | TODO.md "Identified Gaps" table | Architecture docs |
| Gap priority | TODO.md "Identified Gaps" table | Architecture docs |
| Fix sequence | TODO.md "Next Actions" section | Scattered inline notes |
| Decision rationale | TODO.md "Key Decisions" section | Multiple places |

### Rules

1. **NO "Known Gaps" sections in architecture docs** — Docs describe what IS, not what's missing
2. **NO gap indicators in ARCHITECTURE_INDEX.md** — Index is navigation only
3. **NO duplicate gap entries** — One entry per gap in the Identified Gaps table
4. **Fix sequence in Next Actions ONLY** — Not scattered in Doc Creation Order
5. **When gap is fixed** — Delete the row from Identified Gaps, that's it

### Architecture Doc Footer

Every architecture doc ends with:
```
---
For gaps and implementation status, see `../TODO.md`.
```

### Why This Rule

- **Single update point** — Fix a gap, update one place
- **No stale references** — Can't forget to update scattered mentions
- **Clear ownership** — TODO.md owns gaps, architecture docs own specs

---

## Decisions Pending CEO Approval

**Rule:** Any architecture decision that requires judgment (not just documenting what exists) needs CEO sign-off before implementation.

| # | Decision | Options | Recommendation | Doc | Status |
|---|----------|---------|----------------|-----|--------|
| 1 | Default replenishment mode | `full` / `smart` / `manual` | `smart` | MONTHLY_LIFECYCLE.md | PENDING |
| 2 | Auto-apply campaign suggestions | Yes / No (require approval) | No | MONTHLY_LIFECYCLE.md | PENDING |
| 3 | Min conversions for CIS refinement | 10 / 20 / 50 | 20 | MONTHLY_LIFECYCLE.md | PENDING |
| 4 | Campaign pause threshold | 0.5% / 1% / 2% reply rate | 1% after 100 leads | MONTHLY_LIFECYCLE.md | PENDING |
| 5 | Lead carryover to month 2 | All / Active only / None | Active only | MONTHLY_LIFECYCLE.md | PENDING |

**Process:**
1. Dev Team adds decision to this table with recommendation
2. CEO reviews and approves/modifies
3. Decision marked APPROVED with date
4. Implementation proceeds

---

## Identified Gaps

### Priority 1: Critical (Blocking Core Functionality)

| Gap | Location | Status | Notes |
|-----|----------|--------|-------|
| ~~Credit reset flow~~ | `business/TIERS_AND_BILLING.md` | **FIXED** | Implemented in P0 — see `credit_reset_flow.py` |
| ~~Post-onboarding flow not wired~~ | `flows/ONBOARDING.md` | **FIXED** | `/confirm` now calls `post_onboarding_setup_flow` which handles campaigns, lead sourcing, and assignment |
| ALS check at SMS execution | `business/SCORING.md` | **FIXED** | Added hard check in `outreach_flow.py:520` — ALS >= 85 required |
| ALS check at Voice execution | `business/SCORING.md` | **OK** | Hard check in `voice.py:236` requires ALS >= 70 |
| `get_available_channels()` unused | `business/SCORING.md` | **FIXED** | Added `get_available_channels_enum()` to tiers.py, refactored enrichment_flow.py to use it |
| Claude fact-check gate | `content/SDK_AND_PROMPTS.md` | NOT IMPLEMENTED | Verify content against source data before send — prevents hallucination |
| Conservative prompt update | `content/SDK_AND_PROMPTS.md` | NOT IMPLEMENTED | Instruct Claude to only use verified facts, never assume |
| Safe fallback template | `content/SDK_AND_PROMPTS.md` | NOT IMPLEMENTED | Brand-safe template when AI fails fact-check twice |
| Emergency Pause Button | `frontend/DASHBOARD.md` | NOT IMPLEMENTED | Client can pause all outreach instantly from dashboard |
| Daily Digest Email | `flows/TRANSPARENCY.md` | NOT IMPLEMENTED | Automated email summary of content sent + metrics |

### Priority 2: Important (Should Fix Soon)

| Gap | Location | Status | Notes |
|-----|----------|--------|-------|
| ~~Daily pacing flow~~ | `business/TIERS_AND_BILLING.md` | **FIXED** | `daily_pacing_flow.py` + 7 AM AEST schedule + >120%/<50% alerts |
| ~~Monthly replenishment flow~~ | `flows/MONTHLY_LIFECYCLE.md` | **FIXED** | `monthly_replenishment_flow.py` + credit_reset trigger + gap calculation |
| ~~Campaign evolution agents~~ | `flows/MONTHLY_LIFECYCLE.md` | **FIXED** | WHO/WHAT/HOW analyzers + orchestrator → campaign_suggestions table |
| ICP refinement from CIS | `flows/MONTHLY_LIFECYCLE.md` | NOT IMPLEMENTED | WHO patterns not used to refine Apollo search |
| ~~DNCR wiring~~ | `distribution/SMS.md` | **FIXED** | Batch wash at enrichment + cached check at send + quarterly re-wash |
| ~~LinkedIn seat warmup~~ | `distribution/LINKEDIN.md` | **FIXED** | Warmup service + health service + daily flow created |
| ~~Reply handling~~ | `flows/REPLY_HANDLING.md` | **PARTIAL** | Migration 046 + 10 intents + response timing. Remaining: SMS/LinkedIn webhooks |
| Two-way CRM sync | `flows/MEETINGS_CRM.md` | NOT IMPLEMENTED | Pull meetings from CRM to capture blind conversions |
| Frontend hardcoded values | `process/FRONTEND.md` | GAP | credits_remaining=2250, leads_contacted hardcoded |
| Content QA check | `flows/OUTREACH.md` | NOT IMPLEMENTED | No validation before send (length, placeholders, spam) |
| Smart Prompt priority | `content/SDK_AND_PROMPTS.md` | NOT IMPLEMENTED | No weighting of which lead data to prioritize |
| Live Activity Feed | `frontend/DASHBOARD.md` | NOT IMPLEMENTED | Real-time outreach stream visible to client |
| Content Archive | `frontend/DASHBOARD.md` | NOT IMPLEMENTED | Searchable archive of all sent content |

### Priority 3: Documentation (Architecture Docs Needed)

**P3-A: Missing Core Flow Docs**

| Gap | Location | Status | Code Exists | Notes |
|-----|----------|--------|-------------|-------|
| Onboarding flow | `flows/ONBOARDING.md` | **CREATED** | YES | onboarding_flow.py, post_onboarding_flow.py, icp_scraper.py |
| Conversion Intelligence | `business/CIS.md` | **CREATED** | YES | 5 detectors + weight_optimizer in src/detectors/ |
| Meetings & CRM | `flows/MEETINGS_CRM.md` | **CREATED** | YES | meeting_service.py, crm_push_service.py, deal_service.py |
| Outreach execution | `flows/OUTREACH.md` | **CREATED** | YES | outreach_flow.py, outreach_tasks.py, JIT validation |
| Campaign lifecycle | `business/CAMPAIGNS.md` | **CREATED** | YES | campaign_flow.py, campaign_suggester.py |

**P3-B: Missing Infrastructure Docs**

| Gap | Location | Status | Code Exists | Notes |
|-----|----------|--------|-------------|-------|
| Enrichment waterfall | `flows/ENRICHMENT.md` | **CREATED** | YES | Apollo → Apify → Clay in scout.py |
| API layer | `foundation/API_LAYER.md` | **CREATED** | YES | 17 route files, auth, multi-tenancy |
| Database/models | `foundation/DATABASE.md` | **CREATED** | YES | 22 models, soft deletes, migrations |
| Scraper waterfall | `distribution/SCRAPER_WATERFALL.md` | **CREATED** | YES | Cheerio → Playwright → Camoufox |

**P3-C: Missing Content/Process Docs**

| Gap | Location | Status | Code Exists | Notes |
|-----|----------|--------|-------------|-------|
| ~~Smart Prompts~~ | `content/SDK_AND_PROMPTS.md` | **EXPANDED** | YES | Code locations, data flows, context builders documented |
| ~~Frontend architecture~~ | `frontend/TECHNICAL.md` | **CREATED** | YES | 42 pages, 61 components, React Query |

**P3-D: Missing Frontend UI Docs**

| Gap | Location | Status | Code Exists | Notes |
|-----|----------|--------|-------------|-------|
| Client Dashboard | `frontend/DASHBOARD.md` | NOT CREATED | YES | 11 dashboard pages, KPIs, reports |
| Campaign UI | `frontend/CAMPAIGNS.md` | NOT CREATED | YES | Campaign list, detail, sequences |
| Lead UI | `frontend/LEADS.md` | NOT CREATED | YES | Lead list, detail, ALS display |
| Settings UI | `frontend/SETTINGS.md` | NOT CREATED | YES | ICP, LinkedIn, client settings |
| Onboarding UI | `frontend/ONBOARDING.md` | NOT CREATED | YES | 4 onboarding flow pages |

### Priority 4: Nice to Have

| Gap | Location | Status | Notes |
|-----|----------|--------|-------|
| Analytics + Spend Control | `business/METRICS.md` | MISSING DOC | Combines reporter.py, AI spend limiter, SDK cost tracking |
| ~~Admin panel~~ | `frontend/ADMIN.md` | **CREATED** | 23+ endpoints, 21 pages documented |
| Direct mail | `distribution/MAIL.md` | NOT IMPLEMENTED | Spec exists, no code |
| "Best Of" Showcase | `frontend/DASHBOARD.md` | NOT IMPLEMENTED | Display high-performing content examples to client |

### Priority 5: Future Consideration

| Gap | Location | Status | Notes |
|-----|----------|--------|-------|
| Security architecture | `foundation/SECURITY.md` | MISSING DOC | Auth, RBAC, API keys, data encryption, audit logging |

---

## Existing Architecture Files — ALL VERIFIED ✓

All 13 pre-existing architecture files have been verified against codebase (Phase G complete).

| File | Status | Action Taken |
|------|--------|--------------|
| `foundation/DECISIONS.md` | ✅ VERIFIED | Added Email (Salesforge) + LinkedIn (Unipile) providers |
| `foundation/IMPORT_HIERARCHY.md` | ✅ VERIFIED | Enforced in code — confirmed by audit |
| `foundation/RULES.md` | ✅ VERIFIED | Followed — confirmed by audit |
| `foundation/FILE_STRUCTURE.md` | ✅ UPDATED | Complete rewrite with 135+ src files, 41 migrations |
| `distribution/INDEX.md` | ✅ VERIFIED | Fixed file names, added SCRAPER_WATERFALL.md |
| `distribution/EMAIL.md` | ✅ VERIFIED | Updated status to IMPLEMENTED, fixed file locations |
| `distribution/SMS.md` | ✅ VERIFIED | Accurate, DNCR gap tracked in item 13 |
| `distribution/VOICE.md` | ✅ VERIFIED | Stack documented correctly (Vapi + Twilio + ElevenLabs) |
| `distribution/LINKEDIN.md` | ✅ VERIFIED | Updated Current State, models/services exist |
| `distribution/MAIL.md` | ✅ VERIFIED | Confirmed SPEC ONLY status |
| `distribution/RESOURCE_POOL.md` | ✅ VERIFIED | Updated to PARTIALLY IMPLEMENTED, service exists |
| `flows/REPLY_HANDLING.md` | ✅ VERIFIED | Updated to PARTIALLY IMPLEMENTED, closer.py + reply_analyzer exist |
| `content/SDK_AND_PROMPTS.md` | ✅ VERIFIED | Previously expanded with code locations

---

## Codebase Audit Results (2026-01-21)

**Full codebase audit completed. 176+ files across 8 layers.**

### Layer 1: Models (22 files)
| File | Purpose | Doc Needed |
|------|---------|------------|
| base.py | Base classes, enums, mixins | `foundation/DATABASE.md` |
| user.py, client.py, membership.py | Multi-tenancy, RBAC | `foundation/DATABASE.md` |
| campaign.py, lead.py, activity.py | Core business objects | `foundation/DATABASE.md` |
| lead_pool.py | Platform lead repository | `flows/ENRICHMENT.md` |
| conversion_patterns.py | CIS pattern storage | `business/CIS.md` |
| resource_pool.py, client_persona.py | Resource distribution | `distribution/RESOURCE_POOL.md` |
| linkedin_*.py (4 files) | LinkedIn models | `distribution/LINKEDIN.md` |
| client_intelligence.py, sdk_usage_log.py | SDK/intelligence | `content/SMART_PROMPTS.md` |

### Layer 2: Integrations (22 files)
| File | Purpose | Doc Needed |
|------|---------|------------|
| apollo.py, apify.py, clay.py | Enrichment waterfall | `flows/ENRICHMENT.md` |
| salesforge.py, resend.py, postmark.py | Email providers | `distribution/EMAIL.md` |
| clicksend.py, twilio.py, dncr.py | SMS providers + DNCR | `distribution/SMS.md` |
| vapi.py, elevenlabs.py | Voice AI | `distribution/VOICE.md` |
| unipile.py, heyreach.py | LinkedIn automation | `distribution/LINKEDIN.md` |
| camoufox_scraper.py | Anti-detection scraper | `distribution/SCRAPER_WATERFALL.md` |
| anthropic.py, sdk_brain.py | AI/Claude | `content/SMART_PROMPTS.md` |
| redis.py, supabase.py | Cache, database | `foundation/DATABASE.md` |
| sentry_utils.py | Error tracking | `foundation/API_LAYER.md` |

### Layer 3: Engines (20 files)
| File | Purpose | Doc Needed |
|------|---------|------------|
| email.py, sms.py, voice.py, linkedin.py, mail.py | Outreach engines | `flows/OUTREACH.md` |
| scout.py | Enrichment waterfall | `flows/ENRICHMENT.md` |
| scorer.py, allocator.py | ALS + channel allocation | `business/SCORING.md` |
| content.py, smart_prompts.py, content_utils.py | Content generation | `content/SDK_AND_PROMPTS.md` |
| closer.py | Reply handling | `flows/REPLY_HANDLING.md` |
| icp_scraper.py, url_validator.py | Scraper waterfall | `distribution/SCRAPER_WATERFALL.md` |
| reporter.py | Metrics | `business/METRICS.md` |
| client_intelligence.py, campaign_suggester.py | Intelligence | `flows/ONBOARDING.md` |
| timing.py | Humanized delays | `distribution/LINKEDIN.md` |

### Layer 3: Detectors (8 files)
| File | Purpose | Doc Needed |
|------|---------|------------|
| base.py | Abstract detector base | `business/CIS.md` |
| who_detector.py | Lead attributes that convert | `business/CIS.md` |
| what_detector.py | Content patterns that convert | `business/CIS.md` |
| when_detector.py | Timing patterns that convert | `business/CIS.md` |
| how_detector.py | Channel effectiveness | `business/CIS.md` |
| funnel_detector.py | Downstream outcomes | `business/CIS.md` |
| weight_optimizer.py | ALS weight optimization | `business/CIS.md` |

### Layer 3: Services (22 files)
| File | Purpose | Doc Needed |
|------|---------|------------|
| lead_pool_service.py, lead_allocator_service.py | Lead pool CRUD + allocation | `flows/ENRICHMENT.md` |
| jit_validator.py, suppression_service.py | Pre-send validation | `flows/OUTREACH.md` |
| customer_import_service.py, buyer_signal_service.py | Customer data | `business/CAMPAIGNS.md` |
| resource_assignment_service.py | Resource assignment | `distribution/RESOURCE_POOL.md` |
| domain_health_service.py, domain_capacity_service.py | Email domain health | `distribution/EMAIL.md` |
| sequence_generator_service.py | Auto-generate sequences | `flows/AUTOMATION_DEFAULTS.md` |
| timezone_service.py | Recipient timezone | `flows/OUTREACH.md` |
| email_events_service.py, thread_service.py | Email events + threading | `distribution/EMAIL.md` |
| reply_analyzer.py, conversation_analytics_service.py | Reply analysis | `flows/REPLY_HANDLING.md` |
| crm_push_service.py, meeting_service.py, deal_service.py | CRM + meetings | `flows/MEETINGS_CRM.md` |
| linkedin_connection_service.py | LinkedIn tracking | `distribution/LINKEDIN.md` |
| send_limiter.py, sdk_usage_service.py | Rate/cost limiting | `business/METRICS.md` |

### Layer 4: Orchestration (23 files)
| File | Purpose | Doc Needed |
|------|---------|------------|
| campaign_flow.py | Campaign activation | `business/CAMPAIGNS.md` |
| enrichment_flow.py, lead_enrichment_flow.py | Lead enrichment | `flows/ENRICHMENT.md` |
| onboarding_flow.py, post_onboarding_flow.py | Onboarding | `flows/ONBOARDING.md` |
| outreach_flow.py | Hourly outreach | `flows/OUTREACH.md` |
| pattern_learning_flow.py, pattern_backfill_flow.py | CIS patterns | `business/CIS.md` |
| pool_assignment_flow.py, pool_population_flow.py | Lead pool | `flows/ENRICHMENT.md` |
| reply_recovery_flow.py | Reply polling | `flows/REPLY_HANDLING.md` |
| stale_lead_refresh_flow.py | Data freshness | `flows/ENRICHMENT.md` |
| intelligence_flow.py | Hot lead research | `flows/ONBOARDING.md` |
| tasks/*.py (4 files) | Reusable tasks | Various |
| schedules/scheduled_jobs.py | Prefect schedules | `foundation/DECISIONS.md` |

### Layer 5: API Routes (17 files)
| File | Purpose | Doc Needed |
|------|---------|------------|
| main.py, dependencies.py | App entry, auth | `foundation/API_LAYER.md` |
| health.py | Health checks | `foundation/API_LAYER.md` |
| admin.py | Platform admin | `frontend/ADMIN.md` |
| leads.py, campaigns.py | Core CRUD | `foundation/API_LAYER.md` |
| webhooks.py, webhooks_outbound.py | Inbound/outbound hooks | `foundation/API_LAYER.md` |
| reports.py, patterns.py | Metrics + CIS | `business/ANALYTICS.md` |
| replies.py, meetings.py | Reply inbox + meetings | `flows/MEETINGS_CRM.md` |
| crm.py, customers.py | CRM integration | `flows/MEETINGS_CRM.md` |
| onboarding.py | ICP extraction | `flows/ONBOARDING.md` |
| linkedin.py, pool.py | LinkedIn + pool | `distribution/LINKEDIN.md` |

### Frontend (42 pages, 68 components, 11 hooks)
| Area | Files | Doc Needed |
|------|-------|------------|
| app/(auth)/, app/(marketing)/ | Public + auth pages | `process/FRONTEND.md` |
| app/dashboard/ | Client dashboard | `process/FRONTEND.md` |
| app/admin/ | Admin dashboard | `frontend/ADMIN.md` |
| app/onboarding/ | Onboarding flow | `process/FRONTEND.md` |
| components/ui/ | 20 shadcn/ui components | `process/FRONTEND.md` |
| hooks/ | 11 React Query hooks | `process/FRONTEND.md` |
| lib/api/ | 9 API modules | `process/FRONTEND.md` |

---

## Completed Items

| Item | Completed | Notes |
|------|-----------|-------|
| Create `business/TIERS_AND_BILLING.md` | 2026-01-21 | Tiers, credits, pacing documented |
| Create `business/SCORING.md` | 2026-01-21 | ALS formula, channel access documented |
| Restructure architecture folder | 2026-01-21 | 6 subfolders created |
| Update ARCHITECTURE_INDEX.md | 2026-01-21 | Pure navigation with bullet summaries |
| Create TODO.md | 2026-01-21 | This file |
| Partial codebase audit | 2026-01-21 | CIS, Onboarding, CRM/Meetings discovered |
| **FULL codebase audit** | 2026-01-21 | **176+ files across 8 layers audited** |
| Reconcile TODO.md | 2026-01-21 | Fixed doc ordering inconsistencies, clarified 12 docs |
| **P0: Credit reset flow** | 2026-01-21 | `credit_reset_flow.py` + hourly schedule in registry |
| **Create flows/ONBOARDING.md** | 2026-01-21 | 3 phases documented: ICP extraction, resource assignment, post-onboarding |
| **Create flows/ENRICHMENT.md** | 2026-01-21 | Three-tier waterfall (Apollo→Apify→Clay), SDK enhancement, pool operations |
| **Create flows/OUTREACH.md** | 2026-01-21 | Multi-channel execution, JIT validation, rate limits, SDK routing |
| **Create flows/MEETINGS_CRM.md** | 2026-01-21 | Meeting lifecycle, deal pipeline, HubSpot/Pipedrive/Close CRM push |
| **Create business/CIS.md** | 2026-01-21 | 5 detectors, weight optimizer, pattern learning flow |
| **Create business/CAMPAIGNS.md** | 2026-01-21 | Campaign lifecycle, AI suggestions, lead allocation, sequences |
| **Create foundation/API_LAYER.md** | 2026-01-21 | 17 routes, auth/RBAC, multi-tenancy, webhooks, error handling |
| **Create foundation/DATABASE.md** | 2026-01-21 | 22 models, mixins, soft deletes, migrations, Layer 1 rules |
| **Create distribution/SCRAPER_WATERFALL.md** | 2026-01-21 | 4-tier scraping: URL validation → Cheerio → Playwright → Camoufox |
| **P1: Wire post-onboarding flow** | 2026-01-21 | `/confirm` now calls `post_onboarding_setup_flow` for campaigns + lead sourcing + assignment |
| **Create flows/MONTHLY_LIFECYCLE.md** | 2026-01-21 | Month 2+ lifecycle: replenishment, campaign evolution, CIS-informed refinement |
| **Create process/FRONTEND.md** | 2026-01-22 | 42 pages, 61 components, React Query, state patterns, API layer |
| **Create frontend/ADMIN.md** | 2026-01-22 | 23+ endpoints, 21 pages, platform admin panel |
| **Expand SDK_AND_PROMPTS.md** | 2026-01-22 | Code locations, data flows, context builders, SDK routing |
| **P2: Wire DNCR check before SMS send** | 2026-01-22 | Batch wash at enrichment, cached check at send, quarterly re-wash flow created |
| **P2: Implement LinkedIn seat warmup service** | 2026-01-22 | Warmup service, health service, daily health flow, scheduled job |
| **P2: Implement daily pacing flow** | 2026-01-22 | `daily_pacing_flow.py` (465 lines), schedule at 7 AM AEST, flags >120% fast / <50% slow |
| **P2: Implement reply handling code** | 2026-01-22 | Migration 046 (lead_replies table), 3 new intents (referral, wrong_person, angry_or_complaint), response timing service |
| **P2: Implement monthly replenishment flow** | 2026-01-22 | `monthly_replenishment_flow.py`, gap calculation (Tier Quota - Active Pipeline), campaign assignment, credit_reset_flow trigger |
| **P2: Implement campaign evolution agents** | 2026-01-22 | WHO/WHAT/HOW analyzers + orchestrator agent, migration 047 (campaign_suggestions table), Prefect flow + batch flow, confidence thresholds |

---

## Next Actions (Priority Order)

### Phase A: Core Flow Docs (5 docs) - COMPLETE
1. [x] Create `flows/ONBOARDING.md`
2. [x] Create `flows/ENRICHMENT.md`
3. [x] Create `flows/OUTREACH.md` — P1 ALS checks verified OK, `get_available_channels()` still needs fix
4. [x] Create `flows/MEETINGS_CRM.md`
5. [x] Create `business/CIS.md`

### Phase B: Business & Infrastructure Docs (4 docs) - COMPLETE
6. [x] Create `business/CAMPAIGNS.md`
7. [x] Create `foundation/API_LAYER.md`
8. [x] Create `foundation/DATABASE.md`
9. [x] Create `distribution/SCRAPER_WATERFALL.md`

### Phase C: Process Docs (2 docs) - COMPLETE
10. [x] Create `process/FRONTEND.md` → then fix P2: Frontend hardcoded values
11. [x] Create `frontend/ADMIN.md` (moved from process/)

### Expand Existing
12. [x] Expand `content/SDK_AND_PROMPTS.md`

### Phase D: Remaining Code Fixes (ALL P2 Gaps)
13. [x] P2: Wire DNCR check before SMS send — **DONE** (batch wash at enrichment, cached check at send, quarterly re-wash flow)
14. [x] P2: Implement LinkedIn seat warmup service — **DONE** (warmup service, health service, daily health flow)
15. [x] P2: Implement daily pacing flow — **DONE** (`daily_pacing_flow.py`, 7 AM AEST schedule, >120%/<50% alerts)
16. [x] P2: Implement reply handling code — **DONE** (migration 046, 10 intents, response timing service, remaining: SMS/LinkedIn webhooks)
17. [x] P2: Implement monthly replenishment flow — **DONE** (`monthly_replenishment_flow.py`, gap calculation, campaign assignment, credit_reset trigger)
18. [x] P2: Implement campaign evolution agents — **DONE** (WHO/WHAT/HOW analyzers, orchestrator, campaign_suggestions table, Prefect flow)
19. [ ] P2: Implement ICP refinement from CIS
20. [ ] P2: Implement two-way CRM sync
21. [ ] P2: Fix frontend hardcoded values
22. [ ] P2: Add content QA check node in outreach flow
23. [ ] P2: Add priority weighting to Smart Prompt

### Phase E: Nice to Have (1 doc)
24. [ ] Create `business/METRICS.md` — Reporter engine, analytics, spend control combined

### Phase F: Frontend UI Docs (5 docs)
25. [ ] Create `frontend/DASHBOARD.md` — Client dashboard, KPIs, reports
26. [ ] Create `frontend/CAMPAIGNS.md` — Campaign list, detail, sequences UI
27. [ ] Create `frontend/LEADS.md` — Lead list, detail, ALS display
28. [ ] Create `frontend/SETTINGS.md` — ICP, LinkedIn, client settings
29. [ ] Create `frontend/ONBOARDING.md` — 4 onboarding flow pages

### Phase G: Verify Existing Docs (10 items — 3 already verified)

*Already verified:* `foundation/IMPORT_HIERARCHY.md` ✓, `foundation/RULES.md` ✓, `content/SDK_AND_PROMPTS.md` ✓

30. [x] Verify `foundation/DECISIONS.md` — added Email (Salesforge) + LinkedIn (Unipile) providers
31. [x] UPDATE `foundation/FILE_STRUCTURE.md` — complete rewrite with 135+ src files, 41 migrations
32. [x] Verify `distribution/INDEX.md` — fixed file names, added SCRAPER_WATERFALL.md, updated providers
33. [x] Verify `distribution/EMAIL.md` — updated status to IMPLEMENTED, fixed file locations
34. [x] Verify `distribution/SMS.md` — accurate, DNCR gap already tracked in item 13
35. [x] Verify `distribution/VOICE.md` — comprehensive, stack documented correctly
36. [x] Verify `distribution/LINKEDIN.md` — updated Current State, models/services exist
37. [x] Verify `distribution/MAIL.md` — confirmed SPEC ONLY status
38. [x] Verify `distribution/RESOURCE_POOL.md` — updated status to PARTIALLY IMPLEMENTED, documented existing service
39. [x] Verify `flows/REPLY_HANDLING.md` — updated status to PARTIALLY IMPLEMENTED, documented closer.py + reply_analyzer

### Phase H: Client Transparency (Brand Safety + Visibility)
40. [ ] P1: Implement Claude fact-check gate in outreach flow
41. [ ] P1: Update SMART_EMAIL_PROMPT with conservative instructions
42. [ ] P1: Create safe fallback template for fact-check failures
43. [ ] P1: Add Emergency Pause Button to dashboard (client-facing)
44. [ ] P1: Implement Daily Digest Email (content summary + metrics)
45. [ ] P2: Build Live Activity Feed component (real-time outreach stream)
46. [ ] P2: Create Content Archive page (all sent content, searchable)
47. [ ] P3: Build "Best Of" Showcase (high-performing content examples)
