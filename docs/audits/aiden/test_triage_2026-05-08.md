# Test Triage — Phase 1 A3 Pre-Work

**To:** Dave (CEO), Max (COO), Elliot (peer)
**From:** Aiden
**Compiled:** 2026-05-08
**Source:** `python3 -m pytest --tb=line --no-header -rfE` against `aiden/test-triage-doc` branched off `main` at commit `11b098c3`.

---

## RAW SUMMARY

```
28 failed, 3391 passed, 28 skipped, 4 deselected, 26 xfailed, 185 warnings, 16 errors in 213.21s
```

- **Total:** 3,489 tests collected, 3,391 passing (97.2%)
- **A3 deliverable:** drive failures (28) + errors (16) → 0
- **Drift since Phase 2 baseline (25/16):** +3 failures inherited from PR #613 currency refactor (BD `COSTS_AUD` → `COSTS_USD` rename surfaced in tests)

---

## CATEGORIZATION BY ROOT CAUSE

### Cluster 1 — DNCR client (13 failures, single root cause)

**Files:** `tests/integrations/test_dncr_client.py`

**Verbatim error from sample test:**
```
tests/integrations/test_dncr_client.py:60: in test_registered_true
    client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
E   TypeError: DNCRClient.__init__() got an unexpected keyword argument 'http_client'
```

**Diagnosis:** `DNCRClient.__init__()` signature changed (likely refactored param name); tests still pass `http_client=` which the constructor no longer accepts. Single fix touches all 13 tests via shared fixture/setup, OR fix is in `src/integrations/dncr.py` to re-add `http_client=` as an alias.

**Failures:**
1. `TestHappyPathRegistered::test_registered_true`
2. `TestHappyPathNotRegistered::test_registered_false`
3. `TestMissingApiKey::test_no_api_key_returns_degraded`
4. `TestNetworkTimeout::test_timeout_returns_degraded`
5. `TestHTTP500::test_500_returns_degraded_network`
6. `TestHTTP429::test_rate_limited`
7. `TestInvalidJSON::test_bad_json_returns_degraded_parse`
8. `TestCacheHit::test_second_call_uses_cache`
9. `TestCacheExpiry::test_expired_cache_refetches`
10. `TestDegradedNotCached::test_degraded_not_cached_retry_succeeds`
11. `TestPhoneNormalisation::test_variants_share_cache_entry`
12. `TestNeverRaises::test_empty_string_no_raise`
13. `TestNeverRaises::test_garbage_input_no_raise`

**Estimated A3 fix effort:** 1 root cause + 13 affected tests, ~30-45min.

---

### Cluster 2 — Scout engine (15 errors, collection-time)

**Files:** `tests/test_engines/test_scout.py`

**Diagnosis:** All 15 tests are `ERROR` not `FAILED`, indicating collection-time failure (probably import error). `tests/test_engines/test_scout.py` imports `from src.engines.scout import CONFIDENCE_THRESHOLD, REQUIRED_FIELDS, ScoutEngine, get_scout_engine`. The `src.engines.scout` module may have been refactored after the siege_waterfall consolidation.

**Errors:**
1. `TestScoutEngineProperties::test_engine_name`
2-6. `TestEnrichmentValidation::*` (5 tests)
7-8. `TestCacheBehavior::*` (2 tests)
9-10. `TestWaterfallTiers::*` (2 tests)
11. `TestBatchEnrichment::test_batch_enrichment_summary`
12-13. `TestEnrichmentMerge::*` (2 tests)
14-15. `TestHelperFunctions::*` (2 tests)

**Estimated A3 fix effort:** Single import fix likely unblocks all 15. Probably ~15-30min if it's a renamed export.

---

### Cluster 3 — Bright Data costs (3-5 failures, surfaced by PR #613)

**Files:** `tests/integrations/test_bright_data_client.py`

**Verbatim test code:**
```python
def test_serp_cost(self):
    from integrations.bright_data_client import COSTS_AUD
    assert COSTS_AUD["serp_request"] == 0.0015
```

**Diagnosis:** Test imports `COSTS_AUD` which was **renamed to `COSTS_USD`** by PR #613 (currency refactor). The constant value 0.0015 is now stored under `COSTS_USD` (USD). For AUD assertion, test should call `_cost_aud()` helper.

**Failures:**
1. `TestCosts::test_serp_cost` (likely × parametrize giving the duplicate listing)
2. `TestCosts::test_scraper_cost`
3. `TestCostTracking::test_cost_calculation`

**Note:** This is a regression from PR #613 that PR #613 didn't catch in its own pytest run (it added test_leadmagic_client.py + test_dfs_serp_client.py updates but missed test_bright_data_client.py). Sub-cluster of Cluster 5 (PR #613 follow-on).

**Estimated A3 fix effort:** ~15min — rename `COSTS_AUD` → `COSTS_USD` in 2-3 test files OR change assertions to use `_cost_aud("serp_request") == 0.0023`.

---

### Cluster 4 — Siege Waterfall references (3 fail + 1 error)

**Files:** `tests/test_siege_enhancements.py`

**Failures + 1 error:**
1. `TestAustralianLeadNoApolloFallback::test_au_lead_siege_fails_returns_none` (FAIL)
2. `TestAustralianLeadNoApolloFallback::test_non_au_lead_uses_siege` (FAIL)
3. `TestMockDataEnrichment::test_au_lead_siege_enrichment` (FAIL)
4. `TestAustralianLeadNoApolloFallback::test_au_lead_uses_siege` (ERROR)

**Diagnosis:** Likely related to the F2.2 / "Siege Waterfall deprecated" rename per Dave's correction 2026-05-08. The test file name itself (`test_siege_enhancements.py`) is on borrowed time. Fix shape depends on whether siege_waterfall.py module still exists or got renamed.

**Estimated A3 fix effort:** Investigation needed — could be ~15-30min (import rename) or ~1-2hr (semantic refactor following code reorg).

---

### Cluster 5 — Misc one-offs (4 failures + 0 errors)

| File | Test | Likely root cause |
|---|---|---|
| `test_campaign_executor.py` | `test_sequence_step_not_found_raises` | Behavior assertion drift |
| `test_engines/test_closer.py` | `test_handle_meeting_request_intent` | Recent ReplyAnalyzer refactor in closer.py |
| `test_flows/test_directive_196_resilience.py` | `test_enrich_tier_failure_continues` | Tier renaming or flow refactor |
| `orchestration/flows/test_free_enrichment_flow.py` | `test_flow_skips_promote_when_disabled` | Promote logic changed |

**Estimated A3 fix effort:** ~15min each, likely independent — ~1hr total.

---

### Cluster 6 — CIS negative signals (2 failures)

**Files:** `tests/test_services/test_cis_negative_signals.py`

**Failures:**
1. `TestSDKBrainNegativeSignals::test_analyze_cis_outcomes_segments_negative_signals`
2. `TestNegativeSignalsDecreaseWeights::test_prompt_instructs_weight_decrease_for_negatives`

**Diagnosis:** Likely prompt-engineering assertion drift in CIS sdk_brain. Testing LLM-prompt content is brittle when prompts evolve.

**Estimated A3 fix effort:** ~30min (re-anchor assertions to current prompt text or relax to invariant checks).

---

### Cluster 7 — Rescore engine (3 failures)

**Files:** `tests/unit/test_rescore_engine.py`

**Failures:**
1. `test_promotes_qualifying_reject`
2. `test_dry_run_makes_no_db_writes`
3. `test_rescore_result_counts_correct`

**Diagnosis:** Test names abbreviated in pytest output (`Test...promot... - T...`) suggests setup/fixture issue applying to all 3 tests in the file. Likely a single root cause.

**Estimated A3 fix effort:** ~30min — investigate shared fixture, fix once, all 3 unblock.

---

## RECOMMENDED A3 SEQUENCE (single-bot Phase 1 work)

1. **Cluster 3 — BD COSTS_USD rename** (~15min, lowest-hanging, follow-on debt from PR #613)
2. **Cluster 2 — Scout import fix** (~15-30min, unblocks 15 errors with one change)
3. **Cluster 1 — DNCR client signature** (~30-45min, unblocks 13 tests with one root cause)
4. **Cluster 7 — Rescore engine fixture** (~30min, unblocks 3 tests)
5. **Cluster 6 — CIS prompt assertions** (~30min)
6. **Cluster 4 — Siege test file** (~15min-2hr, depending on rename scope)
7. **Cluster 5 — Misc 4 one-offs** (~1hr)

**Total estimated A3 effort:** **3-5 hours** for 28 failures + 16 errors → 0.

---

## CONSTRAINT REMINDER

Per Max directive 2026-05-08 ("F approved — test triage doc is high value. Categorize failures, output the doc. **No code fixes in this pass.**"), this document is data-gathering only. No tests modified, no source code modified.

A3 fixes execute in a separate Phase 1 PR after Phase 0 trigger lands.

---

## DRIFT NOTE FOR FUTURE PR HYGIENE

Cluster 3 (BD `COSTS_AUD` → `COSTS_USD` rename) is a **regression from PR #613** that wasn't caught in PR #613's own CI run. Root cause: test_bright_data_client.py was not updated alongside the rename. Pre-merge CI did pass on PR #613's branch — likely because the test file uses `from integrations.bright_data_client import COSTS_AUD` (no `src.` prefix) and pytest's collection couldn't find it under that path during cached collection.

**Recommendation for future refactor PRs:** add `grep -rE "<old_name>" tests/ src/` as a pre-merge gate (negative grep across both src/ and tests/) so that test imports renamed in src/ are caught.

This pattern matches today's "narrow grep misses adjacent structure" memory pin — Elliot's PR #613 grep covered src/ but not tests/.
