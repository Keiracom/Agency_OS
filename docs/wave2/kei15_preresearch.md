# KEI-15 Pre-Research — Phase 4 (Autonomy + Orchestration)

Source: Dave's 20-Item Roadmap 2026-05-11 (items 12–16). Gate: KEI-14 complete.

## 1. Ralph Loop — NOT STARTED

`grep -r "ralph.loop\|ralph_loop"` = zero hits. No `skills/ralph-loop/`.

**Refs:** `snarktank/ralph` + `frankbria/ralph-claude-code` (Claude Code impl with session continuity + circuit breaker).

**Outline:** `skills/ralph-loop/SKILL.md` + `ralph_loop.sh`. Each iter: spawn fresh `claude --append-system-prompt` with PRD + read prior `progress.md` + append result + check completion regex. Circuit-breaker: halt after 3 no-progress diffs. Memory = git + `progress.md`. Per-callsign tmux.

Effort: ~150 LOC, single PR.

## 2. CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS — NOT STARTED

Env var not set anywhere (`grep CLAUDE_CODE_EXPERIMENTAL` across env files = empty). Claude Code version on disk is **2.1.139** (per session jsonl metadata) — spec requires ≥2.1.32, so compat OK.

**Ref:** https://code.claude.com/docs/en/agent-teams.

**Outline:** set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.config/agency-os/.env`. Sequence: enable AFTER Item 3 (shared task list) so teams have something to coordinate on. Smoke: trivial Atlas↔Orion hand-off before broader rollout.

Effort: ~10 LOC env + smoke test.

## 3. Shared task list (CLAUDE_CODE_TASK_LIST_ID) — NOT STARTED

Only refs: the Beads issue body + Dave's CEO post. No implementation.

**Outline:** generate one shared UUID (or per-scope: Build, Research). Set `CLAUDE_CODE_TASK_LIST_ID=<uuid>` in `~/.config/agency-os/.env`. Tied to Item 2 — Agent Teams enforces dependency-visibility. Defer Beads↔task-list bridge daemon until base feature is verified.

Effort: ~5 LOC env + optional bridge later.

## 4. Deterministic context rotation at 70% — NOT STARTED

`grep -r "context.rotation\|70.*percent.*context"` = zero hits. Current = human `/clear` per `feedback_clear_not_equal_reset.md`.

**Ref:** `ralph-wiggum-cursor` (rotation at 80k tokens) listed in `snwfdhmp/awesome-ralph`.

**Outline:** PostMessage hook reads transcript size from session jsonl (`/home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS-<callsign>/<sid>.jsonl`). At 70% window: trigger anti-amnesia capsule (already shipped via Max #754/#773), then exit-and-reopen session via orchestrator. **Requires orchestrator support** — Claude Code can't self-rotate mid-process. Depends on Item 2 primitives, else alert-only fallback.

Effort: ~80 LOC if Agent Teams supports; ~30 LOC alert-only stub.

## 5. Standardised error recovery playbooks — NOT STARTED

No `_error_playbook.md` in `.claude/modules/` (13 enumerated, none named playbook — see `symlink_governance_audit.md`).

**Ref:** `VoltAgent/awesome-openclaw-skills` (`error-recovery-automation`).

**Outline:** `.claude/modules/_error_playbook.md` (post-KEI-12 → at `~/.config/agency-os/modules/_error_playbook.md`). 8 entries from incident log: Cognee SQLite deadlock, Salesforge 401, Vercel timeout, Supabase RLS denial, Prefect crashed-state, MCP ECONNREFUSED, gh rate-limit, git push hook reject. Each: symptom regex + diagnostic cmd + recovery cmd + escalation trigger. SessionStart hook reads into context; pre-tool-use matches errors against playbook; auto-retry once; escalate on miss.

Effort: ~200 LOC markdown + ~60 LOC matcher hook.

## Sequence

| Item | Depends on |
|---|---|
| Ralph Loop | independent |
| Agent Teams env | independent (compat verified) |
| Shared task list | Agent Teams |
| Context rotation | Agent Teams primitives OR alert-only fallback |
| Error playbooks | KEI-12 symlink (for canonical location) |

Dispatch order: Agent Teams → Shared task list → Ralph Loop (independent track) → Context rotation → Error playbooks (after KEI-12).
