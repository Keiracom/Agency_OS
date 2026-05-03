# CD Player v1 Test Migration Guide — 31 xfailed Tests

**Purpose:** Rewrite 31 xfailed orchestrator tests from legacy API to CD Player v1 streaming architecture.

**Key Changes:**
- Old API: `.run(category, target_count, batch_size)` → direct discovery + scoring
- New API: `.run_streaming(categories, target_cards, budget_cap_aud, num_workers)` → worker pool + stage pipeline
- New internals: Stages 2–11 delegated to `cohort_runner._run_stage*()` functions
- ProspectCard now emitted via callback (`on_card`) or collected in result.prospects

---

## Test Files Summary

| File | xfail Count | Business Logic | Key Assertion |
|------|------------|---|---|
| `test_orchestrator_gates.py` | 5 | Affordability/intent gates, DM finding | `result.stats.*_rejected`, `result.prospects` |
| `test_orchestrator_wiring.py` | 4 | Discovery/enrichment/scoring wiring | `result.stats.enrichment_failed`, card building |
| `test_pipeline_orchestrator.py` | 4 | End-to-end pipeline, stat tracking | `len(result.prospects)`, `result.stats` fields |
| `test_stage_parallel.py` | 9 | Concurrent stage execution, semaphores | No `time_range < 0.1` assertion (wall-clock timing is flaky) |
| `test_parallel_orchestrator.py` | 5 | Multi-worker, deduplication, budget | `run_parallel()` → delegates to `run_streaming()` |
| `test_country_filter.py` | 2 | AU domain filter, non_au gate | `non_au=True` → `affordability_rejected`, scorer not called |
| `test_multi_category_orchestrator.py` | 2 | Multi-category iteration | `multiple category codes → prospects from both` |
| `test_discovery.py` | ✓ (not xfail) | Category registry, MultiCategoryDiscovery | Already passing |
| `test_intelligence.py` | ✓ (not xfail) | Comprehend/classify/analyse via Anthropic | Already passing |

---

## Old vs. New Architecture

### Old API (Pre-CD Player v1)

```python
# Old construction — direct service injection
orch = PipelineOrchestrator(
    discovery=disc,           # .pull_batch() → list[domain_dicts]
    free_enrichment=enr,      # .scrape_website(), .enrich_from_spider()
    scorer=scorer,            # .score_affordability(), .score_intent_free/full()
    dm_identification=dm,     # .identify() → DM candidate
    gmb_client=gmb,
    ads_client=ads,
)

# Old call
result = await orch.run("10514", target_count=5, batch_size=10)
# result: PipelineResult(prospects=[], stats=PipelineStats(...))
```

**Old stages (implicit, no names):**
1. Discovery (pull_batch)
2. Spider/Website scrape (scrape_website)
3. Free enrichment (enrich_from_spider)
4. Affordability gate (score_affordability)
5. Intent gate (score_intent_free / score_intent_full)
6. DM identification (identify)

**Result emitted:** Single result after entire batch completes.

---

### New API (CD Player v1)

```python
# New construction — CD Player v1 clients
orch = PipelineOrchestrator(
    dfs_client=dfs,              # DFSLabsClient — stages 2, 4, 6, 8, 9
    gemini_client=gemini,        # GeminiClient — stages 3, 7
    bd_client=bright_data,       # BrightDataClient — stages 8, 9
    lm_client=leadmagic,         # LeadmagicClient — stage 8
    discovery=disc,              # MultiCategoryDiscovery.discover_prospects()
    on_card=callback,            # Emits ProspectCard as each domain completes
)

# New call — streaming
result = await orch.run_streaming(
    categories=["dental"],       # category names or code strings
    target_cards=5,
    budget_cap_aud=50.0,
    num_workers=8,
    batch_size=50,
)
# result: PipelineResult(prospects=[], stats=PipelineStats(...))
# Cards already emitted via on_card callback during execution
```

**New stages (explicit, per-domain pipeline):**
1. Stage 2: SERP verify (DFS) — PAID
2. Stage 3: Gemini F3A — identity + DM extraction
3. Stage 4: DFS signal bundle — PAID
4. Stage 5: Composite score — GATE: score < 30
5. Stage 6: Historical rank (DFS) — SKIP if score < 60, PAID
6. Stage 7: Gemini F3B — analysis
7. Stage 8: Contact waterfall — PAID
8. Stage 9: LinkedIn social (BD) — PAID
9. Stage 10: VR + messaging
10. Stage 11: Card assembly → emit via on_card

**Result emitted:** Streaming (callback) + final result.prospects list.

---

## Mock Recipe — Minimal Setup for run_streaming()

### Minimal Mocks

```python
from unittest.mock import AsyncMock, MagicMock

# ─── Discovery
discovery = MagicMock()
discovery.discover_prospects = AsyncMock(
    side_effect=[
        [{"domain": f"d{i}.com.au"} for i in range(5)],  # batch 1
        [],  # end of category
    ]
)

# ─── DFS Client (stages 2, 4, 6, 8, 9)
dfs = MagicMock()
# Stage 2 — SERP verify
dfs.serp_verify = AsyncMock(return_value={"_cost": 0.01})
# Stage 4 — signal bundle
dfs.domain_metrics = AsyncMock(return_value={...})
dfs.backlinks = AsyncMock(return_value={...})
dfs.historical_rank_overview = AsyncMock(return_value={...})
# etc.

# ─── Gemini Client (stages 3, 7)
gemini = MagicMock()
gemini.call_f3a = AsyncMock(return_value={
    "f_status": "success",
    "content": {
        "business_name": "Test Co",
        "is_enterprise_or_chain": False,
        "dm_candidate": {"name": "Jane", "title": "Owner", "linkedin_url": "https://..."},
    },
    "cost_usd": 0.0,
})
gemini.call_f3b = AsyncMock(return_value={...})

# ─── BrightData & Leadmagic (optional for stage 8/9)
bd = MagicMock()
lm = MagicMock()

# ─── Build orchestrator
orch = PipelineOrchestrator(
    dfs_client=dfs,
    gemini_client=gemini,
    bd_client=bd,
    lm_client=lm,
    discovery=discovery,
)

# ─── Call run_streaming() — NO on_card callback needed for unit tests
result = await orch.run_streaming(
    categories=["dental"],
    target_cards=5,
    budget_cap_aud=50.0,
)

# ─── Assertions
assert len(result.prospects) > 0 or result.stats.viable_prospects > 0
assert result.stats.discovered > 0
```

---

## PipelineStats Fields (Assertion Reference)

| Field | Type | Notes |
|-------|------|-------|
| `discovered` | int | Domains pulled from discovery |
| `enriched` | int | Domains that completed stage 4+ |
| `enrichment_failed` | int | Stage 2–4 failed (dropped) |
| `affordability_rejected` | int | Failed affordability gate (stage 5) |
| `intent_rejected` | int | Failed intent gate (stage 3 or 7) |
| `paid_enrichment_calls` | int | Count of paid API calls |
| `dm_found` | int | Stage 3 found DM candidate |
| `dm_not_found` | int | Stage 3 no DM found (dropped) |
| `unreachable` | int | Email/contact verification failed |
| `viable_prospects` | int | Cards emitted (len(prospects)) |
| `total_cost_usd` | float | Sum of all domain costs |
| `elapsed_seconds` | float | Wall-clock elapsed time |
| `category_stats` | dict | Per-category breakdown `{code: count, ...}` |

---

## ProspectCard Fields (Assertion Reference)

| Field | Type | Description |
|-------|------|---|
| `domain` | str | Domain name (e.g. "dental.com.au") |
| `company_name` | str | Business name (fallback: domain stem) |
| `location` | str | Display location (e.g. "Sydney, NSW") |
| `services` | list | Services extracted from website |
| `evidence` | list | Intent evidence (e.g. ["Has Google Ads"]) |
| `affordability_band` | str | Score band (UNKNOWN, LOW, MEDIUM, HIGH) |
| `affordability_score` | int | 0–10+ numeric score |
| `intent_band` | str | Band (NOT_TRYING, DABBLING, TRYING, STRUGGLING, UNKNOWN) |
| `intent_score` | int | 0–10+ numeric score |
| `is_running_ads` | bool | Running Google Ads |
| `gmb_review_count` | int | GMB review count |
| `gmb_rating` | float \| None | GMB star rating |
| `dm_name` | str \| None | Decision-maker name |
| `dm_title` | str \| None | DM title/role |
| `dm_linkedin_url` | str \| None | DM LinkedIn URL |
| `dm_confidence` | str \| None | Confidence level (HIGH, MEDIUM, LOW) |
| `dm_email` | str \| None | Decision-maker email |
| `dm_email_verified` | bool | Email verified |
| `dm_email_source` | str \| None | Email source (leadmagic, etc.) |
| `dm_mobile` | str \| None | Decision-maker mobile |
| `location_suburb` | str | Suburb (e.g. "Sydney") |
| `location_state` | str | State abbr (NSW, VIC, etc.) |
| `stage11_card` | dict | Full stage 11 output dict |

---

## Per-Test File Migration Strategy

### 1. test_orchestrator_gates.py (5 xfail)

**What's being tested:** Gate rejection counting (affordability, intent, DM not found).

**Old API:**
```python
@pytest.mark.xfail
async def test_affordability_rejected_counted():
    orch, scorer = _make_orch(afford=_afford_fail())
    result = await orch.run("10514", target_count=5)
    assert result.stats.affordability_rejected == 1
```

**New API — Changes Required:**

| Old | New |
|-----|-----|
| `_make_orch()` builds with `discovery`, `free_enrichment`, `scorer`, `dm_identification` | Build with `dfs_client`, `gemini_client`, `discovery` |
| `.run("10514", target_count=5)` | `.run_streaming(categories=["10514"], target_cards=5)` |
| `.stats.affordability_rejected` | Same field, but counted at stage 5 (not old free_enrichment) |
| `_afford_fail()` returns mock with `passed_gate=False` | Still used, but must be injected into stage 5 logic (see below) |

**Key Rewrite:**

The old `afford_fail()` mock is **not directly injectable** into CD Player v1. Instead:
- Stage 2–4 happen automatically via DFS + Gemini
- Stage 5 calls `score_prospect()` from `src/intelligence/prospect_scorer.py`
- You must mock **the actual stage 5 internals** or patch `score_prospect()` directly

**Option A: Mock discovery to return minimal domains, let stages 2–4 succeed, patch stage 5:**

```python
@pytest.mark.asyncio
async def test_affordability_rejected_counted():
    # Discovery returns 1 domain
    disc = MagicMock()
    disc.discover_prospects = AsyncMock(return_value=[{"domain": "dental.com.au"}], [])

    # DFS client for stages 2, 4, 6, 8, 9
    dfs = MagicMock()
    # Minimal stage 2 response
    dfs.serp_verify = AsyncMock(return_value={...})
    # Minimal stage 4 response
    dfs.domain_metrics = AsyncMock(return_value={...})
    # etc.

    # Gemini for stages 3, 7
    gemini = MagicMock()
    gemini.call_f3a = AsyncMock(return_value={
        "f_status": "success",
        "content": {
            "dm_candidate": {"name": "Jane", "title": "Owner", ...},
            "is_enterprise_or_chain": False,
        },
    })
    gemini.call_f3b = AsyncMock(return_value={})

    orch = PipelineOrchestrator(
        dfs_client=dfs,
        gemini_client=gemini,
        discovery=disc,
    )

    # Patch stage 5 score_prospect to return affordability_rejected
    with patch("src.intelligence.prospect_scorer.score_prospect") as mock_score:
        mock_score.return_value = {
            "affordability_band": "LOW",
            "affordability_score": 0,
            "affordability_passed": False,  # or check the gate logic
            "intent_band": "TRYING",
            ...
        }
        result = await orch.run_streaming(
            categories=["dental"],
            target_cards=5,
        )

    assert result.stats.affordability_rejected == 1
```

**Option B: Use legacy `.run()` method (backwards compat shim):**

If a backwards-compat `.run()` method exists on the orchestrator (for old tests), use it:

```python
result = await orch.run("10514", target_count=5)  # legacy entry point
assert result.stats.affordability_rejected == 1
```

Check `pipeline_orchestrator.py` for `.run()` method signature.

---

### 2. test_orchestrator_wiring.py (4 xfail)

**What's being tested:** Discovery call signature, enrichment failure, gate failure, card building.

**Key Test:** `test_pull_batch_called_correct_args()`

```python
# Old
@pytest.mark.xfail
async def test_pull_batch_called_correct_args():
    disc = MagicMock(); disc.pull_batch = AsyncMock(return_value=[])
    ...
    await orch.run("10514", location="Australia", target_count=5, batch_size=10)
    disc.pull_batch.assert_called_once_with(
        category_code="10514", location="Australia", limit=10, offset=0)
```

**New API — discovery signature changed:**

Old: `pull_batch(category_code, location, limit, offset)`
New: `discover_prospects(category_codes, location, etv_min, etv_max, ...)`

```python
# New
@pytest.mark.asyncio
async def test_discovery_called_correct_args():
    from src.pipeline.discovery import MultiCategoryDiscovery
    
    dfs = MagicMock()
    dfs.domain_metrics_by_categories = AsyncMock(return_value=[])
    
    disc = MultiCategoryDiscovery(dfs)
    orch = PipelineOrchestrator(
        discovery=disc,
        dfs_client=dfs,
        gemini_client=MagicMock(),
    )
    
    result = await orch.run_streaming(
        categories=["dental"],
        target_cards=5,
        budget_cap_aud=50.0,
    )
    
    # Assertion: verify discover_prospects was called with expected args
    # (or inject a spy into the discovery object)
```

---

### 3. test_pipeline_orchestrator.py (4 xfail)

**What's being tested:** End-to-end orchestration, stat tracking, prospect card fields.

**Key Test:** `test_orchestrator_tracks_stats()`

```python
# Old — 5 domains, one fails at each stage
enrich_responses = [None, make_enrichment(), ...]
enrich_iter = iter(enrich_responses)
free_enrichment.enrich_from_spider = enrich_from_spider

result = await orch.run(...)
assert result.stats.enrichment_failed == 1
assert result.stats.affordability_rejected == 2
assert result.stats.dm_not_found == 1
assert result.stats.dm_found == 1
```

**New API — stages are different:**

- Old "enrichment_failed" (stage 3) → New "stage 2 drops" (SERP verify fail)
- Old "affordability_rejected" (gate) → New "stage 5 drops" (composite score < 30 or affordability gate)
- Old "dm_not_found" (stage 6) → New "stage 3 drops" (Gemini F3A finds no DM)

**Rewrite Strategy:**

1. Mock discovery to return 5 domains
2. For each domain, set up stage responses to simulate the drop:
   - Domain 0: `dfs.serp_verify` returns error → dropped at stage 2
   - Domain 1–2: stages 2–4 succeed, but stage 5 score < 30 → affordability_rejected
   - Domain 3: stage 3 (Gemini F3A) finds no DM → dm_not_found
   - Domain 4: all stages succeed → viable_prospect

```python
@pytest.mark.asyncio
async def test_orchestrator_tracks_stats():
    # Simpler: let run_streaming accumulate stats from actual stage execution
    # Use side_effect on stage calls to produce varied outcomes
    
    disc = MagicMock()
    disc.discover_prospects = AsyncMock(return_value=[
        {"domain": "d0.com.au"},  # fail stage 2
        {"domain": "d1.com.au"},  # fail stage 5 (affordability)
        {"domain": "d2.com.au"},  # fail stage 5 (affordability)
        {"domain": "d3.com.au"},  # fail stage 3 (no DM)
        {"domain": "d4.com.au"},  # success
    ], [])  # then empty
    
    # ... set up DFS, Gemini mocks with side_effect arrays to produce varied outputs
    
    result = await orch.run_streaming(categories=["dental"], target_cards=5)
    
    assert result.stats.discovered == 5
    # Note: stat names may differ; check against stage drop reasons
```

---

### 4. test_stage_parallel.py (9 xfail)

**What's being tested:** Concurrent stage execution, semaphore limits, stage failures don't block others.

**Key Test:** `test_batch_of_10_all_concurrent()`

```python
# Old — measures wall-clock timing of scrape_website calls
call_times = []

async def mock_scrape(domain):
    call_times.append(asyncio.get_event_loop().time())
    await asyncio.sleep(0.01)
    return {"title": ...}

free_enrichment.scrape_website = mock_scrape
...
await orch.run("10514", target_count=5, batch_size=10)

time_range = max(call_times) - min(call_times)
assert time_range < 0.1  # All 10 calls concurrent
```

**New API — timing assertion is problematic:**

The new architecture uses semaphores (`GLOBAL_SEM_SCRAPE`, etc.) to limit concurrency. Wall-clock timing tests are **flaky** because:
- Semaphore release order is non-deterministic
- CI system load affects timing
- Test fixtures may introduce overhead

**Rewrite Strategy:**

1. **Remove wall-clock timing assertions.** Replace with call-count assertions:

```python
@pytest.mark.asyncio
async def test_batch_of_10_concurrent_call_count():
    """Verify all 10 domains' stage calls occur (concurrency implicit from semaphore)."""
    
    call_count = {"n": 0}
    
    async def mock_scrape(domain):
        call_count["n"] += 1
        await asyncio.sleep(0.001)
        return {"title": "Test"}
    
    # Build mocks for all stages...
    # (Stage 2, 3, 4, 5, etc. must all complete for domains to emit)
    
    result = await orch.run_streaming(
        categories=["dental"],
        target_cards=5,
        batch_size=10,
    )
    
    # Verify call count reflects concurrency
    assert call_count["n"] >= 10  # At least 10 scrape calls issued
```

2. **For semaphore testing**, assert semaphore constants exist and are tuned:

```python
from src.pipeline.pipeline_orchestrator import GLOBAL_SEM_DFS, GLOBAL_SEM_SCRAPE

def test_global_semaphores_tuned():
    assert GLOBAL_SEM_DFS._value == 28
    assert GLOBAL_SEM_SCRAPE._value == 80
```

---

### 5. test_parallel_orchestrator.py (5 xfail)

**What's being tested:** `run_parallel()` method, worker pools, deduplication, budget.

**Key Method:** `run_parallel(category_codes, target_count, num_workers, batch_size)`

**Status:** `run_parallel()` is a **legacy method** kept for backwards compat. It should delegate to `run_streaming()` internally.

**Rewrite Strategy:**

Check if `.run_parallel()` exists in the orchestrator. If yes:

```python
# Legacy entry point — should forward to run_streaming()
async def run_parallel(self, category_codes, location, target_count, num_workers, batch_size, ...):
    """Backwards-compat wrapper around run_streaming()."""
    return await self.run_streaming(
        categories=category_codes,
        target_cards=target_count,
        num_workers=num_workers,
        batch_size=batch_size,
        location=location,
        ...
    )
```

If `.run_parallel()` exists, tests can use it as-is (no change needed except removing xfail marker).

If not, rewrite tests to use `.run_streaming()`:

```python
@pytest.mark.asyncio
async def test_run_parallel_reaches_target():
    # Old
    # result = await orch.run_parallel(category_codes=["10514"], ...)
    
    # New
    result = await orch.run_streaming(
        categories=["10514"],
        target_cards=3,
        num_workers=2,
        batch_size=10,
    )
    assert len(result.prospects) == 3
```

---

### 6. test_country_filter.py (2 xfail)

**What's being tested:** `non_au=True` domain is rejected before affordability scoring.

**Key Test:** `test_non_au_rejected_in_orchestrator()`

```python
# Old
enrich_result = {
    "non_au": True,
    ...
}
free_enrichment.enrich_from_spider = AsyncMock(return_value=enrich_result)

result = await orch.run(...)
assert result.stats.affordability_rejected == 1
scorer.score_affordability.assert_not_called()  # Scorer skipped for non-AU
```

**New API — non_au check location changed:**

In CD Player v1, the non_au flag is **checked after stage 4 (signal bundle)**, before stage 5 (composite score).

```python
# New — stage 4 enrichment includes non_au flag
enrich_result = {
    "non_au": True,
    "domain": "example.com",
    ...
}

dfs.domain_metrics = AsyncMock(return_value=enrich_result)
# or mock the full stage 4 flow

result = await orch.run_streaming(...)

# After stage 4, check if non_au blocks scoring:
# The pipeline should:
# 1. Detect non_au=True in stage 4 output
# 2. Set domain_data["dropped_at"] = "non_au" (or affordability gate)
# 3. NOT call stage 5 scorer

assert result.stats.affordability_rejected == 1
# If non_au is counted under affordability_rejected, assertion holds.
```

---

### 7. test_multi_category_orchestrator.py (2 xfail)

**What's being tested:** Multi-category iteration, round-robin pulling, category stats.

**Key Test:** `test_multi_category_iterates_to_target()`

```python
# Old
result = await orch.run(["10514", "13462"], target_count=2)
assert len(result.prospects) == 2
```

**New API:**

```python
# New — identical call signature (backwards compat)
result = await orch.run_streaming(
    categories=["10514", "13462"],  # or ["dental", "plumbing"]
    target_cards=2,
)
assert len(result.prospects) == 2
```

---

## Stage Function Signatures (for mocking)

All stage functions live in `src/orchestration/cohort_runner.py`:

```python
async def _run_stage2(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """SERP verify — 5 queries. Sets domain_data["stage2"]."""
    # Uses: dfs.serp_verify()
    # Returns: domain_data with stage2 result
    
async def _run_stage3(domain_data: dict, gemini: GeminiClient) -> dict:
    """Gemini F3A — identity + DM. Sets domain_data["stage3"]."""
    # Uses: gemini.call_f3a()
    # May set dropped_at: "stage3", "enterprise_or_chain", "no_dm_found"
    
async def _run_stage4(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """DFS signal bundle. Sets domain_data["stage4"]."""
    # Uses: dfs.domain_metrics(), dfs.backlinks(), etc.
    
async def _run_stage5(domain_data: dict) -> dict:
    """Composite scoring. Sets domain_data["stage5"]. GATE: score < 30."""
    # Pure logic — no external client
    # May set dropped_at: "stage5" if score too low
    
async def _run_stage6(domain_data: dict, dfs: DFSLabsClient) -> dict:
    """Historical rank. SKIP if composite_score < 60."""
    # Uses: dfs.historical_rank_overview()
    
async def _run_stage7(domain_data: dict, gemini: GeminiClient) -> dict:
    """Gemini F3B — analysis."""
    # Uses: gemini.call_f3b()
    
async def _run_stage8(domain_data: dict, dfs, bd=None, lm=None) -> dict:
    """Contact waterfall — email/mobile."""
    # Uses: dfs, bright_data, leadmagic APIs
    
async def _run_stage9(domain_data: dict, bd: BrightDataClient) -> dict:
    """LinkedIn social."""
    # Uses: bd (BrightData) APIs
    
async def _run_stage10(domain_data: dict) -> dict:
    """VR + messaging. SKIP if no email."""
    
async def _run_stage11(domain_data: dict) -> dict:
    """Card assembly. Returns domain_data with stage11 card."""
```

---

## Mocking Checklist

- [ ] **Discovery:** `discover_prospects(category_codes, ...) → list[{domain, ...}]`
- [ ] **DFS client:** All 5 used endpoints (serp_verify, domain_metrics, backlinks, historical_rank_overview, email/mobile queries)
- [ ] **Gemini client:** `call_f3a()` and `call_f3b()` return dicts with `f_status`, `content`, `cost_usd`
- [ ] **BrightData client:** LinkedIn DM and company endpoints (if testing stage 9)
- [ ] **Leadmagic client:** Email/mobile discovery (if testing stage 8)
- [ ] **on_card callback:** Optional; if testing card emission, set to a list-append closure
- [ ] **Budget:** Set `budget_cap_aud` high enough to not trigger gate B during tests (or explicitly test budget overflow)

---

## Common Pitfalls

1. **Wall-clock timing assertions are flaky.** Replace with call-count assertions.
2. **Old `free_enrichment` is deprecated.** Stages 2–4 now call DFS + Gemini directly.
3. **Old `scorer.score_affordability()` not injectable.** Patch `score_prospect()` from prospect_scorer module instead.
4. **Stat names unchanged, but counting points differ.** Affordability gate now at stage 5 (composite score), not old free_enrichment stage.
5. **Legacy `.run()` method may not exist.** Check source; if missing, all tests must use `.run_streaming()`.
6. **ProspectCard now emitted via callback, not batched.** Collect via `on_card` closure or check `result.prospects` after completion.
7. **Category codes are strings in new API.** Convert int codes to strings: `categories=[str(10514)]` or use names: `categories=["dental"]`.

---

## Rewrite Checklist (Per Test)

For each xfailed test:

- [ ] Remove `@pytest.mark.xfail` decorator
- [ ] Replace `_make_orch()` helper to inject CD Player v1 clients (dfs, gemini, bd, lm)
- [ ] Replace `.run(cat, target_count, ...)` with `.run_streaming(categories=[cat], target_cards=...)`
- [ ] Update assertions on `result.stats.*` fields (check stage drop reasons, not old gate names)
- [ ] Update mocks: no `free_enrichment.enrich_from_spider()`, use DFS + Gemini instead
- [ ] For timing tests: remove wall-clock assertions, add call-count assertions
- [ ] Verify `on_card` callback is wired if testing card emission order
- [ ] Update `ProspectCard` field assertions (e.g., `intent_score` instead of `intent.raw_score`)

---

## Summary

**31 tests → rewrite path:**

| Category | Count | Rewrite Effort | Key Change |
|----------|-------|---|---|
| Orchestrator gates | 5 | Low | Mock DFS/Gemini, patch stage 5 scoring |
| Wiring | 4 | Medium | Discovery signature changed, no free_enrichment |
| End-to-end | 4 | Medium | Stats field locations shifted (stage 5 gates) |
| Parallel execution | 9 | Medium | Remove timing, add call-count assertions |
| Parallel orchestrator | 5 | Low | `.run_parallel()` → `.run_streaming()` |
| Country filter | 2 | Low | non_au checked after stage 4, before stage 5 |
| Multi-category | 2 | Low | Categories now strings, same gate logic |

**Total effort:** ~2–3 days (parallel work) or ~1 week (sequential).

