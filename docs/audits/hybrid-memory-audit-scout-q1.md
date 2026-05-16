# Hybrid Memory Audit — Scout slice (Q1: undocumented data surfaces)

**Author:** scout
**Date:** 2026-05-16
**Mandate:** CEO Research — Hybrid memory data sources audit, Q1 partial (worktree + ~/.claude/ surfaces; Vultr filesystem belongs to Atlas).
**Status:** RESEARCH ONLY — no data moves. Awaiting team CONCUR + Dave plan per Elliot dispatch (max-3-rounds cap).

## Plain English

Dave: outside the **3 known inputs** (Agency_OS repo + `ceo_memory` 604 rows + `agent_memories` 7320 rows), I found **~600MB of agent-written content** living in places nobody indexed yet. Most of it is per-callsign session transcripts (`~/.claude/projects/.../*.jsonl`) — the actual conversation logs of every Claude Code session ever run. The rest is doctrinal docs (CLAUDE/IDENTITY/skills/governance), per-agent inbox/outbox message archives, and runtime/telemetry logs.

The transcript corpus is the **highest-value, highest-cost** decision: it contains every reasoning chain, every successful + failed approach, every Step 0 RESTATE, every PR description we ever wrote — but at 595MB raw it would dominate token cost. **My recommendation is to NOT bulk-ingest transcripts**; instead extract only the structured signal (discoveries, decisions, governance ratifications) via a one-time pass.

## Findings — categorised

### Category A — Agent conversational history (UNDOCUMENTED, ~595MB)

The largest unindexed corpus. Per-worktree JSONL transcripts of every Claude Code session:

| Path | Size | jsonl files |
|------|-----:|------------:|
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/` | 224 MB | 32 |
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS-aiden/` | 129 MB | 21 |
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS-max/` | 117 MB | 10 |
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS-atlas/` | 38 MB | 9 |
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS-orion/` | 28 MB | 5 |
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS-scout/` | 14 MB | 7 |
| `~/.claude/history.jsonl` | 8.2 MB | 1 |

**Total: ~558 MB raw.** Each `.jsonl` is one session — full request/response, tool calls, tool results.

### Category B — Per-callsign operational state (UNDOCUMENTED, ~1.5 MB)

Inbox/outbox archives — every dispatch + every status post each agent sent:

| Path | files | size |
|------|------:|-----:|
| `/tmp/telegram-relay-scout/outbox/` | 153 | 624K |
| `/tmp/telegram-relay-scout/processed/` | 82 | 332K |
| `/tmp/telegram-relay-{aiden,atlas,elliot,max,orion}/` | ? | analogous |
| `~/.claude/capsules/{callsign}_capsule.md` (×6) | 6 | ~9K total |
| `/tmp/{aiden,elliot,max,scout}-pending-concur/` | 72 total | small JSON |
| `/tmp/{callsign}-agent.service` | runtime systemd state | n/a |

Capsules carry anti-amnesia state across compact. Pending-concur files carry in-flight atomic-claim state.

### Category C — Doctrinal source-of-truth (DOCUMENTED partially)

Already known to live in repo, but worth listing for completeness — these are **ratified governance, not agent discovery**, so weight differently than Category A/D:

| Path | files | size |
|------|------:|-----:|
| `CLAUDE.md` (worktree + `~/.claude/CLAUDE.md` global) | 2 | ~30K |
| `IDENTITY.md` (per worktree) | 6 | ~12K |
| `.claude/modules/` (symlink → `~/.config/agency-os/modules/`) | 15 | doctrinal modules |
| `~/.config/agency-os/hooks/` | 7 hook scripts | enforcement code |
| `docs/governance/` | 7 | 52K |
| `skills/` (40 markdown SKILL files + 12 implementation files) | 52 | 764K |
| `ARCHITECTURE.md`, `HEARTBEAT.md`, `HANDOFF.md` | 3 | small |

### Category D — Research + audit corpus (UNDOCUMENTED for retrieval)

High-signal but never indexed:

| Path | files | size |
|------|------:|-----:|
| `docs/audits/` | 37 | 508K |
| `docs/wave2/` (KEI design specs + audits) | 15 | 204K |
| `docs/clones/` | 3 | 36K |
| `docs/scout/` | 1 | 12K |
| `research/` (worktree-local; varies per callsign) | 51 (scout) | varies |

### Category E — Local task tracker

`bd` / Beads issue corpus:

| Path | rows | size |
|------|-----:|-----:|
| `.beads/issues.jsonl` | 99 | 174K |
| `.beads/interactions.jsonl` | small | 435 bytes |
| `~/.claude/tasks/` (per-session task UUIDs) | 60 files | 244K |

### Category F — Discovery / memory surfaces

Designed-for-retrieval but **mostly empty or pending**:

| Path | state | notes |
|------|-------|-------|
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl` | **DOES NOT EXIST YET** | KEI-50 module documents the path; KEI-46/47 backfill pending |
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/MEMORY.md` | 1 | index file |
| same dir, `feedback_*.md` | **71 files** | feedback corpus (most populated) |
| same dir, `reference_*.md` | 7 | API/system reference pins |
| same dir, `project_*.md` | 2 | project-state pins |
| same dir, `user_*.md` | 1 | role swap pin |
| same dir, `research_*.md` + `api_*.md` | 2 | misc |

Per-clone worktrees (`...-aiden`, `...-atlas`, etc.) do NOT have a sibling `memory/` dir — only the main worktree's `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/` is populated.

### Category G — Runtime telemetry + logs (LOW-VALUE for memory; HIGH for ops audit)

| Path | size | content |
|------|-----:|---------|
| `/tmp/agency-os-recorder/mcp.log` | 2.2 MB | every MCP call this session |
| `/tmp/agency-os-recorder/recorder.log` | 204K | hook invocations |
| `/tmp/agency-os-session-store/*.log` | small | hook-side session events |
| `~/.claude/telemetry/` | 64K | Claude Code Sentry-equivalent |
| `~/.claude/sessions/` | 28K | session metadata |
| `~/.claude/stats-cache.json` | 16K | usage stats |
| `/tmp/elliot-polling-loop-throttle-state.json` | small | runtime throttle |
| `/tmp/cognee*.log`, `/tmp/weaviate*.log` | varies | recent vendor smoke output |

### Category H — Config + secrets (NEVER for Weaviate)

| Path | notes |
|------|-------|
| `~/.config/agency-os/.env` | secrets — NEVER index |
| `~/.claude/settings.json`, `settings.local.json` | hooks/permissions |
| `~/.claude/mcp-needs-auth-cache.json` | OAuth pending state |
| `~/.claude/policy-limits.json` | rate limits |
| `~/.config/agency-os/oauth_state_personal.json`, `youtube_tokens.json` | OAuth state |

## Cross-cutting observations

1. **Per-callsign session transcripts are the bulk-volume question.** ~558 MB raw across 6 worktrees. If we index without structuring first, retrieval gets dominated by reasoning chatter, not signal.
2. **`discovery_log.jsonl` is the designed signal-extraction layer but is currently empty on this worktree** (file does not exist; KEI-50 + KEI-46/47 backfill is the gate). Cross-reference Orion's Q3 to understand staleness filtering.
3. **The 71 `feedback_*.md` files in `~/.claude/projects/.../memory/`** are arguably already the "extracted signal" from past transcripts — written by past Claude sessions as auto-memory. **This is the highest-density agent-signal corpus we have today** and is small enough (368K total) to ingest in one pass.
4. **Outbox/processed archives** (~1.5 MB across 6 callsigns) are the **factual** record of who said what to whom. Higher signal than transcripts; lower than discoveries.
5. **`docs/audits/`** is the human-readable retrospective layer — 37 files of "what we found when we looked". Ingesting these gives a code-agent the project's institutional memory of past investigations.
6. **`docs/wave2/` KEI design specs** are ratified design decisions. Higher-signal than transcripts (one doc = one decided architecture vs. 100 turns of arguing).

## Recommendations (proposed, not approved)

**HIGH signal-to-noise for Weaviate (small + structured):**
- `~/.claude/projects/.../memory/` feedback + reference + project + user files (368K total) — already structured, already filtered by past Claude sessions.
- `docs/wave2/` KEI research/design specs (204K) — ratified architectural decisions.
- `docs/audits/` historical audits (508K) — institutional memory of investigations.
- `docs/governance/` consolidated rules (52K) — ratified governance.
- `skills/*.md` (40 files, ~400K of markdown) — canonical interface contracts.
- `.beads/issues.jsonl` (99 entries) — task graph history with status.

**MEDIUM signal — needs Orion's Q3 staleness filter first:**
- `~/.claude/capsules/*.md` (×6 × 1.5K) — current state per callsign. Likely valuable.
- `/tmp/telegram-relay-*/outbox/*.json` — agent self-narration. Risk of noise.
- `/tmp/telegram-relay-*/processed/*.json` — directives received. Useful for "what was Dave told to do" reconstruction.

**LOW signal-to-noise (DO NOT bulk-ingest):**
- `~/.claude/projects/*/` session jsonl transcripts (558 MB) — defer to a one-time extraction pass that pulls only discoveries + decisions + governance ratifications. Bulk-ingesting raw transcripts will swamp retrieval.
- `/tmp/agency-os-recorder/mcp.log` (2.2 MB) — every MCP call. Ops-audit value, not memory value.
- `~/.claude/telemetry/`, `~/.claude/sessions/`, `~/.claude/stats-cache.json` — operational state, not knowledge.

**NEVER ingest:**
- `~/.config/agency-os/.env` — secrets.
- `~/.claude/settings*.json` — config.
- `~/.claude/mcp-needs-auth-cache.json`, OAuth state files.
- `policy-limits.json`.

## Open questions for the team

1. **Discovery_log.jsonl is empty** — is Dave's KEI-50/55 "extract discoveries from transcript pass" the gate that fills it before any Weaviate ingestion run? (Cross-reference with Atlas's Q1 Vultr findings — is the file populated on Vultr but not on local worktrees?)
2. **Per-callsign vs unified retrieval** — should each callsign's memory layer index only its own corpus, or is the team building a unified knowledge graph? (Affects how `~/.claude/projects/-home-elliotbot-clawd-Agency-OS-<callsign>/` transcripts are partitioned.)
3. **Capsules** — these are auto-overwritten by `pre_compact_alert.py`. Indexing a snapshot captures one point in time. Is the index supposed to follow updates, or do we treat capsules as ephemeral?
4. **Recursive growth** — `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/` is 224 MB on this audit run. Two weeks ago it was likely much smaller. Daily-delta indexing strategy needed (Aiden's Q5 territory).

## What's NOT in scope for Scout Q1

- **Vultr filesystem** — Atlas owns. Confirm with Atlas which paths are duplicates of `~/.claude/` (likely none — Vultr is the deploy target, not the dev box).
- **Other Supabase tables** — Aiden Q2.
- **Stale/superseded filter rules** — Orion Q3.
- **Weaviate current state + collections** — Max Q4.
- **40k-context ingestion sequencing** — Aiden Q5.

## Counts summary

- **Total raw unindexed bytes audited:** ~595 MB.
- **High-signal small corpora (recommended for first pass):** ~1.5 MB (memory/ + governance/ + skills/ + .beads/).
- **Medium-signal needing-filter corpora:** ~3 MB (capsules + outbox/processed + wave2/ + audits/).
- **Low-signal bulk transcripts:** 558 MB (defer until extraction pipeline ready).

---

*Per Dave: "No data moves until we have a complete picture and an agreed ingestion plan." Same deliberation discipline as KEI-70 productisation. This doc is research-only; awaiting team CONCUR + Elliot consolidation.*
