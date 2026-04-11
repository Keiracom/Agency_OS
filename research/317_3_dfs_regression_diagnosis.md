# Directive #317.3 — DFS second_date Regression Diagnosis

**Date:** 2026-04-11
**Agent:** research-1 (read-only audit, no code changes)
**Branch:** evo-008-claude-code-migration

---

## VERDICT

**a) Root cause of second_date bug (one sentence)**
`Layer2Discovery.pull_batch()` in `src/pipeline/layer_2_discovery.py` lines 416–419 hardcodes `second_date = date.today().strftime("%Y-%m-%d")` and passes it explicitly to `domain_metrics_by_categories`, which means the `or latest_date` fallback in the #304-FIX is never reached because non-None values bypass it.

**b) Why #304 fix did not cover this path (one sentence)**
The #304-FIX (`7f652b2`) only patched the default-value logic inside `DFSLabsClient.domain_metrics_by_categories()` — it did not audit callers that construct and pass explicit date strings, so `Layer2Discovery.pull_batch()` continued to override the fix by supplying `second_date=today` as a positional argument.

**c) Root cause of 0-AU-domains result (one sentence)**
`pull_batch` passes `second_date=2026-04-11` (today) to the DFS API, which is approximately 35 days ahead of the latest available monthly snapshot (~2026-03-07); the DFS API accepts the request with status 20000 but returns an empty `items` list because no data exists for that future-relative date window, causing `pull_batch` to return `[]` and the orchestrator to log `stage1_category_exhausted category=13686 offset=0`.

**d) Are other DFS call sites at risk? List them.**

| File | Method | Line | Date handling | At risk? |
|------|---------|------|---------------|----------|
| `src/pipeline/layer_2_discovery.py` | `pull_batch()` | 416–419 | Hardcodes `today` for both dates, passes explicitly | **YES — this is the regression** |
| `src/pipeline/layer_2_discovery.py` | `run()` | 221–225 | Passes no dates (None) → fix applies | Safe |
| `src/pipeline/discovery.py` | `pull_batch()` | 322–326 | Passes no dates (None) → fix applies | Safe |
| `src/pipeline/discovery.py` | `discover_prospects()` | 228–234 | Passes no dates (None) → fix applies | Safe |
| `src/pipeline/discovery.py` | `next_batch()` | 119–125 | Passes no dates (None) → fix applies | Safe |

---

## Evidence Trail

### Q1 — The #304-FIX

Commit `7f652b2` (2026-04-03, merged in `af1ad41`) added:
- `_available_history_date` instance cache
- `_get_latest_available_date()` async helper (hits `/v3/dataforseo_labs/google/available_history`, free endpoint)
- Updated `domain_metrics_by_categories()` default resolution:

```python
# BEFORE (#304-FIX)
today = date.today()
resolved_first_date = first_date or (today - timedelta(days=180)).strftime("%Y-%m-%d")
resolved_second_date = second_date or today.strftime("%Y-%m-%d")

# AFTER (#304-FIX)
latest_date = await self._get_latest_available_date()
latest_dt = date.fromisoformat(latest_date)
resolved_second_date = second_date or latest_date
resolved_first_date = first_date or (latest_dt - timedelta(days=180)).strftime("%Y-%m-%d")
```

The fix is ONLY in the `or` fallback. If a caller passes explicit dates, the fix is bypassed.

Source: `git show 7f652b2 -- src/clients/dfs_labs_client.py`

### Q2 — The validation script code path

`scripts/317_live_validation.py` line 153:
```python
discovery = Layer2Discovery(conn=pool, dfs=dfs_client)
```
Line 171–184: passes `discovery` to `PipelineOrchestrator`.

`PipelineOrchestrator.run()` line 524 calls:
```python
raw_domains = await self._discovery.pull_batch(category_code=..., location=..., ...)
```

`Layer2Discovery.pull_batch()` at lines 416–419:
```python
from datetime import date as _date, timedelta as _td
today = _date.today()
first_date = (today - _td(days=180)).strftime("%Y-%m-%d")
second_date = today.strftime("%Y-%m-%d")
```
Then at lines 428–433:
```python
results = await self._dfs.domain_metrics_by_categories(
    category_codes=[code_int],
    location_name=location,
    paid_etv_min=0.0,
    first_date=first_date,   # "2025-10-13"
    second_date=second_date, # "2026-04-11" ← exceeds available history
)
```

Source: `src/pipeline/layer_2_discovery.py:400–444`

### Q3 — All call sites

Five call sites in total across two files. Only `Layer2Discovery.pull_batch()` is at risk — it is the only one that constructs explicit date strings and passes them, overriding the #304-FIX.

```
grep -rn "domain_metrics_by_categories" src/ --include="*.py":
  src/pipeline/layer_2_discovery.py:221   (run — no dates → SAFE)
  src/pipeline/layer_2_discovery.py:428   (pull_batch — hardcoded today → BROKEN)
  src/pipeline/discovery.py:119           (next_batch — no dates → SAFE)
  src/pipeline/discovery.py:228           (discover_prospects — no dates → SAFE)
  src/pipeline/discovery.py:322           (pull_batch — no dates → SAFE)
  src/clients/dfs_labs_client.py:750      (the method itself)
```

### Q4 — 0-AU-domains investigation

The DFS API call in `pull_batch` succeeds (HTTP 200, `status_code=20000`) because `second_date=today` does not trigger a 40501 — the DFS API accepts the payload but returns an empty result set for a date that has no data.

Inside `domain_metrics_by_categories`, `swallow_no_data=False` is set (line 764), but this only matters for 40501 responses. A 20000 with empty `items` is returned as `{"items": [], "total_count": 0}` → `items = []` → `results = []` → `pull_batch` returns `[]`.

`PipelineOrchestrator.run()` line 534–536:
```python
if not raw_domains:
    logger.info("stage1_category_exhausted category=%s offset=%d", category_code, offset)
    break
```
This fires immediately at `offset=0` for every category, producing the observed log pattern.

The AU filter (`_is_au_domain`) is not the cause — it runs only inside `Layer2Discovery.run()` (the DB-write path, lines 253–262), not inside `pull_batch`. The `pull_batch` path only has an `organic_etv` range filter (etv_min=200, etv_max=5000) at line 439–443, but that is moot because the DFS response returns no items at all.

### Q5 — Other call sites at risk

Only `Layer2Discovery.pull_batch()` passes explicit hardcoded dates. All other callers pass no dates and therefore correctly use `_get_latest_available_date()`.

---

## Files Referenced

- `src/clients/dfs_labs_client.py` — lines 667–790 (`_get_latest_available_date`, `domain_metrics_by_categories`)
- `src/pipeline/layer_2_discovery.py` — lines 400–444 (`pull_batch` — broken), 220–225 (`run` — safe)
- `src/pipeline/discovery.py` — lines 119–125, 228–234, 302–340 (all safe)
- `src/pipeline/pipeline_orchestrator.py` — lines 524–536 (`stage1_category_exhausted` logic)
- `scripts/317_live_validation.py` — lines 122–184 (uses `Layer2Discovery`)
- `scripts/output/317_validation.json` — confirmed `prospects_built: 0` from this run

---

## Fix Required (not implemented here — read-only audit)

Remove the hardcoded date construction from `Layer2Discovery.pull_batch()` lines 416–419. Either:
1. Delete lines 416–419 and lines 432–433 (let `domain_metrics_by_categories` resolve dates via `_get_latest_available_date()`), or
2. Replace with `await self._dfs._get_latest_available_date()` to compute correct dates.

Option 1 is simpler and consistent with all other callers.
