# Orion Section — Filesystem + Drive Memory Audit (2026-05-12)

**Stream 1 of 4** · **Owner: Orion (clone of Aiden)** · 6 worktrees + Drive Manual + global memory pins
**Methodology**: Aiden Step 0 + Max methodology tweaks + Elliot synthesis attribute set, adapted to filesystem stores: name / purpose / authority / size (bytes + LOC) / freshness (mtime) / churn (commits last 7d in main) / readers (grep) / writers (grep or "manual") / last-access proxy (atime) / surprises. Cross-worktree drift comparison done by sha256 + line diff. Inventory snapshot timestamp: 2026-05-12 ~03:30 UTC.

## Inventory Table — Per-Worktree Files

Sizes/shas captured against `/home/elliotbot/clawd/Agency_OS{,-aiden,-max,-atlas,-orion,-scout}`. Sha = first 12 hex chars of sha256.

| # | File | Across-Worktree Consistency | Authority | Size (typical) | Latest mtime | 7d churn (main) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `CLAUDE.md` | **5/6 identical** (sha `955b2c491863`, 1244 b, 48 LOC). Scout forked. | SSOT (per-worktree) | 1244 b | 2026-05-12 (main+orion) | 3 commits | Scout = 9258 b (sha `b70ae2553fce`) — pre-modularisation monolithic copy |
| 2 | `IDENTITY.md` | **All 6 different** (expected per dispatch). | SSOT (per-worktree) | 372–2300 b | 2026-05-11 | 0 commits | Stale role refs in Scout; Orion's is 11 LOC minimal |
| 3 | `.claude/modules/*.md` | **13 modules, 5/6 worktrees in lockstep** (every sha identical). Scout has NO `.claude/modules/` dir. | DERIVED (sourced into CLAUDE.md via `@import`) | 120–1324 b each, ~7 KB total | 2026-05-12 (_session_start.md) | 1–3 commits/file | Scout cannot consume modules → still on inline CLAUDE.md |
| 4 | `.claude/settings.json` | **4 distinct shas across 6 worktrees**. main+aiden+orion identical (sha `17c5d17ac508`, 5999 b). Max forked (6363 b). Atlas forked (5550 b). Scout forked (3115 b, 109 LOC). | SSOT (per-worktree, mostly diverged) | 3115–6363 b | 2026-05-12 03:47 (max) | 4 commits | Scout much smaller — missing hooks shipped to peers |
| 5 | `MEMORY.md` (repo-local) | **All 6 byte-identical** (sha `0290f6ddbb5c`, 4495 b, 124 LOC). | ARCHIVE | 4495 b | 2026-03-11 (main), 2026-04-17 to 2026-05-11 (other worktrees) | 0 commits | Per `scripts/seed_claude_md_facts.py:170`: "MEMORY.md (new writes) is deprecated" — frozen but checked-in |
| 6 | `HEARTBEAT.md` | **5/6 identical** (PR #751 BASE template, sha `f721790a981a`, 1170 b). Scout still on pre-#751 (sha `376d1c5a1c65`, 367 b). | SSOT (per-worktree, agent-maintained) | 1170 b | 2026-05-12 03:22 (max), 04-17 (scout) | 1 commit | Scout missed PR #751 propagation; agent-maintained semantics depend on snapshot via PreCompact hook |

## Inventory Table — Shared / Global Stores

| # | Store | Authority | Size | Freshness | Churn | Readers | Writers | Surprises |
|---|---|---|---|---|---|---|---|---|
| 7 | Drive Manual (Doc `1p9F…e9ho`, title "Manual") | SSOT (per global CLAUDE.md), but see drift #5 below | 56,539 b (Docs export) | modifiedTime **2026-05-12 02:51:17** UTC | mirror script invoked 36× in last 30d (via docs/MANUAL.md commits) | `mcp__claude_ai_Google_Drive__*`, all agents via global session-start spec | `skills/drive-manual/write_manual.py` (one-direction mirror) | Last `viewedByMeTime` = **2026-04-20** — Dave hasn't opened the Doc in 3 weeks despite mirror writes |
| 8 | `docs/MANUAL.md` (repo mirror) | SSOT-primary per its own header line 7: "**Primary store.** This file is the CEO SSOT. Google Doc is an auto-generated mirror." | 109,808 b, 1395 LOC | 2026-05-12 02:47:42 UTC (4 min before Drive update — confirms repo→Drive flow) | 2 commits in 7d (Aiden), 36 in 30d | All agents on directive completion; `scripts/seed_claude_md_facts.py`; manual cat/grep | `skills/drive-manual/write_manual.py`, `scripts/three_store_save.py` (LAW XV), manual edits by all callsigns | **Authority contradicts global CLAUDE.md** which calls the Drive Doc the CEO SSOT (see Drift #5) |
| 9 | `~/.claude/projects/-home-elliotbot-clawd/memory/MEMORY.md` (auto-memory index, per-user not per-repo) | SSOT (auto-loaded into every Claude Code session as `<system-reminder>`) | 4611 b, 36 LOC | 2026-05-11 22:50:40 UTC | n/a (per-user, not in git) | Claude Code harness (auto-load); user across all sessions | Auto-written by Claude Code when saving feedback/user/project memories | **Same filename as repo-local MEMORY.md (5/6 above) but DIFFERENT content + sha — easy to confuse** |
| 10 | `~/.claude/projects/.../memory/feedback_*.md` + `project_*.md` (memory pins) | SSOT (each pin is an active directive Claude observes via `MEMORY.md` index) | 30 feedback + 3 project = 33 files, 34,866 b combined, 430 LOC | newest 2026-05-12 00:16 (`feedback_never_stop.md`); oldest 2026-05-02 (`feedback_peer_communication.md`) | n/a (not in repo) | Auto-loaded transitively via MEMORY.md links | Auto-written when Dave gives feedback in sessions; never edited from src/scripts/ | 30 pins is a lot — risk that contradictory feedback accumulates without retirement step |

## Per-Worktree Detail

### Worktree summary (6 trees)

| Worktree | Branch (last commit) | CLAUDE.md size | IDENTITY.md LOC | modules dir | HEARTBEAT.md | settings.json size |
|---|---|---|---|---|---|---|
| `Agency_OS` (main) | `main` | 1244 b ✓ | 20 LOC (elliot) | ✓ | 1170 b ✓ | 5999 b |
| `Agency_OS-aiden` | `aiden/scaffold` | 1244 b ✓ | 22 LOC (aiden) | ✓ | 1170 b ✓ | 5999 b |
| `Agency_OS-max` | `max/*` | 1244 b ✓ | 20 LOC (max) | ✓ | 1170 b ✓ | 6363 b ⚠ |
| `Agency_OS-atlas` | `atlas/*` | 1244 b ✓ | 15 LOC (atlas) | ✓ | 1170 b ✓ | 5550 b ⚠ |
| `Agency_OS-orion` | `orion/*` | 1244 b ✓ | **11 LOC (orion) ⚠** | ✓ | 1170 b ✓ | 5999 b |
| `Agency_OS-scout` | `scout/main` | **9258 b ⚠ (forked)** | 32 LOC (scout) | **✗ MISSING ⚠** | **367 b ⚠ (pre-#751)** | **3115 b ⚠** |

### Module set (`.claude/modules/*.md`)

13 modules, identical byte-for-byte across the 5 modular worktrees (main/aiden/max/atlas/orion). Each module sources into per-worktree `CLAUDE.md` via `@.claude/modules/<name>.md` imports:

| Module | Size | Sha | Purpose |
|---|---|---|---|
| `_project_overview.md` | 497 b | `93a86edd14e6` | Project context (Keiracom, stack, env) |
| `_law_step0.md` | 607 b | `96cb6cd8feec` | LAW XV-D Step 0 RESTATE rules |
| `_session_start.md` | 1324 b | `221fa9478443` | Session start protocol (Manual lazy-load post 2026-05-11) |
| `_law_clean_tree.md` | 400 b | `e130cfcf444d` | LAW XVI clean tree before new work |
| `_law_architecture_first.md` | 402 b | `e2c26655adde` | LAW I-A architecture before changes |
| `_hierarchy.md` | 820 b | `2c01a1f3436b` | Authority chain Dave→Claude→Elliot→… (2026-05-11) |
| `_completion_discipline.md` | 955 b | `2aec3e7fb7b8` | Verify-before-claim hard block (2026-05-11 fabrications) |
| `_mcp_bridge.md` | 564 b | `db5a0d050229` | MCP bridge decision tree LAW VI |
| `_governance_rules.md` | 1076 b | `51056e9a4780` | 7 consolidated rules (ratified 2026-05-01) |
| `_dead_references.md` | 175 b | `55bbe97bf230` | Points to ARCHITECTURE.md §3 |
| `_enrichment_path.md` | 170 b | `fe7a67d284d8` | Points to ARCHITECTURE.md §2/§5 |
| `_directive_format.md` | 120 b | `400155bd43d8` | Directive template |
| `_session_end.md` | 533 b | `01d2b11a4e79` | Session-end three-store check + thresholds |

Authority: DERIVED — these are sourced into CLAUDE.md; canonical truth is the modules themselves. **Scout cannot consume any of these** (no modules dir → falls through to its monolithic CLAUDE.md).

### Readers / Writers Grep Summary

Counts from `grep -rE "<pattern>" src/ scripts/ skills/` in the main worktree.

| File class | Total refs | Top readers/writers (file:line) |
|---|---|---|
| `CLAUDE.md` | 13 | `src/telegram_bot/enforcer_bot.py:69` (R5 shared-file-claim), `src/orchestration/flows/health_check_flow.py:360` (sensitive_patterns guard), `src/governance/coordinator.py:11`, `scripts/seed_claude_md_facts.py:39` (read+seed) |
| `IDENTITY.md` | 17 | `scripts/slack_relay.py:50` (callsign resolution), `scripts/pre_compact_alert.py:46`, `scripts/session_start_audit.py:54`, `scripts/context_compiler.py:293`, `scripts/update_peer.py:17-24` (hardcoded paths for elliot+aiden) |
| `HEARTBEAT.md` | 6 (all in one file) | `scripts/pre_compact_alert.py:36` (sole reader, snapshots to #execution on PreCompact) |
| `MEMORY.md` (string only) | 2 | `scripts/seed_claude_md_facts.py:170, 283` — both say "deprecated" / "dead reference" |
| `.claude/modules` | 4 | `scripts/ssot_drift_check.sh` (only consumer) |
| `settings.json` | 7 | `src/governance/router.py:16`, `scripts/governance_hooks.py:4`, `scripts/governance_router.py:4`, `scripts/session_end_hook.py:5`, `scripts/pre_compact_alert.py:19`, `scripts/session_start_audit.py:22` — all hook docs, not actual readers |

**Writers** for per-worktree files are uniformly `manual edit` — no script systematically writes IDENTITY.md / CLAUDE.md / modules / HEARTBEAT.md. HEARTBEAT.md is "agent-maintained" per its own header but the maintenance loop is opportunistic, not enforced. PR #755 (Orion, just merged-pending) adds a generator that COULD produce per-callsign HEARTBEAT files but is not yet wired into session start.

### Last-Access Proxy (atime)

Most worktree files show atime within hours of mtime (filesystem still tracks atime). Notable exceptions:
- `Agency_OS-atlas/HEARTBEAT.md` atime 2026-05-05 — **but its sha jumped to the new 1170-byte template between my first and second capture** (during this audit). Implies an automated propagation step (commit fetch?) is touching mtime but not atime.
- `Agency_OS-scout/HEARTBEAT.md` atime + mtime both 2026-04-17 — **Scout has not been touched in 25 days.**
- `Agency_OS-scout/CLAUDE.md` atime 2026-05-12 02:20 — was READ today (likely by the auto-deferred audit/session-start tooling) but content has not been updated since 2026-04-26.

## Drift Findings (Inventory + Diff Only — No Fixes Proposed)

### Drift 1 — Scout is the consistent outlier (5 distinct drift points)
- **CLAUDE.md**: 9258 b inline monolith vs the 1244 b modular `@import` form on the other 5 worktrees. Diff shows the Scout file embeds an OLD inline "Read the Manual First (HARD BLOCK)" — pre Phase 6 W4 lazy-load conversion of 2026-05-11.
- **`.claude/modules/` directory**: ABSENT. Scout cannot consume any of the 13 shared modules.
- **HEARTBEAT.md**: still on the 367 b pre-PR #751 template. The PR #751 BASE template propagated to main + 4 worktrees but not Scout.
- **`.claude/settings.json`**: 3115 b vs 5999–6363 b on peers — missing hook wiring (e.g. PreCompact, session-start audit, recorder/store hooks). Operationally Scout is running without the recent governance hooks others rely on.
- **IDENTITY.md role staleness**: Scout's IDENTITY.md says "Reports to Elliot (CTO) and Aiden" — Elliot is COO per 2026-05-11 role swap. Scout's IDENTITY explicitly opts OUT of LAW XV-D Step 0 RESTATE ("You do NOT follow Step 0 RESTATE"). This is a per-callsign carve-out, not a drift bug — but it is a divergence from the CLAUDE.md hard-block declared for the other callsigns.

### Drift 2 — Orion IDENTITY.md is dangerously thin
Orion's IDENTITY.md (11 LOC, 372 b) is the smallest of the 6 and lacks:
- Role description
- Reporting / escalation chain (only "Parent: Aiden")
- Callsign-tag discipline reminder (LAW XVII)
- Slack/relay channel info
- Governance reminder

Compare: Aiden 22 LOC with full Slack channel routing + governance pointer; Max 20 LOC with role + reporting; Atlas 15 LOC with explicit "C3 Prime-Only Channel" rule. Orion is operating without the same identity scaffolding its peers see at session start — and there's no script that compensates (e.g. `scripts/update_peer.py` only knows about elliot + aiden paths).

### Drift 3 — `.claude/settings.json` has 4 distinct shape variants
- `17c5d17ac508` (5999 b): main, aiden, orion
- `48d3cd4eb6ac` (6363 b): max (largest — extra hooks or permissions)
- `8033cbfbb936` (5550 b): atlas
- `6387379e4c31` (3115 b): scout (smallest — missing hooks)

settings.json drives hook wiring (PreCompact, SessionStart, Stop, etc.). 4 shapes for one config file = 4 different behaviour profiles per worktree. **No script in `scripts/` or `src/` reconciles them**; drift only narrows when an operator manually copies.

### Drift 4 — repo-local `MEMORY.md` is byte-identical across 6 worktrees but DEPRECATED
All 6 worktrees carry the same `MEMORY.md` (sha `0290f6ddbb5c`, 4495 b, 124 LOC, last logical update 2026-03-11). `scripts/seed_claude_md_facts.py` lines 170 and 283 explicitly call this file deprecated. Yet it is still committed in every worktree and shows up in `Read` results. It is also EASILY CONFUSED with `~/.claude/projects/.../memory/MEMORY.md` (the auto-memory index that IS active and IS auto-loaded).

### Drift 5 — Drive Manual SSOT label vs `docs/MANUAL.md` self-label CONTRADICT
- Global `~/.claude/CLAUDE.md` Session Startup §0: "Read the Agency OS Manual from Google Drive (Doc ID: …). This is the CEO SSOT."
- `docs/MANUAL.md` line 7: "**Primary store.** This file is the CEO SSOT. Google Doc is an auto-generated mirror."

Two SSOT claims for the same content. The actual write flow (docs/MANUAL.md committed first at 02:47:42, Drive Doc modifiedTime 02:51:17 — 4 min later) **proves docs/MANUAL.md is primary**. Global CLAUDE.md SSOT pointer is therefore stale. Aiden flagged a related drift in her Stream 1 Supabase audit (global vs per-worktree session-start memory pointer mismatch); this is the same pattern in a different file.

### Drift 6 — HEARTBEAT.md "agent-maintained" but no enforced maintenance loop
The BASE HEARTBEAT.md template (PR #751) declares itself "agent-maintained continuation anchor". Only one reader exists: `scripts/pre_compact_alert.py` which snapshots the file's contents into the PreCompact alert. No script ever WRITES the file — agents are expected to edit it manually before context fills up. In practice, mtimes show HEARTBEAT.md mostly untouched between session starts (main mtime jumped 02:40:56 = a session start, not a mid-session update). The template fields ("Active Task", "Last Good Commit", "Blockers", "Next Action") show signs of being left at their `<placeholder>` defaults.

### Drift 7 — Atlas's HEARTBEAT.md sha changed during this audit window
First capture (~03:25): atlas HEARTBEAT.md = 367 b (sha `376d1c5a1c65`). Second capture (~03:32, after touching other files in the worktree but NOT atlas): atlas HEARTBEAT.md = 1170 b (sha `f721790a981a`). Either an automated propagation step (commit fetch / rebase?) caught up during the audit, or another bot touched it. atime is older than mtime now — an unusual signal.

### Drift 8 — 30 feedback pins, no retirement step
`~/.claude/projects/-home-elliotbot-clawd/memory/feedback_*.md` holds 30 active feedback rules + 3 project pins, all auto-loaded into every session via the MEMORY.md index. Pin examples: `feedback_propose_not_ask.md`, `feedback_fix_dont_list.md`, `feedback_never_stop.md`, `feedback_chain_of_command.md` (some superficially overlapping, e.g. propose-not-ask vs check-before-asking). No script retires pins; oldest is 10 days, newest is 9 hours. Auto-memory has a `[[name]]` linking convention but does not have a "supersedes" or "expires" marker. Risk surface: contradictory rules accumulate.

## Surprises (flagged for synthesis)

1. **Scout is structurally on a fork** — old monolithic CLAUDE.md, no modules dir, old HEARTBEAT.md, sub-half-size settings.json, stale role pointer. Functionally Scout is running a 2026-04-17 snapshot of the agent platform.
2. **Orion IDENTITY.md is 11 LOC** vs 15–32 for peers — missing role, governance reminder, channel info. The dispatched scripts that compensate (`update_peer.py`) only handle elliot + aiden hardcoded paths.
3. **4 distinct settings.json shapes** across 6 worktrees. No reconciliation script.
4. **Repo-local MEMORY.md is deprecated by name** (per `seed_claude_md_facts.py:170,283`) but committed in every worktree. Identical sha across all 6. Easy to confuse with the active auto-memory MEMORY.md (different file, different content).
5. **Two SSOT labels for the Manual** — global CLAUDE.md says Drive Doc is CEO SSOT; docs/MANUAL.md self-declares as primary. Write flow proves docs/MANUAL.md is primary; global CLAUDE.md pointer is stale.
6. **HEARTBEAT.md is read-only in practice** — one reader (`pre_compact_alert.py`), zero programmatic writers, manual maintenance is the design but mtimes suggest it rarely actually gets updated mid-session.
7. **Atlas HEARTBEAT.md sha mutated during this audit** — a propagation/refresh ran without operator action. Atime did not advance, so it wasn't a read.
8. **30 feedback pins accumulating without retirement** — auto-memory has no supersedes/expires; oldest already 10 days old. Some pins look like near-duplicates (e.g. `feedback_propose_not_ask.md` vs `feedback_check_before_asking.md`).
9. **`scripts/seed_claude_md_facts.py` references "MEMORY.md and HANDOFF.md are deprecated"** but neither file is removed from worktrees — code is documenting the deprecation but not enforcing it.
10. **`scripts/update_peer.py` hard-codes only elliot + aiden paths** (`scripts/update_peer.py:17, 24`) — there is no mechanism to keep max/atlas/orion/scout IDENTITY.md in sync; manual maintenance only.

## Methodology Caveats

- **`mtime` is a touch proxy, not a content-change proxy.** A `git checkout` of a sibling branch can update mtime without changing content; sha256 is the actual content signal. I used both.
- **`atime` is unreliable on some filesystems** (often disabled or coarsely updated). Treated as best-effort. Where mtime > atime (e.g. atlas HEARTBEAT.md after refresh), I flagged it but did not over-interpret.
- **Grep-based reader/writer counts** miss MCP-bridge runtime reads and ad-hoc `cat`/`Read` tool invocations.
- **Drive Manual `fileSize` (56,539 b) is the Docs-API export size**, not raw text bytes — cannot be directly compared to `docs/MANUAL.md` 109,808 b. I compared modifiedTime timestamps instead to establish write ordering.
- **PR #755 (this clone's prior task) is mentioned in the HEARTBEAT.md row** because it's structurally relevant to that store's future maintenance, but the PR is OPEN, not yet merged, so it does not change the current inventory snapshot.

## Status

Section complete. Ready for Elliot synthesis into `docs/audits/memory_audit_2026-05-12.md`. PAUSE per Dave rule (no redesign proposals in this phase).
