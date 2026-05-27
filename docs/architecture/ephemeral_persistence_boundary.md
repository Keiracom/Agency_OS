# Ephemeral Persistence Boundary — Spec

**Status:** RATIFIED-CEO via Cutover Readiness Gate (Dave directive 2026-05-27)
**Anchor:** Cutover Readiness Gate STATE_SEPARATION section
**Filed under:** Agency_OS-b0lx (cutover-blocker 8)
**Inventory row:** Category 21 — Cutover Readiness Gate (V2 inventory)

This document is the canonical reference for **what survives between Claude spawns and what dies with them**. Every engineer touching the dispatcher, atomization, ephemeral agent, or any per-spawn state code must read this before designing reads or writes.

The boundary is **load-bearing** for the bounded-spawn discipline. If state that should DIE survives, multi-agent reasoning chains corrupt on non-determinism. If state that should SURVIVE dies, agents lose access to durable ground truth and re-derive incorrectly.

---

## 1. SURVIVES between spawns

State in this list is durable across the full Claude process lifecycle: termination, restart, host reboot, the entire fleet rotating through respawns. Agents read it; agents write to it via the documented APIs.

### (a) Temporal Workflow state

- **Lives in:** Temporal cluster (workflow + activity state) backed by Postgres
- **Carries:** task_id, status (pending/in-progress/completed/failed), dependencies (blocked-by chain), prior task outputs (signals + workflow results)
- **Why durable:** Temporal's replayable workflow log IS the source of truth for in-flight task graphs; survives worker restarts by design
- **Read API:** Temporal Python SDK + workflow handle queries
- **Write API:** activities + signals (NEVER direct DB)

### (b) Hindsight semantic memory

- **Lives in:** Hindsight engine (self-hosted Postgres + pgvector backend)
- **Carries:** ratified decisions, recurring patterns, deliberation outcomes, supersession chains, atomized skill atoms (per atomization pilot PRs #1185/#1189/#1191)
- **Why durable:** the canonical knowledge layer; pulled targeted via memory MCP tools at reasoning time
- **Read API:** `mem.wrap.*` wrappers (Decision/AntiPattern/Artifact/Observation per PR #1134) → memory MCP tools
- **Write API:** same wrappers; agents call them via MCP, never direct SQL

### (c) ceo_memory canonical keys

- **Lives in:** Supabase `public.ceo_memory` table
- **Carries:** ratified facts, directives, canonical decisions, governance rules (e.g. `ceo:boundary_matrix_v1`, `ceo:atomization_architecture_v1`, `ceo:five_store_completion_rule`)
- **Why durable:** the policy layer; would-this-content-read-the-same-way-for-any-tenant test classifies as policy → ceo_memory (per boundary matrix v1 §5 policy-vs-memory test)
- **Read API:** Supabase MCP execute_sql OR `control_plane` wrappers (when built)
- **Write API:** `three_store_save.py` discipline + LAW XV five-store rule for directive ratifications

### (d) Git history

- **Lives in:** GitHub Keiracom/Agency_OS repo
- **Carries:** code, PRs, commits, branches, merge history, review comments (orchestrator-merge-after-NATS-concur signals)
- **Why durable:** ground truth for the codebase; PRs are the operator-visible state of in-flight work
- **Read API:** `gh` CLI + git tools
- **Write API:** `git commit` + `gh pr create` (only — never force-push to main without Dave override)

### (e) Atomized skills + system prompt + IDENTITY template + tool definitions

- **Lives in:**
  - System prompt + IDENTITY: per-callsign template under `docs/runbooks/<callsign>-identity.md` (fallback `IDENTITY.md`)
  - Atomized skills: Hindsight `mem.wrap.atom` rows post-atomization-pilot (PRs #1185/#1189)
  - Tool definitions: MCP server registrations (tier-aware per PR #1136)
- **Carries:** the agent's role brief, persona, available tools, skill knowledge
- **Why durable:** loaded fresh at spawn (per `spawn_composer.py` Part A/B template) but the SOURCE files survive
- **Read API:** `spawn_composer.compose_initial_prompt()` Part A/B/D/E (PR #1184)
- **Write API:** IDENTITY/runbook edits via PR review; atom updates via atomizer + verifier pipeline

---

## 2. DIES with spawn

State in this list terminates when the Claude process exits, the keepalive respawns, or any spawn-cycle boundary is crossed. **By design.** Treating any of these as durable is the cardinal anti-pattern.

### (a) Agent process memory

- Variables, in-process state, accumulated context vectors
- Python module-level caches inside the running Claude
- Any state that lives only in Claude's runtime

### (b) Conversation history

- The current Claude conversation transcript — every turn, tool call, response
- Per Dave directive 2026-05-27 keepalive bounded-spawn discipline (PR #1201): `claude` respawns WITHOUT `--continue` by default; conversation context does NOT carry over unless `--preserve-context "<justification>"` is explicitly set + logged to `/tmp/keepalive_override_log.jsonl`

### (c) Tool client state

- MCP client connection state (gets re-established per spawn via fresh handshake)
- HTTP session cookies / connection pools inside the agent process
- Any in-process tool-call caches (Hindsight client cache, Better Stack emitter buffers, etc.)

### (d) Any in-process caches

- Atomization Composer rendering cache (none currently; future caches MUST be either externalized to Valkey or accept their dies-with-spawn nature)
- Retrieval result caches
- LLM response caches at the agent layer (Valkey semantic cache is a DIFFERENT layer — that survives)

---

## 3. When to write to which store

| What you're persisting | Target store | API |
|---|---|---|
| Final task outcome / decision | Temporal workflow result OR Hindsight Decision wrapper | Activity return OR `mem.wrap.decision.ingest()` |
| Ratified directive / canonical fact | ceo_memory + LAW XV five-store rule | `three_store_save.py` |
| Code change / merge | Git via PR | `git commit` + `gh pr create` |
| Recurring pattern (lessons learned) | Hindsight Pattern/Observation wrapper | `mem.wrap.observation.ingest()` |
| Anti-pattern (what NOT to do) | Hindsight AntiPattern wrapper | `mem.wrap.antipattern.ingest()` |
| Atomized skill knowledge | Hindsight atom store | atomizer pipeline (PR #1185 + #1189) |
| In-flight task graph state | Temporal workflow | activities + signals |
| Rate-limit counters | Valkey `rl:` namespace | `src/dispatcher/valkey_pool.py` |
| Idempotency claims (dispatcher dedup) | Valkey `idem:` namespace | `src/dispatcher/idempotency.py` (PR #1204) |
| Per-tenant budget caps | Postgres `keiracom_tenant_budgets` | `TenantBudgetPolicy.from_db()` (PR #1173) |
| Paused-task durable wait | Postgres `paused_tasks` | `PausedTasksStore` (PR #1194) |
| Cache layer (semantic) | Valkey via `ValkeyClient` | `ValkeyClient.canonical_cache_key()` (PR #1173) |

**Default if unsure:** if it should outlive THIS spawn — pick the store from the table above and use its documented API. Never write to a Hindsight wrapper that doesn't match the content shape (per boundary matrix v1 policy-vs-memory test).

---

## 4. Anti-patterns — DO NOT

1. **Don't store conversation history across spawns.** The Claude conversation is dies-with-spawn by design. If you find yourself wanting to "remember what we talked about" across a respawn, you're violating the bounded-spawn principle. Extract the decision / outcome / lesson into Hindsight via the right wrapper.

2. **Don't trust the agent's mental state across spawns.** Agents don't have a mental state across spawn boundaries. Every fresh spawn re-reads CLAUDE.md + IDENTITY.md + session-start hooks; only on-disk state survives. If an agent's behavior depends on "remembering" what it just did, it will fail on the next respawn.

3. **Don't cache in-process and assume durability.** Module-level dicts, instance-state, lru_cache decorators — all die at spawn. If you need a cross-spawn cache: Valkey for ms-latency caches, Postgres for durable, Hindsight for semantic. Never agent-process memory.

4. **Don't write to ceo_memory for tenant-specific content.** Per boundary matrix v1 policy-vs-memory test: "would this content read the same way for ANY tenant?" Yes → policy → ceo_memory. No (tenant-specific) → Hindsight `mem.wrap.*`. Mixing the two is a hard-flag violation (CI guard `check_no_governance_policy_in_hindsight.sh` exists for the other direction).

5. **Don't bypass MCP for tool access.** Composio/Slack/etc tool calls go through MCP layer. Direct SDK imports outside MCP route around the per-tenant allowed-set + violate the boundary matrix v1 layer ownership contract.

6. **Don't assume Composer output is durable or re-readable.** ComposedOutput.text is user-facing prose — render-then-discard. It does NOT enter agent reasoning input (atomization architecture v1 hard constraint #1; PR #1198 CI guard enforces import isolation). If something needs to be re-read by an agent, persist the atom IDs / source atoms, not the composed prose.

7. **Don't rely on tmux pane state.** Per Dave directive 2026-05-27 cutover gate, tmux retired; ephemeral agent system replaces it. Any code reading from tmux pane stdout / pane history is going to break post-cutover.

8. **Don't write durable state via the keepalive script.** The keepalive is process supervision only. It does NOT carry state. Per PR #1201, even the `--preserve-context` override is for Claude-session continuity ONLY (resumed conversation) — not arbitrary state persistence.

---

## 5. Mapping to Cutover Readiness Gate

This document is the concrete reference for `STATE_SEPARATION` of the Cutover Readiness Gate (verbatim restated 2026-05-27):

| Gate criterion | Where in this doc |
|---|---|
| Durable: Temporal + Postgres | §1(a) + §1(c) + §3 row "Final task outcome" |
| Knowledge: atomized pgvector | §1(b) + §1(e) + §3 row "Atomized skill knowledge" |
| Config: versioned (ceo_memory + boundary matrix v1) | §1(c) + §1(d) |
| Ephemeral: dies-with-spawn | §2 (all 4 rows) + §4 anti-patterns 1-3 |
| Cold archive: recall-API-only | §1(b) (Hindsight semantic memory is the recall-only path — atomization hard constraint #5 from PR #1185) |

The CONCUR-GATE RULE applies: every deliberation that touches state-persistence design MUST open with "does this satisfy STATE_SEPARATION?" Gate-violating proposals are REJECTED at the deliberation tier.

---

## 6. Related PRs (the implementation footprint)

| PR | Domain | What it locks |
|---|---|---|
| PR #1134 | Hindsight wrappers (Atlas) | `mem.wrap.*` ingest pipeline |
| PR #1140 | Ephemeral agent system scoping (Aiden) | `paused_tasks` semantics + dispatcher protocol |
| PR #1156 / #1165 | A7 cache architecture (Orion) | Valkey ValkeyClient + tenant-prefix guard |
| PR #1169 | Boundary matrix v1 (Atlas) | The 8-layer ownership + policy-vs-memory test |
| PR #1173 | A7 cache build (Orion) | Cache layer + budget policy + tenant prefix |
| PR #1184 | Spawn-with-context composer (Nova) | Part A/B/C/D/E + resume-context branch |
| PR #1185 / #1189 / #1191 | Atomization pilot (Orion) | Atom schema + retriever + composer + metering |
| PR #1194 | paused_tasks accessor (Orion) | Durable wait state for decision-response handshake |
| PR #1198 | Composer-isolation CI guard (Orion) | Composer output never reaches agent reasoning input |
| PR #1199 / #1200 | Auto-claim race + sweep (Nova) | Orchestrator dispatcher loop fixes |
| PR #1201 | Keepalive bounded-spawn (Orion) | Fresh-context default + --preserve-context override |
| PR #1203 | Budget ceiling gate (Orion) | Daily fleet budget + Dave bypass |
| PR #1204 | Idempotency gate (Orion) | Webhook retry dedup |

---

## 7. Open questions / future work

1. **Atomization vocabulary finalization.** Schema.py vocabularies are PLACEHOLDER pending Elliot's 48-hour design report (B1 dispatch blocker). Once finalized, atom store is fully load-bearing for "Atomized skill knowledge" row.
2. **Cold archive Postgres on Vultr.** Currently `state='cold_archive'` flag in `keiracom_atoms`; physical move to separate Postgres host is a separate infra dispatch.
3. **MCP tool call audit log durability.** Not yet captured here — falls under `Hindsight Observation wrapper` row but the wire-up KEI is open.
4. **Whiteboard / inter-agent ephemeral state.** Currently undefined per V1 — placeholder for V2 deliberation.

These are flagged for Phase 2 deliberation, not load-bearing for the V1 cutover gate.

---

**Authoritative trace:** Dave directive 2026-05-27 Cutover Readiness Gate; restated verbatim 2026-05-27 (orion outbox `orion-cutover-gate-verbatim-restate-resumed-1779851819.json`); this doc is the engineer-facing reference for the STATE_SEPARATION section.
