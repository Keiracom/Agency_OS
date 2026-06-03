# Concurrency Cap — Opus 4.8 RSS Re-measurement & N Derivation

**KEI:** Agency_OS-03w4 · **Decision:** `ceo:decision:concurrency_cap_2026-06-04`
**Author:** orion · **Date:** 2026-06-03 · **Model under test:** Opus 4.8 (`claude-opus-4-8`)

## Why re-measure

The original cap sizing (`N=3`, worst-session 5.1 GB) was measured on the
**old** model. The fleet has since pinned `claude-opus-4-8`
(`.claude/settings.json`). The ratified decision requires N to be recomputed
from a measured 4.8 footprint, verbatim — not carried over.

## Measurement method

A session's true footprint is the `claude` process **plus its whole MCP
server forest** (~13 node servers per session). The `claude` tree is
reparented under a `tmux-spawn-*.scope` cgroup, so `*-agent.service`
cgroup accounting reads only ~3 MB (the launcher) and misses it. The
accurate high-water mark is each tmux scope's `memory.peak` (counts unique
pages — no shared-page double-counting). Reproduce with:

```
python3 scripts/measure_session_rss.py
```

## Verbatim measurement (2026-06-03, 7 live sessions, 9–13 min old)

```
─── MEASURED (verbatim) ──────────────────────────────────────────
physical RAM     :  15986.5 MB (15.61 GB)
swap             :   5400.0 MB (5.27 GB)
addressable      :  21386.5 MB (20.89 GB)
live sessions    : 8
per-session peak : max=2603.1 MB  mean=1188.9 MB
  2603  1421  932  923  918  914  901  899 MB
```

- Typical session peak: **~0.9–1.4 GB**.
- Worst observed spike: **2603 MB** (one session spiked to 2.6 GB under load
  then compacted to 55 MB — shows what a session *can* reach).
- vs OLD-model 5.1 GB → **4.8 sessions are roughly half** the footprint.
- Sessions were 9–13 min old (post-crash recovery), i.e. early-session, not
  sustained-load peak — so the planning footprint below adds headroom.

## N derivation

| Quantity | Value |
|---|---|
| Physical RAM | 15986 MB (15.61 GB) |
| Swap (emergency only — swap-thrash was the crash) | 5400 MB (5.27 GB) |
| Addressable (RAM+swap) | 21386 MB (20.89 GB) |
| Planning per-session **sustained** peak | 1.5 GB (> mean 1.19, headroom) |
| Planning per-session **worst spike** | 2.6 GB (observed) |
| Infra reserve (OS, redis, postgres, 6× NATS bridges, watchers, buffers) | 4.0 GB |

```
sustained:       6 × 1.5 + 4.0 = 13.0 GB  < 15.6 GB RAM         (no swap)
worst all-spike: 6 × 2.6 + 4.0 = 19.6 GB  < 20.9 GB RAM+swap    (no OOM)
7 sessions worst-spike = 22.2 GB > 20.9 GB  ← the config that crashed
```

**=> N_TOTAL = 6** concurrent sessions.

## Partition (the stage-pair guard)

Elliot (orchestrator) bypasses the gate but is counted → gated band = 5,
partitioned into reserved caps that **sum to 5**:

| Role | Cap | Guarantee |
|---|---|---|
| deliberator (aiden, max) | 2 | dual-concur pair always co-resides |
| reviewer | 2 | 2 parallel reviewers always co-reside |
| worker | 1 | overflow queues (requeue-not-drop) |

Because the caps partition the band, a worker can never occupy a
deliberator's or reviewer's slot — the proof-gate NEGATIVE ("blocks the 2
deliberators / 2 reviewers from co-residing") is impossible **by
construction**, not by priority heuristics.

## Proof gate result (this box, verbatim)

```
─── PROOF GATE (1) ───────────────────────────────────────────────
sustained under physical RAM : PASS
worst-spike under RAM+swap   : PASS (no OOM)
```

Proof gate (2) — full chain completes under the cap with no role starved —
is proven deterministically in `tests/agent_concurrency/test_concurrency_cap.py`
(proof gates a/b/c) and `tests/dispatcher/test_main_concurrency_wiring.py`.
