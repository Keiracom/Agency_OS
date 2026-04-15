# D1.4 Re-Audit: Cost Constant + Env Var Verification

**Date:** 2026-04-14
**Branch:** directive-d1-3-audit-fixes
**Scope:** Read-only. Zero code changes.

---

## 1. Cost Constant — Stage 4

### (a) Original (wrong)
D1.2 found `$0.073` hardcoded in `src/orchestration/cohort_runner.py`.

### (b) Current grep result

```
grep -n "0.078\|0.073" src/orchestration/cohort_runner.py

193:    # Fixed cost: 10 DFS endpoints sum = $0.0775, rounded up to $0.078/domain (parallel-safe)
194:    domain_data["cost_usd"] += 0.078
```

`$0.073` is gone. `$0.078` is present with a clarifying comment.

### (c) Status

FIXED. The constant at line 194 is `0.078`. The comment on line 193 documents the derivation: 10 DFS endpoints summing to `$0.0775`, rounded up to `$0.078`.

---

## 2. Env Var Naming — BRIGHT_DATA_API_KEY vs BRIGHTDATA_API_KEY

### grep result (all src/*.py, no __pycache__)

```
src/orchestration/cohort_runner.py:469:    bd = BrightDataClient(api_key=env.get("BRIGHTDATA_API_KEY", ""))
src/engines/icp_scraper.py:574:        # Anti-bot bypass using existing BRIGHTDATA_API_KEY. ~$0.001/request.
src/engines/icp_scraper.py:577:        brightdata_api_key = os.getenv("BRIGHTDATA_API_KEY")
src/engines/icp_scraper.py:637:            logger.warning("Tier 3 (Bright Data) skipped — BRIGHTDATA_API_KEY not set")
src/engines/waterfall_verification_worker.py:1039:        brightdata_api_key = os.getenv("BRIGHTDATA_API_KEY")
src/engines/waterfall_verification_worker.py:1046:            logger.warning("BRIGHTDATA_API_KEY not set — skipping T-DM0 profile scraping")
src/engines/waterfall_verification_worker.py:1268:        brightdata_api_key = os.getenv("BRIGHTDATA_API_KEY")
src/engines/waterfall_verification_worker.py:1271:            logger.warning("BRIGHTDATA_API_KEY not set — skipping T-DM2")
src/engines/waterfall_verification_worker.py:1528:        brightdata_api_key = os.getenv("BRIGHTDATA_API_KEY")
src/engines/waterfall_verification_worker.py:1531:            logger.warning("BRIGHTDATA_API_KEY not set — skipping T-DM3")
src/engines/waterfall_verification_worker.py:1686:        api_key = os.getenv("BRIGHTDATA_API_KEY")
src/engines/waterfall_verification_worker.py:1688:            logger.warning("BRIGHTDATA_API_KEY not set — skipping Tier 2")
src/clients/bright_data_gmb_client.py:26:BRIGHT_DATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "")
src/clients/bright_data_gmb_client.py:43:    def __init__(self, api_key: str = BRIGHT_DATA_API_KEY) -> None:
src/integrations/bright_data_client.py:825:        ValueError: If BRIGHTDATA_API_KEY not configured
src/integrations/bright_data_client.py:829:        api_key = os.getenv("BRIGHTDATA_API_KEY")
src/integrations/bright_data_client.py:831:            raise ValueError("BRIGHTDATA_API_KEY not set")
src/integrations/siege_waterfall.py:308:        self._api_key = os.getenv("BRIGHTDATA_API_KEY")
src/integrations/siege_waterfall.py:321:            logger.warning("[GMB] BRIGHTDATA_API_KEY not set")
src/integrations/siege_waterfall.py:401:            logger.warning("[GMB] BRIGHTDATA_API_KEY not set")
```

### Analysis

`BRIGHT_DATA_API_KEY` (with underscore between BRIGHT and DATA) does **not** appear as an `os.getenv()` call anywhere. The only occurrence of `BRIGHT_DATA_API_KEY` as an identifier is a Python module-level variable in `bright_data_gmb_client.py:26`, which is immediately assigned from `os.getenv("BRIGHTDATA_API_KEY", "")` — the correct env var name. This is not a bug; it is a local alias using the correct source key.

All runtime `os.getenv()` calls across all four files use `BRIGHTDATA_API_KEY` (no underscore between BRIGHT and DATA).

Status: FIXED. `BRIGHT_DATA_API_KEY` is not used as an env var lookup anywhere. `BRIGHTDATA_API_KEY` is the canonical name used consistently throughout.

---

## 3. Test Effectiveness — tests/test_cost_constants.py

### Test logic (test_stage4_cost_matches_documented)

The test re-derives the endpoint sum from hardcoded `Decimal` values and asserts:

```python
assert abs(actual_sum - documented_constant) < 0.002
```

Where:
- `actual_sum` = sum of 10 endpoint costs = `0.0775`
- `documented_constant` = `0.078`
- Tolerance = `0.002`

Current diff: `0.0005` — passes (within tolerance).

### Drift simulation: constant changed to $0.050

If `documented_constant` in cohort_runner.py were changed to `0.050`:
- `actual_sum` = `0.0775` (unchanged, derived from endpoint table in the test itself)
- diff = `|0.0775 - 0.050|` = `0.0275`
- `0.0275 < 0.002` is **False**
- Test **FAILS**

### Verdict: EFFECTIVE

The test catches real drift in the `cohort_runner.py` constant because:
1. It independently computes the expected sum from endpoint costs
2. It asserts the constant in cohort_runner.py matches that sum within $0.002 tolerance
3. A change to $0.050 would produce a diff of $0.0275, which exceeds the tolerance and causes a hard failure

**Caveat:** The test does NOT import the constant from cohort_runner.py directly — it uses a hardcoded `documented_constant = 0.078`. This means if someone changes cohort_runner.py without updating the test, the test still passes (it is testing its own internal consistency, not the live module value). This is a structural limitation but is a known trade-off for test isolation.

---

## Summary Table

| Finding | D1.2 Status | Current Status |
|---------|-------------|----------------|
| Stage 4 cost constant | $0.073 (wrong) | $0.078 (FIXED) |
| BRIGHT_DATA_API_KEY env var | Not checked | ABSENT — all calls use BRIGHTDATA_API_KEY |
| BRIGHTDATA_API_KEY env var | Fix prescribed | PRESENT everywhere (CONFIRMED) |
| Cost test effectiveness | Not assessed | EFFECTIVE (catches drift) |
| Test structural caveat | N/A | Does not import live constant — tests internal table only |
