# Audit 04 — Naming Consistency
Branch: directive/f-refactor-01
Date: 2026-04-14
Auditor: review-5 (claude-sonnet-4-6)

---

## 1. Old Stage Names: f3a / f3b

### Classification Key
- **(a)** Deferred param with NOTE comment
- **(b)** DEPRECATED config key with DEPRECATED note
- **(c)** Real miss — should have been renamed
- **(d)** Legacy key with DEPRECATED note

| File:Line | Text | Classification | Action Needed |
|-----------|------|----------------|---------------|
| src/intelligence/verify_fills.py:204 | `f3a_output: dict` (param sig) | (a) | None — NOTE comment at line 211 explains retention for caller compat |
| src/intelligence/verify_fills.py:211 | `NOTE: param name retained for caller compatibility` | (a) | None — correct annotation |
| src/intelligence/verify_fills.py:219–223 | `f3a_output.get(...)` (body references) | (a) | None — follows from retained param name |
| src/intelligence/gemini_client.py:21 | `from src.intelligence.comprehend_schema_f3a import ...` | (c) | Schema file is active and not deprecated — import name uses old f3a naming. File should be renamed to `comprehend_schema_stage3.py` or import aliased with a NOTE |
| src/intelligence/gemini_client.py:22 | `from src.intelligence.comprehend_schema_f3b import ...` | (c) | Same as above — file should be renamed to `comprehend_schema_stage7.py` |
| src/intelligence/gemini_client.py:61 | `async def call_f3a(` | (c) | Public method name still uses old nomenclature. Called from cohort_runner and scripts. Rename to `call_stage3_identify` would require coordinated rename across 3 callers — flag as tech debt |
| src/intelligence/gemini_client.py:185 | `async def call_f3b(` | (c) | Same as above — rename to `call_stage7_analyse` |
| src/intelligence/gemini_client.py:187 | `f3a_output: dict` (param on call_f3b) | (a) | NOTE comment at line 195 explains retention |
| src/intelligence/gemini_client.py:194–195 | `NOTE: param name retained for caller compatibility` | (a) | Correct annotation |
| src/intelligence/gemini_client.py:230 | comment `migrated to call_f3a / call_f3b` | (c) | Stale comment references old names without noting they are themselves legacy — minor |
| src/intelligence/prospect_scorer.py:58 | `f3a_output: dict` (param sig) | (a) | NOTE comment at line 65 explains retention |
| src/intelligence/prospect_scorer.py:65 | `f3a_output: Stage 3 IDENTIFY output ...` | (a) | Correct annotation |
| src/intelligence/prospect_scorer.py:103–217 | `f3a_output.get(...)` body refs | (a) | Follow from retained param |
| src/intelligence/contact_waterfall.py:374 | `f3a_linkedin_url: str \| None = None` (param) | (a) | NOTE comment at line 384 explains retention |
| src/intelligence/contact_waterfall.py:384 | `NOTE: param name retained for caller compatibility` | (a) | Correct annotation |
| src/intelligence/contact_waterfall.py:395 | `f3a_linkedin_url` in body | (a) | Follows from retained param |
| src/config/stage_parallelism.py:229 | `"stage_f3a_comprehend"` config key | (b) | Marked DEPRECATED with note at line 235 — correct |
| src/config/stage_parallelism.py:237 | `"stage_f3b_compile"` config key | (b) | Marked DEPRECATED with note at line 243 — correct |
| src/orchestration/cohort_runner.py:151 | `result = await gemini.call_f3a(` | (c) | Active call using old method name — no NOTE. Real miss at call site |
| src/orchestration/cohort_runner.py:205 | `f3a_output=domain_data.get("stage3", {})` | (a) | Kwarg uses old name but maps to "stage3" key — acceptable bridge |
| src/orchestration/cohort_runner.py:250 | `result = await gemini.call_f3b(f3a_output=identity, ...)` | (c) | Active call using old method name — no NOTE at call site |
| src/orchestration/cohort_runner.py:269 | `fills = await run_verify_fills(dfs=dfs, f3a_output=identity)` | (a) | Kwarg retained for compat, consistent with NOTE in verify_fills |
| src/orchestration/cohort_runner.py:285 | `f3a_linkedin_url=dm.get("linkedin_url")` | (a) | Kwarg retained for compat, consistent with NOTE in contact_waterfall |
| scripts/f_refactor_e2e.py:5,71–141 | All `f3a`/`f3b` variable/label refs | (c) | Script is an active E2E test runner, not a legacy script. All f3a/f3b variable names are unnamed local vars — no NOTE or DEPRECATED marker. Medium priority |
| scripts/f_cohort_100.py:4,152–413 | All `f3a`/`f3b` variable/label refs | (c) | Same — active cohort script, no deprecation annotations, uses old stage names throughout |

### Summary — Audit 1
- **(a) Deferred param with NOTE comment:** 9 instances across verify_fills, gemini_client, prospect_scorer, contact_waterfall — all correctly annotated.
- **(b) DEPRECATED config key with note:** 2 instances in stage_parallelism.py — correctly marked.
- **(c) Real misses (no rename, no NOTE):** 6 substantive issues:
  1. `gemini_client.py` — method names `call_f3a` / `call_f3b` are public API, not annotated as legacy
  2. `comprehend_schema_f3a.py` / `comprehend_schema_f3b.py` — active schema files still carry f3a/f3b filename
  3. `cohort_runner.py:151,250` — call sites use old method names with no NOTE
  4. `scripts/f_refactor_e2e.py` — active script, pervasive f3a/f3b local vars, no annotations
  5. `scripts/f_cohort_100.py` — same

---

## 2. Noun Consistency: prospect / lead / domain

Sampling across `src/intelligence/` and `src/orchestration/cohort_runner.py`.

| Context | Term Used | Verdict |
|---------|-----------|---------|
| `prospect_scorer.py` — function name, docstring, return key | `prospect` (`score_prospect`, `is_viable_prospect`) | Consistent |
| `prospect_scorer.py` — input data | `f3a_output` (identity dict) | Consistent with param-retention pattern |
| `cohort_runner.py` — pipeline element | `domain` (`domain_data`, `domain_data["domain"]`) | Consistent within orchestration layer |
| `cohort_runner.py:355` | `lead card` (stage 11 function docstring: "assemble final lead card") | **Inconsistency** — orchestration layer otherwise uses `domain`; this function uses `lead` |
| `cohort_runner.py:385,400` | `lead_pool_eligible` key | Consistent with funnel_classifier output key |
| `funnel_classifier.py:28,48,52` | `lead_pool_eligible` | Consistent — this is the output gate term |
| `enhanced_vr.py:43` | `lost leads` (inside prompt text) | Acceptable — this is natural language in a prompt template, not a code noun |
| `gemini_client.py:5,71` | `prospect domain` (docstring/comment) | Consistent with `prospect` for the entity, `domain` as identifier |
| `stage9_social.py:27` | `prospect` | Consistent |
| `dfs_signal_bundle.py:3` | `prospect domain` | Consistent |
| `serp_verify.py:115` | `domain` (function param and docstring) | Consistent |

### Noun Consistency Verdict
The codebase is **mostly consistent** with this convention:
- **`domain`** = the string identifier / pipeline row key (used in orchestration)
- **`prospect`** = the scored entity (used in intelligence layer)
- **`lead`** = the post-classification output eligible for outreach (used in funnel output keys)

**One genuine inconsistency flagged:**
- `cohort_runner.py:355` function docstring says "assemble final lead card" but the surrounding orchestration layer uses `domain_data` throughout. The function is Stage 11 CARD and the key `lead_pool_eligible` comes from funnel_classifier — so "lead" is appropriate at that boundary. However the mixed usage within a single function (`domain_data` in → `lead card` out) could confuse readers. Low severity.

---

## 3. Pipeline Version References

| File:Line | Text | Classification | Action Needed |
|-----------|------|----------------|---------------|
| src/intelligence/stage9_social.py:6 | `Pipeline F v2.1. Ratified: 2026-04-15` | Active — current version | None |
| src/intelligence/prospect_scorer.py:6 | `Pipeline F v2.1. Ratified: 2026-04-15` | Active — current version | None |
| src/intelligence/parallel.py:1 | `Pipeline F v2.1 stage execution` | Active — current version | None |
| src/intelligence/contact_waterfall.py:3 | `directive F-REFACTOR-01` (not a version ref) | Directive reference, not version | None |
| src/intelligence/enhanced_vr.py:13 | `Pipeline F v2.1. Ratified: 2026-04-15` | Active — current version | None |
| src/intelligence/serp_verify.py:6 | `Pipeline F v2.1. Ratified: 2026-04-15` | Active — current version | None |
| src/intelligence/stage6_enrich.py:8 | `Pipeline F v2.1. Ratified: 2026-04-15` | Active — current version | None |
| src/intelligence/funnel_classifier.py:6 | `Pipeline F v2.1. Ratified: 2026-04-15` | Active — current version | None |
| src/intelligence/comprehend_schema_f3a.py:7 | `Pipeline F v2. Ratified: 2026-04-15` | **Stale** — v2 not v2.1 | Minor — schema files lag one minor version behind |
| src/intelligence/comprehend_schema_f3b.py:15 | `Pipeline F v2. Ratified: 2026-04-15` | **Stale** — v2 not v2.1 | Same |
| src/orchestration/cohort_runner.py:1,9 | `Pipeline F v2.1` | Active — current version | None |
| src/orchestration/cohort_runner.py:460 | `Pipeline F v2.1 economics doc` | Active — current version | None |
| src/orchestration/cohort_runner.py:710 | `Pipeline F v2.1 Cohort Runner` | Active — current version | None |

### No stale v1 references found in active (non-deprecated) code.
All active `src/` files reference v2 or v2.1. The two schema files (`comprehend_schema_f3a.py`, `comprehend_schema_f3b.py`) show `v2` rather than `v2.1` — consistent with the fact these files also carry the unresolved f3a/f3b naming issue from Audit 1.

---

## Dead Reference Check (Bonus — spotted during audit)

| File:Line | Reference | Status | Action |
|-----------|-----------|--------|--------|
| src/intelligence/contact_waterfall.py:29,236,265,269,277 | `HunterIO` (HUNTER_EMAIL_FINDER_URL, HUNTER_API_KEY) | **Dead reference** — HunterIO listed in CLAUDE.md dead references table; replacement is Leadmagic | Needs remediation. HunterIO is actively called at L2 of the email waterfall with no DEPRECATED marker |
| src/intelligence/contact_waterfall.py:31,298,338–359 | `Apify` (APIFY_BASE, apimaestro actor, harvestapi actor) | **Dead reference** — Apify listed in CLAUDE.md dead references table; replacement is Bright Data GMB Web Scraper | Needs remediation. Apify is used for LinkedIn profile scraper and DM posts scraper. Note: docstring line 11 says "Leadmagic EXCLUDED" but does not explain Apify exclusion from dead-ref policy |

Note: The CLAUDE.md dead references table lists "Apify → Bright Data GMB Web Scraper (gd_m8ebnr0q2qlklc02fz)" but the Apify usage in contact_waterfall is for LinkedIn profile scraping and DM posts (harvestapi/apimaestro actors), not GMB scraping. The replacement mapping may be incomplete — flag for Dave to clarify whether these specific Apify actors are ratified or also dead.

---

## Findings Summary

| Severity | Count | Description |
|----------|-------|-------------|
| HIGH | 2 | Dead references in active code: HunterIO email-finder (L2 email waterfall) and Apify LinkedIn scraper — both in CLAUDE.md dead-ref table, no DEPRECATED marker |
| MEDIUM | 2 | Public method names `call_f3a` / `call_f3b` in gemini_client.py not annotated as legacy; active callers in cohort_runner use them without NOTE |
| MEDIUM | 2 | Active script files (f_refactor_e2e.py, f_cohort_100.py) use f3a/f3b variable names pervasively with no annotations |
| LOW | 2 | Schema files comprehend_schema_f3a.py / comprehend_schema_f3b.py: filename uses old nomenclature; version header says v2 not v2.1 |
| LOW | 1 | `lead card` docstring inconsistency in cohort_runner Stage 11 function |
| INFO | 9 | f3a_output / f3a_linkedin_url param names retained with correct NOTE comments — no action needed |
| INFO | 2 | stage_f3a_comprehend / stage_f3b_compile config keys — correctly DEPRECATED with notes |
