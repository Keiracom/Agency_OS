# F2.1 Evidence Audit — Converged Final

**Date:** 2026-04-20
**Auditors:** Elliot (Build-2, claude-sonnet-4-6) + Aiden (Build-3, claude-sonnet-4-6), independent drafts converged
**Directive:** F21-EVIDENCE-AUDIT
**Methodology:** Desk audit only. No new tests executed. All claims sourced from four validation runs (D2 / D2.2 / F-REFACTOR-01 / 100-domain smoke), two formal audits (D1.2 seam audit, D2 pipeline audit at `research/d2_audit/PIPELINE_AUDIT_MASTER.md`), and direct code inspection of `pipeline_orchestrator.py`, `src/intelligence/`, outreach modules, and `src/pipeline/mobile_waterfall.py` HEAD. Confidence is capped at the evidence supplied — where no run, commit, or test covers a path, classification is UNTESTED regardless of code presence. Felt-sufficiency rule applied: every claim is cited against a specific file, run ID, commit SHA, or ceo_memory key.
**Divergence resolution rule:** where Elliot and Aiden classified a stage differently, this document takes the more cautious classification. All divergences are noted and resolved on-record in Appendix A.

---

## 1. TL;DR Verdict

**NOT SHIPPABLE to first paying customer based on existing evidence.**

Pipeline core is GREEN on a clean SMB cohort with the 2026-04-16-era provider stack (D2.2: 83% post-SMB-clean conversion, $0.26 AUD/card). Today's operational reality is more constrained: ContactOut exhausted, Hunter dead, three critical audit findings unresolved on HEAD, and the outreach stack has zero E2E evidence. Bounded remediation path exists — 2–3 engineering sessions plus Dave decisions — without architecture redesign.

**Ship-gating conditions (must resolve before any live customer send):**

1. ~~Three D2-CRITICAL audit findings unresolved on HEAD~~ **CORRECTED 2026-04-21 via PR #363 (merge 6c39458a):** only the mobile waterfall client pass-through (Fix 1) required new code — shipped in PR #363. Felt-sufficiency check during directive F21-CRITICAL-3-FIX prep revealed the other two findings were already resolved in PR #336 (merged 2026-04-16): `{{agency_name}}` token substitution and Hunter dm_verified runtime conditional. PR #363 added six lock-in tests (3 per finding) to prevent silent regression. B7 is now CLOSED.
2. Provider collapse: ContactOut exhausted (email + phone + search all dead), Hunter 401 auth failure. Effective email waterfall reduced from six layers to two; effective mobile waterfall to one partial layer.
3. Channel cooldown is a stub (`jit_validator.py:413–418` is `pass`). GOV-12 violation — gate not enforced at runtime.
4. 5-day same-channel rule conflicts with day-3 email cadence step. Specification conflict unresolved.
5. Email hard-gate at Stage 11 drops domains with DM + mobile + score but no email (D2.2: 4 domains dropped). Blocks multi-channel outreach routing.
6. Zero E2E tests on outreach stack. Cadence orchestrator, suppression manager, compliance handler, booking handler never exercised on a real run.

**Additional product-readiness blockers (not pipeline-gating but required before first paying customer):**
- `STRIPE_SECRET_KEY` missing blocks billing + onboarding + customer lifecycle (Dave action).
- Dashboard V4 (commits 4ff5de13 + e9c31483) shipped but no real customer walk-through evidence.
- Agency self-serve onboarding flow never exercised end-to-end.

---

## 2. Validation Run Summary

| Run | Date | N | Conversion | Cost AUD/card | Wall | Key Findings |
|-----|------|---|-----------|---------------|------|--------------|
| F-REFACTOR-01 | 2026-04-14 | 1 (taxopia.com.au) | 100% (single domain) | $0.077 ($0.0495 USD) | 82s | All 8 stages fired real APIs; DM identified correctly |
| D2 validation | 2026-04-15 | 20 | 35% headline / 54% SMB-clean | $0.65 ($0.42 USD) | 399s | 6 enterprise + 1 directory contaminated discovery; 0 Gemini failures; 100% DM on cards produced |
| 100-domain smoke | 2026-04-15 | 100 | 28% | **$5.55 ($3.58 USD)** | 1061s (17.7 min) | Gemini 18% failure rate; DM id 82%. **COST ANOMALY: 9–20x D2.2 per-card — pre-fix run with known bugs (mobile dead, tokens broken, google_ads misuse). EXCLUDED from cost baseline.** |
| D2.2 fresh | 2026-04-16 | 12 | 42% / 83% post-Stage-3-SMB-clean | $0.41 ($0.26 USD) | 345s | Cleanest cohort. 5/5 L2 Hunter email (Hunter was live at time). 4/5 ContactOut mobile. |
| D2.2 replay | 2026-04-16 | 5 | 40% | $0.93 ($0.60 USD) | 475s | Re-scrape validation. 2/5 email via L0 Gemini. |

**Note on 100-domain cost:** $5.55 AUD/card ($3.58 USD) is the correct figure. A figure of $0.82 AUD was circulated during discussion — this was incorrect (7x error). The 100-domain run is excluded from cost baseline due to known pre-fix bugs.

**Scale gap:** No N≥50 clean cohort exists. D2.2 combined (N=17 fresh+replay) is the largest clean evidence baseline. All runs used the 2026-04-16-era provider stack, which has since collapsed (see §4).

---

## 3. Per-Stage Evidence Classification

Operational structure: 9-stage sequence per `src/pipeline/pipeline_orchestrator.py`. Stage-count drift across numbering systems documented in Appendix B.

### Stage 1 — Discovery (pull_batch from DFS categories)

- **Status:** E2E VALIDATED (with known contamination defect)
- **Evidence:** D2 (N=20): 20 domains discovered, 6 enterprise + 1 directory contaminated. D2.2 (N=12 fresh): enterprise filter caught 5/6 after D1.3–D1.5 fixes (PR #328). Blocklist expanded to 1,515 entries (commit 8a82becf, 2026-04-20).
- **Open issues:**
  - D2 audit #5 HIGH: discovery randomization absent — same domains every run. 15-min fix, not applied as of main HEAD.
  - Residual 1/6 enterprise leak post-PR #328: filter improved but not complete.
  - No category-level conversion telemetry to identify systematically contaminated discovery categories.

### Stage 2 — Spider Scrape (sem=15)

- **Status:** E2E VALIDATED
- **Evidence:** F-REFACTOR-01 confirmed real scrape on taxopia.com.au. Stage timing present in all three cohort summaries (11–19s per cohort). D2 and D2.2 both produced scraped content reaching downstream stages.
- **Open issues:**
  - No per-stage failure-rate metric for scrape specifically. Scrape failures are indistinguishable from DNS/ABN failures in aggregate conversion numbers.
  - Scraper waterfall (Jina AI → Bright Data Web Unlocker) not independently validated against JS-heavy sites.

### Stage 3 — DNS + ABN + DM Extraction (sem=1)

- **Status:** E2E VALIDATED with known drop-rate envelope
- **Evidence:** D2 drop_reasons: {enterprise_or_chain: 6, no_dm_found: 1, directory: 1} — 35% drop on N=20. D2.2 fresh drop_reasons: {enterprise_or_chain: 5, no_dm_found: 1} — 50% drop on N=12. D2.2 post-Stage-3 SMB-clean cohort explicitly defined in run report (83% conversion on passing domains). Stage 3 timing: 54–64s per cohort.
- **Open issues:**
  - D2 audit #8 HIGH: DM hallucination pressure — 57% fabricated name rate flagged. 15-min fix, not applied as of main HEAD.
  - sem=1 is a deliberate rate-limit constraint; at 100 domains, ABN lookup is the serial wall-time bottleneck (contributing to 17.7 min in 100-domain smoke).
  - No evidence of ABN API failure handling under timeout.

### Stage 4 — Affordability Gate (in-memory)

- **Status:** COMPONENT TESTED
- **Evidence:** Gate exercised in every validation run — drops visible in aggregate between Stage 3 and Stage 6. pytest suite: 2134 passed. D2 timing: 96s (heaviest single stage per cohort summary).
- **Open issues:**
  - D2 audit #6 HIGH: `google_ads_advertisers` field misuse — domain-as-keyword produces zero signal at $9.30/1000 wasted spend. 30-min fix, not applied as of main HEAD. Corrupts intent signals propagating to Stage 7.
  - No per-gate drop count in any run report. Cannot confirm ALS gate threshold (`PRE_ALS_GATE = 20`) is enforced as a runtime conditional vs documentation-only (GOV-12 exposure).

### Stage 5 — Intent Free Gate (in-memory)

- **Status:** COMPONENT TESTED
- **Correction of Aiden's UNCLEAR classification:** Aiden flagged Stage 5 as UNCLEAR based on 0.0s timing across all cohort runs, inferring it was a no-op or skipped gate. Code inspection confirms: Stage 5 executes `score_intent_free(enrichment)` at `pipeline_orchestrator.py:617–630`. This is an in-memory scoring check — a domain with status `NOT_TRYING` is skipped without paid enrichment. The 0.0s timing is expected for an in-memory gate with no I/O. Stage 5 is COMPONENT TESTED, not UNCLEAR.
- **Evidence:** Gate fires every run; timing confirms in-memory execution. No paid API call issued for NOT_TRYING domains.
- **Open issues:**
  - No per-gate drop count attributing Stage 5 drops separately from Stage 4 in any run report (same GOV-12 exposure as Stage 4).

### Stage 6 — Paid Enrichment: DFS Ads + GMB (sem=20)

- **Status:** E2E VALIDATED with known data-flow bug
- **Evidence:** F-REFACTOR-01 confirmed real DFS API call on taxopia.com.au. D2 and D2.2 both produced enrichment data that scored into Stage 7. Stage timing: 1.09–1.45s per cohort. Cost: ~$0.106/domain.
- **Open issues:**
  - D2 audit #4 HIGH: Stage 6 trend data never reaches Stage 7/10 — paid-for data unused downstream. 1h fix, not applied as of main HEAD. "declining" vs "34% down in 5 months" urgency signal is lost.
  - `google_ads_advertisers` field misuse (D2 audit #6 HIGH, 30-min fix, unresolved) propagates incorrect intent signal to Stage 7.
  - No evidence of GMB enrichment failure rate or fallback when GMB returns no data.

### Stage 7 — Intent Full Score + Outreach Draft (in-memory)

- **Status:** COMPONENT TESTED
- **Evidence:** ALS values used in Stage 8 gating (`ALS gate >=20 / HOT_THRESHOLD = 85` confirmed active). D2.2 enterprise filter directionally correct on 5/6 domains. Timing: 20–26s per cohort.
- **Open issues:**
  - `google_ads` misuse from Stage 6 propagates here — intent scores may be inflated or deflated.
  - D2 audit #2 CRITICAL: `{{agency_name}}` tokens unfilled in outreach drafts. **RESOLVED in PR #336 (2026-04-16) — `enhanced_vr.py` prompts rewritten to literal "Agency OS".** Test coverage added in PR #363 commit 7d77ad39 (3 lock-in tests).
  - No score distribution shown across any run — cannot validate threshold calibration for AU SMB population.

### Stage 8 — DM Identification / Contact Waterfall (sem=20)

- **Status:** E2E VALIDATED for L1 Gemini path. L2/L3 mobile waterfall layers NOT validated via ratified waterfall flow.
- **Evidence:**
  - F-REFACTOR-01: DM correctly identified on taxopia.com.au.
  - D2 (N=20): 100% DM identification on cards produced.
  - D2.2 replay (N=5): Gemini dm_phone returned mobile 5/5 — confirming L1 Gemini mobile path wired correctly after PR #328.
  - D2.2 fresh per_tier_hit_rate_mobile: {UNKNOWN:html_regex: 2, NONE: 6, L1: 4} on N=12 — mobile hit ~33% but via html_regex (UNKNOWN tier) and Gemini (L1), not ContactOut or Leadmagic waterfall layers.
  - 100-domain smoke: 82% DM identification rate; 18% failure = Gemini failure rate at scale.
- **Mobile waterfall status — correction of Aiden's "DEAD" claim:** Aiden's draft stated mobile waterfall is "DEAD per D2 CRITICAL finding #1" (mobile waterfall wiring: `leadmagic_client` + `brightdata_client` not passed to `run_mobile_waterfall`). This finding is PARTIALLY FIXED, not DEAD. PR #328 applied the fix to `cohort_runner.py` (passes brightdata_client). However, `pipeline_orchestrator.py` does NOT pass either client. D2.2 mobile 5/5 was via L1 Gemini dm_phone, not via L2 Leadmagic or L3 Bright Data. The wiring gap persists in the orchestrator path. Aiden's "DEAD" overstated the regression; status is PARTIALLY FIXED — orchestrator path is the remaining wiring gap.
- **Open issues:**
  - Mobile waterfall wiring: `pipeline_orchestrator.py` passes neither `leadmagic_client` nor `brightdata_client`. L2 and L3 layers silently dead in production path. 15-min fix, unresolved on HEAD.
  - D2 audit #3 CRITICAL: Hunter dm_verified gate is a comment, not a runtime conditional. **RESOLVED in PR #336 (2026-04-16) — runtime conditional enforced at `email_waterfall.py:565`.** GOV-12 compliant. Test coverage added in PR #363 commit e3ee5edb (3 lock-in tests).
  - Gemini SPOF: 18% failure rate at N=100 scale, no fallback DM identification path.
  - DM hallucination pressure (D2 audit HIGH): Gemini may confabulate DM names on thin-content sites. No adversarial test in evidence.

### Stage 9 — Reachability + ProspectCard Build (in-memory)

- **Status:** E2E VALIDATED (with critical provider failures as of 2026-04-20)
- **Evidence:** D2.2 fresh: 5/5 Hunter email, 4/5 ContactOut mobile — card build confirmed operational at time of run. D2.2 Stage 11 finding: 4 domains dropped despite DM + mobile + score because email was missing — confirms email is a hard gate in card build.
- **Open issues:**
  - As of 2026-04-20: Hunter DEAD (401), ContactOut fully exhausted (email=0, phone=0, search=0). D2.2 card-build evidence is stale — the provider stack cannot reproduce those results today.
  - **B5 (Elliot finding, not in Aiden's draft):** Email hard-gate drops mobile-ready domains. 4 domains with DM + mobile + score dropped for missing email. Must route to alternative channel or relax gate. Blocking if mobile/LinkedIn outreach is in scope.
  - D2 audit #9 MEDIUM: Stage 9 charges $0.027 for 50% zero-yield runs.
  - D2 audit #7 HIGH: dropped domains write nothing to BU — GOV-8 violation. 2h fix, not applied.

### Stage 10 — VR Synthesis + Message Generation

- **Status:** COMPONENT TESTED with broken output
- **Evidence:** F-REFACTOR-01 confirmed message generation executed on single domain. D2.2 produced cards with personalised fields. Timing: 22–26s per cohort.
- **Open issues:**
  - D2 audit #2 CRITICAL: `{{agency_name}}` token unfilled. **RESOLVED in PR #336 (2026-04-16); test-locked in PR #363.** See §7.1 for detail.
  - No evidence of VR synthesis failure fallback — unknown card state when Stage 10 VR fails.

### Stage 11 — Cards / Funnel Classification

- **Status:** E2E VALIDATED at small scale (with known gate defect)
- **Evidence:**
  - D2 (N=20): 7/20 cards = 35% overall, 54% post-enterprise-filter.
  - D2.2 fresh (N=12): 5/12 = 42% overall, 83% post-SMB-clean.
  - D2.2 replay (N=5): 2/5 = 40% yield.
  - Stage 11 gate confirmed: 4 domains dropped for missing email despite having DM + mobile + score.
- **Open issues:**
  - Email gate too strict: domains with mobile + high score but no email discarded rather than routed to SMS/LinkedIn channel. BLOCKING if multi-channel outreach is the intended product.
  - D2 audit #10 MEDIUM: no card quality tier — verified DM + verified email treated same as inferred DM + pattern email. 1h fix.
  - `pytest test_schema_f1.py` 12 failures (listener schema tests) — potential card output schema drift between pipeline and outreach consumer. Needs triage.

### Intelligence Modules (post-pipeline, src/intelligence/)

- **Stage 6 Enrich — Trend Data:** UNTESTED. Module exists in `src/intelligence/`. No validation run report mentions trend data fields. D2 audit #4: trend data never reaches Stage 7/10.
- **Stage 9 Social — LinkedIn / Facebook Posts:** UNTESTED (zero yield confirmed). D2 pipeline audit: zero yield. Apify facebook-posts-scraper configured (CLAUDE.md dead references exception) — auth/quota root cause undiagnosed.

---

## 4. Waterfall v2: Ratified vs Operational

Ratified 2026-04-16 (`ceo:waterfall_layer_order_v2`). Wiring verified correct per `research/d2_audit/ratified_vs_wired.md` as of 2026-04-16. Between 2026-04-16 and 2026-04-20, the providers the waterfall calls have collapsed or been demoted. **The audit is clean on wiring. The providers have regressed. No directive has reconciled the ratified architecture with current operational state.**

### Email Waterfall

| Layer | Provider | Status 2026-04-20 | Evidence |
|-------|----------|-------------------|---------|
| L0 Gemini | Gemini (contact-page extract via Stage 3) | OPERATIONAL | D2.2 replay: 2/5 email via L0 Gemini. 18% failure rate at N=100 scale. |
| L1a ContactOut search | ContactOut `/v1/people/search` | DEAD — pool exhausted, search=0 | FM-BUILD-V1 diagnostic 2026-04-20; `/v1/stats` + `/v1/people/search` returns 403 |
| L1b ContactOut enrich | ContactOut `/v1/people/enrich` | DEAD — email pool=0; phone pool (214) stranded behind email gate | FM-BUILD-V1 diagnostic 2026-04-20 |
| L2 Hunter | Hunter email-finder | DEAD — 401 authentication_failed. Auth broken, not quota. | FM-PRE-FLIGHT 2026-04-20 |
| L3 Leadmagic | Leadmagic email-finder | OPERATIONAL | FM-BUILD-V1: 47% AU enterprise hit rate on 171 profiles. 4,233–4,324 credits live. |
| L4 ContactOut stale | ContactOut stale fallback | DEAD — same pool as L1a/L1b | Same as L1a/L1b |
| L5 Bright Data | BD LinkedIn profile | PARTIAL — no email returned in any run | API key active; zero email yield across D2 / D2.2 / 100-domain smoke. Non-functional for email waterfall. |

**Email waterfall effective depth as of 2026-04-20:** L0 Gemini → (L1a/L1b/L2/L4 dead) → L3 Leadmagic → (L5 non-yielding). Two operational layers remain from six ratified.

### Mobile Waterfall

| Layer | Provider | Status 2026-04-20 | Evidence |
|-------|----------|-------------------|---------|
| L0 ContactOut phone | ContactOut | DEAD — phone credits (214) stranded behind email pool gate (email=0) | FM-BUILD-V1 diagnostic 2026-04-20 |
| L1 Gemini dm_phone | Gemini (Stage 3) | OPERATIONAL — cohort_runner path only. pipeline_orchestrator path missing client pass-through. | D2.2 replay: 5/5 mobile via dm_phone. PR #328 wired cohort_runner; orchestrator path not wired. |
| L2 Leadmagic mobile | Leadmagic | NON-FUNCTIONAL (AU). Also silently dead in pipeline_orchestrator (missing leadmagic_client pass-through). | 0/5 FM-BUILD-V1 pilot 2026-04-20. Historical 0% AU per Directive #317. 4,233 credits live but AU coverage absent. |
| L3 Bright Data | BD LinkedIn | PARTIAL — wired in cohort_runner only (brightdata_client passed); pipeline_orchestrator not wired. No mobile yield in any run. | Zero mobile yield in all runs. |

**Mobile waterfall effective depth as of 2026-04-20:** (L0 dead) → L1 Gemini (cohort_runner path only) → (L2 zero AU yield + orchestrator wiring dead) → (L3 orchestrator wiring dead + non-yielding). One partially-wired operational layer.

**Ghost provider — Prospeo:** Deprecated 2026-03-13 via Directive #192 but ghost-wired in MCP + settings + env per Aiden's audit. LAW XIII deprecation cascade not completed.

---

## 5. Provider Health Check

| Provider | Status | Last Verified | Pipeline Impact |
|----------|--------|--------------|-----------------|
| Gemini 2.5-flash | LIVE | 2026-04-16 (D2.2) | **SPOF.** Sole functional DM identification + L0 email + L1 mobile. 18% failure at N=100 scale. Single point of failure for DM path. |
| ContactOut | DEAD (all pools effectively) | 2026-04-20 | Critical: L1a/L1b email dead, L4 email dead, L0 mobile stranded. Three waterfall layers non-functional. |
| Hunter | DEAD (401 auth) | 2026-04-20 | High: L2 email non-functional. Auth issue, not quota — requires credential rotation or replacement. |
| Leadmagic | LIVE (email only) | 2026-04-20 | Moderate: 4,233 credits, email works. AU mobile 0% yield — L2 mobile dead in practice even if wiring were fixed. |
| Bright Data | LIVE (profile only) | 2026-04-16 | Low-current: profile data only. No email/phone in any run. L5 email and L3 mobile are theoretical layers being billed without output. |
| DataForSEO | LIVE | 2026-04-16 (D2.2) | Functional: T-DM0 DM identification ($0.0465/call). Stage 6 enrichment confirmed. |
| Apify (LinkedIn + Facebook) | UNKNOWN | No run evidence | Stage 9 Social zero yield. Auth/quota root cause undiagnosed. |

---

## 6. Outreach Stack Evidence

### Built and confirmed present

| Module | File | Built | E2E Tested |
|--------|------|-------|-----------|
| Cadence orchestrator | `cadence_orchestrator.py` | Yes | No evidence in any run |
| Compliance handler | `compliance_handler.py` | Yes | No evidence in any run |
| Suppression manager | `suppression_manager.py` | Yes | No evidence in any run |
| Email scoring gate | `email_scoring_gate.py` | Yes | No evidence in any run |
| Booking handler | `booking_handler.py` | Yes | No evidence in any run |
| Prospect telemetry | `prospect_telemetry.py` | Yes | No evidence in any run |

### Governance gaps (GOV-12 violations)

**Channel cooldown stub:**
- Specified: 5-day cooldown on same-channel re-contact (`CHANNEL_COOLDOWN_DAYS = 5` defined in `jit_validator.py:96`).
- Actual: `jit_validator.py:413–418` check is `pass` with comment. No executable conditional.
- Classification: GOV-12 violation.

**Aggregate tier daily cap absent:**
- Specified: tier-level daily send cap.
- Actual: `TierConfig.daily_outreach = 50` is per-campaign default only. No tier-level aggregate gate across multiple campaigns in the same tier.
- Classification: GOV-12 violation.

**5-day / 3-day cadence specification conflict:**
- Specified: 5-day cooldown on same-channel re-contact.
- Implemented cadence: email step 2 fires on day 3 (`cadence_orchestrator.py` default).
- Classification: specification conflict. Day-3 email step violates 5-day same-channel rule as written. No runtime enforcement exists to catch this conflict.

### Outreach stack verdict

Zero E2E test coverage. Three GOV-12 violations. The outreach stack is built but unvalidated and contains an unresolved specification conflict. Must not touch live customers until all blocking items are resolved and at least one full E2E outreach run is verified (cadence → send → telemetry).

---

## 7. Gap Analysis: What Would Close the Shippability Gap

All items are bounded and addressable pre-ship without architecture redesign.

### 7.1 — Fix the 3 D2-CRITICAL Audit Findings — **CLOSED 2026-04-21** (effort: ~15 min new code + 6 lock-in tests)

Source: `research/d2_audit/PIPELINE_AUDIT_MASTER.md`

Status resolved under directive F21-CRITICAL-3-FIX (PR #363, merge 6c39458a). Felt-sufficiency check during directive prep revealed 2 of 3 findings were already resolved in PR #336 (merged 2026-04-16). Only Fix 1 required new code; Fix 2 and Fix 3 received lock-in test coverage to prevent silent regression.

| Gap | Status | Resolution |
|-----|--------|-----------|
| Mobile waterfall client pass-through | RESOLVED in PR #363 | `leadmagic_client` + `brightdata_client` passed to `run_mobile_waterfall` in both `pipeline_orchestrator.py` and `cohort_runner.py`. Commit a1251081. |
| `{{agency_name}}` token substitution | ALREADY RESOLVED in PR #336; test-locked in PR #363 | `enhanced_vr.py` prompts rewritten to the literal "Agency OS" in PR #336 (2026-04-16). PR #363 commit 7d77ad39 added 3 lock-in tests asserting no `{{agency_name}}` / no `{{...}}` tokens in `*_PROMPT` constants + "Agency OS" literal presence. |
| Hunter dm_verified gate — comment to conditional | ALREADY RESOLVED in PR #336; test-locked in PR #363 | Runtime conditional enforced at `email_waterfall.py:565`. PR #363 commit e3ee5edb added 3 lock-in tests verifying Hunter GET is not called when `dm_verified=False`, IS called when `dm_verified=True + name + domain`, and skipped when `HUNTER_API_KEY` absent. |

Post-fix requirement (original): re-run D2.2-level cohort (N=12–20) to verify mobile non-zero and tokens resolve. Status: deferred to the separate N≥50 clean cohort directive (see §7.3).

Process note (felt-sufficiency): this audit initially claimed 3 findings unresolved based on reading `PIPELINE_AUDIT_MASTER.md` without per-finding HEAD verification. Elliot's directive-scrutiny step during F21-CRITICAL-3-FIX prep applied the felt-sufficiency rule ratified 2026-04-20 (`feedback_felt_sufficiency_signal.md`) and caught the staleness. This is the pattern working as designed.

### 7.2 — Reconcile Ratified-vs-Operational Waterfall (effort: scope-dependent on provider decisions)

Source: §4 waterfall table; FM-BUILD-V1 diagnostic; FM-PRE-FLIGHT 2026-04-20.

| Provider | Decision Required |
|----------|-----------------|
| Hunter | Renew account / rotate API key / accept deprecation + remove L2 from waterfall |
| ContactOut email | Purchase credits OR remove L1a/L1b/L4 from waterfall |
| ContactOut phone | Coupled to email pool unlock — independent decision or combined with email purchase |
| Leadmagic AU mobile | Accept 0% AU coverage (remove L2 from mobile waterfall) OR source AU mobile replacement |
| Prospeo | Complete deprecation cascade (LAW XIII-A) — remove from MCP + settings + env |

Post-decision: update `ceo:waterfall_layer_order_v2` to reflect post-reconciliation state.

### 7.3 — N≥50 Clean Cohort Run (effort: ~1h wall + $5–10 AUD)

Source: Aiden's gap analysis; GOV-11.

No N≥50 clean cohort exists. Ship-readiness validation at realistic Ignition volume slice (600 records/month → ~150 cards/week). Cards-only structural validation — no outreach firing. Run to execute after 7.1 + 7.2 complete. This audit satisfies GOV-11 structural audit requirement for the next run.

### 7.4 — OUTREACH-GATES-AUDIT (effort: ~1 session)

Source: `jit_validator.py` code inspection; governance gap analysis above.

Runtime enforcement required for: channel cooldown, tier aggregate daily cap, LinkedIn warmup ramp, email health signal wiring, DNCR gate, business-hours UTC/DST check. All must be executable conditionals (GOV-12). Manual mode does not protect volumetric burn risks (per 2026-04-20 peer analysis).

### 7.5 — First Manual-Mode Outreach Run (effort: ~1 day wall)

Source: Aiden's gap analysis.

Everything downstream of card generation is cold-start. One Salesforge manual campaign on ~50 real cards required to: produce first CIS outcome data, exercise reply handling, suppression_manager, compliance_handler, validate end-to-end send → receipt → reply loop.

### 7.6 — Dashboard V4 Customer Walk-Through (effort: ~30 min)

Source: Aiden's gap analysis; commits 4ff5de13 + e9c31483.

Dashboard V4 shipped but no evidence of a real or simulated customer walk-through: onboarding → campaign → card-approval → outreach-review. Even a simulated walk-through surfaces UX gaps before first paying customer.

### 7.7 — Billing Unblock (effort: Dave action)

Source: Aiden's gap analysis.

`STRIPE_SECRET_KEY` missing blocks onboarding → billing → revenue path. Not pipeline-gating but product-gating for first paying customer.

### Additional HIGH-priority gaps (Elliot's B/H detail)

| # | Gap | Evidence Source | Detail |
|---|-----|----------------|--------|
| H1 | Gemini sole DM identification — SPOF | 100-domain smoke, 18% failure rate | 18% of domains produce no card because DM identification fails. No fallback DM identification source or graceful degradation. |
| H2 | `google_ads_advertisers` field misuse | D2 pipeline audit #6 HIGH, unresolved | Incorrect field use corrupts intent scores in Stage 7. Not in PR #328 resolved items. |
| H3 | Discovery contamination residual | D2.2 (1/6 enterprise passed filter post-PR #328) | Enterprise filter improved but not complete. Degrades conversion rate and wastes API spend at scale. |
| H4 | Aggregate tier cap absent | Code inspection 2026-04-20 | Multi-campaign sends in same tier can exceed intended daily volume. GOV-12 violation. |
| H5 | Bright Data never yields email/mobile | All runs | L5 email and L3 mobile waterfall layers are theoretical. BD called and billed but producing no contact data. |
| H6 | Stage 9 social zero yield | D2 pipeline audit | Apify LinkedIn/Facebook posts module zero yield. Root cause (auth vs quota) undiagnosed. |

### Medium-priority gaps

| # | Gap | Evidence Source | Detail |
|---|-----|----------------|--------|
| M1 | DM hallucination pressure | D2 audit #8 HIGH, partially addressed | 57% fabricated name rate flagged. No adversarial test in evidence post-fix. |
| M2 | Per-gate drop accounting absent | All runs | Cannot distinguish Stage 4 vs Stage 5 drops. Blocks pipeline optimization and cost attribution. |
| M3 | Discovery randomization absent | D2 audit #5 HIGH, unresolved | Deterministic category sampling. 15-min fix not applied. |
| M4 | ABN sem=1 bottleneck | 100-domain smoke (17.7 min wall) | Serial ABN lookup is wall-time bottleneck at 100+ domains. Not blocking correctness but limits throughput. |
| M5 | VR synthesis failure fallback unknown | No multi-domain test | Unknown card state when Stage 10 VR fails. Silent failure risks empty personalisation fields reaching outreach. |
| M6 | test_schema_f1.py 12 failures | pytest output | Schema test failures may indicate card output schema drift between pipeline and outreach consumer. Needs triage. |

---

## 8. Shippability Verdict

**NOT SHIPPABLE TODAY.**

### Mandatory pre-ship (blocking)

| Item | Effort |
|------|--------|
| 7.1 — Fix 3 D2-CRITICAL findings | **CLOSED — PR #363 merged 6c39458a (2026-04-21). 2 of 3 were pre-resolved in PR #336.** |
| 7.2 — Waterfall reconciliation | Scope-dependent on provider decisions |
| 7.3 — N≥50 clean cohort after 7.1+7.2 | ~1h wall + $5–10 AUD |
| 7.4 — OUTREACH-GATES-AUDIT (GOV-12 compliance) | ~1 session |
| 7.5 — First manual outreach run | ~1 day wall |
| B5 — Relax email hard-gate or add multi-channel card routing | Scoped within 7.4 work |

### Dave actions required

| Item | Owner |
|------|-------|
| 7.6 — Dashboard walk-through | Build agent + Dave |
| 7.7 — Stripe secret key | Dave |

### Effort estimate

- **Optimistic:** 7.1 + 7.2 + 7.3 + 7.4 close in one long session. 7.5 takes one day. 7.6 + 7.7 in parallel. Shippable in 3–5 work items if no new blockers surface and provider decisions land cleanly.
- **Pessimistic:** 7.2 waterfall reconciliation spawns new provider sourcing (Hunter replacement, AU mobile replacement). Could extend 1+ week depending on procurement lead time.

**The pipeline logic is sound.** D2.2 83% post-SMB-clean conversion demonstrates the architecture works on a clean cohort with a full provider stack. The current gap is providers + gates + outreach validation, not pipeline design. With all blocking items resolved and HIGH items on a tracked backlog, F2.1 is shippable for a controlled first-customer cohort (10–20 domains, monitored manually).

---

## Appendix A: Felt-Sufficiency Self-Audit (Aiden's Section 9, peer-resolved)

Applied today's ratified pattern-recognition rule: where did the auditors rely on felt-sufficiency rather than cited evidence? Two flags raised in independent drafts, both resolved via peer-verification.

**FLAG 1 — Aiden raised, Elliot verified:**
Aiden claimed mobile waterfall is "DEAD per audit finding #1" based on reading `PIPELINE_AUDIT_MASTER.md` without re-verifying against current `src/pipeline/mobile_waterfall.py` HEAD or git log. Elliot's code inspection corrects: the function fires; L1 Gemini dm_phone is operational; L2 Leadmagic and L3 BD layers are silently dead due to missing client pass-through in `pipeline_orchestrator.py`. `cohort_runner.py` has a partial fix (brightdata_client only). D2.2 mobile 5/5 was via L1 Gemini, not L2/L3. Final claim: PARTIALLY FIXED — orchestrator path is the remaining wiring gap. Aiden's "DEAD" overstated the regression.

**FLAG 2 — Aiden raised, Elliot verified:**
Aiden inferred Stage 5 was "UNCLEAR" from 0.0s timing data without code inspection. Elliot's code inspection at `pipeline_orchestrator.py:617–630` confirms `score_intent_free(enrichment)` is an in-memory NOT_TRYING gate — 0.0s is correct, not suspicious. Reclassified from UNCLEAR to COMPONENT TESTED.

**FLAG 3 — Elliot raised, Aiden verified (reverse peer review):**
Elliot's draft stated 100-domain smoke cost-per-card as "$0.82 AUD." The actual figure from `scripts/output/cohort_run_20260415_103508/summary.json` is $5.55 AUD ($3.58 USD) — a 7x error. Corrected in §2 with explicit cost anomaly note flagging it as excluded from cost baseline.

**Remaining felt-sufficiency risks in this document:**
- Bright Data mobile status is inferred from "no mobile in any run" — no explicit BD mobile isolation test has been run. "PARTIAL — no mobile yielded" is accurate to evidence but does not confirm BD mobile is broken vs simply uncovered.
- Stage 9 social root cause (Apify auth vs quota) is genuinely unknown. UNTESTED is the correct classification.

All three flags resolved with evidence. No unresolved felt-sufficiency claims in the converged document.

---

## Appendix B: Stage-Count Drift (informational, not a ship gate)

Three numbering systems coexist in the codebase per Elliot's DIAGNOSE-REUSE-V1 (2026-04-20):

- **7 conceptual stages:** VERIFY → IDENTIFY → SIGNAL → ANALYSE → SCORE → ENRICH → OUTREACH (commit c1fbd67c)
- **9 operational stages:** per `pipeline_orchestrator.py` docstring — used in this audit
- **11 legacy F-stages:** per `src/intelligence/` module names

This audit uses the 9-stage operational numbering because cohort run summaries key on `stage1..stage11` in `per_stage_timing`. Convergence on one canonical numbering is Cat-3 technical debt and ratification hygiene. Not a ship gate.
