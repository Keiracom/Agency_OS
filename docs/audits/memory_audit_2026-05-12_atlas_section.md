# Atlas Section — Mem0 Integration Audit (2026-05-12)

**Stream 1 of 4 (mem0 contribution)** · **Owner: Atlas** · Mem0 cloud SDK + adapter + 4 call-site files
**Methodology**: per Elliot dispatch — grep call-sites, verify env, inspect JSONL usage log, query mem0 cloud directly via SDK to enumerate live contents per callsign, cross-reference with `ceo:mem0_decision_2026-05-01` and Supabase agent_memories.

## Inventory Table

| # | Component | Authority | Status | Last write | Last read | Live contents | Activity |
|---|---|---|---|---|---|---|---|
| 1 | mem0 cloud store (api.mem0.ai) | Graph layer over agent_memories | INACTIVE | 2026-04-30T22:07:25-07:00 (~12d) | 2026-05-02T09:53:36+00:00 (~10d, prod) | 82 memories, all under `system` callsign | 0 production reads since 2026-05-02 |
| 2 | `src/governance/mem0_adapter.py` (189 lines) | adapter SDK wrapper | WIRED | — | — | exports `Mem0Adapter`, `get_monthly_usage` | importable; init succeeds w/ env key |
| 3 | `migrations/mem0_backfill.py` | one-shot backfill script | RAN ONCE | 2026-05-01 (50 adds) | n/a | populated 82 cloud memories | no re-run since |
| 4 | `src/memory/store.py` L207-220 | dual-write site | GATED OFF | n/a | n/a | guarded by `MEM0_INTEGRATION_ENABLED=true` | env flag UNSET → never fires |
| 5 | `src/telegram_bot/memory_listener.py` L595-649 (`recall_via_mem0`) | hybrid recall path | WIRED, IDLE | n/a | last call 2026-05-02 | callable, returns [] from mem0 leg (callsign mismatch) | 0 reads in 10 days |
| 6 | `src/coo_bot/memory_retriever.py` L94-106 | COO context loader → mem0 | WIRED, ORPHAN | n/a | n/a | calls `recall_via_mem0` when `MEMORY_RECALL_BACKEND ∈ {mem0,hybrid}` | consumer service inactive |
| 7 | `src/telegram_bot/recall_handler.py` (`/recall` TG cmd) | TG slash command | WIRED to Supabase only | n/a | n/a | uses `src.memory.recall.recall()` (pure Supabase, NOT mem0) | mem0 path bypassed by design |
| 8 | `logs/mem0-usage.jsonl` (5421 bytes) | cap-tracking log | FROZEN | 2026-05-02T09:53:36+00:00 | n/a | 60 entries (50 add + 10 search) | nothing since 2026-05-02 |
| 9 | `agency-os-coo.service` (would consume the path) | systemd unit | INACTIVE + DISABLED | n/a | n/a | n/a | confirmed via `systemctl --user is-active` |

## Per-Component Detail

### 1. mem0 cloud store — INACTIVE
- **Purpose**: cross-session relationship-aware recall on top of Supabase. Per `ceo:mem0_decision_2026-05-01`: "Mem0 is graph layer ON TOP of agent_memories. Supabase remains SSOT. Mem0 adds cross-session recall + graph relationships."
- **API**: `https://api.mem0.ai/v3/memories/` — SDK `mem0ai>=2.0.0,<3.0.0` (per `requirements*.txt`).
- **Empirical contents** (probed live via `Mem0Adapter._client.get_all(filters={'user_id':<cs>})`):

  | callsign | memories |
  |---|---|
  | system | 82 |
  | aiden | 0 |
  | elliot | 0 |
  | max | 0 |
  | atlas | 0 |
  | orion | 0 |
  | **total** | **82** |

  All 82 created 2026-04-30T22:03:47 → 22:07:25 (-07:00). source_type breakdown: 62 `verified_fact` + 20 `pattern`.
- **Surprise**: backfill wrote everything under `user_id="system"`, but recall code (`memory_listener.py:614` → `Mem0Adapter.search(callsign=callsign)`) filters by per-agent callsign. **Every production search returns 0 results by construction.**

### 2. `src/governance/mem0_adapter.py` — WIRED
- 189 LOC, free-tier caps (10k add / 1k search / month), JSONL usage logging at `/home/elliotbot/clawd/logs/mem0-usage.jsonl`, monthly rollup via `get_monthly_usage()`.
- Public surface: `Mem0Adapter.add | search | delete | update`.
- Init requires `MEM0_API_KEY` (set in env: `m0-nlcYiL5jC4l2LBfjEJooU0l9lMbGHOXRsxQXTtdN`). SDK 2.x filter-style enforced (`filters={'user_id': cs}`).
- Tests: `tests/governance/test_mem0_adapter.py` — hermetic unit tests pass; **no integration test against live cloud**.

### 3. `migrations/mem0_backfill.py` — RAN ONCE 2026-05-01
- One-shot backfill from `public.agent_memories` → mem0 cloud. Default dry-run; `--apply` actually writes.
- Last execution wrote 50 adds (per JSONL log, all 2026-05-01, all `callsign=system`).
- **Bug confirmed**: backfill writes everything under `callsign="system"` regardless of source row's actual callsign. Recall searches under per-agent callsign → 0 hits. (Source row's `callsign` column not passed through to `adapter.add(callsign=…)`.)

### 4. `src/memory/store.py:207-220` — GATED OFF
- Dual-write hook: after Supabase insert succeeds, mirrors content to mem0 via `Mem0Adapter().add()`.
- **Guard**: `if os.environ.get("MEM0_INTEGRATION_ENABLED", "").lower() == "true"`.
- **Env state**: `MEM0_INTEGRATION_ENABLED` is **not set** in `/home/elliotbot/.config/agency-os/.env` (verified via grep — no line matches).
- **Consequence**: every Supabase memory write since the flag was first introduced has been single-write (Supabase only). Mem0 cloud receives zero ongoing data.

### 5. `src/telegram_bot/memory_listener.py:595-649` (`recall_via_mem0`) — WIRED, IDLE
- Hybrid path: queries mem0 + Supabase, dedupes by content prefix, sorts by similarity, returns top-K.
- **Gated by**: `MEMORY_RECALL_BACKEND` env (`mem0|supabase|hybrid`). Env is set to `hybrid` (verified line 185 in `.env`).
- **Effective behaviour**: mem0 leg returns [] (callsign mismatch — see #1 surprise). Supabase leg returns full results. So hybrid acts like Supabase-only in production, with the added latency of a mem0 round-trip.
- Last invocation: pre-2026-05-02 (per JSONL — only my audit-time probes appear after).

### 6. `src/coo_bot/memory_retriever.py:94-106` — WIRED, ORPHAN
- COO bot's context assembler: routes through `recall_via_mem0` when `MEMORY_RECALL_BACKEND ∈ {mem0,hybrid}`, else direct Supabase ILIKE.
- **Consumer service**: `agency-os-coo.service` — verified `inactive` + `disabled`. The only production caller (`dm_handler.py:205`) is in the COO bot module.
- Read path exists, but no live process exercises it.

### 7. `src/telegram_bot/recall_handler.py` — bypasses mem0
- `/recall` TG slash command uses `src.memory.recall.recall()` — pure Supabase, no mem0 branch.
- File docstring explicitly says: "Hybrid Mem0 retrieval is M3 territory and lives in `src.telegram_bot.memory_listener.recall_via_mem0`; this handler uses the canonical Supabase-backed recall() for now."
- **Status**: by design, this handler does not exercise mem0.

### 8. JSONL usage log — FROZEN
- 60 entries total, by op: 50 add (all `system`) + 10 search (9 `aiden` + 1 `elliot`).
- Date range: 2026-05-01T05:03:44 → 2026-05-02T09:53:36. **Zero production activity for ~10 days** (only my audit-time probes appear after).
- Monthly cap usage May 2026: 50/10,000 adds (0.5%), 10/1,000 searches (1.0%). Cost: free-tier.

### 9. agency-os-coo.service — INACTIVE
- `systemctl --user is-active agency-os-coo.service` → `inactive`
- `systemctl --user is-enabled agency-os-coo.service` → `disabled`
- The COO bot is the primary production consumer of `assemble_context` (which calls `get_relevant_memories` → `recall_via_mem0`). With the bot offline, mem0's recall path has no live caller.

## Cross-Reference vs Supabase agent_memories

| Capability | Mem0 cloud | Supabase `agent_memories` (per Aiden's section) |
|---|---|---|
| Rows | 82 (all `system`) | 6,311 (callsign-scoped) |
| Size | n/a (managed) | 31 MB |
| Embeddings | yes (managed) | yes (`embedding` column, `text-embedding-3-small`, `store.py:55`) |
| Graph / supersession | yes (mem0's pitch) | yes (`supersedes_id` FK + `match_agent_memories` RPC, `store.py:66-115`) |
| Per-callsign isolation | yes (via `user_id` filter) | yes (`callsign` column) |
| State machine (tentative/confirmed/superseded) | no | yes (`state` column, `memory_listener.py:582` promotion) |
| Production writers | none (gated off + backfill stale) | many (`store.py`, `memory_listener.py`, `coo_bot/*`) |
| Production readers | none (callsign-mismatch deadlock) | many + heavy idx_scan traffic |

Supabase already provides every capability mem0 was meant to add (embeddings, graph via `supersedes_id`, callsign isolation, semantic search via `match_agent_memories` RPC), and is actively used (683k idx_scans per Aiden's stat dump). Mem0's claimed differentiator — graph relationships — is structurally duplicated by `supersedes_id` and the in-flight Phoenix exporter.

## Surprises (flagged for synthesis)

1. **Callsign-mismatch deadlock**: backfill wrote 82 memories under `user_id="system"`; recall searches under per-agent callsign (`aiden`, `elliot`, etc.). Every production search returns `[]` from mem0 by construction. (Verified: live `get_all` returned 0 for every per-agent callsign, 82 for `system`.)
2. **Dual-write gate is off**: `MEM0_INTEGRATION_ENABLED` is not set in `.env`, so `store.py:208-220` never executes. Mem0 cloud receives zero ongoing writes — frozen at 2026-05-01 backfill snapshot.
3. **MEMORY_RECALL_BACKEND=hybrid but effectively Supabase-only**: hybrid path queries both stores, but mem0 leg always returns [] (see #1). Net effect is Supabase-only retrieval with added mem0 round-trip latency in the hybrid code path.
4. **COO bot consumer is inactive + disabled**: `agency-os-coo.service` is the only production caller of `assemble_context` → `recall_via_mem0`. With the bot offline, the mem0 recall path has no live invocation source. (10-day silence in JSONL log confirms.)
5. **No live integration test**: `tests/governance/test_mem0_adapter.py` is fully hermetic (mocks `mem0.MemoryClient`). No CI gate exercises the live cloud API. The callsign-mismatch bug (#1) was therefore undetectable by the existing test suite.
6. **`ceo:mem0_decision_2026-05-01` claims "BUILT + OPERATIONAL (80%)"**: ratified state vs empirical state diverged. ceo_memory says mem0 is "dual-writing, recall active, agent_memories live"; in fact dual-writes are gated off, recall returns 0, and the consumer service is disabled. (Direct contradiction — ceo_memory key needs correction or supersession regardless of disposition outcome.)
7. **`mem0ai==2.x` SDK has v3 endpoint drift**: `client.get_all(user_id=…)` raises `ValueError`; only `filters={'user_id': …}` works. Our adapter handles `add`/`search` per 2.x, but other parts of the SDK still emit 400 Bad Request on `/v3/memories/search/` if filters are empty (verified during audit probes). Latent SDK-version brittleness.
8. **Free-tier viability**: 50 adds + 10 searches used in May = 0.5%/1% of cap. If we revive at 2026's volume of writes to `public.agent_memories` (6,311 rows / ~3 months ≈ 70/day), we'd hit the 10k add cap in ~140 days. Free-tier is *not* a permanent home — revive triggers a paid-tier decision.

## Disposition Recommendation

### RETIRE

**Justification (empirical, not speculative):**

1. **Functional parity**: Supabase `agent_memories` already provides every capability mem0 was meant to add — embeddings (OpenAI), graph (`supersedes_id` + `match_agent_memories` RPC), callsign isolation, state machine. Aiden's section confirms 683k idx_scans on `agent_memories` (active, healthy).
2. **Zero production utility**: 10-day silent JSONL, callsign-mismatch deadlock on all per-agent searches, dual-write gate off, consumer service disabled. The path *exists* but emits zero signal.
3. **ceo_memory drift**: ratified status ("BUILT + OPERATIONAL 80%") contradicts empirical state. Continuing to maintain a "wired but dead" integration creates governance debt with no upside.
4. **Free-tier cliff**: revive forces a paid-tier decision within ~140 days of resumed write volume. Pre-revenue stance (per `feedback_pre_revenue_reality.md`) argues against adding a recurring vendor cost for capability we already have in-house.
5. **Maintenance load**: 4 production files + tests + backfill migration + skill placeholder = real surface area. SDK breaks (2.x→3.x already wobbly per surprise #7) force re-work cost with no offsetting recall gain.

**REVIVE rejected** because it requires: (a) re-backfilling per-callsign (50+ adds against cap), (b) setting `MEM0_INTEGRATION_ENABLED=true` and watching the 70/day write rate, (c) re-enabling `agency-os-coo.service`, (d) adding a live-integration test to catch callsign-mismatch class bugs, (e) accepting eventual paid-tier — all to obtain a recall feature we already get from Supabase RPC.

**REPLACE rejected** because the replacement (Supabase agent_memories) is already in place and serving 683k idx_scan reads. There is no "replace mem0 with X" — we just stop pretending mem0 is in the loop.

### Retirement Plan (Phase 2 dispatch)

1. **Delete code**: `src/governance/mem0_adapter.py`, `migrations/mem0_backfill.py`, `tests/governance/test_mem0_adapter.py`, the `recall_via_mem0` function in `memory_listener.py`, the mem0 branches in `coo_bot/memory_retriever.py` and `src/memory/store.py:207-220`.
2. **Delete env vars**: remove `MEM0_API_KEY`, `MEM0_INTEGRATION_ENABLED`, `MEMORY_RECALL_BACKEND` lines from `/home/elliotbot/.config/agency-os/.env` (and document the retirement in CLAUDE.md governance section).
3. **Update preflight**: drop `check_mem0` from `scripts/preflight_phase1.py:107-130`.
4. **Update ceo_memory**: write new `ceo:mem0_decision_2026-05-12` key with status `RETIRED`, supersede the 2026-05-01 key, link to this audit doc.
5. **Drop mem0 cloud account / rotate API key**: 82 stale "system" memories can stay (no PII risk per content sample — all generic verified_facts about Jina/Brightdata/etc.), but key rotation closes the loop.
6. **Update docs/MANUAL.md** memory architecture section to drop mem0 references.

Out of scope for this audit: deciding whether to do retirement in one PR or staged. Defer to Elliot synthesis.

## Methodology Caveats

- **Live cloud probes were read-only** (`get_all` with per-callsign filter, `search` with limit=3). The 10 search events I logged at 03:53 UTC during this audit slightly inflate the May-2026 search counter (10 → 20). Treat the production-search count as 10, not 20.
- **Grep-based detection misses**: (a) reflection-style imports (none found), (b) MCP-bridge invocations (none — mem0 has no MCP server entry), (c) runtime feature-flag flips since process start. The `MEM0_INTEGRATION_ENABLED` env state at probe time is canonical for *new* processes; long-lived processes may have a different cached state.
- **No way to attribute the 82 "system" memories to a specific run** — JSONL log shows 50 adds on 2026-05-01 but cloud has 82. Either (a) prior pre-JSONL backfill, or (b) write-without-log path. Not material to disposition.
- **SDK 2.x has v3 endpoint drift** (`/v3/memories/search/` requires non-empty filters). If we ever revived, we'd need to pin and CI-gate.

## Status

Section complete. Ready for Elliot synthesis into `docs/audits/memory_audit_2026-05-12.md`. Empirical evidence supports **RETIRE** with the staged plan above; final disposition is Elliot's call.
