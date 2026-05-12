# MEMORY.md Deprecation Runbook (KEI-9 Wave 2 Item 2)

## What this is

Per Dave Urgent directive ts ~1778624650 (KEI-9 Wave 2): "remove deprecated MEMORY.md from all 6 worktrees". The repo-tracked instance at `governance/MEMORY.md` is removed in the same PR as this runbook. This file covers operator-side cleanup of any non-repo-tracked MEMORY.md copies on each of the 6 worktrees.

## Repo-tracked deletion (done in this PR)

```
$ find . -name MEMORY.md -not -path "./.git/*"
./governance/MEMORY.md  ← repo-tracked, deleted in this PR

$ git rm governance/MEMORY.md
rm 'governance/MEMORY.md'
```

The file was archived to Supabase `elliot_internal.memories` on 2026-02-12; its header verbatim says "DEPRECATED — Migrated to Supabase elliot_internal.memories on 2026-02-12. Read-only reference only. Do not add new entries here." Per `_orchestrator.md` `bd remember` usage section + the agent_memories Supabase table, the file has no active readers in `src/`, `scripts/`, or `skills/`.

## Operator-side cleanup (per host, per worktree)

The 6 worktrees on the elliotbot host:

```
/home/elliotbot/clawd/Agency_OS                  (elliot main)
/home/elliotbot/clawd/Agency_OS-aiden            (aiden)
/home/elliotbot/clawd/Agency_OS-max              (max)
/home/elliotbot/clawd/Agency_OS-atlas            (atlas clone)
/home/elliotbot/clawd/Agency_OS-orion            (orion clone)
/home/elliotbot/clawd/Agency_OS-scout            (scout clone)
```

After this PR merges to main, each worktree's `git pull --rebase origin main` removes the tracked `governance/MEMORY.md` automatically. No operator action required for repo-tracked instances.

**If any worktree has a non-tracked MEMORY.md at a different path** (e.g., `~/MEMORY.md`, `~/.claude/MEMORY.md`, `.beads/MEMORY.md`), the operator must `find` + `trash` (per CLAUDE.md "trash > rm" safety):

```
# Per-worktree probe (run from each worktree root):
$ find . -name MEMORY.md -not -path "./.git/*"

# If anything surfaces, archive + remove:
$ trash <found_path>
```

## Why not auto-delete via script

Operator-side file deletion across 6 worktrees is irreversible without `trash` recovery. CLAUDE.md "Ask before external actions (anything irreversible)" applies. The runbook makes the deletion explicit + auditable, vs scripting a sweep that could mass-delete.

## Verification post-merge

Single command per worktree:

```
$ find . -name MEMORY.md -not -path "./.git/*"
(no output = clean)
```

Elliot's smoke test for KEI-9 Wave 2 PR-A should include this find across the 6 worktrees.

## Related

- `elliot_internal.memories` table (Supabase) — canonical memory store since 2026-02-12
- `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/MEMORY.md` — auto-memory index (per-host, not the same file class)
- `.claude/modules/_orchestrator.md` `bd remember` section — current memory mechanism
