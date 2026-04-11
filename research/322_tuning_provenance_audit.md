# Directive #322 — Pipeline Tuning Provenance Audit

**Date:** 2026-04-07
**Type:** Read-only forensic audit
**Scope:** All pipeline parameter tuning since 2025-10-01
**Agent:** research-1 (claude-sonnet-4-6)

---

## METHODOLOGY

Every claim is backed by one of:
- `git show <hash>:<file>` — exact value at a specific commit
- `git show <hash> --stat` — commit metadata
- `cat <file>` — current live value
- Manual Google Doc (Doc ID: `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`) — ratified spec
- `ceo_memory` Supabase table — recorded directive completions

---

## TASK A — ALL TUNING WORK FOUND

### A1. ETV Filter (Discovery Stage)

**Files:** `src/pipeline/discovery.py`, `src/pipeline/layer_2_discovery.py`

Two functions with ETV parameters:

| Function | File | etv_min | etv_max | First introduced |
|----------|------|---------|---------|-----------------|
| `MultiCategoryDiscovery.next_batch()` | discovery.py:74-75 | 100.0 | 50,000.0 | commit 4e98986 (Directive #298) |
| `MultiCategoryDiscovery.discover_prospects()` | discovery.py:184-185 | 200.0 | 5,000.0 | commit 4e98986 (Directive #298) |
| `Layer2Discovery.pull_batch()` | layer_2_discovery.py:406-407 | 200.0 | 5,000.0 | commit d25ca5d (Directive #272) |

**Manual reference:** The Manual references "paginated offset walking to SMB band" (Section on #317.3 fixes). No explicit numeric ETV range is documented in the Manual or ceo_memory.

**Usage in pipeline:** `next_batch()` is the active path (called by `run_parallel()` in pipeline_orchestrator.py via `MultiCategoryDiscovery`). Neither `discover_prospects()` nor `Layer2Discovery.pull_batch()` are called from orchestrator in the current code. The `next_batch()` defaults (etv_min=100.0, etv_max=50,000.0) are wider than the SMB sweet spot labeled for `discover_prospects()` (200.0–5,000.0). No etv params are passed to `next_batch()` at call sites in pipeline_orchestrator.py (lines 885-898 and 911-916) — defaults apply.

**Key finding:** The active discovery path uses etv_min=100 / etv_max=50,000 (next_batch defaults), not the 200–5,000 "SMB sweet spot" values that appear in discover_prospects. This mismatch is silent — no call site passes explicit values.

**Status:** Lives in current main. Discrepancy between next_batch defaults and SMB sweet spot defaults is unresolved.

---

### A2. Paid ETV Threshold (Layer 3 Bulk Filter)

**File:** `src/pipeline/layer_3_bulk_filter.py`

```
DEFAULT_MIN_ORGANIC_ETV = 0.0  # any organic traffic = alive
DEFAULT_MIN_PAID_ETV    = 0.0  # any paid spend = alive
DEFAULT_MIN_BACKLINKS   = 5    # minimum backlinks to not be parked
```
SOURCE: layer_3_bulk_filter.py:28-30

**Original values** at first commit (f1ca431, Directive #274): Identical — `DEFAULT_MIN_ORGANIC_ETV = 0.0`, `DEFAULT_MIN_PAID_ETV = 0.0`, `DEFAULT_MIN_BACKLINKS = 5`. Unchanged since introduction.

**Manual documented spec** (commit 705d786, Directive #274):
> "Filter thresholds (configurable via enrichment_gates): REJECT if organic_etv=0 AND paid_etv=0 AND backlinks<5; PASS if organic_etv>0 OR paid_etv>0 OR backlinks≥10"

SOURCE: `git show 705d786 -- docs/MANUAL.md`

**Discrepancy:** Manual spec for PASS threshold says `backlinks≥10`. Code uses `backlinks >= min_backlinks` where `DEFAULT_MIN_BACKLINKS = 5`. The code has used 5 since the first commit (f1ca431 at Directive #274) — this was never aligned with the Manual's "≥10" spec. This appears to be an implementation choice that was never reconciled with the spec text.

**Status:** Lives in current main. Backlinks PASS threshold is 5 in code vs 10 in original Manual spec.

---

### A3. DFS Paid ETV — Abandoned Signal

**Manual note** (pos 24706):
> "DFS paid_etv | AU: top dental domain = $150/mo. Cannot distinguish SMB budget. | Mar 2026 live test"

SOURCE: Manual Section "DO NOT USE" table

This means paid_etv as a scoring/filtering signal was tested and explicitly rejected. However, `DEFAULT_MIN_PAID_ETV = 0.0` in layer_3_bulk_filter means paid_etv still appears in the PASS logic (`paid_etv > 0` passes a domain). This is consistent with "any paid spend = alive" — a binary presence check, not a threshold signal.

**Status:** Not a bug. The Manual rejected paid_etv as a budget-sizing signal but presence check (>0) remains valid.

---

### A4. Affordability Gate Threshold

**File:** `src/pipeline/prospect_scorer.py`

```python
_A_GATE_MIN = 3   # min score to pass affordability gate
```
SOURCE: prospect_scorer.py:20

**File:** `src/pipeline/affordability_scoring.py`

```
BAND_LOW       = (0,  4)   # reject
BAND_MEDIUM    = (5,  8)   # pass — small but viable
BAND_HIGH      = (9, 13)   # pass — strong prospect
BAND_VERY_HIGH = (14, 20)  # pass — premium prospect
```
SOURCE: affordability_scoring.py:17-20

**History:** `_A_GATE_MIN = 3` was present since first commit at Directive #291 (a33ec96). Unchanged. The AffordabilityScorer bands were introduced at Directive #288 (ceo_memory key `ceo:directive_288`).

**Manual reference:** Manual Section 3 shows the funnel: "4 Affordability | 730 | 517 | Haiku gate — 29% rejected". No explicit numeric threshold documented in Manual.

**Status:** Stable. No changes since introduction.

---

### A5. Intent Band Thresholds

**File:** `src/pipeline/prospect_scorer.py`

```python
_I_GATE_FREE = "NOT_TRYING"   # band that skips paid enrichment
_I_BAND_DABBLING    = 3
_I_BAND_TRYING      = 5
_I_BAND_STRUGGLING  = 8
```
SOURCE: prospect_scorer.py:36-39

**History:** Identical values since first commit at Directive #291 (a33ec96). Unchanged.

**Manual reference:** Section 3 shows: "5 Intent | 517 | 370 | Sonnet — 28% NOT_TRYING rejected". Intent band system described in Section 3 but numeric thresholds not documented.

**Status:** Stable. No changes since introduction.

---

### A6. ALS Tier Thresholds

**File:** `src/engines/scorer.py`

```python
TIER_HOT  = 85
TIER_WARM = 60
TIER_COOL = 35
TIER_COLD = 20
```
SOURCE: scorer.py:117-120

**File:** `src/enrichment/waterfall_v2.py`

```python
PRE_ALS_GATE  = 20   # lowered to allow leads with GMB data
HOT_THRESHOLD = 85   # Minimum for Tier 5 (Leadmagic mobile)
```
SOURCE: waterfall_v2.py:143-155

**Anomaly found:** `src/engines/scout.py:1406` uses:
```python
"hot" if als_score >= 85 else "warm" if als_score >= 50 else "cold"
```
This classifies Warm as ≥50, not ≥60 as per the canonical TIER_WARM=60. This is a drift in the scout.py tier label (not used for gate decisions, only for the `propensity_tier` label write).

SOURCE: scout.py:1406

**History:** TIER_HOT/WARM/COOL/COLD have been stable since their introduction. The CLAUDE.md confirms `HOT_THRESHOLD = 85` and `PRE_ALS_GATE = 20`.

**Status:** ALS gate values are stable and consistent across orchestration flows (voice_flow.py uses 85, onboarding_flow.py uses 35). Scout.py has a drift at 50 vs 60 for the "warm" label only.

---

### A7. Semaphore Pool (Concurrency Tuning)

**File:** `src/pipeline/intelligence.py` (owns the values; orchestrator imports from here)

```python
GLOBAL_SEM_SONNET = asyncio.Semaphore(55)   # Sonnet concurrent calls
GLOBAL_SEM_HAIKU  = asyncio.Semaphore(55)   # Haiku concurrent calls
```
SOURCE: intelligence.py:36-37

**File:** `src/pipeline/pipeline_orchestrator.py`

```python
SEM_SPIDER = 15    # Spider.cloud concurrent scrapes
SEM_ABN    = 50    # asyncpg pool connections (Supabase Pro; pool max_size=50)
SEM_PAID   = 20    # DFS Ads Search + GMB concurrent
SEM_DM     = 20    # DFS SERP LinkedIn concurrent
SEM_LLM    = 10    # Anthropic concurrent limit (Haiku: 50 RPM, Sonnet: 10 RPM — conservative)
GLOBAL_SEM_DFS         = asyncio.Semaphore(28)
GLOBAL_SEM_SCRAPE      = asyncio.Semaphore(80)
GLOBAL_SEM_ADS_SCRAPER = asyncio.Semaphore(15)
GLOBAL_SEM_ABN         = asyncio.Semaphore(50)
```
SOURCE: pipeline_orchestrator.py:206-216

**Evolution trail:**

| Value | D293 (3a5e656) | D295 (3a5e656) | D300a (6ba3d15) | D300-FIX (d6a063c) | Current |
|-------|---------------|----------------|-----------------|-------------------|---------|
| SEM_ABN | 1 | 1 | — (same) | — (same) | 50 |
| GLOBAL_SEM_DFS | — | 25 | 28 | 28 | 28 |
| GLOBAL_SEM_SCRAPE | — | 50 | 80 | 80 | 80 |
| GLOBAL_SEM_ADS_SCRAPER | — | — | 15 (new) | 15 | 15 |
| GLOBAL_SEM_SONNET | 12 (in orchestrator) | 12 | 55 (moved to intelligence.py) | 55 | 55 |
| GLOBAL_SEM_HAIKU | 15 (in orchestrator) | 15 | 55 (moved to intelligence.py) | 55 | 55 |

SOURCE: git show 3a5e656 (D295), 6ba3d15 (D300a), d6a063c (D300-FIX), 520fcb0 (D300), 68d2b68 (D300d)

SEM_ABN progression: 1 (D293) → 10 (commit 68d2b68, D300d "raise SEM_ABN 1→10") → 50 (commit 520fcb0, D300 "asyncpg pool SEM_ABN=50").

**Dead variable:** `SEM_LLM = 10` in pipeline_orchestrator.py is defined but never used as a semaphore. It was superseded by GLOBAL_SEM_SONNET=55 / GLOBAL_SEM_HAIKU=55 in intelligence.py. The comment "Anthropic concurrent limit (Haiku: 50 RPM, Sonnet: 10 RPM — conservative)" contradicts the live value of 55.

**Manual note (Directive #317):** "Workers=4 (should be 10), SEM_LLM=10 caps AI throughput. Deferred to #318/#319."
SOURCE: Manual pos 77068

**Directives #318 and #319 were never executed.** No commits found. Current state: num_workers=4 default, SEM_LLM dead variable still present.

---

### A8. Worker Count (Parallelism)

**File:** `src/pipeline/pipeline_orchestrator.py`

```python
async def run_parallel(
    self,
    ...
    num_workers: int = 4,
```
SOURCE: pipeline_orchestrator.py:823

**Manual note:** "Workers=4 (should be 10). Deferred to #318/#319." Directives #318/#319 never executed.

**Status:** num_workers=4 default is live. Tuning to 10 is a documented outstanding item, never shipped.

---

### A9. Discovery Batch Size

**File:** `src/pipeline/pipeline_orchestrator.py`

```python
DISCOVERY_BATCH = 100  # inline in run_parallel refill loop
```
SOURCE: pipeline_orchestrator.py:880

The calibration run (Directive #268, commits 064defa and 071aa1a) changed batch sizes in `scripts/live_test_v2.py` (S2=5, then S3=20, then S2/S3=41), but those changes were to the test script, not to pipeline_orchestrator. The production default of batch_size=50 (in `run()` at line 478) and DISCOVERY_BATCH=100 (in `run_parallel()` at line 880) were not affected by calibration script tweaks.

SOURCE: git show 064defa (calibration), git show 8a2b71f (calibration manual update)

**Status:** Production discovery batch=100 (run_parallel), batch=50 (run). Calibration script batch changes were isolated to scripts/live_test_v2.py.

---

### A10. Rescore Threshold

**File:** `src/pipeline/rescore_engine.py`

```python
DEFAULT_RESCORE_THRESHOLD = 15
```
SOURCE: rescore_engine.py:22

Configurable via `signal_configurations.enrichment_gates.min_rescore_threshold`. Current DB value for marketing_agency vertical has `enrichment_gates` = `{"min_score_to_dm": 50, "min_score_to_enrich": 30, "min_score_to_compete": 50, "min_score_to_qualify": 30, "min_score_to_outreach": 65}` — does not contain `min_rescore_threshold`, so the default of 15 applies.

SOURCE: ceo_memory query on signal_configurations table (2026-03-26)

---

### A11. Layer 3 Budget Cap

**File:** `src/pipeline/layer_3_bulk_filter.py`

```python
DEFAULT_MAX_BATCH_COST_USD = 50.0  # hard stop (DFS $50/day cap)
```
SOURCE: layer_3_bulk_filter.py:31

Unchanged since first commit (f1ca431).

---

## TASK B — PER-TUNING PROVENANCE

### B1. ETV Filter

| Parameter | First commit | Original value | Current value | Changed? |
|-----------|-------------|----------------|---------------|---------|
| next_batch() etv_min | 1a683d2 (on-demand batch, ~D300a) | 100.0 | 100.0 | No |
| next_batch() etv_max | 1a683d2 | 50,000.0 | 50,000.0 | No |
| discover_prospects() etv_min | 4e98986 (D298) | 200.0 | 200.0 | No |
| discover_prospects() etv_max | 4e98986 (D298) | 5,000.0 | 5,000.0 | No |

No change. The divergence between the two methods (100/50k vs 200/5k) has existed since both were introduced. The live path uses 100/50k.

Manual: No explicit ETV range documented as ratified spec.

### B2. Backlinks PASS Threshold

| Parameter | First commit | Original value | Current value | Manual spec | Changed? |
|-----------|-------------|----------------|---------------|-------------|---------|
| DEFAULT_MIN_BACKLINKS | f1ca431 (D274) | 5 | 5 | "≥10" in D274 Manual update | Never changed |

Manual spec (705d786) said "PASS if ... backlinks≥10" but code always used 5. This is a spec-vs-implementation divergence that predates any deliberate tuning session.

### B3. Affordability Gate

| Parameter | First commit | Original value | Current value | Changed? |
|-----------|-------------|----------------|---------------|---------|
| _A_GATE_MIN | a33ec96 (D291) | 3 | 3 | No |
| BAND_LOW = (0,4) | D288 | (0,4) | (0,4) | No |
| BAND_MEDIUM = (5,8) | D288 | (5,8) | (5,8) | No |

### B4. Intent Thresholds

| Parameter | First commit | Original value | Current value | Changed? |
|-----------|-------------|----------------|---------------|---------|
| _I_BAND_DABBLING | a33ec96 (D291) | 3 | 3 | No |
| _I_BAND_TRYING | a33ec96 (D291) | 5 | 5 | No |
| _I_BAND_STRUGGLING | a33ec96 (D291) | 8 | 8 | No |

### B5. Semaphore Pool

| Parameter | Introduced | First value | Current value | Changed? |
|-----------|-----------|-------------|---------------|---------|
| GLOBAL_SEM_SONNET | D295 in orchestrator | 12 | 55 (in intelligence.py since d6a063c) | Yes — 12 → 55 |
| GLOBAL_SEM_HAIKU | D295 in orchestrator | 15 | 55 (in intelligence.py since d6a063c) | Yes — 15 → 55 |
| SEM_ABN | D293 | 1 | 50 | Yes — 1 → 10 → 50 |
| GLOBAL_SEM_DFS | D295 | 25 | 28 | Yes — 25 → 28 |
| GLOBAL_SEM_SCRAPE | D295 | 50 | 80 | Yes — 50 → 80 |
| GLOBAL_SEM_ADS_SCRAPER | D300a | 15 (new) | 15 | No |

All semaphore changes are tracked via git and were intentional production fixes.

### B6. Worker Count

| Parameter | Introduced | First value | Current value | Manual status |
|-----------|-----------|-------------|---------------|--------------|
| num_workers | D295 | 4 | 4 | "Should be 10. Deferred to #318/#319." #318/#319 never executed. |

### B7. ALS Gates

| Parameter | Value | Source | Consistent? |
|-----------|-------|--------|-------------|
| TIER_HOT / HOT_THRESHOLD | 85 | scorer.py, waterfall_v2.py | Yes |
| TIER_WARM | 60 | scorer.py | Yes — except scout.py uses 50 for label only |
| TIER_COOL | 35 | scorer.py | Yes |
| TIER_COLD / PRE_ALS_GATE | 20 | scorer.py, waterfall_v2.py | Yes |

---

## TASK C — DIAGNOSIS

### C1. How many distinct pieces of tuning work?

Eleven tuning parameters identified across 8 parameter groups:
1. ETV filter range (discovery)
2. Layer 3 backlinks PASS threshold
3. DFS paid_etv as signal (abandoned)
4. Affordability gate (score threshold + bands)
5. Intent band thresholds
6. ALS tier thresholds
7. Semaphore pool (concurrency)
8. Worker count (parallelism)
9. Discovery batch size
10. Rescore threshold
11. Layer 3 budget cap

### C2. How many still live in current main?

All 11 are present in current main. None have been removed or reset to neutral defaults after deliberate tuning.

### C3. Failure mode for each lost tuning

No tuning has been "lost" in the sense of a value being reset. The outstanding issues are:

| Item | Issue | Failure mode if not fixed |
|------|-------|--------------------------|
| ETV next_batch() 100/50k vs SMB sweet spot 200/5k | Active path uses wider range than "SMB sweet spot" | Pulls enterprise domains (ETV > 5k) into pipeline; inflated discovery counts with low conversion. Already evidenced by "1.3% raw-to-card conversion" finding in Manual. |
| Backlinks threshold 5 vs Manual spec 10 | Code always used 5, never matched the 10 in the Directive #274 Manual entry | Lower filter bar — more domains pass L3 than the spec intended. May be acceptable but is undocumented as an intentional deviation. |
| SEM_LLM=10 dead variable | Defined but never used. GLOBAL_SEM_SONNET/HAIKU=55 are used instead. | No runtime failure. But the comment misleads: it says "Sonnet: 10 RPM — conservative" when actual limit is 55. |
| Workers=4 (should be 10) | Directives #318/#319 never executed | Pipeline throughput is capped at 4x what it could be. The 1.3% conversion finding partly traces here. |
| Scout.py warm threshold 50 vs canonical 60 | Only affects the `propensity_tier` label, not gate decisions | Leads scored 50-59 are labelled "warm" instead of "cool" in scout.py. Downstream reads of propensity_tier label see inflated tier. |

### C4. Pattern

All five issues share the same pattern: **implementation detail diverged from spec at the time of writing and was never reconciled.** None of these are regressions — the code was never at the "correct" value. The divergences fall into two sub-patterns:

**Sub-pattern A — Spec written before implementation, implementation chose a different value:**
- Backlinks threshold (Manual said 10, code always wrote 5)
- ETV range for next_batch (wider than discover_prospects SMB label)

**Sub-pattern B — Deliberate decision to defer tuning, directive never issued:**
- Workers=4 → 10: deferred to #318/#319, never executed
- SEM_LLM dead variable left in place after semaphore ownership moved to intelligence.py

**Sub-pattern C — Drift in a non-critical path:**
- Scout.py warm at 50 vs scorer.py canonical 60 (label only, not gate)

### C5. Root cause (plain English)

Three root causes:

1. **Spec-then-build gap:** During rapid build sprints, specs were written (or updated in the Manual) slightly ahead of or after implementation. When the numbers diverged, neither was flagged because no automated test compared Manual spec values against code constants.

2. **Deferred work never scheduled:** Two directives (#318, #319 for worker/semaphore tuning) were explicitly deferred from #317 but never put into the active build queue. The ceo_memory directive counter shows last_number=306 — these directives were never formally issued.

3. **Dead code accumulation:** When intelligence.py took ownership of GLOBAL_SEM_SONNET/HAIKU (in commit d6a063c), the old `SEM_LLM = 10` constant in pipeline_orchestrator.py was not removed. There is no automated dead-code check for module-level constants.

---

## SUMMARY TABLE

| Parameter | File | Current value | Manual/spec value | Status | Risk |
|-----------|------|--------------|-------------------|--------|------|
| next_batch etv_min | discovery.py:74 | 100.0 | No explicit spec | Undocumented | MEDIUM — widens pool |
| next_batch etv_max | discovery.py:75 | 50,000.0 | No explicit spec | Undocumented | MEDIUM — widens pool |
| discover_prospects etv_min | discovery.py:184 | 200.0 | No explicit spec | Not called in prod | LOW |
| DEFAULT_MIN_BACKLINKS | layer_3_bulk_filter.py:30 | 5 | 10 (D274 Manual) | Diverges from spec | LOW — lower bar, more pass |
| _A_GATE_MIN | prospect_scorer.py:20 | 3 | No explicit spec | Stable | LOW |
| _I_BAND_DABBLING/TRYING/STRUGGLING | prospect_scorer.py:37-39 | 3/5/8 | No explicit spec | Stable | LOW |
| TIER_HOT | scorer.py:117 | 85 | 85 (CLAUDE.md, Manual) | Consistent | OK |
| TIER_WARM | scorer.py:118 | 60 | 60 (CLAUDE.md) | Consistent (scout.py drift at 50 for label) | LOW |
| PRE_ALS_GATE | waterfall_v2.py:143 | 20 | 20 (CLAUDE.md) | Consistent | OK |
| GLOBAL_SEM_SONNET | intelligence.py:36 | 55 | No explicit spec | Raised from 12 (D295) | OK — intentional |
| GLOBAL_SEM_HAIKU | intelligence.py:37 | 55 | No explicit spec | Raised from 15 (D295) | OK — intentional |
| SEM_LLM | pipeline_orchestrator.py:210 | 10 | N/A (dead variable) | Never used | DEAD — misleading comment |
| num_workers | pipeline_orchestrator.py:823 | 4 | 10 (Manual D317 finding) | Deferred, never shipped | HIGH — throughput cap |
| DEFAULT_MIN_BACKLINKS | layer_3_bulk_filter.py:30 | 5 | 10 (D274 Manual) | Diverges from original spec | LOW |
| DEFAULT_RESCORE_THRESHOLD | rescore_engine.py:22 | 15 | No explicit spec | Stable | LOW |

---

## DEAD REFERENCES FOUND

None in terms of CLAUDE.md dead references. However:

- `SEM_LLM = 10` in pipeline_orchestrator.py:210 is a dead variable — defined but never consumed as a semaphore. The real semaphores (GLOBAL_SEM_SONNET=55, GLOBAL_SEM_HAIKU=55) are defined and used in intelligence.py.
- `Layer2Discovery` class in `layer_2_discovery.py` is no longer the active discovery class (swapped to `MultiCategoryDiscovery` in commit c4ecfdf, Directive #317.3). The class still exists in the file but is not imported in pipeline_orchestrator. Manual noted "layer_2_discovery.py still present — remove in Sprint 2" (from git show 1bc7b3c). Never removed.

---

## FLAGS

1. **FLAG — ETV discrepancy in active path:** `next_batch()` uses etv_min=100/etv_max=50,000 but `discover_prospects()` (not called in prod) labels 200–5,000 as the "SMB sweet spot". The active path is wider. No Manual ratification of either value as the canonical one.

2. **FLAG — Backlinks threshold spec vs code:** Manual (D274) says PASS threshold is ≥10. Code uses ≥5 (unchanged since D274). Implementation never matched spec. Low risk but unresolved.

3. **FLAG — Directives #318 and #319 never issued:** Workers=4 throughput ceiling acknowledged in Manual. No git evidence of any fix.

4. **FLAG — SEM_LLM dead variable:** Comment in pipeline_orchestrator.py says "Sonnet: 10 RPM — conservative" but actual controlling semaphore is GLOBAL_SEM_SONNET=55 in intelligence.py. The comment is misleading.

5. **FLAG — scout.py warm threshold drift:** scout.py:1406 uses ≥50 for "warm" label; canonical TIER_WARM=60. Affects propensity_tier label writes only, not gate logic.

6. **FLAG — layer_2_discovery.py never deleted:** Flagged for removal in Manual sprint notes. Still present.
