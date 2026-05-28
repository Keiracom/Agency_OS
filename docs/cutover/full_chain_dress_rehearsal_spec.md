# Full-Chain Dress-Rehearsal — THE Cutover Gate

**KEI:** `Agency_OS-jb4e` (P0). **Design:** Viktor (thread 1779955041). **Owner:** Aiden · **Build:** Scout.
**Status:** ▸ HARNESS BUILT — live run **GATED on `Agency_OS-f5yt`** (work-loop consumer running). Nothing flips until this gate passes.

This is the end-to-end proof that the ephemeral self-driving loop works: a **real** open KEI flows through the full chain to a merged PR, with memory measurably helping. It supersedes the single-hop `empirical_test_spec.md` (which proves one retrieval hop); this proves the *whole pipeline*.

---

## What it proves

> A real backlog task, dropped into the running loop, is picked up and carried — with no human in the loop — through Chat → Deliberator → Worker → Reviewer → **merge**, honouring governance, with retrieval firing (and helping) at every hop.

Run it **twice** on the same KEI: once **recall-active**, once **cold** (recall disabled). The *gap* between the two runs is the empirical proof that memory adds value — not an assertion, a measurement.

---

## §1 — The chain (4 hops → merge)

| Hop | Subsystem | Agent label in `retrieval_events` | Handoff |
|---|---|---|---|
| 1. **Chat** | #ceo capture listener (`ceo_capture_listener`, Agency_OS-yku8) → a decision/directive enters `ceo_memory` | `failure-recall` / capture agent | decision recorded → KEI exists/updated |
| 2. **Deliberator** | task enters `keiracom:tasks:available` → consumer (#1275) → `/dispatcher/spawn` a deliberator | `<deliberator-callsign>` | KEI scoped → worker task published |
| 3. **Worker** | dispatcher spawns a worker; worker builds + opens a PR | `<worker-callsign>` (spawn-recall) | PR opened |
| 4. **Reviewer** | deliberators review; 2-of-3 NATS concur (author-exclusion) | `<reviewer-callsign>` | concur recorded |
| → **merge** | orchestrator admin-merge after concur; CI green | — | PR merged to `main` |

The work-loop entry point (hops 2→merge) is the consumer subscribing to `keiracom:tasks:available`, wired to `/dispatcher/spawn` (Atlas #1275, merged; **deployed/running = f5yt, pending**). Hop 1 (Chat) depends on `classify_and_save` (Nova #1268).

---

## §2 — Real KEI selection (NOT synthetic)

The KEI under test MUST be a genuine backlog item, never a test fixture. The harness picks the highest-priority `bd ready` issue, **excluding** synthetic markers: ids matching `KEI-TEST`, `*-test*`, `*smoke*`, or titles containing `smoke`/`test`/`scaffold`/`dress-rehearsal`. If only synthetic candidates exist, the gate **cannot run** (reported, not faked).

---

## §3 — Dual run (recall-active vs cold)

| Run | Recall config | Purpose |
|---|---|---|
| **A — recall-active** | `DISPATCHER_SPAWN_RECALL_ENABLED=true` + retrieval flags on; Hindsight + reranker reachable | the real ephemeral pipeline |
| **B — cold** | spawn recall disabled (no prior-context injection) | the control — agents act with no memory |

Both runs use the **same KEI** (reset between runs). The task payload carries `recall_mode` so the consumer/dispatcher spawns the chain in the right config — **wiring dependency on the consumer (Atlas)**: the consumer must honour `recall_mode`, or the operator flips the fleet env between runs.

**Memory gap (what we measure per hop):** recall-active hops have non-empty `retrieval_events` rows with `bypass_rerank=false` and `top_score > 0`; cold hops have empty / bypassed retrieval. The gate requires the active run to **strictly out-trace** the cold run (≥1 hop where active surfaced a citation the cold run did not) AND the active run to reach merge with fewer worker retries than (or equal to and no worse than) cold. The gap is the proof.

---

## §4 — Retrieval trace at every hop

Every spawned agent's `agent_query.query()` writes a `public.retrieval_events` row (`agent, query_text, collections, k_initial, k_returned, elapsed_ms, bypass_rerank, top_citation_id, top_score, occurred_at`). The harness collects, per hop, the rows for that hop's agent within the run window. **A hop with no retrieval_events row in the recall-active run is a FAIL** (recall did not fire there).

---

## §5 — Success criteria (ALL must hold, recall-active run)

| # | Criterion | Measured by |
|---|---|---|
| S1 | PR merged to `main` | `gh pr view <n> --json state` → `MERGED` |
| S2 | CI passed | `gh pr checks <n>` all green before merge |
| S3 | Governance honoured | callsign tag on PR title + commits; **2-of-3** (or 2-of-2 author-excluded) `[REVIEW:approve:<callsign>]` NATS-concur comments present; claim-before-touch observed; **no Linear write** |
| S4 | Trace at every hop | a `retrieval_events` row for each of the 4 hop agents (§4) |
| S5 | Memory gap demonstrated | §3 — active strictly out-traces cold |

Any criterion failing → **gate FAILS → cutover does NOT proceed.**

---

## §6 — Run prerequisites (gate is inert until all true)

1. **`Agency_OS-f5yt`** — work-loop consumer deployed + running (subscribed to `keiracom:tasks:available`, wired to `/dispatcher/spawn`). **Pending.**
2. **Nova `#1268`** — `exit_cycle.classify_and_save` merged (Chat hop write). **Pending.**
3. Live Hindsight (`:8889`) + reranker (`:8091`) reachable; `DATABASE_URL`/`RETRIEVAL_EVENTS_DSN` set (trace reads).
4. A real open backlog KEI exists (§2).

Until 1+2 land, `scripts/cutover/full_chain_dress_rehearsal.py` **self-skips** (exit 0, prints readiness) — the harness is built and CI-green; the green run is captured when the loop is switched on.

---

## §7 — Harness

- `scripts/cutover/full_chain_dress_rehearsal.py` — driver: real-KEI selection (§2), seed task per run (§3), poll hops, collect per-hop traces (§4), dual run + gap (§3/§5-S5), success evaluation (§5). `--live` + loop-reachable required; otherwise SKIP.
- `tests/scripts/test_full_chain_dress_rehearsal.py` — unit tests for the pure core (KEI selection, gap computation, success evaluation, skip-guard) — runnable + green now, without the live loop.

## §8 — Open wiring dependencies (flagged to Elliot / Atlas)

- **`recall_mode` honouring** in the consumer/dispatcher (§3) — confirm with Atlas (#1275 owner) or fall back to fleet-env flip between runs.
- **Task-seed schema** — the production path is a Postgres task-row insert that triggers the publish to `keiracom:tasks:available`; the harness publishes to that channel directly (contract-equivalent for the consumer). Confirm the exact task payload fields with Atlas before the live run.
- **Governance-honoured (S3) automation** — callsign + concur checks via `gh`; claim-before-touch + no-Linear-write are observed from logs. Final S3 automation may need the enforcer's signals.
