# KEI-23 Track 1 Stream 2 Crash Diagnosis

**Author:** Aiden
**Date:** 2026-05-13
**Branch:** `aiden/kei23-stream2-crash-investigation`
**Scope:** diagnostic-only (no code change in this PR)
**Status:** Track 1 BLOCKED until Dave A/B/C call

## TL;DR

- Lance `Too many concurrent writers` exception at **2026-05-13T01:54:53.409106**, originating in `lance-4.0.0/src/dataset/write/retry.rs:48:5` after **2 retries / 30s retry_timeout**.
- Cascade: lance writer-conflict → `add_data_points` errored (01:55:16) → `extract_graph_and_summarize` errored (01:55:51) → `extract_chunks_from_documents` errored (01:56:43). Process died.
- **Root cause is Cognee-internal, not our wrapper.** `scripts/cognee_ingest.py` calls `cognify()` exactly once after `add()` (line 536). The concurrency originates inside Cognee's own `run_tasks_base` task scheduler, which spawns `add_data_points` + `extract_graph_and_summarize` (and others) as concurrent async coroutines for the same dataset — all of which flush graph edges to a single Lance dataset.
- **Recommended retry strategy: C (concurrency-config-fix) is mandatory pre-cursor, then A (resume) preferred over B (restart-from-scratch).** Resume alone or restart-alone would re-trigger the same lance conflict.

## Verbatim Log Evidence

From `/home/elliotbot/.cognee/logs/2026-05-12_23-16-29.log` (final crash sequence, lines 191-200):

```
2026-05-13T01:54:53.409106 [ERROR   ] Failed to index graph edges: lance error: Too many concurrent writers. Attempted 2 times, but failed on retry_timeout of 30.000 seconds., /root/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/lance-4.0.0/src/dataset/write/retry.rs:48:5 [cognee.shared.logging_utils]
2026-05-13T01:55:16.564290 [ERROR   ] Coroutine task errored: `add_data_points`
Graph edge indexing error
 exception_message=Graph edge indexing error traceback=True [run_tasks_base]
2026-05-13T01:55:51.216451 [ERROR   ] Coroutine task errored: `extract_graph_and_summarize`
Graph edge indexing error
 exception_message=Graph edge indexing error traceback=True [run_tasks_base]
2026-05-13T01:56:43.625032 [ERROR   ] Async Generator task errored: `extract_chunks_from_documents`
Graph edge indexing error
 exception_message=Graph edge indexing error traceback=True [run_tasks_base]
```

Pre-crash pipeline state — last clean cycle at lines 159-165 (~32s before crash):

```
2026-05-13T01:54:21.113015 [INFO    ] Coroutine task started: `extract_dlt_fk_edges` [run_tasks_base]
2026-05-13T01:54:21.318133 [INFO    ] Coroutine task completed: `extract_dlt_fk_edges` [run_tasks_base]
2026-05-13T01:54:21.476446 [INFO    ] Coroutine task completed: `add_data_points` [run_tasks_base]
2026-05-13T01:54:21.657373 [INFO    ] Coroutine task completed: `extract_graph_and_summarize` [run_tasks_base]
2026-05-13T01:54:21.794364 [INFO    ] Async Generator task completed: `extract_chunks_from_documents` [run_tasks_base]
2026-05-13T01:54:21.925273 [INFO    ] Coroutine task completed: `classify_documents` [run_tasks_base]
2026-05-13T01:54:22.083701 [INFO    ] Pipeline run completed: `02186213-68e4-5786-bdf1-e23f924947fa` [run_tasks_with_telemetry()]
2026-05-13T01:54:22.624996 [INFO    ] Pipeline run started: `02186213-68e4-5786-bdf1-e23f924947fa` [run_tasks_with_telemetry()]
```

Note: same pipeline run id `02186213-68e4-5786-bdf1-e23f924947fa` re-starts immediately. Cognee runs the same dataset through the task list per batch — many pipeline-run cycles per long-running ingest.

## Error Classification — 3 candidate layers

### Layer 1: Lance default-config (CONFIRMED)

- Stack frame: `lance-4.0.0/src/dataset/write/retry.rs:48:5`. Lance crate version 4.0.0.
- Lance's default writer-concurrency policy: single-writer-per-dataset semantics with optimistic retry. Default retry budget = 2 attempts at 30s each = 60s total before abort.
- Lance is doing the correct thing: it detected a concurrent commit conflict on the graph-edges dataset and exhausted its retry budget.
- **This is Lance defending dataset integrity, not a Lance bug.** Lance is downstream of the actual concurrency source.

### Layer 2: Cognee task scheduler (ROOT CAUSE)

- Cognee's `cognee.tasks.run_tasks_base` fires `add_data_points`, `extract_graph_and_summarize`, `extract_chunks_from_documents`, `classify_documents`, and `extract_dlt_fk_edges` as concurrent coroutines within a single pipeline run (visible in log as multiple "Coroutine task started" entries 50-100ms apart at lines 144, 137, 169-176).
- All of these write to the SAME graph-edges Lance dataset.
- Cognee 1.0.9 has no documented writer-serialization for Lance graph backend — async tasks issue Lance commits in parallel.
- **The retry-timeout of 30s + 2 attempts is Cognee/Lance default, not configured on our side.**

### Layer 3: Our wrapper (`scripts/cognee_ingest.py`) — RULED OUT

- `scripts/cognee_ingest.py:536` — `await cognify()` is called exactly ONCE per ingest run. No parallel cognify invocations from our side.
- `--streams 2` flag controls which stream-loaders to concat for ingestion (data input), NOT how many parallel Cognee pipelines run. `parse_streams` at line 459 just resolves stream ids; the resulting documents are ingested sequentially via `add()` then a single `cognify()` (line 536).
- Our wrapper is well-behaved. Removing it from the call chain would NOT fix this.

## Retry Strategy Decision Matrix

| Strategy | Description | Feasibility | Cost | Risk |
|----------|-------------|-------------|------|------|
| **A. Resume** | Re-invoke `cognify()` on the existing dataset; durable data persists in graph store from pre-crash pipeline cycles. | MEDIUM — depends on whether Cognee's pipeline-run state is checkpointable. The same `pipeline_run_id` is reused, suggesting Cognee tracks per-document idempotency. Empirical re-run required to confirm. | LOW — ~30-60 min to redo remaining documents only (per Max's pre-crash ETA at 2387 pipeline runs / 113% CPU 2h36m). | **HIGH** — re-triggers same lance writer-conflict unless Strategy C is applied first. |
| **B. Restart-from-scratch** | `cognee.prune()` to wipe dataset, then full re-ingest of Stream 2 from zero. | HIGH — well-understood path. | HIGH — full re-ingest cost (~2-3 hr CPU based on the pre-crash run). All pre-crash work discarded. | **HIGH** — same lance writer-conflict reproduces unless Strategy C is applied first. |
| **C. Concurrency-config-fix** | Patch Cognee task-scheduler to serialise graph-edges Lance writes (one-writer-at-a-time) OR set Lance retry-timeout/attempts to absorb burst. | MEDIUM — needs a minimal patch in Cognee task scheduler OR a Lance dataset config (`enable_optimistic_concurrency`) OR an env var if Cognee exposes one. Requires source-dive into installed Cognee 1.0.9. | LOW — patch is small (single semaphore around graph-edge writes). | LOW — once serialised, no further lance conflicts. Throughput halved on the graph-edges phase but pipeline survives. |

## Recommendation to Dave

**C-then-A.** Apply concurrency-config-fix first (pre-cursor). Then resume from where it crashed. Restart-from-scratch (B) is wasteful given durable storage; it should be reserved for the case where Cognee's resume path is found to be non-idempotent.

If Cognee does not expose a config knob for graph-edges writer concurrency, the patch is a single asyncio.Semaphore around the Lance write call in Cognee's `add_data_points` task. This is a 5-10 line fix and would land as a separate PR after Dave's A/B/C call.

### Concrete next steps post-Dave-call

- **If A:** Need to verify Cognee re-runs are idempotent at the document level (empirical probe: re-invoke `cognify()` on a 3-document subset and inspect graph-store deltas).
- **If B:** `cognee.prune.prune_data()` + `cognee.prune.prune_system()` then full ingest.
- **If C:** Source-dive `~/.cognee/lib/python3.X/site-packages/cognee/tasks/...` to locate the graph-edges write call; wrap with a module-level `asyncio.Semaphore(1)`. Atomic PR, ship + smoke against a 10-doc subset.

## Assumptions

- Lance version 4.0.0 retry behaviour (2 attempts × 30s) is upstream default — not configured on our side. Confirmed by stack frame path `/root/.cargo/registry/src/index.crates.io-.../lance-4.0.0/src/dataset/write/retry.rs:48`.
- Cognee 1.0.9 (per CLAUDE.md technical concepts).
- Process death cascade is final — `tmux list-sessions` shows `maxbot` SESSION GONE per Elliot's report, and `ps` returns no Cognee ingest PID. No partial pipeline can complete.
- Stream 2 in the canonical Max ingest command is `--streams 2` of the cognee_ingest.py CLI, which controls input data scope (not parallelism).

## Open questions for Dave + Max (post Dave A/B/C call)

1. Are previously ingested Stream 2 documents (before 01:54:53 crash) durable in the graph store + Lance? Likely yes (Lance commits are transactional); empirical verification gated on retry path chosen.
2. Was Max's tmux session shut down by him explicitly (clean close) or did it die with the process (operator restart needed)?
3. If Strategy C is selected, who owns the Cognee patch — Aiden (CTO build) or Max (was the original ingest operator)?
