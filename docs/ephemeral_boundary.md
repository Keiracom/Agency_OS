# Ephemeral Persistence Boundary (V1 chain)

**Status:** ratified — sourced from `ceo:v1_chain_architecture` and `ceo:v1_chain_roles_ratified_2026_05_29` (Dave, 2026-05-29).
**KEI:** Agency_OS-b0lx. **Companion:** the [Agent loop architecture (V1 chain)](../README.md#agent-loop-architecture-v1-chain) section.

Every agent in the V1 chain runs as a **separate, short-lived spawn** — Face → Aiden (deliberate) → Max (challenge) → `[CONCUR]` → Worker → Orion (spec) + Atlas (safety) → `[DUAL CONCUR]` → result to Slack. No agent shares process memory with the next. This document is the reference for **what an agent must write before it exits** versus **what is automatically available when the next one spawns**. If a fact is not written to a persistent store before exit, it is gone.

> **The one rule that makes everything else work:** *nothing is persisted automatically.* Each role is responsible for its own writes at exit. Write discipline at exit is the gate — skip it and the next spawn starts blind.

---

## 1. What SURVIVES between spawns (persistent stores)

| Store | Holds | Written by | Read at |
|-------|-------|------------|---------|
| **Hindsight** (Weaviate `fleet_decisions` bank) | AtomV1 atoms — the decisions/knowledge an agent produced | any agent on exit (`exit_cycle.classify_and_save`) | next spawn, Layer 2 recall |
| **Postgres `public.tasks`** | task rows: status, title/brief, acceptance criteria, concur/reject | Worker + Reviewers | dispatcher, work-loop consumer |
| **Postgres `public.keiracom_spawn_attribution`** | per-spawn cost/telemetry (`cost_usd`, tokens, source, completion_status) | Worker (and dispatcher hook) on exit | operator rollups |
| **Postgres `public.persona_bank`** | role system prompts (5 rows: face/aiden/max/orion/atlas) | provisioning (Orion) | spawn, Layer 1 |
| **Postgres `public.agent_memories` / `public.ceo_memory`** | facts, daily logs, directives; `ceo_memory` is the governance audit/admin target | agents + governance writers | recall, governance gates |
| **Valkey / Redis** | task queue + concurrency leases (see TTLs below) | work-loop consumer | work-loop consumer |

**AtomV1 atom shape** (`ceo:atomization_architecture_v1`): `trigger_condition`, `content`, `anti_pattern`, `example`, `provenance`, `supersession_edges`, `composition_tags`.

**Valkey keys (with TTLs)** — from `src/keiracom_system/work_loop/consumer.py`:

| Key | Type | TTL | Purpose |
|-----|------|-----|---------|
| `keiracom:tasks:available` | pub/sub channel | — | new-task announcements |
| `keiracom:tenant:active_spawns:{tenant_id}` | INT | none | live concurrent-spawn counter |
| `keiracom:tenant:lease:{tenant_id}:{task_id}` | STR | 300s | per-agent slot lease (heartbeat renews) |
| `keiracom:tenant:leases:{tenant_id}` | SET | none | task_ids the counter believes live |
| `keiracom:tenant:overflow:{tenant_id}` | LIST | none | tasks queued at the tier ceiling (FIFO, never dropped) |
| `keiracom:tasks:lock:{task_id}` | STR | 300s | distributed dup-spawn lock |
| `keiracom:tasks:attempts:{task_id}` | INT | 3600s | spawn-attempt counter (drives dead-letter at max) |
| `keiracom:tasks:deadletter` | LIST | none | tasks that exhausted retries |

> **Cutover note:** Postgres is Supabase today and migrating to Railway Postgres (`ceo:two_store_architecture_v1`). Post-cutover, Hindsight is the sole knowledge store and `ceo_memory` is audit/admin only — **not a pipeline step** (`ceo:session_2026-05-28_architecture_decisions`). The boundary in this doc is store-role-stable across that move.

---

## 2. What DIES with the spawn (ephemeral)

Gone the moment the agent process exits — never assume any of this reaches the next spawn:

- **The in-process context window** — the conversation/reasoning the agent just did.
- **Local variables and in-memory state** — anything not flushed to a store above.
- **tmux pane / session state** — pane scrollback, shell variables, cwd.
- **Any file under `/tmp`** written without an explicit persistence step (e.g. scratch output, intermediate artifacts).
- **Redis "whiteboard" scratch** — fast cross-task coordination is ephemeral by design; task-relevant state must route to a durable store explicitly, not live in Redis as de-facto memory.

---

## 3. The write discipline — what each role writes before exit

Nothing writes automatically. Before an agent exits, it **must** perform its writes or the work is invisible to the chain.

**Worker**
- AtomV1 atom → Hindsight `fleet_decisions`, via `src.keiracom_system.chat.exit_cycle.classify_and_save` (Gemini classifier, confidence > 0.8, max 3 atoms — the precision gate).
- Task status update in `public.tasks` (done / blocked + result).
- Spawn row in `public.keiracom_spawn_attribution` (`cost_usd` + tokens + completion_status).
- Signal the reviewers (NATS) that output is ready.

**Deliberators (Aiden + Max)**
- Aiden writes the structured KEI work plan; Max writes a CONCUR or BLOCK (one sentence per gap). Two CONCURs are required before the Worker is dispatched.

**Reviewers (Orion + Atlas)**
- Review-result atom → Hindsight, and a CONCUR / REJECT recorded on the task row. Both must CONCUR (dual concur) before merge/completion; neither concurs alone.

**All agents**
- **Nothing writes automatically — write discipline at exit is the gate.** An agent that exits without its writes hands the next spawn an empty context.

---

## 4. What the NEXT spawn picks up (the 4-layer context contract)

On spawn, the dispatcher hydrates the agent through four layers (`ceo:session_2026-05-28_architecture_decisions` — `ephemeral_spawn_contract`). **Fail-open at every layer:** a missing layer degrades context, it does not abort the spawn.

| Layer | Source | Contents |
|-------|--------|----------|
| **L1 — system prompt** | `public.persona_bank` via `GET /dispatcher/persona?role=<role>&tier=<tier>&variant=<variant>` | the role's identity/instructions |
| **L2 — Hindsight recall** | Weaviate `fleet_decisions` | 3–5 relevant AtomV1 atoms (~100–150 tokens, no repeated preamble) |
| **L3 — spend gate** | Valkey | per-tenant spend/ceiling check before the run proceeds |
| **L4 — dispatcher wiring** | dispatcher | `task_id`, `callsign`, env, and the atom pointer for this task |

**Hand-off mechanism:** the exiting agent writes its atom to Hindsight; NATS carries `task_id + atom_id` to the next agent; the next agent recalls the atom at spawn via L2. The pointer travels over NATS — the payload lives in Hindsight.

---

## Notes — canonical sources (audit-dispatch checklist)

- `ceo:v1_chain_architecture` (2026-05-29): chain = `Face -> Aiden (deliberate) -> Max (challenge) -> [CONCUR] -> Worker -> Orion (spec) + Atlas (safety) -> [DUAL CONCUR] -> Slack`; handoff = AtomV1 pointer over NATS (`task_id + atom_id`), recalled at spawn; persona_bank = 5 rows served via `GET /dispatcher/persona`.
- `ceo:v1_chain_roles_ratified_2026_05_29`: role identities (Face / Aiden=Architect / Max=Challenger / Orion=Spec / Atlas=Quality+Safety).
- `ceo:ephemeral_capture_model_v1` (v2): direct-write capture — `exit_cycle.classify_and_save`; nothing writes automatically.
- `ceo:session_2026-05-28_architecture_decisions`: two-store model + 4-layer ephemeral spawn contract.
- `ceo:atomization_architecture_v1`: AtomV1 schema.
- `ceo:two_store_architecture_v1`: Postgres (operational) + Hindsight (knowledge); Supabase → Railway cutover.
