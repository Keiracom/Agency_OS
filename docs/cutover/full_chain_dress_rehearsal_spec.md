# Full-Chain Dress-Rehearsal — THE Cutover Gate

**KEI:** `Agency_OS-jb4e` (P0). **Design:** Viktor (thread 1779955041) + Dave/Viktor **v2.0** 2026-05-29. **Owner:** Aiden · **Build:** Scout.
**Status:** ▸ HARNESS BUILT — live run **GATED on `Agency_OS-f5yt`** (work-loop consumer running) + the dispatcher container-defaults fix (g9xx). Nothing flips until this gate passes.

## v2.0 deltas (Dave/Viktor 2026-05-29)

1. **SEAM (single wire):** the Slack-origin step (Chat hop entry) and Atlas's task producer are the **same wire** — build to Atlas's shared-interface note (incoming), NOT a parallel path. The Slack-origin step is **HELD** until Atlas confirms whether a `Slack → public.tasks` row-creator even exists. The harness's `seed_task` (INSERT into `public.tasks`) IS that shared wire for seeding; it does not build a second Slack path.
2. **WITNESS (live #ceo, Dave signs off):** the rehearsal streams its log **LIVE to #ceo in real time** — state transitions, retrieval trace, cost per run, failure results — so **Dave watches it happen**. **Dave's P1-P11 pass/fail table is the sign-off — NOT the harness.** The harness is the witness/instrument: it produces the per-criterion evidence (`collect_gate_evidence`) and streams it (`post_witness`); it never self-declares the gate passed.
3. **COST (soak binds, per-loop is a floor):** the rehearsal measures **per-loop cost as a FLOOR**. The **binding** number is the **48-72h soak actual run-rate** (`soak_run_rate_aud`) validated against **A$350** (`validate_soak`). A single-loop estimate is not the cost gate.
4. **Gate = P1-P11 + 4 runs** (`cold` / `recall` / `crash` / `dead_letter`) — supersedes the earlier S1-S5 / 2-run shape. **P1-P11 below are PROPOSED — pending Viktor's authoritative enumeration (flagged to Elliot).**

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

The KEI under test MUST be a genuine backlog item, never a test fixture — the gate proves the system does **real work** end-to-end (governance + merge included), not a toy (Viktor; Elliot ratified 2026-05-29).

**First-run safety (Elliot 2026-05-29):** `select_gate_kei` picks a deliberately **LOW-STAKES real KEI** (docs / trivial / P3-P4 scope) so the real PR + auto-merge is safe to land. Synthetic markers excluded: ids matching `KEI-TEST` / `*-test*` / `test001`, or titles containing `smoke`/`scaffold`/`dress-rehearsal`/`bd claim`. Note: bare `test` is **not** a synthetic title marker — a real "add tests for X" KEI is a valid low-stakes subject.

**Fallback:** if no low-stakes real KEI is ready, the harness falls back to a synthetic `rehearsal task` (`rehearsal-1`) — it will **never** auto-merge a high-stakes real PR on the first run.

---

## §3 — Dual run (recall-active vs cold)

| Run | Recall config | Purpose |
|---|---|---|
| **A — recall-active** | `DISPATCHER_SPAWN_RECALL_ENABLED=true` + **restart dispatcher**; Hindsight + reranker reachable | the real ephemeral pipeline |
| **B — cold** | `DISPATCHER_SPAWN_RECALL_ENABLED` **unset** + **restart dispatcher** | the control — agents act with no memory |

Both runs use the **same task** (re-seeded between). **Recall is toggled by the
`DISPATCHER_SPAWN_RECALL_ENABLED` env on the dispatcher + a restart between arms —
NOT a per-task flag** (Atlas grounding 2026-05-29). Restart-between-arms is
acceptable; the harness runs one arm, the operator (or the harness's restart
hook) flips the env + restarts the dispatcher, then runs the other arm.

### Seed (Atlas-grounded 2026-05-29)

Each arm is driven by inserting a task row — the `public.tasks` AFTER-INSERT
trigger (#1275) publishes to `keiracom:tasks:available`, which the consumer
drains:

```sql
INSERT INTO public.tasks (id, title, status) VALUES ('rehearsal-1', 'rehearsal task', 'available');
```

The harness binds the values as parameters (injection-safe). **Open question for
Elliot:** Viktor's design says "real backlog KEI, not synthetic", but Atlas's
seed example is a dedicated `rehearsal task`. The harness defaults to a real
`bd ready` KEI (§2); confirm whether a dedicated rehearsal task is the canonical
gate subject instead.

### THE recall assert (Elliot 2026-05-29)

`assert_recall_returned_atom(recall_active_run)` — the recall-active arm MUST
surface **≥1 relevant atom** (a hop where recall fired, was not bypassed, and
returned a scored citation). Zero atoms in the recall arm = gate FAIL (criterion
S5). This is the concrete, measured memory proof.

**Memory gap (what we measure per hop):** recall-active hops have non-empty `retrieval_events` rows with `bypass_rerank=false` and `top_score > 0`; cold hops have empty / bypassed retrieval. The gate requires the active run to **strictly out-trace** the cold run (≥1 hop where active surfaced a citation the cold run did not) AND the active run to reach merge with fewer worker retries than (or equal to and no worse than) cold. The gap is the proof.

---

## §4 — Retrieval trace at every hop

Every spawned agent's `agent_query.query()` writes a `public.retrieval_events` row (`agent, query_text, collections, k_initial, k_returned, elapsed_ms, bypass_rerank, top_citation_id, top_score, occurred_at`). The harness collects, per hop, the rows for that hop's agent within the run window. **A hop with no retrieval_events row in the recall-active run is a FAIL** (recall did not fire there).

---

## §5 — P1-P11 evidence (PROPOSED — DAVE's table is the sign-off)

The gate is **4 runs** (`cold` / `recall` / `crash` / `dead_letter`). The harness
produces the evidence per criterion (`collect_gate_evidence`) and streams it LIVE
to #ceo; **Dave marks each P pass/fail** — the harness never self-declares the gate
passed. **The list below is PROPOSED, pending Viktor's authoritative P1-P11.**

| P | Criterion | Run | Observed by |
|---|---|---|---|
| P1 | cold run completes (control) | cold | run present + chain ran |
| P2 | recall run completes | recall | run present + chain ran |
| P3 | crash run **recovers** | crash | `recovered=true` after injected crash |
| P4 | dead-letter run routes failed task to **DLQ** | dead_letter | `dead_lettered=true` |
| P5 | PR merged to `main` | recall | `gh pr view --json state → MERGED` |
| P6 | CI passed | recall | `gh pr checks` green pre-merge |
| P7 | governance honoured | recall | callsign tag + **2-of-3** concur + claim-before-touch + **no Linear write** |
| P8 | retrieval trace at every hop | recall | a `retrieval_events` row per hop agent |
| P9 | recall returned **≥1 relevant atom** | recall | `assert_recall_returned_atom` |
| P10 | memory gap (recall **out-traces** cold) | recall vs cold | `memory_gap.active_strictly_outtraces_cold` |
| P11 | per-loop cost floor measured | all | `cost_aud > 0`; **binding** = 48-72h soak run-rate ≤ A$350 (§3 / `validate_soak`) |

Dave's table is authoritative. The harness streaming + evidence exists so the
sign-off is **witnessed**, not asserted.

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

## §9 — Failure-path scenarios (the harness must detect + report each, never hang)

| Failure mode | Trigger | Detection |
|---|---|---|
| `spawn_rejected` | `/dispatcher/spawn` non-2xx — **TODAY: 400 = missing container image/name/port** (Atlas container-defaults fix pending) | `classify_spawn_failure(status)` → surfaced, not a silent hang |
| `no_trace` | a hop fired no `retrieval_events` row | S4 — missing-hop reason |
| `no_recall_atom` | recall arm surfaced 0 relevant atoms | `assert_recall_returned_atom` → S5 |
| `pr_not_opened` / `not_merged` | chain produced no PR / PR unmerged | S1 |
| `ci_failed` | PR CI not green | S2 |
| `governance_violation` | callsign / <2 concur / claim / Linear-write | S3 |
| `no_memory_gap` | recall arm did not out-trace cold | S5 |

The harness classifies the failure and reports it; it never reports a false pass.

## §8 — Open wiring dependencies (flagged to Elliot / Atlas)

- **Real-spawn arm gated on the dispatcher container-defaults fix.** Live container spawn returns **400 today** (missing image/name/port); Atlas is shipping the fix. Until it lands, `spawn_rejected` fires and the real-spawn arm cannot complete. Everything else (seed, trace collection, dual-arm comparison, recall-atom assert, gate evaluation, failure classification) is built + tested now.
- **Recall toggle** is env (`DISPATCHER_SPAWN_RECALL_ENABLED`) + dispatcher restart between arms (Atlas grounding 2026-05-29) — resolved; no per-task flag needed.
- **Seed schema** = `INSERT INTO public.tasks (id, title, status) VALUES (…, 'available')` (Atlas grounding) — resolved; harness binds values as parameters.
- **Real-KEI vs rehearsal-task** — confirm whether the gate subject is a real `bd ready` KEI (Viktor) or a dedicated `rehearsal task` (Atlas's seed example). Harness defaults to a real KEI.
- **Governance-honoured (S3) automation** — callsign + concur via `gh`; claim-before-touch + no-Linear-write observed from logs / enforcer signals.
