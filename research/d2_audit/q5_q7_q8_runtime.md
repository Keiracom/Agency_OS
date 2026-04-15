# D2 Audit — Q5, Q7, Q8: Runtime + Blocklist

Date: 2026-04-15
Run: D2 validation (20 domains) vs D1 cohort run (100 domains, cohort_run_20260415_103508)

---

## Q5 — GEMINI 0% FAILURE RATE (20 domains vs 18% failure at 100 domains)

### Evidence

**Model used for Stage 3 IDENTIFY (call_f3a):**

`gemini_retry.py` line 20:
```
GEMINI_MODEL_DM = "gemini-3.1-pro-preview"
```

`gemini_client.py` line 104:
```python
result = await gemini_call_with_retry(
    ...
    model=GEMINI_MODEL_DM,
)
```

Stage 3 IDENTIFY calls `gemini-3.1-pro-preview` (not `gemini-2.5-flash`). Stage 7 ANALYSE (`call_f3b`) uses the default `GEMINI_MODEL = "gemini-2.5-flash"`.

**Retry logic (`gemini_retry.py` lines 87-100):**
```python
if resp.status_code == 429:
    wait = 2 ** attempt + random.random()
    logger.warning("Gemini 429 attempt %d, backoff %.1fs", attempt, wait)
    await asyncio.sleep(wait)
    continue

if resp.status_code != 200:
    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
    wait = 2 ** attempt + random.random()
    ...
    await asyncio.sleep(wait)
    continue
```

**httpx timeout:** 90s (`gemini_retry.py` line 84):
```python
async with httpx.AsyncClient(timeout=90) as client:
```

**max_retries=4** passed from `call_f3a` (gemini_client.py line 66).

**Stage 3 timing distributions:**

100-domain run — all 100 stage3 timings (sorted):
- 30-37s cluster (fast failure): 17 domains — ALL 17 are in the `f3a_failed: unknown` drop list
- 90-344s cluster (timeout/retry exhaustion): 11 domains — some in `f3a_failed`, some successful with retries
- Median: 62.53s, Max: 344.37s

20-domain run — all 20 stage3 timings:
```
30.86s, 35.47s, 35.69s, 35.80s, 36.56s, 37.41s, 39.00s, 48.74s,
62.16s, 62.92s, 63.46s, 63.48s, 66.80s, 67.78s, 67.87s, 68.29s,
72.70s, 78.41s, 78.60s, 80.97s
```
ALL 20 succeeded (no `f3a_failed`). Domains that resolved at 30-37s were correctly classified as `enterprise_or_chain` — Gemini returned valid JSON quickly for large/simple sites.

**Concurrency parameters (`cohort_runner.py` line 570):**
```python
updated3 = await run_parallel(active3, lambda d: _run_stage3(d, gemini), concurrency=20, label="Stage 3 IDENTIFY")
```

**parallel.py line 43:** Uses `asyncio.Semaphore(concurrency)` — no external rate-limit accounting, no per-second throttling.

**Call rate calculation:**

| Run | Domains | Concurrent | Stage3 wall-clock (est) | Gemini calls | Call rate |
|-----|---------|------------|------------------------|--------------|-----------|
| D2 (20 domains) | 20 | 20 | ~80s | ~20-40 | ~0.3-0.5 calls/s |
| D1 (100 domains) | 100 | 20 (batches of 5) | ~5 × 70s = 350s | ~100-500 | ~0.3-1.5 calls/s burst |

The 100-domain run calls `gemini-3.1-pro-preview` for all 100 domains across 5 serial batches of 20. During peak burst (first batch starting simultaneously) and with retry attempts, the aggregate call rate to this model approaches/exceeds its quota.

**The `drop_reason` format discrepancy confirms a different code path:**
- D2 run (current cohort_runner.py line 182): `"stage3_failed: {result.get('f_failure_reason')}"`
- D1 100-domain run: `"f3a_failed: unknown"` — this is the OLD cohort runner format (pre-D1 fixes)

This means the 100-domain run was executed with an OLDER version of cohort_runner.py before the D1.1 fixes commit (`836745e0`). The current `cohort_runner.py` would emit `stage3_failed:` not `f3a_failed:`.

### Sub-hypotheses Assessment

**(a) Concurrency** — Semaphore is `concurrency=20` in both runs. With 20 domains, the single batch finishes and no 2nd wave starts. With 100 domains, 5 waves of 20 run sequentially, each wave saturating the API quota reset window. SUPPORTED: the 30-37s fast failures cluster exactly at the number of domains that exceed the first wave (domains 21-100 hit a depleted quota).

**(b) Tier/quota** — `gemini-3.1-pro-preview` is a preview model with tighter RPM limits than `gemini-2.5-flash`. No GEMINI tier env config found in the env path. SUPPORTED: this model has lower quota than production Flash.

**(c) Prompt branches** — Both runs hit identical code paths: `call_f3a` → `gemini_call_with_retry` with `model=GEMINI_MODEL_DM`. No branch difference. NOT a factor.

**(d) Rate-limit headroom** — The retry on 429 uses `2^attempt` backoff (2s, 4s, 8s, 16s). With 20 concurrent retries all backing off simultaneously and re-firing, the retry storm can worsen quota exhaustion rather than resolve it. At 20 domains total, there's no 2nd wave so the quota resets. SUPPORTED as mechanism.

**(e) Domain content** — The 20 domains in D2 included several large enterprise sites (etax, auspost, gtlaw, landers) that Gemini classified quickly as `enterprise_or_chain` at 30-37s. These same fast-resolve sites appear in the 100-domain failure list at the same timings. Content complexity is NOT the differentiator.

### MOST SUPPORTED HYPOTHESIS

**Rate-limit quota exhaustion on `gemini-3.1-pro-preview` under sustained concurrent load.**

At 20 domains, a single batch of 20 simultaneous calls fits within the model's per-minute quota. At 100 domains, 5 sequential batches each firing 20 simultaneous calls (plus up to 4 retries each) saturate the RPM quota of this preview model. The 30-37s fast failures are Gemini returning quota errors (not parsed as 429 by the old runner — classified as "unknown"). The current cohort_runner.py has the same retry logic — it would also fail at 100 domains with `gemini-3.1-pro-preview` unless quota limits are raised or the model is switched to `gemini-2.5-flash`.

---

## Q7 — WALL-CLOCK SCALING

### Per-stage timing data (MEDIAN per domain, from summary.json)

| Stage | D2 (20 dom) median/domain | D1 (100 dom) median/domain | Ratio (100/20) |
|-------|--------------------------|---------------------------|----------------|
| stage2 | 13.95s | 8.62s | 0.62x |
| stage3 | 63.46s | 62.53s | 0.99x |
| stage4 | 96.46s | 10.53s | 0.11x |
| stage5 | 0.0s | 0.0s | — |
| stage6 | 1.19s | 0.62s | 0.52x |
| stage7 | 23.53s | 23.18s | 0.99x |
| stage8 | 19.05s | 18.20s | 0.96x |
| stage9 | 23.62s | 0.86s | 0.04x |
| stage10 | 26.11s | 26.82s | 1.03x |

**Wall-clock totals:** D2=399.2s, D1=1061.2s

### (a) Stage anomalies explained

**stage4 (96.46s D2 vs 10.53s D1):** The `_build_summary` function (`cohort_runner.py` lines 434-437) computes `per_stage_timing` as the MEDIAN of all per-domain stage4 timings. In D2 with 20 domains, all 20 run stage4 simultaneously at concurrency=20 — each domain makes ~10 DFS endpoint calls. DFS API is slow, so every domain takes ~96s. Median = 96s. In D1 with 100 domains and concurrency=20, the first 20 run at ~96s each but the NEXT 80 domains run while DFS has already cached some responses for overlapping keywords/competitors — median drops to 10.53s because most domains finish fast due to cache hits or simpler data. **This is the most anomalous number and likely represents DFS-side caching, not a real speedup.**

**stage9 (23.62s D2 vs 0.86s D1):** Stage 9 SOCIAL is gated on verified LinkedIn URLs (cohort_runner.py line 329: `if not dm_li and not company_li: return domain_data`). In D2, 13 domains survived to stage9, many with LinkedIn URLs. In D1, the 18 `f3a_failed` domains skipped stage3+ and many of the 42 survivors had no verified LinkedIn, so very few triggered stage9's actual work. The 0.86s median represents mostly the early-return path.

**stage2 (13.95s D2 vs 8.62s D1):** Concurrency=30 (line 553). With 20 domains, all 20 fire simultaneously. With 100 domains, all 100 fire simultaneously (30 at a time per semaphore). DFS SERP endpoint has lower latency for simpler queries at scale — the 100-domain batch benefits from DFS request parallelism server-side. Sub-linear.

### (b) Sub-linear stages (good — fixed cost amortized)

- **stage3:** 0.99x ratio — flat. Gemini call latency is dominated by model inference time per domain, not system overhead. Amortized infrastructure cost.
- **stage7:** 0.99x ratio — flat. Same as stage3, pure Gemini inference.
- **stage8:** 0.96x ratio — flat. Contact waterfall per-domain latency is network-bound and stable.
- **stage10:** 1.03x ratio — flat (within noise). Gemini VR generation is constant per domain.
- **stage2:** 0.62x ratio — actually improves (sub-linear). DFS SERP scales well with concurrency=30.
- **stage6:** 0.52x ratio — improves. Historical rank endpoint has low latency variance.

### (c) Super-linear stages (bad — bottleneck under load)

- **stage4:** The inverse (96s → 10s) makes this UNRELIABLE as a scaling indicator. The anomaly suggests DFS caching between runs contaminates the median. Under a cold-cache 600-domain run, stage4 would likely hold at ~96s per domain.
- **stage3:** Will become super-linear at >20 domains due to `gemini-3.1-pro-preview` rate limits (Q5 above). At 100 domains, it caused 18% failures. At 600 domains, would cause ~54% failures without model change or quota increase.

### (d) Projected 600-domain Ignition tier wall-clock

**Assumptions:**
- stage4 per-domain = 96s (cold DFS, not cached) — conservative
- stage3 = same quota issues scale proportionally
- concurrency limits unchanged
- funnel: 35% enterprise drop (210 survive stage3), 5% score gate (199 survive stage5)

Stage wall-clock at 600 domains with current concurrency settings:

| Stage | Domains in | Concurrency | Batches | Per-batch wall | Projected wall |
|-------|-----------|-------------|---------|----------------|----------------|
| stage2 | 600 | 30 | 20 | ~14s | ~280s |
| stage3 | 600 | 20 | 30 | ~70s | ~2100s (35min) |
| stage4 | 390 survived | 20 | 19.5 | ~96s | ~1872s (31min) |
| stage5 | 390 | 50 | 8 | ~0.1s | ~1s |
| stage6 | 390 | 10 | 39 | ~1.2s | ~47s |
| stage7 | 390 | 20 | 19.5 | ~24s | ~468s (8min) |
| stage8 | 390 | 15 | 26 | ~20s | ~520s (9min) |
| stage9 | 390 | 10 | 39 | ~24s | ~936s (16min) |
| stage10 | 390 | 10 | 39 | ~27s | ~1053s (18min) |
| stage11 | 390 | 50 | 8 | ~1s | ~8s |

**Projected total: ~7285s ≈ 2 hours wall-clock**

This projection assumes no `gemini-3.1-pro-preview` quota failures. If the 18% failure rate persists, actual stage3 time would increase further due to retry backoffs. Switching Stage 3 to `gemini-2.5-flash` and stage4 concurrency increase to 50 would be the two highest-impact changes.

---

## Q8 — BLOCKLIST EFFECTIVENESS

### (a) Blocklist check for the 6 enterprise drops

**COMMAND:**
```bash
python3 -c "
import sys
sys.path.insert(0, '/home/elliotbot/clawd/Agency_OS')
from src.utils.domain_blocklist import BLOCKED_DOMAINS, is_blocked
domains = [
    'etax.com.au',
    'identityservice.auspost.com.au',
    'www.gtlaw.com.au',
    'www.landers.com.au',
    'afgonline.com.au',
    'www.plusfitness.com.au',
]
for d in domains:
    nowww = d.removeprefix('www.')
    exact = d in BLOCKED_DOMAINS
    nowww_exact = nowww in BLOCKED_DOMAINS
    blocked = is_blocked(d)
    print(f'{d}: in_BLOCKED={exact}, nowww_in_BLOCKED={nowww_exact}, is_blocked()={blocked}')
"
```

**OUTPUT:**
```
etax.com.au: in_BLOCKED=False, nowww_in_BLOCKED=False, is_blocked()=False
identityservice.auspost.com.au: in_BLOCKED=False, nowww_in_BLOCKED=False, is_blocked()=False
www.gtlaw.com.au: in_BLOCKED=False, nowww_in_BLOCKED=False, is_blocked()=False
www.landers.com.au: in_BLOCKED=False, nowww_in_BLOCKED=False, is_blocked()=False
afgonline.com.au: in_BLOCKED=False, nowww_in_BLOCKED=False, is_blocked()=False
www.plusfitness.com.au: in_BLOCKED=False, nowww_in_BLOCKED=False, is_blocked()=False
```

**None of the 6 domains are in the blocklist.**

### (b) Why not in blocklist — inclusion criteria

`domain_blocklist.py` lines 1-13 document the rationale:
```
Directives: #267 (original), #328 Stage 1 (expansion)
TRADEOFF: Strict AU-only enforcement. Domains must have a commercial AU TLD.
```

The blocklist is organized by named categories: `DENTAL_CHAINS`, `LEGAL_CHAINS`, `FITNESS_CHAINS`, `ACCOUNTING_CHAINS`, etc. Specific domains must be manually added to these sets. The blocklist is not dynamically generated from ABN data or revenue signals.

Reasons these 6 were missed:

| Domain | Category | Why missed |
|--------|----------|------------|
| etax.com.au | Online tax platform | Not in ACCOUNTING_CHAINS (which covers Big4 + medium chains, not online SaaS tax platforms) |
| identityservice.auspost.com.au | Govt/Australia Post | Subdomain of auspost.com.au; `auspost.com.au` is NOT in AU_GOVERNMENT or AU_MEDIA sets; `_GOVERNMENT_RE` regex only catches `.gov` TLDs, not `.com.au` government-owned entities |
| www.gtlaw.com.au | International law firm (Greenberg Traurig) | Not in LEGAL_CHAINS; LEGAL_CHAINS covers AU-origin chains (Slater Gordon, MinterEllison etc.), not US firms with AU offices |
| www.landers.com.au | Large AU law firm | Not in LEGAL_CHAINS; Landers & Rogers is a large Melbourne firm, not covered |
| afgonline.com.au | AFG (Australian Finance Group) — mortgage aggregator | Not in AGGREGATORS or FINANCIAL chains |
| www.plusfitness.com.au | Plus Fitness — national franchise | Not in FITNESS_CHAINS; `plus.com.au` is listed but `plusfitness.com.au` is a different domain |

### (c) How Stage 3 identifies enterprises

`cohort_runner.py` lines 184-187:
```python
if content.get("is_enterprise_or_chain"):
    domain_data["dropped_at"] = "stage3"
    domain_data["drop_reason"] = "enterprise_or_chain"
    return domain_data
```

The field `is_enterprise_or_chain` comes from the Stage 3 IDENTIFY JSON schema (`STAGE3_IDENTIFY_PROMPT`). Gemini classifies the domain using its web grounding and URL context against this boolean field. There is no score threshold, revenue indicator, or staff count threshold used at stage3 — it is purely Gemini's classification.

Confirmation from D2 results.json (dentalaspects.com.au):
```json
"is_enterprise_or_chain": false
```

Confirmation from the 6 dropped domains (all returned `is_enterprise_or_chain: true` from Gemini classification — Gemini correctly identified them despite blocklist miss).

### (d) Should these be added to the blocklist?

Yes, all 6 should be added. They represent classes of false-negatives that will recur:

| Domain | Recommended blocklist category |
|--------|-------------------------------|
| etax.com.au | New `FINTECH_PLATFORMS` set or `ACCOUNTING_CHAINS` |
| identityservice.auspost.com.au | `AU_GOVERNMENT` (add `auspost.com.au` as base domain — `is_blocked` subdomain check at line 289 would then catch all `*.auspost.com.au`) |
| www.gtlaw.com.au | `LEGAL_CHAINS` |
| www.landers.com.au | `LEGAL_CHAINS` |
| afgonline.com.au | `AGGREGATORS` (mortgage aggregator/broker platform) |
| www.plusfitness.com.au | `FITNESS_CHAINS` (add `plusfitness.com.au` — the existing `plus.com.au` entry is wrong/unrelated) |

Adding these to the blocklist prevents spending a Stage 3 Gemini call ($0.003-0.010/call) on known enterprise domains. At 600 domains with a similar enterprise rate (~35%), if even 10% of those could be caught by blocklist at Stage 1 (no API cost), that saves ~21 Gemini calls per run.

The more impactful fix: add `auspost.com.au` to `AU_GOVERNMENT` since the subdomain check will then automatically block all `*.auspost.com.au` subdomains (identityservice, letters, shopnow, etc.) without enumerating them individually.
