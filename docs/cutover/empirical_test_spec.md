# Empirical End-to-End Test Spec — Ephemeral Agent + Retrieval

**Cutover gate item 2 (the critical gate).** Proves that an ephemeral agent —
one spawned with no prior session context — can retrieve a past decision it
could not otherwise know, with the cross-encoder reranker actually engaged, and
use it to answer a real task.

- **Dispatch:** Elliot, 2026-05-28 (cutover gate item 2)
- **Author:** Nova
- **Status:** spec — **partially runnable now.** Stage A (retrieval quality)
  and Stage B.1 (context injection) are runnable once PR #1246 merges. **Stage
  B.2 + criterion P5 (agent consumes the injected memory) are BLOCKED** pending
  the session-launch wrapper (see §6) — that wrapper does not yet exist
  (`spawn_recall.py` marks it out-of-scope). This spec documents the gate
  accurately at current state; full gate sign-off requires §6 first.
- **Related:** PR #1246 (reranker on :8091), Wave 3 retrieval orchestrator

---

## 0. System under test

| Component | Identity | Notes |
|---|---|---|
| Reranker sidecar | TEI `cpu-1.7`, `BAAI/bge-reranker-base`, `http://localhost:8091` | `--auto-truncate`, `--max-client-batch-size=128` (PR #1246) |
| Hindsight | `http://localhost:8889`, tenant slug `default` | bank `fleet_decisions` populated (~1900 docs as of 2026-05-28) |
| Retrieval orchestrator | `src/retrieval/orchestrator.py` → `retrieve_with_outcome()` | reranker gated behind `DISPATCHER_RERANKER_ENABLED` |
| Agent query entry | `src/retrieval/agent_query.py` → `query()` | returns `QueryResult(answer, citations, elapsed_ms, bypass_rerank)`; writes `public.retrieval_events` |
| Ephemeral-spawn recall | `src/retrieval/spawn_recall.py` → `inject_prior_context()` | injects top-3 block into `env[AGENCY_OS_PRIOR_CONTEXT]`, forwarded to the agent via `--append-system-prompt` |
| Collection → bank map | `orchestrator.HINDSIGHT_BANK_BY_CLASS` | `Decisions → fleet_decisions` |

**Required environment for the test run:**
```
DISPATCHER_RERANKER_ENABLED=true     # engages the cross-encoder; without it the path is raw-ANN
HINDSIGHT_BASE=http://localhost:8889
KEIRACOM_RERANKER_URL=http://localhost:8091
```

**Pre-flight (all must pass before the test is valid):**
```
curl -fsS http://localhost:8091/health                 # → 200
curl -fsS http://localhost:8091/info | grep bge-reranker-base
curl -fsS http://localhost:8889/health                 # → {"status":"healthy"...}
curl -fsS http://localhost:8889/v1/default/banks/fleet_decisions/stats   # total_documents > 1000
```

---

## 1. The test task

The task must demand a **ratified past decision the agent cannot derive from its
session context** — i.e. genuine retrieval, not reasoning from the prompt.

### 1.1 Primary task (corpus-verified)

> **"What is the ratified decision on how this system handles multi-tenancy —
> one shared system or per-tenant isolation, and how are tenant IDs assigned?"**

- **Why this task:** the decision is a concrete, ratified fact (single shared
  system with tenant isolation; Dave = tenant_id 1, customers = tenant_id 2+)
  that an ephemeral agent has no way to infer from a cold prompt.
- **Expected memory that MUST surface in top-3** (verified retrievable
  2026-05-28, reranker score **0.97**):
  > "Decision made for single system with tenant isolation, no sandbox or
  > mirrored version; Dave is tenant_id 1 and customers are tenant_id 2+."
- **Supporting memories expected in the pool:** "multi-tenant isolation at the
  API layer" (0.94), "per-tenant storage isolation enforced" (0.57).

### 1.2 Control task (corpus-verified second topic)

> **"What governance rule covers the three-store completion requirement, and is
> it mechanized?"**

- **Expected top-3 memory** (verified, reranker score **0.98**):
  > "Governance Rule 6 directive 'GOV-6-three-store-completion-mechanized'
  > completed … after ensuring all required documents were written."

Running two independent topics guards against a single-topic fluke.

### 1.3 ⚠ Finding on the originally-suggested tasks — do NOT use as written

The dispatch suggested *"the ratified decision on the dispatcher canonical
implementation"* and *"what governance rule applies to direct Anthropic SDK
calls"*. Both were **empirically probed against the live reranked pipeline on
2026-05-28 and retrieve weakly** from `fleet_decisions`:

| Suggested query | Top reranker score | Top hit |
|---|---|---|
| dispatcher canonical implementation | **0.08** | generic "one canonical parser per data source" |
| governance rule / direct Anthropic SDK calls | **0.07** | unrelated Governance Rules 1/5/3a |

Root cause: `fleet_decisions` is sourced **only** from `public.ceo_memory`
(Weaviate `Decisions` class). The dispatcher-canonical decision and the
Skills-First / direct-SDK rule (LAW XII) live in governance docs / commits / bd
— not in `ceo_memory`. **Using either as the test task would produce a FALSE
FAIL** (corpus gap, not a retrieval-system defect).

**Recommendation:** use §1.1/§1.2 for the cutover gate now. If the
dispatcher/LAW-XII topics are required, index their source into the appropriate
bank first (separate task) and re-verify retrievability before adding them.

---

## 2. Test procedure

Run on the fleet host (where Hindsight + reranker live), from the repo root with
the venv python and `PYTHONPATH=.`.

### Stage A — Retrieval-layer proof (orchestrator direct)

Confirms the reranked retrieval path returns the right memory with the sidecar
engaged, independent of any agent.

```python
import os
os.environ["DISPATCHER_RERANKER_ENABLED"] = "true"      # set BEFORE import (module-level flag)
os.environ["HINDSIGHT_BASE"] = "http://localhost:8889"
from src.retrieval import orchestrator as o

outcome = o.retrieve_with_outcome(
    "What is the ratified decision on how this system handles multi-tenancy "
    "— one shared system or per-tenant isolation, and how are tenant IDs assigned?",
    ("Decisions",), k_initial=20, k_returned=3, tenant_id="default",
)
print("rerank_reason:", outcome.rerank_reason)      # expect "sidecar_reranked"
print("bypass:", outcome.bypass_rerank)             # expect False
for i, n in enumerate(outcome.nodes):
    print(i + 1, round(n.score, 4), n.text[:160])
```

### Stage B.1 — Context injection proof (RUNNABLE NOW)

Confirms the spawn-time recall hook produces the injectable block from the
retrieved decision. This does **not** spawn an agent — it exercises
`inject_prior_context` directly, which is the full extent of what is runnable
until the §6 wrapper exists.

```python
from src.retrieval import spawn_recall
kwargs = spawn_recall.inject_prior_context(
    {"env": {}},
    task_type="research",
    task_brief="Answer: ratified decision on multi-tenancy / tenant-id assignment.",
)
block = kwargs["env"][spawn_recall.PRIOR_CONTEXT_ENV_KEY]
print(block)   # the "Prior context from memory" block that WOULD be injected
```
Satisfies **P4** (block non-empty, contains the expected decision) and
indirectly re-confirms P1–P3/P6 (the block is built from the reranked recall).

### Stage B.2 — Agent-consumes-memory proof (⛔ BLOCKED — not yet runnable)

> **Blocked pending §6.** The session-launch wrapper that reads
> `env[AGENCY_OS_PRIOR_CONTEXT]` and forwards it to the agent CLI via
> `--append-system-prompt` **does not exist yet** — `spawn_recall.py`'s own
> docstring marks it "out of scope (separate PR)". Without it there is no path
> for the injected block to reach a spawned agent's context, so **P5 cannot be
> observed**. Do not mark gate item 2 fully passed until §6 lands and this stage
> runs green.

Intended steps once unblocked:
1. Spawn the ephemeral agent through the §6 wrapper with `kwargs["env"]` (so
   `AGENCY_OS_PRIOR_CONTEXT` reaches the agent via `--append-system-prompt`).
   The agent starts with **no other memory**.
2. Give the agent the §1.1 task verbatim.
3. Observe the agent's answer (P5) and the audit row:
   ```sql
   SELECT agent, top_citation_id, top_score, bypass_rerank, elapsed_ms, created_at
   FROM public.retrieval_events
   ORDER BY created_at DESC LIMIT 5;
   ```

### Stage C — Repeat Stage A + Stage B.1 for the §1.2 control task (B.2 when unblocked).

---

## 3. Pass criteria (all must hold)

| # | Criterion | Measured by |
|---|---|---|
| P1 | Reranker engaged, not bypassed | Stage A `rerank_reason == "sidecar_reranked"` **and** `bypass_rerank == False`; Stage B.1 `retrieval_events.bypass_rerank == false` (the recall fires `agent_query.query`, which writes the row) |
| P2 | Correct memory in top-3 | The §1.1 expected memory (tenant isolation, Dave=1/customers=2+) appears among the 3 returned nodes/citations |
| P3 | Reranker discriminates | Top node score **≥ 0.5** for the primary task (observed 0.97); top score strictly greater than the 3rd |
| P4 | Context actually injected | Stage B.1 `env[AGENCY_OS_PRIOR_CONTEXT]` is **non-empty** and contains the expected decision text — **RUNNABLE NOW** |
| P5 | Agent uses retrieved memory | The ephemeral agent's answer states the ratified decision (single shared system, tenant isolation, Dave=1/customers=2+) and attributes it to the injected prior-context block — **not** a hedge ("I don't have that information") and **not** a fabricated answer — **⛔ BLOCKED: not runnable until the §6 wrapper exists** |
| P6 | Audit trail written | A `public.retrieval_events` row exists for the run with non-null `top_citation_id` and `top_score > 0` |
| P7 | Control task also passes | §1.2 satisfies P1–P4 + P6 now; P5 when unblocked (expected GOV-6 three-store memory in top-3, score ≥ 0.5) |

**Runnable now (Stage A + B.1):** P1, P2, P3, P4, P6, and their P7 equivalents.
**Blocked on §6 wrapper:** P5 (and P7's P5 component). The gate is **not fully
signed off** until P5 passes — Stages A + B.1 green is a *partial* pass that
proves retrieval quality + injection, but not end-to-end agent consumption.

---

## 4. Fail criteria & cutover implications

| Failure | Signal | Meaning for cutover |
|---|---|---|
| Reranker bypassed | `rerank_reason ∈ {sidecar_unavailable, reranker_flag_off, empty_pool}` or `bypass_rerank == True` | **BLOCK.** The gate is specifically that *reranking* works end-to-end; raw-ANN fallback is not a pass. Fix the sidecar / flag before cutover. |
| Wrong/missing memory | expected decision absent from top-3 | **BLOCK.** Retrieval can't surface known decisions → ephemeral agents will operate blind. Investigate corpus coverage + reranker scoring. |
| Empty injected block | Stage B block is `""` | **BLOCK.** The spawn-recall hook is broken; ephemeral agents spawn with no memory regardless of corpus quality. |
| Agent ignores context | answer hedges or fabricates despite a correct injected block | **BLOCK.** The retrieval works but the agent doesn't consume it — the system-prompt forwarding (`--append-system-prompt`) or the agent's use of prior-context is broken. |
| No audit row | `retrieval_events` empty for the run | **CONDITIONAL.** Retrieval may still work, but observability is broken — fix before cutover (no way to monitor ephemeral retrieval in prod). |

A single BLOCK on the primary OR control task fails the gate. Cutover to
ephemeral agents does not proceed until all BLOCKs clear.

---

## 5. Who runs it & how

- **Runner:** the retrieval-substrate owner (Nova), on the fleet host, because
  the reranker (`:8091`) and Hindsight (`:8889`) are loopback-only there.
- **When:** after PR #1246 merges (so the reranker config is on `main`) and
  `keiracom-reranker-sidecar.service` is installed + healthy.
- **How:** execute Stages A→C from §2 manually, record raw output verbatim
  (anti-ghost-green), and check each row of §3 against the observed values.
  Report pass/fail per criterion with the raw `rerank_reason`, the top-3
  scores+excerpts, the injected block, and the `retrieval_events` row.
- **Sign-off:** result posted to #execution / Elliot. A **partial pass**
  (Stages A + B.1: P1–P4, P6) clears the *retrieval-quality + injection* portion
  of the gate. **Full** gate item 2 sign-off requires P5 — i.e. §6 built and
  Stage B.2 green across both tasks.
- **Automation (follow-up, not blocking):** Stage A is directly portable to a
  `pytest` e2e (`tests/cutover/test_empirical_retrieval.py`) once the reranker
  runs in CI; Stage B.2 requires a live spawn harness and stays manual for V1.

---

## 6. Stage B.2 unblock — build the session-launch wrapper

Stage B.2 / P5 cannot run until a wrapper bridges the injected env var to the
agent CLI. Current gap: `spawn_recall.inject_prior_context` writes the recall
block to `env[AGENCY_OS_PRIOR_CONTEXT]`, but nothing reads it back and forwards
it to the spawned agent.

**Required wrapper** (e.g. `scripts/run_agent_with_recall.sh`):
1. Read `AGENCY_OS_PRIOR_CONTEXT` from the environment.
2. If non-empty, pass it to the agent CLI via `--append-system-prompt` (so the
   block lands in the agent's system prompt); if empty, launch normally
   (fail-open — recall outage never blocks a spawn).
3. Be the launch path the dispatcher spawn uses for ephemeral agents, so the
   injection from `inject_prior_context` actually reaches the agent.

**Acceptance for the wrapper:** spawning through it with a populated
`AGENCY_OS_PRIOR_CONTEXT` results in an agent whose system prompt contains the
"Prior context from memory" block (verifiable by having the agent echo or act
on it). Once it exists, run Stage B.2 → confirm P5 → full gate sign-off.

**Sequencing:** filed as the next dispatch after this spec merges (Elliot,
2026-05-28). This spec is accurate documentation of the gate at current state;
the wrapper is the one remaining build to make the gate fully runnable.

---

## Appendix — empirical pre-validation (2026-05-28, live pipeline)

Probed via `orchestrator.retrieve_with_outcome(..., ("Decisions",), tenant_id="default")`
with `DISPATCHER_RERANKER_ENABLED=true`, reranker on `:8091`, `fleet_decisions`
at ~1900 docs. All five returned `rerank_reason=sidecar_reranked`:

| Topic | Top score | Verdict |
|---|---|---|
| tenant isolation (§1.1) | 0.97 | strong — **chosen primary** |
| three-store completion (§1.2) | 0.98 | strong — **chosen control** |
| memory layer cutover | 0.92 | strong (alternate) |
| budget ceiling enforcement | 0.55 | relevant (alternate) |
| dispatcher bounded spawn | 0.19 | weak — corpus gap, **not used** |
| dispatcher canonical implementation (suggested) | 0.08 | weak — corpus gap, **not used** |
| governance rule / direct SDK calls (suggested) | 0.07 | weak — corpus gap, **not used** |
