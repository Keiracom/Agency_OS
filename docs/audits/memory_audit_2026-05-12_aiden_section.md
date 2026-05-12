# Aiden Section — Supabase Memory Audit (2026-05-12)

**Stream 1 of 4** · **Owner: Aiden** · 9 tables across 3 schemas
**Methodology**: per Aiden Step 0 + Max methodology tweaks + Elliot synthesis attribute set (5-cat authority, n_live_tup/n_dead_tup churn, MAX(created_at|updated_at) freshness, pg_stat seq_scan/idx_scan last-access proxy).

## Inventory Table

| # | Table (schema.name) | Authority | Rows | Size | Freshness (latest write) | Churn (live/dead) | Activity (seq+idx) | Last autovacuum |
|---|---|---|---|---|---|---|---|---|
| 1 | public.ceo_memory | **SSOT** | 575 | 616 kB | 2026-05-12 02:51:20 (hot) | 575 / 67 | 240 / 2041 | — |
| 2 | public.agent_memories | **SSOT** | 6,311 | 31 MB | 2026-05-12 02:51:20 (hot) | 6311 / 4 | 30562 / 683917 | 2026-05-07 |
| 3 | public.governance_events | **SSOT** | 25,617 | 7.3 MB | 2026-05-12 03:22:10 (hot) | 25617 / 11 | 21 / 14996 | 2026-05-11 |
| 4 | public.cis_directive_metrics | **SSOT** | 195 | 176 kB | 2026-05-12 02:45:19 (hot) | 195 / 1 | 65 / 347 | — |
| 5 | keiracom_admin.task_queue | **SSOT** (evo) | 91 | 128 kB | 2026-05-08 21:02:20 (4d) | 91 / 8 | 46 / 36 | 2026-05-08 |
| 6 | elliot_internal.memories | **DEPRECATED** | 1,665 | 30 MB | 2026-05-10 08:58:22 (2d) | 1665 / 237 | 2858 / 1777 | 2026-02-02 |
| 7 | public.ceo_memory_archive | **ORPHAN** | 14 | 64 kB | 2026-05-07 05:01:20 (5d) | 14 / 0 | 1 / 0 | — |
| 8 | public.elliot_knowledge | **ORPHAN** | 659 | 2.6 MB | 2026-02-03 12:27:26 (~3mo stale) | 659 / 63 | 126 / 906 | 2026-01-30 |
| 9 | public.elliot_signoff_queue | **ORPHAN** | 52 | 168 kB | 2026-02-02 01:55:03 (~3mo stale) | 52 / 24 | 26 / 150 | 2026-01-30 |

## Per-Table Detail

### 1. public.ceo_memory — SSOT
- **Purpose**: CEO state singleton — directive counter, system state, blockers (key/value). Every directive completion + session-end writes here.
- **Writers**: `scripts/three_store_save.py`, `scripts/session_end_check.py`, `src/telegram_bot/chat_bot.py`, `src/services/cis_outcome_service.py`, `src/orchestration/flows/cis_learning_flow.py`, `src/engines/scorer.py`, `src/bot_common/enforcer_deterministic.py`, `src/bot_common/session_end_gate.py`.
- **Readers**: same set + LAW XV gate (`session_end_gate.py:103`).
- **Note**: 67 dead tuples / 575 live = 10.4% churn — moderate-write SSOT, vacuum is silent (no last_autovacuum recorded; autoanalyze ran 2026-05-07).

### 2. public.agent_memories — SSOT
- **Purpose**: Per-callsign session memory (replaces elliot_internal.memories). Schema: callsign, source_type, content, state, valid_from.
- **Writers**: `src/memory/store.py`, `src/coo_bot/*.py`, `src/telegram_bot/memory_listener.py`.
- **Readers**: `src/memory/retrieve.py`, `src/coo_bot/memory_retriever.py`, plus session-START SQL per CLAUDE.md.
- **Note**: 683k idx_scans → heavy read traffic, healthy index coverage (idx >> seq).

### 3. public.governance_events — SSOT (audit trail)
- **Purpose**: Append-only governance log — rule fires, enforcer actions, LAW violations.
- **Writers**: `src/governance/gatekeeper.py`, `src/governance/tg_alert.py`, `src/telegram_bot/enforcer_bot.py`, `src/coo_bot/*.py`.
- **Readers**: `scripts/phoenix_export_loop.py` (export), `src/governance/*` (governance trace lookups).
- **Note**: 25k rows, hottest table (latest write 03:22:10 = 3 min ago at audit time). Append-only design — n_dead_tup=11 only.

### 4. public.cis_directive_metrics — SSOT
- **Purpose**: One row per directive — `save_completed` boolean closes LAW XV four-store loop.
- **Writers**: `scripts/three_store_save.py` (only writer; plain INSERT, no ON CONFLICT — re-runs duplicate rows).
- **Readers**: `src/bot_common/session_end_gate.py`, `scripts/session_end_check.py`, `scripts/seed_claude_md_facts.py`.

### 5. keiracom_admin.task_queue — SSOT (evo task dispatch)
- **Purpose**: Cross-bot task queue for evo orchestration.
- **Writers/Readers**: `src/evo/agent_invoker.py`, `src/evo/consumer_helpers.py`.

### 6. elliot_internal.memories — DEPRECATED
- **Purpose**: Original session memory (pre public.agent_memories migration).
- **Writers (src/)**: none. Only `scripts/migrate_memories.py`, `scripts/memory_consolidation.py`, `scripts/memory_rem_backfill.py`, `scripts/update_peer.py`, `scripts/seed_claude_md_facts.py`.
- **Readers**: same scripts + ad-hoc psql (per global CLAUDE.md session-START block — note: GLOBAL CLAUDE.md still says read from elliot_internal.memories, while per-worktree CLAUDE.md says read from public.agent_memories — **drift**).
- **Replacement**: public.agent_memories (callsign-scoped, multi-tenant).
- **State**: kept warm by ad-hoc reads (seq_scan=2858) but no current src/ writer — frozen at migration boundary.

### 7. public.ceo_memory_archive — ORPHAN
- **Purpose**: Was meant as ceo_memory rotation target (cols: key, value, original_updated_at, original_version, archived_at, archive_reason).
- **Writers**: ZERO production references. No DB triggers (verified via information_schema.triggers).
- **Readers**: ZERO production references.
- **State**: 14 historical rows, no current archival process. Likely populated by one-off script that no longer exists.

### 8. public.elliot_knowledge — ORPHAN
- **Purpose**: Scored-knowledge store with embedding + auto-scoring (cols: content, embedding, learned_at, scored, business_score, learning_score, final_score, score_reasoning, action_type).
- **Triggers**: `trg_score_knowledge_insert` + `trg_score_knowledge_update` → `trigger_score_knowledge()` (still attached, would fire if anything wrote).
- **Writers/Readers**: ZERO production references across src/scripts/skills.
- **State**: 659 rows of scored knowledge + 2.6 MB of embeddings, silent since 2026-02-03. Scoring infrastructure still wired at DB level but never invoked.

### 9. public.elliot_signoff_queue — ORPHAN
- **Purpose**: Signoff/approval queue (was likely human-in-the-loop gate).
- **Writers/Readers**: ZERO production references.
- **State**: 52 rows, silent since 2026-02-02.

## Surprises (flagged for synthesis)

1. **3 ORPHAN tables, ~3 MB of dead data**: `ceo_memory_archive` (14 rows), `elliot_knowledge` (659 rows + 2.6 MB embeddings + 2 still-attached triggers), `elliot_signoff_queue` (52 rows). Zero production-code references. Phase 2 candidates for retirement.
2. **GLOBAL vs PER-WORKTREE CLAUDE.md drift on session-START**: global `~/.claude/CLAUDE.md` says query `elliot_internal.memories`; per-worktree (Aiden) `.claude/modules/_session_start.md` superseded by `CLAUDE.md` Supabase section says query `public.agent_memories`. Same agents — two different SSOT pointers. (Reconcile in Phase 2.)
3. **elliot_internal.memories is DEPRECATED but warm**: no src/ writers, only migration scripts — yet pg_stat shows 2858 seq_scans + 1777 idx_scans. Implies live ad-hoc reads (psql / global CLAUDE.md startup block). The MIGRATION never finished closing reads.
4. **cis_directive_metrics has no ON CONFLICT clause** in `scripts/three_store_save.py` (L294-321). Re-running three_store_save for the same directive creates duplicate rows. Latent bug if a save is ever replayed (e.g. LAW XV gate-bypass refresh).
5. **Drive mirror (4th store of LAW XV) marked "invoked but unverified"** for directive 10015 — per Elliot flag. `scripts/three_store_save.py` L341-346 captures subprocess exit code but doesn't write it to ceo_memory/cis_directive_metrics. The "completed" status on cis_directive_metrics covers stores 1-3 only.
6. **elliot_knowledge has 2 INSERT/UPDATE triggers still attached** (`trg_score_knowledge_insert`, `trg_score_knowledge_update`). If we revive any writer to this table, scoring will fire silently. Retirement plan should drop triggers first.

## Methodology Caveats

- **No real read-access timestamps available** on Supabase managed Postgres. `pg_stat_user_tables.seq_scan + idx_scan` are cumulative-counter proxies, not last-read timestamps. A table with high seq_scan but stale freshness (e.g. elliot_internal.memories) signals "still read, no longer written" — interpret accordingly.
- **`MAX(created_at|updated_at)` is the freshness ground truth**, not `last_autovacuum`. Two tables (ceo_memory, cis_directive_metrics) have `null` last_autovacuum despite active writes — autovacuum gates on dead-tuple threshold, which low-churn append-tables rarely hit.
- **Grep-based reader/writer detection misses**: (a) ad-hoc psql / Supabase Studio queries, (b) MCP-bridge invocations parameterised at runtime, (c) DB triggers (verified separately above).

## Status

Section complete. Ready for Elliot synthesis into `docs/audits/memory_audit_2026-05-12.md`.
