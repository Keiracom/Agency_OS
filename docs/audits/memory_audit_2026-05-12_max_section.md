# Memory Audit 2026-05-12 — MAX section (Drevon-port audit-trail tables)

**Owner:** max (CTO)
**Scope:** 5 tables in `public` schema — Drevon-port audit/replay store (PR-A, PR #715/#718).
**Compiled:** 2026-05-12, queries against Supabase project `jatzvazlbusedwsnqxzr`.
**Status:** Inventory only, no redesign. Append-only contribution for Elliot synthesis.

---

## Inventory table

| Table | Purpose | Authority | Rows (live) | Total size | Freshness (latest write UTC) | Churn (live/dead) | Writers | Readers | Last-access proxy (idx_scan / seq_scan) |
|---|---|---|---|---|---|---|---|---|---|
| `public.sessions` | One row per Claude Code agent session (callsign, session_uuid, working_dir, tmux_session, started_at, ended_at, status) | **SSOT** — canonical resumption state | 137 | 144 kB | 2026-05-12 03:15:57 | 157/17 | `.claude/hooks/session_store_posttooluse.sh` (open via `record_session_start`); `.claude/hooks/session_store_stop.sh` (close via `record_session_end`); `src/session_resumption/watchdog.py::clear_stuck_sessions` (mark stuck) | `src/session_resumption/resolver.py::resolve_session_uuid`; `src/session_resumption/watchdog.py::clear_stuck_sessions` | 260 / 69 (healthy index use) |
| `public.turns` | One row per assistant turn (user msg → tool calls → response). Links `session_id`, tracks turn_index, started_at/completed_at, token + AUD cost rollup | **SSOT** — canonical turn ledger | 125 | 128 kB | 2026-05-12 03:15:57 | 145/3 | `.claude/hooks/session_store_posttooluse.sh` (open via `record_turn_start`, close via `record_turn_complete`); `.claude/hooks/session_store_stop.sh` (flush trailing turn) | `src/skill_gen/extractor.py::_fetch_turns` (compress window) | 1168 / 695 (37% seq-scan ratio — see Surprise #4) |
| `public.turn_logs` | One row per tool call (tool_name, tool_args_json, tool_result_summary, exit_status, duration_ms). Links `turn_id`. Replay-on-claim scans this | **SSOT** — canonical tool-call ledger | 1663 | 1688 kB | 2026-05-12 03:17:18 | 1677/0 | `.claude/hooks/session_store_posttooluse.sh` (every PostToolUse via `record_tool_call`) | `src/replay/claim_verifier.py::_fetch_turn_logs` (LAW XV gate — completion-claim verification); `src/skill_gen/extractor.py::_fetch_turn_logs` (skill synthesis window) | 338 / 30 (healthy) |
| `public.turn_files` | One row per file operation inside a tool call (file_path, operation, bytes_read/written, content_hash, lines_added/removed). Links `turn_log_id` | **DERIVED** — denormalised file-op view of what's also in `turn_logs.tool_args_json` (separated for query efficiency on file paths) | 321 | 248 kB | 2026-05-12 03:17:19 | 318/0 | `.claude/hooks/session_store_posttooluse.sh` → `record_tool_call(files=[...])` (only when caller passes `files` list — currently always empty per recorder.py L188-201) | `src/skill_gen/extractor.py::_fetch_turn_files` (file-touch chronology in compression) | 0 / 8 (**ZERO idx_scan — see Surprise #2**) |
| `public.messages` | Intended: one row per user/assistant message (role, message_index, content_hash/text/bytes). Schema + writer function exist | **ORPHAN** — schema + writer defined, no production hook ever calls `record_message`. Has a live READER that gets zero results every time | **0** | 32 kB | (never written) | 0/0 | **NONE in production.** `src/session_store/recorder.py::record_message` exists; exported from `__init__.py`; not invoked by any hook under `.claude/hooks/` | `src/skill_gen/extractor.py::_fetch_user_messages` (broken — see Surprise #1) | 0 / 7 (no rows to scan) |

---

## Surprises / drift flags

### Surprise #1 — `messages` table is an ORPHAN with a live reader (REAL BUG)
- **Writer:** `src/session_store/recorder.py::record_message` is fully implemented and exported, but **no hook under `.claude/hooks/`** calls it. `session_store_posttooluse.sh` records `turn_logs` rows; `session_store_stop.sh` closes sessions/turns. Neither writes to `messages`.
- **Reader:** `src/skill_gen/extractor.py::_fetch_user_messages` (line 76-88) actively queries `messages` for `role=user` within the compression window, joined to `session_id` + `timestamp` range.
- **Impact:** Every skill-gen compression run silently receives `[]` for user messages → the synthesised SKILL.md is missing the actual user-prompt chronology. The bug is invisible because `_safe_post`/`sb_get` swallow zero-row responses without warning.
- **Suggested resolution (Phase 2 only):** either wire `record_message` into a `UserPromptSubmit` / pre-LLM hook, OR remove `_fetch_user_messages` from `compress()` and update the SKILL.md template to not assume user-message context. Out of scope for this audit (no redesign).

### Surprise #2 — `turn_files` has ZERO `idx_scan` (potential sleeping bug)
- `pg_stat_user_tables.idx_scan = 0` despite 321 rows and indexes on `turn_log_id` (FK).
- Either: (a) no reader queries `turn_files` with the `turn_log_id` predicate that would hit the index, (b) the table is too small for Postgres to choose the index (cost-based planner prefers seq-scan under ~1000 rows), or (c) reads are happening but only via seq-scan paths.
- `skill_gen/extractor.py::_fetch_turn_files` uses `turn_log_id=in.(...)` which *should* hit the FK index. Worth a Phase 2 EXPLAIN.
- **Currently harmless** at 321 rows. Bookmark for when row count crosses ~10k.

### Surprise #3 — All 4 active tables have identical write origin timestamp
- `sessions`, `turns`, `turn_logs`, `turn_files` all earliest at 2026-05-11 23:24:13–14 UTC.
- Confirms PR-A go-live ~3.5 hours before this audit. **No retroactive backfill** — by design per PR-A spec. Anything older than 2026-05-11 23:24 is permanently invisible to replay-on-claim, skill-gen, and resumption.
- Implication for Phase 2: don't assume long history is available for skill compression or claim verification.

### Surprise #4 — `turns` has 37% seq-scan ratio
- `turns.seq_scan = 695`, `idx_scan = 1168` → 37% of reads are full-table scans across 125 rows.
- At this scale, planner cost-difference is small enough that seq-scan is competitive. But the ratio is much higher than `turn_logs` (8%) or `sessions` (21%), suggesting at least one query pattern doesn't match the existing index set.
- Likely culprit: `_fetch_turns` uses `or=(completed_at.is.null,completed_at.lte.{end_ts})` (extractor.py L53) — Postgres can't usually push an OR-with-IS-NULL down to a btree index. Worth Phase 2 evaluation.

### Surprise #5 — `sessions.session_uuid` clean-close bug ties to Stream 3 (Orion's PR-C fix)
- This is the bug Dave caught in PR #725 (already merged). Stop hook sets `ended_at` + watchdog clears `session_uuid` → resolver finds no resumable UUID → fresh start. Confirmed during tonight's restarts.
- The `sessions` table itself is fine (SSOT); the schema supports the fix Orion is building (add `status='closed_clean'` + resolver query change).
- **Not new info for the audit — surfaced for synthesis cross-link.**

### Surprise #6 — `extra` jsonb column on `sessions` is undocumented
- `sessions.extra jsonb DEFAULT {}` exists in schema and is written as `extra or {}` by recorder (line 73). No reader uses it. No producer puts anything in it.
- Phase 2 candidate for either: removal (truly unused) or repurpose (per-session feature flags, debug breadcrumbs).

---

## Methodology notes

- **Freshness:** `MAX(started_at)` for sessions/turns/turn_logs; `MAX(timestamp)` for turn_files/messages. Soft-deleted rows excluded (`deleted_at IS NULL`). Autovacuum timestamps reported separately in churn column proxy but not used as freshness.
- **Last-access proxy:** `pg_stat_user_tables.idx_scan + seq_scan` — Supabase managed Postgres does not expose query log. This is a read-traffic proxy, not a "last SELECT" timestamp.
- **Writers/readers:** repo grep over `src/`, `scripts/`, `skills/`, `.claude/hooks/`. Test files excluded. Module-level imports (`from src.session_store import ...`) are noted only when a call site uses them.
- **Authority taxonomy** (per CONCUR @aiden / @elliot):
  - **SSOT** — canonical source of truth, no peer table competes
  - **DERIVED** — exists as a denormalisation/projection of another table for query efficiency
  - **ARCHIVE** — historical/snapshot, not live
  - **DEPRECATED** — explicitly slated for removal
  - **ORPHAN** — schema exists but no production write path

---

## Verbatim verification (Rule 6 — SAVE-CLAIM-REQUIRES-PROOF)

Queries executed against `jatzvazlbusedwsnqxzr` via `mcp__supabase__execute_sql`. Row-count + freshness query:
```
sessions    rows=137  latest=2026-05-12 03:15:57.316453+00  callsigns=7
messages    rows=0    latest=null
turns       rows=125  latest=2026-05-12 03:15:57.679167+00
turn_logs   rows=1663 latest=2026-05-12 03:17:18.640303+00
turn_files  rows=321  latest=2026-05-12 03:17:19.497045+00
```
Per-table pg_stat + size queries logged in audit conversation; raw output available on request.

— max
