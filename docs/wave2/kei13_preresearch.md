# KEI-13 Pre-Research — Phase 2 (Memory + Task Graph Services)

Source: Dave's 20-Item Roadmap CEO post 2026-05-11 (Phase 2 items 5–8).

## Item 1 — agentmemory hybrid MCP server

**Ship-status:** NOT STARTED. Grep across `src/`, `skills/`, `.claude/` for `agentmemory-hybrid`, `agent_memory.*hybrid` returns no matches. No MCP server entry for it in `skills/mcp-bridge/scripts/mcp-bridge.js`.

**Reference:** https://github.com/rohitg00/agentmemory — hybrid BM25 + vector retrieval, PostToolUse hook auto-captures, SessionEnd compresses + indexes.

**Implementation outline:**
1. Provision MCP server (Vultr instance per Dave's note). Docker compose from upstream repo.
2. Add `agentmemory` to `mcp-bridge.js` `MCP_SERVERS` map with the right endpoint.
3. PostToolUse hook in `.claude/hooks/` writing observation JSON to the MCP server. Mirror pattern used by `session_store_posttooluse.sh`.
4. SessionStart hook to query BM25 + vector for relevant context, inject as system prompt prefix.
5. Decision pending: does `agentmemory` REPLACE or COMPLEMENT current Supabase `agent_memories` table? Roadmap says "Replaces flat 56-pin system" — implies replacement of MEMORY.md not Supabase. Aiden's wrapper for Cognee already overlaps this area — coordinate to avoid duplicate storage.

## Item 2 — Beads-git dependency task graph

**Ship-status:** **DONE.** PR #771 ([ELLIOT] feat(orchestration): Linear + Beads wiring (Parts A + B)) merged 2026-05-12T06:56:23Z.

```
$ gh pr view 771 --json title,state,mergedAt
{"mergedAt":"2026-05-12T06:56:23Z","state":"MERGED",
 "title":"[ELLIOT] feat(orchestration): Linear + Beads wiring (Parts A + B of directive)"}
```

`bd` CLI is live at `/home/elliotbot/.local/bin/bd`; `bd ready --json` returns claimable issues; Linear ↔ Beads sync runs via the wiring in PR #771. Close on Wave 2 dispatch confirmation.

## Item 3 — Pensyve entity-aware memory

**Ship-status:** DROPPED per Dave. The dispatch confirms — Cognee covers entity-aware retrieval (per-entity recall via the knowledge graph; see `docs/cognee/internals.md` Q1 — `extract_graph_and_summarize` produces entity nodes). Pensyve would duplicate Cognee's entity layer. Mark "won't-fix — superseded by Cognee" and close.

## Item 4 — Per-agent token + cost tracking (Supabase)

**Ship-status:** PARTIAL. Existing table + service does **not** track per-callsign.

```
$ ls supabase/migrations/ | grep sdk_usage
018_sdk_usage_log.sql
20260509_sdk_usage_log_rls_policies.sql
```

`src/models/sdk_usage_log.py` has token, cost (AUD), turns, duration, tool calls, success/failure — but no `callsign` column. `grep -n callsign src/models/sdk_usage_log.py` returns nothing. Per-AGENT (callsign-scoped) breakdown isn't possible against current schema.

**Implementation outline:**
1. Alembic migration: `ALTER TABLE sdk_usage_log ADD COLUMN callsign TEXT;` + index on `(callsign, created_at)`.
2. Update `src/services/sdk_usage_service.py::log_sdk_usage` signature to take `callsign: str` and persist it.
3. PostToolUse hook captures the current callsign from `$CALLSIGN` env var (already set per worktree) and forwards to log. Same hook pattern as `session_store_posttooluse.sh`.
4. New `/cost` slash-command + skill that queries `SELECT callsign, SUM(total_cost_aud), SUM(total_tokens) FROM sdk_usage_log WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY callsign`.
5. Reference: `VoltAgent/awesome-openclaw-skills` (`api-credits-lite`, `cost-optimizer`) — patterns to mirror but internal implementation against our Supabase.

**Effort:** 1 migration + 1 service patch + 1 hook + 1 skill ≈ 80–120 LOC + 1 PR.

## Summary

| Item | Status | Action |
|---|---|---|
| agentmemory hybrid MCP | NOT STARTED | Provision + 3 hooks + decide overlap with Cognee |
| Beads-git | **DONE** (PR #771) | Close on dispatch |
| Pensyve | DROPPED | Mark won't-fix |
| Per-agent token cost | PARTIAL | Migration + service patch + hook + /cost skill |

KEI-13 close-out path: 1 build (agentmemory) + 1 patch (token cost) + 2 admin closures (Beads done, Pensyve dropped).
