# Cascade + Continuous Replenishment — Architecture Design (v2)

**Date:** 2026-04-16
**Version:** 2 (CEO design review applied)
**Status:** Design draft (pre-build)
**Predecessor:** ARCHITECTURE.md v1 (2026-04-16 morning) — see `ceo:cascade_architecture_v2` for changelog
**Ratified sources:**
- `ceo:pipeline_cascade_architecture` (2026-04-15)
- `ceo:bu_discovery_rule` (2026-04-16)
- `ceo:gemini_multi_project_pooling` (2026-04-16)
**Build target:** Directive D2 post-validation

---

## Executive Summary

Replace the current D1 batch-parallel cohort runner with:
- **Cascade:** streaming pipeline with fork/join. Domains flow continuously, first card at ~90s regardless of cohort size.
- **Continuous Replenishment:** every drop triggers Stage 1 to inject a fresh virgin domain. Guarantees target card count.
- **BU-aware Discovery:** Stage 1 only returns domains not in business_universe. No re-discovery, ever.

Final state: customer sees cards populate their dashboard live, one by one, highest-ETV first, target count guaranteed.

---

## v2 Changelog (CEO review 2026-04-16)

**Critical fixes (3):**
- **C1 Fork concurrency** — per-track sub-dict isolation replaces shared-reference model
- **C2 State model** — commit to state-in-queues; remove global `domain_state[domain_id]` lookup
- **C3 Gemini pooling** — multi-project sem=30 (was sem=10); ratified in `ceo:gemini_multi_project_pooling`

**Important additions (3):**
- **I4** Per-stage timeouts + per-provider circuit breakers (new Component 14b)
- **I5** Customer tenant context on `domain_state` (flows through all stages → BU → card)
- **I6** GOV-8 extended to success path — raw provider responses persisted before transformation

**Open question overrule:**
- **Q4** Customer cancellation behaviour → pause replenishment, let in-flight finish (GOV-2 cost discipline)

**Minor adjustments (5):** M1 Stage 3 enterprise note (concession), M2 MAX_OFFSET=500, M3 batched replenishment, M4 oracle scope 50-100 domains, M5 backpressure relax-not-drain

**Build sequence:** reordered with timeouts before replenishment. 7.5d → 9d.

---

## Stage Logic Preservation (hard constraint)

Cascade v2 does NOT modify stage-internal logic locked in `ceo:stage*_locked` keys. It changes orchestration (streaming vs batch, fork/join, replenishment) but preserves what each stage DOES. If any stage's internal behaviour requires modification during Cascade build, that triggers a separate directive with its own LAW I-A audit against the relevant `_locked` key.

---

## Component Architecture

### 1. Domain State Schema (tenant-aware)

Every domain carries a state dict through the pipeline:

```python
domain_state = {
    "domain": str,
    "customer_id": uuid,           # NEW I5: propagated from Stage 1 injection
    "category": str,
    "track_a": dict,               # NEW C1: Track A (Intelligence) writes only here
    "track_b": dict,               # NEW C1: Track B (Contact) writes only here
    "track_c": dict,               # NEW C1: Track C (Social) writes only here
    "stage1": dict,                # Stage 1-3 (pre-fork) write to top level
    "stage2": dict,
    "stage3": dict,
    "cost_accumulator": float,
    "started_at": datetime,
    # Stages 10-11 (post-join) read from track_a/b/c and write to top level
    "stage10": dict,
    "stage11": dict,
}
```

**Tenant context (I5):** `customer_id` is mandatory from Stage 1 injection. Propagated through every stage. Written on every BU INSERT/UPDATE and on the final card output.

**Track isolation (C1):** Tracks A, B, C write ONLY to their own sub-dicts. No shared-reference mutation across concurrent tracks. Python asyncio coroutines interleave at await boundaries — shared dict mutation spanning an await is unsafe. Per-track isolation is mandatory.

### 2. Stage Queues (asyncio.Queue + PriorityQueue)

Each stage has an input queue and writes to the next stage's input queue. 11 stages + 3 fork branches + 1 join queue = 15 queues total.

```
q_stage1   -> q_stage2 (PriorityQueue, ETV-sorted) -> q_stage3 (fork)
                                                     -> q_track_a_4, q_track_b_8, q_track_c_9
q_track_a_4 -> q_track_a_5 -> q_track_a_6 -> q_track_a_7 -> signal(complete, A)
q_track_b_8 -> signal(complete, B)
q_track_c_9 -> signal(complete, C)
join_waiter (counter per domain) -> when all 3 signals received -> q_stage10
q_stage10 -> q_stage11 -> on_prospect_found callback
```

**State travels in queues (C2):** `domain_state` objects move by reference through queues. The join waiter holds direct references to state objects, not domain_id lookups in a global dict. Cleaner lifecycle, no global state cleanup required.

### 3. Stage Workers (coroutine per stage)

Long-running worker loops, one per stage:
```python
async def stage_worker(stage_id, in_queue, out_queues, sem):
    while running:
        domain_state = await in_queue.get()
        async with sem:
            updated = await run_stage_N(domain_state)
        for out_q in out_queues:
            await out_q.put(updated)
```

Semaphore limits per-stage concurrency per provider rate limits.

### 4. Fork Step (Stage 3 output)

After Stage 3 completes successfully:
```python
async def fork_stage3(domain_state):
    # Per-track isolation: each track operates on its own sub-dict
    domain_state["track_a"] = {}
    domain_state["track_b"] = {}
    domain_state["track_c"] = {}
    # State object shared but tracks never touch same keys
    await q_track_a_4.put(domain_state)
    await q_track_b_8.put(domain_state)
    await q_track_c_9.put(domain_state)
```

Tracks A, B, C read from top-level `stage3` data (read-only after fork), write only to their own sub-dicts. No race conditions possible.

### 5. Join Step (Stage 10 input)

Stage 10 requires all 3 tracks complete. Join counter holds direct refs to state objects:

```python
# Keyed by id(domain_state) — direct object reference, not domain_id
join_waiters: dict[int, set[str]] = defaultdict(set)

async def track_complete(domain_state, track_name):
    state_id = id(domain_state)
    join_waiters[state_id].add(track_name)
    if join_waiters[state_id] == {"A", "B", "C"}:
        await q_stage10.put(domain_state)
        del join_waiters[state_id]
```

State-in-queues model (C2): when Stage 10 dequeues, it reads `domain_state["track_a"]`, `domain_state["track_b"]`, `domain_state["track_c"]` and merges. Explicit merge point.

### 6. Per-Stage Semaphores (provider rate limits)

| Stage | Provider pool | Sem | Source |
|-------|---------------|-----|--------|
| 1 DISCOVER | DFS | 28 | DFS 30 concurrent |
| 2 VERIFY | DFS SERP | 28 | Same DFS pool |
| 3 IDENTIFY | Gemini (multi-project) | **30** | **ceo:gemini_multi_project_pooling (3 GCP × 150 RPM)** |
| 4 SIGNAL | DFS | 28 | Same DFS pool |
| 5 SCORE | Local | 50 | CPU |
| 6 ENRICH | DFS | 28 | Same DFS pool |
| 7 ANALYSE | Gemini (multi-project) | **30** | **Same Gemini pool** |
| 8 CONTACT | ContactOut+Hunter+Leadmagic | 15 | Conservative |
| 9 SOCIAL | Bright Data | 15 | BD async |
| 10 VR+MSG | Gemini (multi-project) | **30** | **Same Gemini pool** |
| 11 CARD | Local | 50 | CPU |

**Gemini sem=30 (C3):** Ratified 2026-04-16 in `ceo:gemini_multi_project_pooling`. Three GCP projects at Tier 1 (150 RPM each) = effective sem=30. Tier 2 upgrade ($250 cumulative per project) adds path to sem ~200+.

### 7. Backpressure Controller

Monitor queue depths. If any queue exceeds 2× downstream stage semaphore, upstream stages pause.

```python
async def backpressure_monitor():
    while running:
        for queue_name, sem in queue_limits.items():
            depth = queues[queue_name].qsize()
            if depth > 2 * sem:
                pause_upstream(queue_name)
            elif depth < sem:
                resume_upstream(queue_name)
        await asyncio.sleep(1)
```

Upstream stages check `paused` flag before enqueuing. Prevents memory bloat, auto-throttles.

### 8. ETV-Sorted Priority Queue for Stage 2

Use `asyncio.PriorityQueue` (negative ETV as priority key for descending order):

```python
q_stage2 = asyncio.PriorityQueue()
for d in discovered:
    await q_stage2.put((-d["organic_etv"], d))
```

Highest-value domains flow first. Replenishment domains are inserted at their correct ETV position — not appended to back. High-value replacements don't wait behind low-value originals.

### 9. BU Exclusion at Stage 1 (virgin domains only)

```python
async def discover_virgin_domains(category_code, need_count, customer_id):
    discovered = []
    offset = 50  # mid-tail start
    while len(discovered) < need_count:
        page = await dfs.domain_metrics_by_categories(
            category_codes=[category_code],
            location_name="Australia",
            limit=100,
            offset=offset,
        )
        for row in page:
            if is_blocked(row["domain"]):
                continue
            if await bu_exists(row["domain"]):  # SELECT 1 FROM business_universe WHERE domain=X
                continue
            discovered.append(row)
            # Lock immediately: INSERT stub row
            await bu_insert_stub(
                domain=row["domain"],
                category=category_code,
                customer_id=customer_id,  # I5: tenant context
            )
            if len(discovered) >= need_count:
                break
        offset += 100
        if offset > MAX_OFFSET:
            raise CategoryDepleted(category_code)
    return discovered

MAX_OFFSET = 500  # M2: AU categories long-tail beyond 500 = sole traders, out of ICP
```

Guarantees fresh domains. BU UNIQUE constraint on domain handles concurrent customer races.

### 10. on_prospect_found Callback

```python
async def on_prospect_found(card, domain_state):
    await bu_update(card.domain, {
        "status": "card_ready",
        "card_json": card,
        "completed_at": now(),
        "claimed_by": domain_state["customer_id"],  # I5
        # I6: raw responses persisted (see Component 14c)
    })
    await supabase_realtime_publish("lead_pool", card, customer_id=domain_state["customer_id"])
    replenishment_state.completed_count += 1
    if replenishment_state.completed_count >= replenishment_state.target:
        replenishment_state.stop = True
```

### 11. on_prospect_dropped Callback (GOV-8 partial persistence)

```python
async def on_prospect_dropped(domain_state, stage, reason):
    await bu_update(domain_state["domain"], {
        "status": "dropped",
        "dropped_at_stage": stage,
        "drop_reason": reason,
        "partial_data": domain_state,  # GOV-8: persist paid-for data
        "claimed_by": domain_state["customer_id"],  # I5
    })
    if replenishment_state.stop or replenishment_state.cancelled:
        return
    if replenishment_state.total_discovered >= replenishment_state.max_cap:
        log_alert("Max discovery cap reached — halting replenishment")
        return
    # M3: buffer pending drops, batch replenishment every 5s
    replenishment_buffer.append(domain_state["category"])
```

### 12. Replenishment Controller (batched)

```python
replenishment_state = {
    "target": 600,
    "completed": 0,
    "total_discovered": 0,
    "max_cap": 1800,  # 3× target
    "stop": False,
    "cancelled": False,  # Q4: customer cancel flag
}

async def batched_replenishment_loop():
    """M3: batch replenishment every 5s or when buffer ≥10."""
    while not replenishment_state.stop:
        await asyncio.sleep(5)
        if replenishment_state.cancelled:
            continue  # Q4: no new injections after cancel
        if len(replenishment_buffer) == 0:
            continue
        # Group by category
        categories = Counter(replenishment_buffer)
        replenishment_buffer.clear()
        for category, need_count in categories.items():
            try:
                fresh = await discover_virgin_domains(category, need_count, customer_id=...)
                for d in fresh:
                    await q_stage2.put((-d["organic_etv"], d))
            except CategoryDepleted:
                log_alert(f"Category {category} depleted")
```

**Q4 cancellation behaviour:** `replenishment_state.cancelled = True` stops new Stage 1 injections. In-flight domains finish (already paid). Partial card inventory remains in BU unclaimed. GOV-2 cost discipline.

### 13. Observability

Per-stage metrics every 5s:
- Queue depth
- Active workers (sem_value - sem_available)
- Completion count
- Error count
- Cost accumulator

Telegram summary every 30s. Per-domain state in Supabase.

### 14a. Gemini Key Rotator (NEW — C3)

Round-robin API key assignment across 3 GCP projects:

```python
class GeminiKeyRotator:
    def __init__(self):
        self.keys = [
            os.environ["GEMINI_API_KEY_PROJECT_1"],
            os.environ["GEMINI_API_KEY_PROJECT_2"],
            os.environ["GEMINI_API_KEY_PROJECT_3"],
        ]
        self.counter = 0
        self.lock = asyncio.Lock()

    async def next_key(self) -> str:
        async with self.lock:
            key = self.keys[self.counter % 3]
            self.counter += 1
            return key
```

Each Gemini call (Stages 3, 7, 10) calls `rotator.next_key()` before the API request. Round-robin distributes load evenly. 150 RPM per project × 3 = effective 450 RPM = sem=30 safe at Tier 1.

### 14b. Per-Stage Timeouts + Per-Provider Circuit Breakers (NEW — I4)

**Per-stage timeouts** (interim defaults 2026-04-16, based on D2 median + safety headroom):

| Stage | Timeout | Rationale |
|-------|---------|-----------|
| 2 VERIFY | 20s | D2 median 14s + headroom |
| 3 IDENTIFY | **120s** | D2 median 63s; Gemini grounded is slow |
| 4 SIGNAL | 30s | D2 median 14s + headroom |
| 6 ENRICH | 30s | D2 median 1s + headroom for cold cache |
| 7 ANALYSE | 90s | Gemini VR generation |
| 8 CONTACT | 30s | D2 median 14s + headroom |
| 9 SOCIAL | 90s | BD LinkedIn 30s+ per D2; headroom |
| 10 VR+MSG | 90s | Gemini 2-call chain |

On timeout: abort domain → persist partial data to BU (GOV-8) → fire `on_prospect_dropped(reason="stage_N_timeout")`.

**Note:** These are interim. Elliottbot re-evaluates using D2.2-RUN summary.json p95 timings when available. Material delta triggers separate directive for adjustment.

**Per-provider circuit breakers:**

```python
class CircuitBreaker:
    def __init__(self, name, error_threshold=0.5, recovery_threshold=0.2, window_s=60, recovery_s=30):
        self.name = name
        self.calls = deque()  # (timestamp, success)
        self.tripped = False
        self.recovery_start = None

    async def call(self, fn, *args):
        if self.tripped and not self._can_recover():
            return None  # short-circuit
        try:
            result = await fn(*args)
            self._record(success=True)
            return result
        except Exception as exc:
            self._record(success=False)
            if self._error_rate() > self.error_threshold:
                self.tripped = True
                log_alert(f"Circuit breaker {self.name} TRIPPED")
            raise
```

Providers tracked: DFS, Gemini, ContactOut, Hunter, Leadmagic, Bright Data. If >50% failure in 60s window → short-circuit. Recovery when error rate <20% for 30s.

### 14c. Raw Response Persistence (NEW — I6, GOV-8 extended)

Every stage calling a paid provider writes raw response to BU **before** transformation:

```python
async def run_stage4_signal(domain_state):
    raw = await dfs.build_signal_bundle(domain_state["domain"])
    # I6: persist raw before transformation
    await bu_update(domain_state["domain"], {"raw_stage4_signal": raw})
    # Transform for pipeline
    domain_state["track_a"]["stage4"] = transform_signal_bundle(raw)
    return domain_state
```

**Target BU fields (TARGETS — schema migrations deferred to separate directive):**
- `raw_stage2_serp` (JSONB)
- `raw_stage3_gemini` (JSONB)
- `raw_stage4_signal` (JSONB)
- `raw_stage6_enrich` (JSONB)
- `raw_stage7_analyse` (JSONB)
- `raw_stage8_contact` (JSONB)
- `raw_stage9_social` (JSONB)

Write timing: immediately after provider returns, before any parsing or transformation. Persists paid-for data even if downstream pipeline logic drops the domain.

---

## Data Flow Walkthrough (one replenishment cycle)

1. Customer buys Spark tier (150 cards). `customer_id=<uuid>` recorded.
2. Replenishment state: target=150, completed=0, max_cap=450, cancelled=False
3. Stage 1 discovers 150 virgin domains (BU check per domain), inserts 150 stub rows in BU with `claimed_by=customer_id`
4. Stage 1 pushes domains to Stage 2 PriorityQueue sorted by -ETV
5. Stage 2 workers pick up domains. Fastest ones finish first.
6. Domain #1 (highest ETV) finishes Stage 2 in ~5s → Stage 3 queue
7. Domain #1 finishes Stage 3 in ~20s → FORKS into 3 track queues (per-track sub-dicts initialised)
8. Track A: Stage 4 → 5 → 6 → 7 (~40s). Raw responses persisted to BU per I6 at each paid stage.
9. Track B: Stage 8 (~10s). Completes before Track A.
10. Track C: Stage 9 (~20s). Completes before Track A.
11. All 3 tracks signal complete for Domain #1 at ~65s. Join waiter triggers. Domain #1 enters Stage 10.
12. Stage 10: VR + outreach (~20s)
13. Stage 11 assembles card at ~85s
14. `on_prospect_found` fires. BU updated with `claimed_by=customer_id`. Dashboard pushes card live. completed=1.
15. Meanwhile domains 2-150 flowing through stages concurrently.
16. Domain #50 drops at Stage 3 Gemini (`enterprise_or_chain`). `on_prospect_dropped` fires. BU updated with `status=dropped`, partial_data persisted (GOV-8). Category added to replenishment buffer.
17. Batched replenishment (5s timer): discovers 1 new virgin domain for that category, inserts BU stub, enqueues to Stage 2 priority queue at correct ETV position.
18. Cycle continues until completed=150. Replenishment stops.

---

## Build Sequence (v2 — reordered)

### Phase 1: Cascade Core (3 days)
- Async queue infrastructure
- Stage worker coroutines (11 stages)
- Fork at Stage 3 with per-track sub-dict isolation (C1)
- Join at Stage 10 with direct state refs (C2)
- Per-stage semaphores (shared provider pools) with Gemini sem=30 via key rotator (C3, 14a)
- ETV-sorted PriorityQueue for Stage 2

### Phase 2: BU Integration + Tenant Context (1.5 days)
- BU exclusion query at Stage 1
- BU stub insert on discovery (with `customer_id`)
- BU update on drop (partial_data + claimed_by)
- BU update on card completion (claimed_by)
- `customer_id` propagation through all stages (I5)

### Phase 3: Timeouts + Circuit Breakers (1 day) — NEW
- Per-stage timeout wrappers with proposed defaults (I4)
- Per-provider circuit breaker infrastructure (14b)
- GOV-8 raw response persistence at every paid stage (14c, I6)

### Phase 4: Replenishment (1 day)
- Replenishment state tracker
- `on_prospect_dropped` callback
- `on_prospect_found` callback
- Batched replenishment (5s timer, buffer ≥10 trigger) (M3)
- Q4 cancel flag handling
- Max cap safety stop
- `CategoryDepleted` handling

### Phase 5: Backpressure + Observability (1 day)
- Queue depth monitor
- Upstream pause/resume (relax-not-drain per M5)
- Per-stage metrics emission
- Telegram progress updates (30s)
- Supabase realtime event for dashboard

### Phase 6: Regression Oracle (1 day)
- Parallel run script (D1 + Cascade on same cohort)
- Field-by-field card diff
- Cost + wall-clock comparison
- Oracle cohort size: 50-100 domains (M4 — not full Velocity, too slow for CI)

### Phase 7: Production Cutover (0.5 day)
- Feature flag to toggle D1 vs Cascade
- Gradual rollout: 10% → 50% → 100%
- Monitor error rates, cost, wall-clock
- Rollback plan: flag flip to D1

**Total: 9 days engineering (was 7.5d in v1)**

Reorder rationale: timeouts precede replenishment because replenishment depends on `on_prospect_dropped` firing reliably, which requires timeouts to trigger drops on hangs.

---

## Open Design Questions

1. **ETV-sort for replenishments:** new domains enter after initial batch. Slot in by ETV using PriorityQueue or append to back?
   - **Recommendation:** insert by ETV via PriorityQueue. High-value replacements shouldn't wait behind low-value originals.

2. **Gemini retry scheduling:** current pipeline retries Gemini 4x. Cascade: retries go to front of queue or normal?
   - **Recommendation:** retries to front of Stage 3 queue. Reduces tail latency.

3. **BU stub vs full row on discovery:** minimal stub at Stage 1 or wait until Stage 3 for real data?
   - **Recommendation:** stub at Stage 1 (locks the domain). Update in place as stages complete.

4. ~~**Customer cancellation mid-run:** continue for BU growth or stop?~~
   - **RATIFIED 2026-04-16:** Pause replenishment immediately on cancel. Let in-flight domains finish (already paid). No new Stage 1 injections after cancel signal. Partial card inventory remains in BU unclaimed. GOV-2 cost discipline overrides speculative BU inventory growth.

5. **Monthly cycle boundary:** unclaimed back to pool, claimed stay owned?
   - **Recommendation:** unclaimed return to pool after 30 days. Claimed stay for tier period. Deferred to BU lifecycle directive.

6. **Concurrent customer runs:** 2 customers same vertical simultaneously?
   - **Recommendation:** yes. BU stub INSERT is atomic (UNIQUE constraint on domain). First-write wins. Second customer gets next unseen domain.

7. **Stage 2 enterprise pre-screen (M1 future optimisation):** migrate enterprise detection from Stage 3 Gemini to Stage 2 SERP-based heuristic to save ~25% of Stage 3 cost.
   - **Deferred — not in v2.** Candidate for v3. In v2, enterprise filter remains at Stage 3 (confirmed via cohort_runner.py L191-193).

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Fork/join bug causes domain loss | HIGH | Per-track sub-dict isolation (C1). Regression oracle against D1. Domain-level logging at every stage. |
| Backpressure deadlock (circular pause) | MEDIUM | **M5: alert + log pause duration. If pause >120s, dynamically relax downstream sem by 20% and re-evaluate. Force-drain prohibited — data loss violates GOV-8.** |
| BU stub insert race condition | LOW | UNIQUE constraint on domain. First-write wins. |
| Replenishment infinite loop | LOW | max_cap enforces hard stop. Alert on cap hit. |
| Memory bloat from queue overflow | MEDIUM | Backpressure prevents. Absolute max queue size fallback. |
| Gemini rate limit exhaustion at scale | LOW | **Multi-project pooling (sem=30) now primary per `ceo:gemini_multi_project_pooling`. Tier 2 upgrade ($250 cumulative spend per project → 1,000+ RPM) is additive upgrade path.** |
| Hung provider call holds sem slot | HIGH | Per-stage timeouts (14b). Circuit breakers on repeated failures. |
| State corruption from concurrent track writes | HIGH | Per-track sub-dicts (C1). Tracks never share keys. |

---

## Success Criteria

Cascade is ready to replace D1 when:

1. **Correctness:** Regression oracle passes — 100% card parity with D1 on 50-100 domain cohort
2. **Speed:** First card in <90s. Total wall-clock 2x+ faster than D1.
3. **Cost:** Within 5% of D1 for same cohort
4. **Reliability:** 0 deadlocks, 0 lost domains in 5 consecutive test runs
5. **Replenishment:** Target card count hit in 5/5 test runs (with variance in conversion rate)
6. **Observability:** Per-stage metrics, cost tracker, Telegram updates on schedule
7. **Concurrency safety:** 2 concurrent customer runs produce disjoint card sets (no shared domains)

---

## References

- `ceo:pipeline_cascade_architecture` (2026-04-15 ratified)
- `ceo:bu_discovery_rule` (2026-04-16 ratified)
- `ceo:gemini_multi_project_pooling` (2026-04-16 ratified)
- `ceo:pipeline_speedup_architecture` (2026-04-15, predecessor context)
- `src/orchestration/cohort_runner.py` (D1 sequential oracle)
- `src/intelligence/parallel.py` (reusable semaphore utility)
- `docs/MANUAL.md` Section 3 (BU rule)
- GOV-8 (max extraction per call), GOV-2 (cost discipline), GOV-11 (structural audit)
- Directive GOV-9 (Layer 2 scrutiny — applied to this v2 design review)
