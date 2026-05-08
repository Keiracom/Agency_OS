# audit_phase2_aiden.md

**Submitted:** 2026-05-07
**Author:** Aiden
**Tasks:** A1 (frontend shipping audit), A2 (PR #609 spec vs reality), A3 (deprecated code inventory)

---

## A1 — Frontend Shipping Audit

Walking the frontend route-by-route. Status legend: WORKS (renders, functional logic visible) / PARTIAL (renders but stub-shaped or backend missing) / MISSING (route file does not exist or is hollow stub).

### Auth + landing
| Route | Lines | Status |
|---|---|---|
| `/(auth)/login` | 28 | PARTIAL (thin Supabase wrapper) |
| `/(auth)/signup` | 182 | PARTIAL (form exists, Stripe wiring unverified) |
| `/auth/callback` | exists | OAuth callback |
| `/(marketing)/{about,how-it-works,pricing}` | exists | Marketing |
| `/welcome` | exists | Post-signup |

### Onboarding (10 pages, ~3000 lines — see A2 for spec gap)
| Route | Lines | Status |
|---|---|---|
| `/onboarding` (root) | 12 | PARTIAL (redirect) |
| `/onboarding/step-1` | 309 | WORKS |
| `/onboarding/step-2` | 284 | WORKS |
| `/onboarding/step-3` | 319 | WORKS |
| `/onboarding/step-4` | 253 | WORKS |
| `/onboarding/step-5` | 305 | WORKS |
| `/onboarding/agency` | 613 | WORKS |
| `/onboarding/service-area` | 268 | WORKS |
| `/onboarding/crm` | 236 | WORKS |
| `/onboarding/linkedin` | 250 | WORKS |

### Dashboard (client-facing) — mixed substantial vs stub
| Route | Lines | Status |
|---|---|---|
| `/dashboard` (root) | 45 | PARTIAL (landing tiles only) |
| `/dashboard/activity` | 37 | PARTIAL (stub) |
| `/dashboard/approval` | 39 | PARTIAL (stub) |
| `/dashboard/archive` | 513 | WORKS |
| `/dashboard/campaigns` | 474 | WORKS |
| `/dashboard/campaigns/[id]` | 556 | WORKS |
| `/dashboard/campaigns/approval` | 332 | WORKS |
| `/dashboard/campaigns/new` | 575 | WORKS |
| `/dashboard/elliot` | 119 | PARTIAL |
| `/dashboard/inbox` | 13 | **MISSING** (stub) |
| `/dashboard/inbox/[id]` | 155 | PARTIAL (detail only, no index) |
| `/dashboard/leads` | 21 | **MISSING** (stub) |
| `/dashboard/leads/[id]` | 22 | PARTIAL (stub) |
| `/dashboard/meetings` | 159 | WORKS |
| `/dashboard/pipeline` | 212 | WORKS |
| `/dashboard/replies` | 12 | **MISSING** (stub) |
| `/dashboard/reports` | 181 | WORKS |
| `/dashboard/settings` | 373 | WORKS |
| `/dashboard/settings/icp` | 486 | WORKS |
| `/dashboard/settings/linkedin` | 235 | WORKS |
| `/dashboard/settings/notifications` | 619 | WORKS |
| `/dashboard/settings/profile` | 440 | WORKS |

### Top-level (parallel to dashboard)
| Route | Lines | Status |
|---|---|---|
| `/billing` | 59 | PARTIAL (Stripe price_ids=None per Max audit) |
| `/campaigns` | 90 | PARTIAL (duplicate-shape of dashboard route?) |
| `/leads` | 72 | PARTIAL (duplicate-shape of dashboard route?) |
| `/leads/[id]` | 59 | PARTIAL |
| `/replies` | 64 | PARTIAL (duplicate-shape of dashboard route?) |

### Admin (internal, agency-staff facing) — heavily built
20 admin routes, all 200-400 lines:
- `/admin` (308), `/admin/activity` (283), `/admin/campaigns` (197), `/admin/clients` (294), `/admin/clients/[id]` (387), `/admin/compliance` (252), `/admin/compliance/bounces` (279), `/admin/compliance/suppression` (278), `/admin/costs` (211), `/admin/costs/ai` (254), `/admin/costs/channels` (224), `/admin/leads` (226), `/admin/replies` (351), `/admin/revenue` (314), `/admin/settings` (234), `/admin/settings/users` (348), `/admin/system` (346), `/admin/system/errors` (285), `/admin/system/queues` (282), `/admin/system/rate-limits` (243)

All WORKS rating.

### A1 summary
- WORKS: ~32 routes (most onboarding, all admin, selected dashboard)
- PARTIAL: ~13 routes (auth, marketing, billing, top-level duplicates, dashboard sub-pages)
- MISSING (functional stubs): 4 critical client-facing routes — `dashboard/inbox`, `dashboard/leads`, `dashboard/replies`, `dashboard/activity`/`approval`

**Critical Phase 1 gap:** unified inbox + replies + leads list — the surfaces a paying client uses to actually run their outreach — are stubs (12-21 lines each).

**Asymmetry:** admin surface is disproportionately built (20 substantial routes) vs client dashboard (mix of substantial + stubs). Internal-tool-first build order.

---

## A2 — Onboarding Flow: PR #609 Spec vs Current Reality

### What PR #609 spec mandates (`docs/specs/onboarding_email_provisioning.md`, 170 lines, Variant A locked)

7 steps:
1. Marketing site: "Send your first cold email within 24 hours"
2. Signup form (<2 min): email, password, company name, ABN
3. Email Setup Dashboard — domain provisioning (Primeforge mailbox)
4. DNS verification — webhook-first SPF/DKIM/DMARC, polling fallback
5. Mailbox provisioning — Primeforge pre-warmed (vendor-claimed, pending API verification)
6. Self-test send to user's own email (gate before live prospect send)
7. First campaign test post-gate

Plus: free-trial 14d/45d/75d lifecycle, advanced settings toggle, transfer-on-churn.

### What current frontend has

10 pages, ~3,000 lines — agency-onboarding shape (CRM connect, LinkedIn account, service area, ICP, etc.)

### Spec keyword search across current onboarding pages

| Keyword | Files matching |
|---|---|
| `domain` | 0 |
| `DNS` | 0 |
| `SPF` | 0 |
| `DKIM` | 0 |
| `DMARC` | 0 |
| `Primeforge` | 0 |
| `mailbox provision` | 0 |
| `self-test` | 0 |
| `stripe` | 0 |

**Zero overlap** between PR #609 email-provisioning spec and existing onboarding code.

### Verdict

The current 10-page onboarding flow is a DIFFERENT flow shape (agency profile collection) from the PR #609 email-provisioning spec. PR #609 was merged to `docs/specs/` but no parallel frontend work was done.

If PR #609 ships as-specified, three options:
- (a) Existing 10-page flow REPLACED by 7-step email-provisioning flow (loses ~3,000 lines of agency-config UX)
- (b) PR #609 7-step ADDED as steps 6-12 of an extended onboarding (combined 17-step journey, very long)
- (c) PR #609 spec REVISED to integrate domain/DNS/mailbox into existing 10-page flow

This decision has not been made and is not currently in any task queue.

---

## A3 — Deprecated Code Inventory

Counts per vendor per Dave's deprecation list. Search method: `grep -rli --include="*.py" "<vendor>" src/`. Case-insensitive.

### Truly clean (0 references — fully removed)

| Vendor | Count |
|---|---|
| Apollo | 0 |
| Kaspr | 0 |
| Proxycurl | 0 |
| Webshare | 0 |
| Lemlist | 0 |

### References remaining

#### Hunter — 4 files (within §3 EXCEPTION clause)
- `src/orchestration/cohort_runner.py`
- `src/pipeline/email_waterfall.py`
- `src/intelligence/contact_waterfall.py`
- `src/config/stage_parallelism.py`

ARCHITECTURE.md §3 EXCEPTION: "Hunter email-finder active in Pipeline F v2.1 as L2 email fallback (score >= 70)." All 4 references appear consistent with the exception. Score-gate enforcement not directly verified.

#### Apify — 2 files (within §3 EXCEPTION clause)
- `src/intelligence/contact_waterfall.py`
- `src/config/stage_parallelism.py`

ARCHITECTURE.md §3 EXCEPTION: "Apify harvestapi/linkedin-profile-scraper active in Pipeline F v2.1 for L2 LinkedIn verification. Apify facebook-posts-scraper active for Stage 9 social." References appear consistent.

#### Smartlead — 6 files (DEPRECATED, references NOT cleaned)
- `src/integrations/smartlead_mcp.py`
- `src/services/domain_pool_manager.py`
- `src/services/email_events_service.py`
- `src/api/routes/webhooks.py`
- `src/config/email_costs.py`
- `src/config/settings.py`

Smartlead added to ARCHITECTURE.md §3 deprecated list in PR #603 (this session). 6 files still reference it. **Layer 7.X follow-up cleanup candidate** — same shape as Siege Waterfall PR #611 just-merged.

#### Vapi — 15 files (AMBIGUOUS — needs Dave clarification)
- `src/integrations/vapi.py` (21.8KB active)
- `src/integrations/elevenlabs.py`, `src/integrations/__init__.py`
- `src/engines/deprecated/voice_vapi.py` (already in deprecated/ subdir ✓)
- `src/engines/voice_agent_telnyx.py`, `src/engines/sms.py`
- `src/services/{phone_provisioning_service,voice_context_builder,voice_compliance_validator,recording_cleanup_service}.py`
- `src/orchestration/tasks/outreach_tasks.py`
- `src/orchestration/flows/{voice_flow,recording_cleanup_flow}.py`
- `src/api/routes/webhooks.py`
- `src/config/settings.py`

Vapi is NOT listed in ARCHITECTURE.md §4 LIVE VENDORS (which lists ElevenAgents for Voice AI). One file is in `deprecated/`. The other 14 active references suggest:
- (a) Vapi still in active use (not actually deprecated despite Dave's list), OR
- (b) Genuinely deprecated and 14 files have stale references needing cleanup

**Cannot determine from code-only audit. Needs Dave clarification.**

### A3 totals

| Vendor | Files | Verdict |
|---|---|---|
| Apollo | 0 | Clean |
| Kaspr | 0 | Clean |
| Proxycurl | 0 | Clean |
| Webshare | 0 | Clean |
| Lemlist | 0 | Clean |
| Hunter | 4 | Consistent with §3 EXCEPTION |
| Apify | 2 | Consistent with §3 EXCEPTION |
| Smartlead | 6 | DEPRECATED — references not cleaned (Layer 7.X candidate) |
| Vapi | 15 | AMBIGUOUS — needs Dave clarification on deprecation status |

**Net cleanup work identified:** Smartlead (6 files), Vapi (potentially 14 files if confirmed deprecated). Total ~20 files of potential dead-reference cleanup.

---

## End of report
