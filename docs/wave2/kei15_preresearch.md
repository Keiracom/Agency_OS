# KEI-15 Pre-Research — Phase 4 (Autonomy + Orchestration)

Source: Dave's 20-Item Roadmap CEO post 2026-05-11 (Phase 4 items 12–16). Phase gate: KEI-14 (audit hardening) complete.

## Item 1 — Ralph Loop (autonomous PRD-driven iteration)

**Ship-status:** NOT STARTED. Grep for `ralph.loop`, `ralph_loop`, `PRD.*driven.*iter` across `src/`, `scripts/`, `.claude/` returns zero hits. No skill for it in `skills/`.

**References:**
- https://github.com/snarktank/ralph (canonical pattern)
- https://github.com/frankbria/ralph-claude-code (Claude Code implementation with session continuity + circuit breaker)

**Implementation outline:**
- New `skills/ralph-loop/SKILL.md` + `ralph_loop.sh`. Inputs: PRD path, completion-criteria regex, max-iterations. Each iteration: spawn fresh Claude Code session (`claude --append-system-prompt`) with PRD attached, read prior `progress.md`, append result, exit when criteria matched or budget exhausted.
- Circuit breaker: halt on 3 consecutive iterations with no progress-file diff.
- Memory: git commits per iteration + `progress.md` file appended in-place. Both checked in.
- Runs per callsign — Aiden's Ralph operates on her tmux, etc.

**Effort:** ~150 LOC shell + skill spec, 1 PR.

## Item 2 — CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS (native parallel)

**Ship-status:** NOT STARTED. No env var set across worktrees (`grep CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS /home/elliotbot/.config/agency-os/.env*` returns empty). Claude Code version on disk is `2.1.139` per session jsonl metadata — sufficient (spec requires ≥2.1.32).

**Reference:** https://code.claude.com/docs/en/agent-teams (per Dave's roadmap).

**Implementation outline:**
- Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.config/agency-os/.env` (shared across worktrees per `EnvironmentFile=` pattern in our systemd units).
- Each callsign tmux gets the env var on session start.
- Configure shared task list (Item 3 below) before enabling team mode — otherwise teams form but have nothing shared to coordinate on.
- Test path: trivial cross-callsign hand-off (Atlas → Orion) to validate the feature works on our Claude Code version before broader rollout.

**Effort:** ~10 LOC env + smoke test + skill doc. Dispatch coordination effort > code effort.

## Item 3 — Shared task list via CLAUDE_CODE_TASK_LIST_ID

**Ship-status:** NOT STARTED. Only references to `CLAUDE_CODE_TASK_LIST_ID` are in the Beads issue body (Agency_OS-jhd) and Dave's CEO post itself — no implementation.

**Implementation outline:**
- Generate one shared task-list UUID for the team (or per-phase scope: one for Build, one for Research).
- Set `CLAUDE_CODE_TASK_LIST_ID=<uuid>` in `~/.config/agency-os/.env`.
- Tied to Item 2 above — Agent Teams feature is what enforces dependency-visibility on the shared list.
- Bridge to Beads: a daemon could sync the Claude-Code task list ↔ Beads issues so both views stay live. Defer until base feature is verified.

**Effort:** ~5 LOC env + bridge daemon optional later. ~10-line PR for the bare minimum.

## Item 4 — Deterministic context rotation at 70%

**Ship-status:** NOT STARTED. Grep for `context.rotation`, `deterministic.*context`, `70.*percent.*context` returns zero hits. Current behaviour relies on human-triggered `/clear` per `feedback_clear_not_equal_reset.md`.

**Reference:** `ralph-wiggum-cursor` — context rotation at 80k tokens; listed in `snwfdhmp/awesome-ralph`.

**Implementation outline:**
- Hook on PostToolUse / PostMessage that reads the Claude Code transcript size from the session jsonl (path pattern: `/home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS-<callsign>/<session_id>.jsonl`).
- Compute token estimate (sum of `usage.input_tokens + output_tokens` across recent messages OR file-size proxy).
- At 70% of model's context window: trigger anti-amnesia capsule write (Item 3 in Phase 1, already shipped per Max #754/#773), then exit-and-reopen the Claude Code session via the orchestrator. **This requires orchestrator support** — Claude Code can't currently rotate its own context mid-process. Dependency on Item 2 (Agent Teams) which may provide the rotation primitive natively.
- Without Agent Teams support: implement as a soft signal — alert the human (Dave or the callsign) at 70%, do NOT auto-rotate. Document why.

**Effort:** ~80 LOC if Agent Teams supports it; otherwise ~30 LOC alert-only stub.

## Item 5 — Standardised error recovery playbooks

**Ship-status:** NOT STARTED. No `_error_playbook.md` in `.claude/modules/` (confirmed per `symlink_governance_audit.md` — 13 modules enumerated, none named playbook). No `recovery_playbook` references in repo.

**Reference:** `error-recovery-automation` skill — `VoltAgent/awesome-openclaw-skills`. Per Dave's roadmap: 8 pre-written recovery procedures for common failures.

**Implementation outline:**
- New file `.claude/modules/_error_playbook.md` (or `~/.config/agency-os/modules/_error_playbook.md` after KEI-12 symlink work lands).
- Enumerate 8 most common failure modes from the audit + incident log. Initial candidates: (a) Cognee SQLite deadlock, (b) Salesforge auth 401, (c) Vercel deploy timeout, (d) Supabase RLS denial, (e) Prefect flow crashed-state, (f) MCP bridge ECONNREFUSED, (g) gh CLI rate-limit, (h) git push hook rejection. Each entry: symptom regex + diagnostic command + recovery command + escalation trigger.
- Agent SessionStart hook reads the playbook into context. Pre-tool-use check: match observed error against playbook regex; if hit, execute recovery and retry once; if miss, escalate.
- Reference implementation pattern from the VoltAgent skill — fork the SKILL.md file structure.

**Effort:** ~200-300 lines markdown content + ~60 LOC matcher hook. 1 PR.

## Summary

| Item | Status | Dependency |
|---|---|---|
| Ralph Loop | NOT STARTED | independent |
| Agent Teams env | NOT STARTED | independent (verify version compat first) |
| Shared task list | NOT STARTED | depends on Agent Teams |
| Context rotation 70% | NOT STARTED | depends on Agent Teams primitives OR alert-only fallback |
| Error playbooks | NOT STARTED | depends on KEI-12 symlink for canonical location |

All 5 items are unstarted. Recommended dispatch order: Agent Teams enable → Shared task list → Ralph Loop (independent track) → Context rotation → Error playbooks (after KEI-12 lands).
