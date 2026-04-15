# Waterfall Evolution — Empirical Testing Data Extraction

Sources:
- `research/d1_8_2_extraction/01_dave_directives.md` (6157 lines)
- `research/d1_8_2_extraction/02_elliottbot_restates.md` (extracted restates)
- `research/d1_8_2_extraction/04_verification_outputs.md` (test result data)
- `research/d1_8_2_extraction/05_ceo_ratifications.md` (approvals/rejections)
- `research/d1_8_2_extraction/06_governance_language.md` (13979 lines)
- `research/d1_8_2_extraction/08_bug_discoveries.md` (bug + cost audit entries)

All quotes are verbatim from the source files with line citations where available.

---

## 1. METHODOLOGY EVOLUTION

### 1.1 Stage-by-Stage Sequential Execution with CEO Gate Between Each Stage

The foundational testing methodology was "stage-by-stage pipeline diagnosis" where each stage runs independently, pauses for CEO scrutiny, and only advances on approval. This is the primary empirical pattern from directives #327–#338.

**Origin — directive #328, April 2026:**

Restate entry (02_elliottbot_restates.md, Entry 49):
```
- Objective: Stage-by-stage pipeline diagnosis — Stage 1 ONLY: fresh DFS discovery of 100 raw domains across 3 categories
- Success criteria: 100 raw domains discovered, per-category breakdown, first 20 domains per category verbatim, JSON saved, cost under $5 AUD
- Assumptions: DFS credits sufficient for ~$0.30-0.50 USD of calls. #328 directive number reassigned from SQLAlchemy fix to pipeline diagnosis
```

Stage 1 ran first, results were delivered, CEO held at gate. Stage 2 only launched after Stage 1 gate was open. This pattern repeated through all 10 stages.

Verification output (04_verification_outputs.md, Entry 40):
```
S1-RERUN complete. 100/100, true middle-of-pool sampling (~30% position across all categories). $1.20 USD.
Engineering PASS, Demo PASS, Scaling FAIL (sequential DFS calls — parallelizing categories would cut wall-clock by ~10x).
Standing by for CEO scrutiny before Stage 2.
```

### 1.2 "E2E to Discover, Isolation to Close" Methodology

The session summary in 01_dave_directives.md (Entry 27, context block at line ~4688) explicitly documents this methodology:

```
Two separate pipelines: #323 forensic audit revealed PipelineOrchestrator (v7, tested in #300 and #317) and pool_population_flow + Siege Waterfall (old, actual production path) coexist with zero integration.
```

The practical pattern — discovered through directives #327–#338 — was:
1. Run E2E ("canonical run") to surface failures and blockers
2. Use isolation scripts for each stage to close the specific failure
3. The canonical run defined the production path; isolation scripts were diagnostic and remediation tools

This was codified in the Stage 1 rerun failure — Stage 1 passed engineering but "SCALING FAIL" because sequential DFS calls were exposed by the isolated stage run, not the E2E.

### 1.3 Mini-Cohort Validation Before Scale

Each stage ran on a cohort defined by what passed the prior stage gate:

- Stage 1: 100 raw domains across 3 categories (dental/legal/plumbing, ~34 each)
- Stage 2: 102 Stage 1 domains (some categories produced slightly more)
- Stage 3: 97 Stage 2 domains (after scrape failures excluded)
- Stage 4: 65 domains (service/hybrid after product filtering)
- Stage 5: 57 CLEAR+STRONG domains (affordability gate)
- Stage 6: 57 prospects for DM identification
- Stage 7: 57 prospects (40 with DM identified + 17 company-level fallback)
- Stage 8: 57 domains for LinkedIn company enrichment
- Stage 9: 35 DMs for profile enrichment cascade

Restate entry (02_elliottbot_restates.md, Entry 86, "Directive S1"):
```
- Objective: Run Stage 1 Discovery on 10 categories × 10 domains = 100 into BU. Stage 1 ONLY. Pause for CEO scrutiny.
- Success criteria: 100 domains in BU at pipeline_stage=1 with stage_completed_at + stage_metrics populated. Pause-report delivered.
```

The later F-TEST-100 run (01_dave_directives.md Entry 96 restate) scaled this to a 100-prospect end-to-end test:
```
- Objective: Build Pipeline F modules (F1-F6), single-domain end-to-end test, then full 100-prospect run. First ever Gemini hybrid pipeline execution.
- Success criteria: >=95% Gemini success, >=98% name, >=75% DM LinkedIn, >=75% email, <5% hallucination, <=$100 total, <=20 min wall.
```

### 1.4 Cost Estimation Before Run, Actual After

Every stage restate included a cost estimate; every completion included actuals. The gap between estimates and actuals drove architecture decisions.

**Example — #317.1 cost reconciliation (08_bug_discoveries.md, Entry 16):**

```
QUESTION 5 ANSWER: (b) Partial — the script bypasses the entire AI intelligence layer (Sonnet/Haiku), and additionally cannot run at all due to the `PipelineConfig` import error. The $14 estimate in the script header reflects the non-AI waterfall cost, which itself uses over-stated DFS rates.
```

```
Revised full-cycle cost if intelligence is wired: ~$42.58 USD / ~$66 AUD for 600 domains.
```

Bot response (08_bug_discoveries.md, Entry 17):
```
The honest answer is (b) Partial — the validation script was broken (dead import) and bypassed the entire AI intelligence layer. My $14 estimate was wrong because it excluded Sonnet/Haiku costs. Your $75 was closer to reality.
Revised full-cycle estimate: ~$66 AUD.
```

**CEO cost reference vs actual gap (06_governance_language.md, Entry 75):**
```
FINDING: CEO's DFS per-call cost of $0.04 does not match any code constant or MANUAL entry.
SOURCE (code): dfs_gmaps_client.py line 23 — COST_PER_SEARCH_AUD = Decimal("0.003") ($0.002 USD)
SOURCE (MANUAL): MANUAL.md line 407 — DFS SERP Organic = $0.01/call
RELEVANCE: CEO estimated Maps at $0.04 (actual $0.002 — 20x over) and DM SERP at $0.04 (actual $0.01 — 4x over).
```

**Stage 10 cost actual vs target (04_verification_outputs.md, Entry 19):**
```
Cost: $0.011 AUD/DM actual — 64% below $0.030 target. Cache doesn't activate (prompt too short), but irrelevant at these costs.
```

### 1.5 Pre-Run / Post-Run Comparison Protocol

Every stage defined explicit acceptance gates before run (in the restate) and measured actuals after run. The format was fixed:

| Gate | Target | Actual | Verdict |
|------|--------|--------|---------|

**S2 Results (04_verification_outputs.md, Entry 41):**
```
| Gate       | Target | Actual | Verdict |
|------------|--------|--------|---------|
| Scrape OK  | >=90%  | 93%    | PASS    |
| Business name | >=80% | 92% | PASS   |
| Footer ABN | >=30%  | 17%    | FAIL    |
| Emails     | >=60%  | 30%    | FAIL    |
| Cost       | <=$1.00| $0.00  | PASS    |
Two gates failed. Footer ABN at 17% (target 30%) and emails at 30% (target 60%).
```

**F-TEST-100 F3 results (04_verification_outputs.md, Entry 43):**
```
| Metric     | Gate   | Result | Verdict |
|------------|--------|--------|---------|
| F3 success | >=95%  | 90%    | FAIL (10 JSON parse failures) |
| Name       | >=98%  | 90%    | FAIL    |
| Location   | -      | 89%    | -       |
| ABN        | >=85%  | 83%    | CLOSE   |
| DM name    | >=85%  | 73%    | FAIL    |
| Combined   | >=90%  | 89%    | CLOSE   |
| Cost       | <=$100 | $0.13  | PASS    |
| Wall       | <=20min| 379s (6.3min) | PASS |
```

---

## 2. ARCHITECTURE DECISIONS DRIVEN BY TEST DATA

### 2.1 Stage 8 (LinkedIn Company) Reorder Audit — Before vs After Stage 6 (DM ID)

This was an explicit reorder audit triggered by the hypothesis that employee list data from Stage 8 could improve Stage 6 DM discovery. The audit ran on 2026-04-12.

**Restate (02_elliottbot_restates.md, Entry 67):**
```
- Objective: Audit whether LinkedIn Company (Stage 8) should move before DM ID (Stage 6) by measuring Apify employee list contribution to DM discovery
- Scope: IN: extract employee arrays from existing Stage 8 data, simulate reordered pipeline, measure DM lift. OUT: no pipeline code changes
- Success criteria: Classify as STRONG/MODERATE/NULL based on DM lift
- Assumptions: Apify employee arrays exist in Stage 8 output for 47 scraped companies
```

Follow-up with correct actor (Entry 68):
```
- Objective: Reorder audit with correct actor (george.the.developer employee scraper) on 47 validated LinkedIn company URLs. Measure DM lift from employee arrays.
- Success criteria: Classify as STRONG/MODERATE/NULL based on DM + email lift. Alternatives evaluated section mandatory.
```

Parallel enrichment test (Entry 69):
```
- Objective: Parallel Apify employee scrape (15 batches of 3) + multi-input Stage 7 waterfall on 14 discovered DMs (ContactOut URL, ContactOut search, Hunter Finder, Leadmagic)
- Success criteria: Wall time <5 min, email ≥+2 on new DMs for STRONG
```

The audit classified the DM lift as MODERATE (not STRONG enough to reorder). The Stage 6 → Stage 8 order was preserved. Employee list data was retained as a supplementary input to Stage 6 rather than a pre-Stage 6 gate.

### 2.2 Email Waterfall Reordering — ContactOut Before Website HTML

The session summary in 01_dave_directives.md (Entry 27, line ~4693) records this decision:

```
Waterfall ordering: Website HTML (L1) short-circuits before ContactOut (L1.5) can fire. Generic emails like sales@ accepted as DM email. Fixed by promoting ContactOut above website HTML + adding generic inbox penalty.
```

And from the parameter ledger (06_governance_language.md, constant table entry):
```
src/pipeline/email_waterfall.py
  Critical waterfall ordering file. On main branch: OLD order (L0 contact_registry → L1 website HTML → L2 Leadmagic → L3 Bright Data). On PR #291 feature branch: REORDERED (L0 contact_registry → L1 ContactOut → L2 website HTML with generic penalty → L3 Leadmagic → L4 ContactOut stale → L4.5 website generic → L5 Bright Data). PR #291 NOT MERGED to main.
```

**Root cause that drove the reorder:** Website HTML at L1 was finding generic inbox addresses (sales@, info@, contact@) and accepting them as DM email before ContactOut got a chance to fire. This resulted in 0% effective DM email quality even with apparent high hit rates.

The generic inbox blocklist added:
```python
GENERIC_INBOX_PREFIXES = frozenset({"sales", "info", "contact", "admin", "hello", "office", "enquiries", "reception", "team", "mail", "general", "accounts", "support", "help", "billing", "enquiry", "feedback", "marketing"})
```

Dave's ratification (01_dave_directives.md, Entry 40):
```
[TG] Generic inbox blocklist is a silent-failure risk. Same class as #292/#328.6/#330. If any info@ ends up in dm_email, that's the blocklist not firing. grep audit on output before save. Fire #334.
```

### 2.3 S2 Identity: SERP-First Before Website Scrape

S2 went through 5 iterations (V1 through V5) based on empirical test failures. The critical pivot was V5 — "SERP-first identity."

**S2-V5 restate (02_elliottbot_restates.md, Entry 93–94):**
```
- Objective: SERP-first identity (domain → Google → business name/location/ABN/GMB) + scrape-for-detail (services/tech/team). Two parallel tracks merged.
- Scope: IN: serp_identity_parser.py, parallelism key, narrowed Sonnet prompt, merge logic. OUT: no S3 advance.
- Success criteria: >=98% biz name, >=90% location, >=95% S3 readiness, >=13/15 failure domains resolved, <=$5, <=150s.
```

What drove this: Scraping-first (V1–V4) failed because:
1. Cloudflare and JS-heavy sites blocked httpx
2. Footer ABN extraction from raw HTML was unreliable (17% actual vs 30% target)
3. Canonical business names from HTML meta/title were inconsistent (90% name vs 98% target)

After V5 (SERP as primary identity source, scrape for detail only):

Verification output from F-TEST-100 (04_verification_outputs.md, Entry 42):
```
Identity: MASSIVE WIN. Services: 0% — Sonnet detail broken.

| Metric           | V4-patched | V5  | Verdict  |
|------------------|-----------|-----|----------|
| business_name    | 85%       | 100% | PASS ✓  |
| location         | 78% S3-ready | 87% | PASS ✓ |
| ABN              | 62%       | 98% | PASS ✓  |
| combined identity| ~78%      | 98% | PASS ✓  |
| services         | 85%       | 0%  | FAIL ✗  |
| cost             | $2.78     | $0.60 | PASS ✓ |
| wall             | 138s      | 114s | PASS ✓ |
```

Sonnet detail returned 0% services in V5 — the prompt narrowing broke service extraction. This was fixed in a separate prompt iteration (services were moved back to scrape-for-detail track).

**HARD DOMAINS finding (04_verification_outputs.md, Entry 43):**
```
HARD DOMAINS: ALL 4 RESOLVED — idealbathroomcentre, tkelectric, maddocks, bentleys all returned full identity via grounding. The Cloudflare-blocked sites that killed scraping are no problem for Gemini's search grounding.
```

This drove the adoption of Gemini search grounding as the canonical identity source in Pipeline F.

### 2.4 Stage 6 DM Waterfall — "Barnaby Hobbs" Contamination Gate Added

A cross-validation gate was added to Stage 6 DM identification after the early #327 run produced wrong DMs — the same person appearing across different businesses.

Restate for Stage 6 fix (02_elliottbot_restates.md, Entry 61):
```
- Objective: Stage 6 DM identification with stacked L0-L4 waterfall + 4 cross-validations on 57 prospects
- Scope: IN: free layers first (team page, ABN entity, GMB), SERP LinkedIn with AU enforcement, ContactOut fallback, cross-validation at every accept.
- Success criteria: ≥75% DM found, ≥40% from free tiers, zero cross-validation bypass, zero Barnaby Hobbs, spot-check 10 before save
```

The "Barnaby Hobbs" pattern was the canonical internal name for the contamination bug: SERP LinkedIn queries returned the same DM name across multiple unrelated businesses. Cross-validation enforcement was the fix — every DM accept required domain-to-profile matching before save.

### 2.5 Enterprise Filter Removal from Stage 1 Discovery

Stage 1 calibration revealed the enterprise filter was excluding too many valid SMBs. The category ETV calibration walk (directive #328.1) produced measured ETV windows for 21 categories.

**Restate (02_elliottbot_restates.md, Entry 50):**
```
- Objective: Two-step: (1) Patch dfs_labs_client.py to return organic_count, tiny PR. (2) Run 21-category ETV window calibration walk.
- Success criteria: category_etv_windows.py with measured ETV windows for all 21 categories, raw walks saved, $20 USD hard cap.
```

**Restate for config ship (Entry 51):**
```
- Objective: Ship category_etv_windows.py as canonical config, replace all hardcoded ETV ranges, add CI guard, three-store save
- Success criteria: get_etv_window(10514) returns measured values on main, grep shows zero hardcoded ETV outside the canonical file, three stores written
```

The pre-calibration code had a single hardcoded ETV range (100–50,000) applied to all categories. The calibration walk measured that categories like "window installation" and "plumbing" had fundamentally different ETV distributions — some SMB-dense bands were being missed by the global filter.

**Hardcoded ETV vs calibrated from 06_governance_language.md (parameter table):**
```
| 5 | etv_min (L2) | layer_2_discovery.py:406 | 200.0 | Code comment | ✓ | SMB tier |
| 6 | etv_max (L2) | layer_2_discovery.py:407 | 5000.0 | Code comment | ✓ | SMB tier |
```

After calibration, these became per-category values from `category_etv_windows.py`.

### 2.6 ALS Gate Calibration — PRE_ALS_GATE and HOT_THRESHOLD Locked

The two ALS gates were locked empirically and then made immutable:

From parameter ledger (06_governance_language.md):
```
| 23 | PRE_ALS_GATE | waterfall_v2.py:143 | 20 | CLAUDE.md:125 ✓ LOCK | ✓ | Minimum T2.5+ (cost control) |
| 24 | HOT_THRESHOLD | waterfall_v2.py:146 | 85 | CLAUDE.md:125 ✓ LOCK | ✓ | Minimum T5 (mobile) |
```

The gates had already been ratified in CLAUDE.md as "CRITICAL LOCKS" — not derived from the current session tests but from prior empirical tuning. The #328–#338 test runs validated that these gates produced the expected funnel shape.

**Hard gate on parameter changes (01_dave_directives.md, Entry 23):**
```
[TG] - This directive is a HARD GATE on any further pipeline parameter changes. Until #322 is closed, no directive may modify Stage 1 filter values, intent thresholds, ETV ranges, or any other tuning parameter. We do not tune again until we know why the last tuning disappeared.
```

### 2.7 Score Gate for Stage 7 Contact Enrichment (DM-Level Targeting)

Stage 7 used a combined contact waterfall with an explicit score gate determining whether to fire paid enrichment layers:

Restate (02_elliottbot_restates.md, Entry 62):
```
- Objective: Stage 7 contact enrichment — unified email+mobile waterfall on 57 prospects (40 with DM, 17 company-level)
- Scope: IN: ContactOut L1, Leadmagic L4/L5 fallback, website L0, pattern L6.
- Success criteria: ≥80% DM email, ≥60% verified, ≥40% mobile, zero generic inbox in dm_email
```

The Stage 7 verified email rate reaching only 40% (16/40 DMs with URLs) drove the Hunter addition:

```
Stage 7 verified email rate stuck at 40% (16/40 DMs). Current waterfall: L0 website scrape (free), L1 ContactOut (LinkedIn-URL-indexed, 31% hit on DMs with URLs), L4 Leadmagic (pattern+SMTP, 15% AU ceiling), L6 pattern (unverified, unusable).
```

(from 01_dave_directives.md, Entry 43, ~line 4920)

---

## 3. WATERFALL EVOLUTION TIMELINE

### 3.1 Email Waterfall — Chronological Order History

**Era 1 — Pre-#327 (production "old" waterfall on main):**
```
L0: contact_registry (free, unverified)
L1: website HTML scrape (free)
L2: Leadmagic (email+SMTP, $0.015 USD)
L3: Bright Data BD (unverified, $0.00075 USD)
```

Source: parameter ledger (06_governance_language.md):
```
| 61 | Email L0 | email_waterfall.py:10 | contact_data | Code comment | ✓ | Free, unverified |
| 62 | Email L2 | email_waterfall.py:12 | Leadmagic | Code comment | ✓ | $0.015 USD, verified |
| 63 | Email L3 | email_waterfall.py:13 | Bright Data BD | Code comment | ✓ | $0.00075 USD, unverified |
```

**Era 2 — PR #291 (ContactOut wired, not merged to main):**
```
L0: contact_registry
L1: ContactOut (LinkedIn-URL-indexed)
L2: website HTML (with generic inbox penalty)
L3: Leadmagic
L4: ContactOut stale
L4.5: website generic
L5: Bright Data BD
```

Source: session summary (01_dave_directives.md, Entry 27, ~line 4630):
```
On PR #291 feature branch: REORDERED (L0 contact_registry → L1 ContactOut → L2 website HTML with generic penalty → L3 Leadmagic → L4 ContactOut stale → L4.5 website generic → L5 Bright Data). PR #291 NOT MERGED to main.
```

**Era 3 — Hunter added as L2 (directive #334, April 2026):**

```
L0: website scrape (free)
L1: ContactOut (LinkedIn-URL-indexed, 31% hit on DMs with URLs)
L2: Hunter (new — inserted between L1 and L4)
L4: Leadmagic (pattern+SMTP, 15% AU ceiling)
L6: pattern (unverified, unusable)
```

Source: 01_dave_directives.md (~line 4920–4990):
```
Stage 7 verified email rate stuck at 40% (16/40 DMs). Current waterfall: L0 website scrape (free), L1 ContactOut (LinkedIn-URL-indexed, 31% hit on DMs with URLs), L4 Leadmagic (pattern+SMTP, 15% AU ceiling), L6 pattern (unverified, unusable).

Wire into email_waterfall.py as L2 (between L1 ContactOut and existing L4 Leadmagic):
L0 website scrape (free)
[L2 Hunter layer]
L1 ContactOut → L2 Hunter → L4 Leadmagic
```

**Rationale for Hunter addition:** ContactOut 31% hit was tied to DMs with LinkedIn URLs. Without a LinkedIn URL, ContactOut returned nothing. Hunter's company-domain method could recover some of the remaining 60% of DMs. The goal was to lift the 40% verified rate.

### 3.2 Mobile Waterfall — Chronological History

**Era 1 — Pre-#327 (main branch):**
```
L1: HTML regex (free)
L2: Leadmagic ($0.077 AUD)
L3: Bright Data BD
```

Source: parameter ledger (06_governance_language.md):
```
| 64 | Mobile L1 | mobile_waterfall.py:9 | HTML regex | Code comment | ✓ | Free |
```

**Era 2 — PR #291 (ContactOut as L0 primary, not merged):**
```
L0: ContactOut mobile (primary, $0.00/credit)
L1: HTML regex
L2: Leadmagic
L3: Bright Data BD
```

Source: session summary (01_dave_directives.md, Entry 27):
```
src/pipeline/mobile_waterfall.py — On main: OLD order (L1 HTML regex → L2 Leadmagic → L3 Bright Data). On PR #291: ContactOut as L0 primary. NOT merged to main.
```

**Rationale:** ContactOut at $0 marginal cost (included in email credits) should run before paying for Leadmagic mobile at $0.077.

### 3.3 DM Identification Waterfall — Evolution

**Era 1 — #327 initial run (failed):**
- DFS SERP organic LinkedIn query only
- No cross-validation
- Result: "Barnaby Hobbs" contamination (same DM name across multiple businesses)

**Era 2 — Stage 6 rebuild (#329):**

Restate (02_elliottbot_restates.md, Entry 61):
```
- Scope: IN: free layers first (team page, ABN entity, GMB), SERP LinkedIn with AU enforcement, ContactOut fallback, cross-validation at every accept.
```

Explicit waterfall:
```
L0: Team page scrape (free — available for ~40% of domains from Stage 3 team_candidates)
L1: ABN entity name (free)
L2: GMB (free)
L3: SERP LinkedIn with AU enforcement + cross-validation
L4: ContactOut fallback
```

- Success criteria: ≥75% DM found, ≥40% from free tiers
- "AU enforcement" = DFS SERP query included location filter forcing Australian results
- Cross-validation: every accept required domain-to-profile matching

**Era 3 — Apify Employee List attempt (#335 audit):**

Tested adding Apify employee scraper (george.the.developer actor) BEFORE the SERP layer to improve DM discovery from LinkedIn company pages.

Restate (02_elliottbot_restates.md, Entry 68):
```
- Objective: Reorder audit with correct actor (george.the.developer employee scraper) on 47 validated LinkedIn company URLs. Measure DM lift from employee arrays.
- Success criteria: Classify as STRONG/MODERATE/NULL based on DM + email lift.
```

Result: classified as MODERATE (not STRONG). The reorder was NOT implemented in the production waterfall because the lift did not meet the STRONG threshold required for architectural change.

### 3.4 LinkedIn Verification — L1/L2/L3 Emergence

The LinkedIn verification cascade evolved during Stage 8 build (#335):

Restate (02_elliottbot_restates.md, Entry 63):
```
- Objective: Audit Hunter Company Enrichment vs BD LinkedIn Company (single batch vs 10 parallel) for Stage 8 architecture decision
- Scope: IN: 5 Hunter company calls, 57-URL BD single batch, 57-URL BD 10 parallel batches.
- Success criteria: Side-by-side comparison table, wall time data, coverage data, architecture recommendation
```

Stage 8 build restate (Entry 64):
```
- Objective: Build Stage 8 LinkedIn Company enrichment: Hunter L1 → DFS SERP L2 → Apify L3 on 57 domains
- Success criteria: ≥85% combined enrichment (≥48/57), ≤$3.50, ≤5min wall time
```

Final Stage 8 waterfall:
```
L1: Hunter Company (company-domain indexed)
L2: DFS SERP (organic LinkedIn company search)
L3: Apify LinkedIn Company scraper (last resort)
```

The audit found Hunter Company was faster but lower coverage than BD LinkedIn Company for batch operations. Hunter returned results immediately for known domains; BD was better for unindexed Australian SMBs. The SERP layer (L2) provided the bridge.

### 3.5 DM Profile Enrichment (Stage 9) Waterfall

Stage 9 was designed from the provider audit (restate Entry 70):

```
- Objective: Audit LinkedIn DM profile enrichment providers for Stage 9 personalisation — test coverage, cost, data richness on 5 sample DMs
- Success criteria: Recommendation with ≥70% coverage, ≤$0.05/prospect, sufficient personalisation hooks
```

Resulting cascade (from restate Entry 74):
```
L1: ContactOut (by LinkedIn URL)
L2: BD Person (Bright Data person profile)
L3: BD Company (Bright Data company profile)
L4: ContactOut (by email — fallback when no URL)
L5: null (no data found)
```

The Stage 9 success criterion was ≥70% coverage at ≤$0.05/prospect AUD.

---

## 4. NEGATIVE → POSITIVE LEARNING LOOPS

### 4.1 ContactOut 401 — Bearer Auth → Basic Auth

**Failure:** ContactOut API returned 401 on all calls during #317 validation.

**Root cause found:** Incorrect auth scheme. The API used `authorization: basic` + `token: <key>` header, not `Authorization: Bearer <key>`.

**Fix:** Auth header corrected.

**Source (session summary, 01_dave_directives.md, Entry 27, ~line 4698):**
```
ContactOut 401: Initial attempts used Bearer auth. Correct auth is `authorization: basic` + `token: <key>` header (discovered from API docs Dave sent via Telegram).
```

**Outcome after fix (01_dave_directives.md, line ~3717):**
```
ContactOut unblocked (auth fixed, 70% hit rate, data quality validation queued)
```

### 4.2 DFS Second_Date Regression — Hardcoded date.today()

**Failure:** Discovery ran 0 domains because DFS returned empty results.

**Root cause:** `Layer2Discovery.pull_batch()` had `date.today()` hardcoded as second_date. DFS returns empty for current date (data isn't indexed yet). The dynamic `_get_latest_available_date()` method existed but was bypassed.

**Fix:** Removed hardcoded dates, used the dynamic method. Regression test added.

**Source (session summary, 01_dave_directives.md, Entry 27, ~line 4689):**
```
DFS second_date regression: Layer2Discovery.pull_batch() hardcoded date.today() as second_date, bypassing _get_latest_available_date(). DFS returns empty for future dates. Fixed by removing hardcoded dates, added regression test.
```

**Outcome:** Stage 1 discovery ran and produced 100 domains.

### 4.3 Wrong Discovery Class — Layer2Discovery vs MultiCategoryDiscovery

**Failure:** Validation script used `Layer2Discovery` which had no pagination offset. Top 100 DFS domains all had ETV > 5000, so the SMB filter (200-5000) rejected all of them.

**Root cause:** `Layer2Discovery.pull_batch()` never passed offset to DFS. `MultiCategoryDiscovery` had `next_batch()` with paginated offset walking.

**Fix:** Swapped import to `MultiCategoryDiscovery`. `next_batch()` auto-paginates to SMB band.

**Source (session summary, ~line 4690):**
```
Wrong discovery class: Validation script used Layer2Discovery (no pagination) instead of MultiCategoryDiscovery (paginated). Fixed by swapping import.
ETV filter at offset 0: Top 100 DFS domains all have ETV > 5000, filter 200-5000 rejects all. Fixed by using next_batch() which auto-paginates to SMB band.
```

**S1-RERUN result after fix (04_verification_outputs.md, Entry 40):**
```
S1-RERUN complete. 100/100, true middle-of-pool sampling (~30% position across all categories). $1.20 USD.
```

### 4.4 Producer-Consumer Race Condition — Pre-Fill Fix

**Failure:** Workers started and exited before the refill loop made its first DFS call. Zero domains processed.

**Root cause:** Workers consumed from an empty queue and exited before the producer populated it.

**Fix:** Pre-fill queue with one `next_batch()` call before starting workers.

**Source (session summary, ~line 4692):**
```
Producer-consumer race: Workers start and exit before refill loop makes first DFS call. Fixed with Option B: pre-fill queue with one next_batch() before starting workers.
```

### 4.5 Footer ABN 17% → 98% — SERP Grounding vs HTML Scrape

**Failure:** Stage 2 website scraping achieved only 17% footer ABN extraction (target: 30%). Follow-up ABN matching with domain keyword extraction achieved only ~40% (target: 60%+).

**Root cause chain:**
1. Domain keyword extraction was using string splitting not semantic word-boundary detection
2. AU business suffix lexicon was missing (Pty Ltd, Pty. Ltd., PTY LTD variants)
3. Trading names JOIN was incomplete — Tier 3 ABN matching didn't call ABR SearchByABN for full record enrichment

**Fixes applied:**
- New `au_lexicon.py` with semantic word-boundary detection
- Rewrite of `_extract_domain_keywords` in `free_enrichment.py`
- Tier 3 ABR follow-up call added to `abn_client.search_by_abn()`
- GST three-state model fixed (REGISTERED/NOT_REGISTERED/UNKNOWN)

**S2-V5 result after SERP-first identity:**
```
ABN: 62% → 98% (PASS ✓)
```

Source (04_verification_outputs.md, Entry 42).

### 4.6 #327 Canonical Run — 1.3% Raw-to-Card Conversion

**Failure:** The canonical run (#327) produced only 3 DM cards from 228 raw domains (1.3% conversion).

**Root causes identified (01_dave_directives.md, Entry 27, ~line 4700):**
```
Pipeline conversion rate: 1.3% raw-to-card (228→3). Root causes identified: 4 workers instead of 10, category exhaustion at SMB ETV band depth, and fundamentally — PipelineOrchestrator was never deployed to production.
```

Three separate issues:
1. `num_workers` defaulted to 4, should be 10 for Ignition tier
2. Category exhaustion: SMB ETV bands were shallow in the categories tested
3. PipelineOrchestrator (v7, tested in #300 and #317) was never deployed — old production path (pool_population_flow + Siege Waterfall) ran instead

**Outcome:** Stage-by-stage isolation testing (#328–#338) was launched specifically to diagnose and close each failure root cause independently before wiring the production path.

### 4.7 write_manual.py — Hardcoded Skeleton Instead of Reading docs/MANUAL.md

**Failure:** Every "Manual updated" report was false. Drive was stale.

**Root cause (06_governance_language.md, Entry 11):**
```
Root cause confirmed: write_manual.py --full writes a hardcoded skeleton from Directive #168 — it never reads docs/MANUAL.md. This is why Drive has always been stale. The script is the bug.
```

**Fix:** `write_manual.py` patched to read actual `docs/MANUAL.md` instead of hardcoded skeleton.

**Outcome:** 53,079 chars written. Drive Manual and local file now in sync.

### 4.8 Sonnet Detail 0% Services — Prompt Narrowing Side Effect

**Failure:** S2-V5 identity pass achieved 98% name/ABN but 0% services (V4 was 85%).

**Root cause:** The prompt narrowing for identity (to improve name/ABN accuracy) accidentally dropped the services extraction block from the Sonnet prompt.

**Fix:** Services moved to a separate scrape-for-detail track with its own Sonnet call, not competing with identity extraction.

Source (04_verification_outputs.md, Entry 42):
```
Identity: MASSIVE WIN. Services: 0% — Sonnet detail broken.
services | 85% | 0% | FAIL ✗
Sonnet detail returned 0% services — the narrowed prompt or JSON parsing is failing. Let me diagnose quickly:
```

### 4.9 Stage 7 Email Verified Rate Stuck at 40% — Hunter Addition

**Failure:** Stage 7 achieved 40% verified email (16/40 DMs). Target was ≥80%.

**Root cause analysis (01_dave_directives.md, ~line 4920):**
```
Stage 7 verified email rate stuck at 40% (16/40 DMs). Current waterfall: L0 website scrape (free), L1 ContactOut (LinkedIn-URL-indexed, 31% hit on DMs with URLs), L4 Leadmagic (pattern+SMTP, 15% AU ceiling), L6 pattern (unverified, unusable).
```

ContactOut was limited to DMs with LinkedIn URLs (31% of those). Leadmagic had a 15% AU ceiling on email pattern matching. No layer covered DMs without LinkedIn URLs.

**Fix:** Hunter email-finder added as L2 between ContactOut and Leadmagic. Hunter uses name+domain which doesn't require a LinkedIn URL.

**Rationale from directive (#334):**
```
Wire into email_waterfall.py as L2 (between L1 ContactOut and existing L4 Leadmagic)
Files in scope: src/integrations/hunter_client.py (new), src/pipeline/email_waterfall.py (add L2 Hunter layer between existing L1 ContactOut and L4 Leadmagic)
```

---

## 5. PROVIDER SWAP DECISIONS (CHRONOLOGICAL)

| Date | Old Provider | New Provider | Reason |
|------|-------------|-------------|--------|
| Pre-Apr 2026 | Proxycurl | Bright Data LinkedIn Profile (gd_l1viktl72bvl7bjuj0) | Dead reference, Bright Data = lower cost, better AU coverage |
| Pre-Apr 2026 | Apollo (enrichment) | Waterfall Tiers 1-5 | Replaced by multi-tier cascade |
| Pre-Apr 2026 | Apify (GMB scraping) | Bright Data GMB Web Scraper (gd_m8ebnr0q2qlklc02fz) | EXCEPTION: Apify harvestapi/linkedin-profile-scraper active in Pipeline F v2.1 |
| Pre-Apr 2026 | HunterIO (email verify) | Leadmagic ($0.015/email) | EXCEPTION: Hunter email-finder active in Pipeline F v2.1 as L2 email fallback |
| Pre-Apr 2026 | Kaspr (mobile) | Leadmagic mobile ($0.077) | Leadmagic lower cost, single provider |
| Pre-Apr 2026 | HeyReach | Unipile | Higher rate limits, better compliance |
| Pre-Apr 2026 | ABNFirstDiscovery | MapsFirstDiscovery (Waterfall v3) | GMB as discovery source vs ABN-first |
| Apr 2026 (#317) | None (ContactOut new) | ContactOut added as L1 | 70% hit rate after auth fix; replaces Leadmagic+ZeroBounce if quality validates |
| Apr 2026 (#334) | (gap layer) | Hunter email-finder added as L2 | Stage 7 40% verified rate — Hunter covers DMs without LinkedIn URL |

Source: CLAUDE.md "Dead References" table + session data.

---

## 6. SUMMARY WATERFALL STATES

### Final Pipeline F Waterfall (as-of Apr 2026, empirically validated)

**Discovery:**
```
T0: GMB (Bright Data GMB Web Scraper, gd_m8ebnr0q2qlklc02fz)
T1: ABN registry (local JOIN, 2.4M rows, free)
T1.5a: SERP Maps (DataForSEO)
T1.5b: SERP LinkedIn (DataForSEO)
```

**Identity (Stage 2, S2-V5 methodology):**
```
Primary: SERP grounding (Gemini search) → business_name/ABN/location
Secondary: Website scrape → services/tech/team
```

**DM Identification (Stage 6):**
```
L0: Team page scrape (free, ~40% of domains)
L1: ABN entity name (free)
L2: GMB (free)
L3: DFS SERP LinkedIn with AU enforcement + cross-validation
L4: ContactOut (fallback)
```

**Email waterfall (Stage 7 — PR #291 state, not yet merged to main):**
```
L0: contact_registry (free)
L1: ContactOut (LinkedIn-URL-indexed, 31% hit on DMs with URLs)
L2: Hunter email-finder (name+domain, covers DMs without LinkedIn URL)
L2(old): website HTML (demoted to L2 with generic inbox penalty)
L3: Leadmagic ($0.015 USD, 15% AU ceiling)
L4: ContactOut stale
L4.5: website generic
L5: Bright Data BD
```

**Mobile waterfall:**
```
L0: ContactOut mobile (if available, $0)
L1: HTML regex (free)
L2: Leadmagic ($0.077 AUD)
```

**ALS gates (locked):**
```
PRE_ALS_GATE = 20 (minimum for T2.5+ enrichment)
HOT_THRESHOLD = 85 (minimum for T5 mobile)
```

**LinkedIn Company (Stage 8):**
```
L1: Hunter Company (domain-indexed)
L2: DFS SERP (organic LinkedIn company search)
L3: Apify LinkedIn Company scraper
```

**DM Profile (Stage 9):**
```
L1: ContactOut (by LinkedIn URL)
L2: BD Person
L3: BD Company
L4: ContactOut (by email — fallback)
L5: null
```

---

## 7. KEY METRICS BASELINE (April 2026)

| Stage | Metric | Result | Source |
|-------|--------|--------|--------|
| S1 | Discovery (100 domains) | 100/100, $1.20 USD | 04_verification_outputs.md Entry 40 |
| S2 scrape | Scrape OK | 93% | 04_verification_outputs.md Entry 41 |
| S2 scrape | Business name | 92% | 04_verification_outputs.md Entry 41 |
| S2 scrape | Footer ABN | 17% (FAIL, target 30%) | 04_verification_outputs.md Entry 41 |
| S2 scrape | Emails | 30% (FAIL, target 60%) | 04_verification_outputs.md Entry 41 |
| S2-V5 SERP | Business name | 100% | 04_verification_outputs.md Entry 42 |
| S2-V5 SERP | ABN | 98% | 04_verification_outputs.md Entry 42 |
| S2-V5 SERP | Cost | $0.60 (vs $2.78 prior) | 04_verification_outputs.md Entry 42 |
| F3 (F-TEST-100) | DM name | 73% (FAIL, target 85%) | 04_verification_outputs.md Entry 43 |
| F3 (F-TEST-100) | Combined | 89% (CLOSE, target 90%) | 04_verification_outputs.md Entry 43 |
| F3 (F-TEST-100) | Cost | $0.13 (PASS) | 04_verification_outputs.md Entry 43 |
| Stage 7 | Verified email | 40% (target ≥80%) | 01_dave_directives.md Entry 43 |
| ContactOut | Hit rate on DMs with LinkedIn URLs | 31% | 01_dave_directives.md ~line 4920 |
| ContactOut (post-auth fix) | Overall hit rate | 70% | 01_dave_directives.md line 3717 |
| Stage 10 (message gen) | Cost/DM | $0.011 AUD (64% below $0.030 target) | 04_verification_outputs.md Entry 19 |
