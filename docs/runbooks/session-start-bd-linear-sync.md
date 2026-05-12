# Session-Start: `bd linear sync` (Outcome 3 of Dave Urgent Directive ts ~1778620420)

## What this is

The repo-tracked source-of-truth for **Outcome 3** of the Linear↔Beads sync automation directive:

> OUTCOME 3 — Sync on session start
> Add to Elliot's `_session_start.md`:
>   Run `bd sync --linear` at session start.
>   Resolves any drift that occurred overnight.

Per Max's BLOCK and Dave's Decision 1 verbatim (#ceo ts ~1778623400), the literal command is the **native bd subcommand** `bd linear sync --pull-if-stale --threshold 20m`, not a bespoke wrapper. PR-2 (the bespoke outbound implementation) was reverted in this same PR.

## The line operators must add to their `~/.config/agency-os/modules/_session_start.md`

```markdown
6. **LINEAR ↔ BEADS SYNC (Dave Urgent directive ts ~1778620420, Outcome 3):** Run `bd linear sync --pull-if-stale --threshold 20m` at session start. Resolves any drift between Linear and Beads that occurred since last session. Native bd 1.0.4+ subcommand (no wrapper needed); LINEAR_API_KEY env covers auth. The 5-minute internal debounce in bd prevents agent loops even if multiple sessions start concurrently.
```

On the elliotbot host this PR ships from, the edit is already applied to `~/.config/agency-os/modules/_session_start.md` (the shared canonical file all 6 worktrees symlink to via KEI-12 — see PR #795). All callsigns on this host pick up the line on next session start automatically.

## Why this lives in `docs/runbooks/` and not `.claude/modules/`

Per KEI-12 (PR #779 + #795 merged), the `.claude/modules/` path is a per-host symlink to `~/.config/agency-os/modules/`. Repo cannot track files beyond the symlink. So:

- The canonical operator file is `~/.config/agency-os/modules/_session_start.md` (host-local).
- This runbook is the repo-tracked source-of-truth for the instruction content.
- Future operator hosts (or session-start module restorations) must consult this file to know the exact line.

If KEI-12 is ever rolled back (modules restored as regular files in the repo), this runbook absorbs into `.claude/modules/_session_start.md` directly and the runbook entry becomes a pointer-only.

## Empirical command verification

```
$ /home/elliotbot/.local/bin/bd linear sync --help
Synchronize issues between beads and Linear.

Modes:
  --pull              Import issues from Linear into beads
  --push              Export issues from beads to Linear
  --pull-if-stale     Pull only if data is stale (skip if fresh)
  (no flags)          Bidirectional sync: pull then push, with conflict resolution

Staleness (--pull-if-stale):
  --threshold 20m     How old data must be before pulling (default 20m)
  A 5-minute debounce prevents agent loops...

Examples:
  bd linear sync --pull
  bd linear sync --pull-if-stale --threshold 5m
  bd linear sync --pull --relations    # Import Linear blocking relations as bd deps
```

`bd --version`: `1.0.4 (ce242a879)`. Available in `/home/elliotbot/.local/bin/bd` on this host; systemd-user services must use the absolute path (or `Environment=PATH` extension) — same constraint as `elliot_polling_loop.py:_BD_BIN` from PR #792.

## Coverage matrix (all 4 outcomes from directive)

| Outcome | Coverage | Mechanism |
|---|---|---|
| 1 — Bidirectional sync on Linear events | PR-1 (#804) | FastAPI webhook receiver `/api/webhooks/linear` — push-based real-time |
| 2 — bd → Linear on operations | bd linear sync --push (native) | Operator timer OR manual; previous bespoke PR-2 (#805 + #806) reverted in this PR |
| 3 — Session-start sync | This runbook | `bd linear sync --pull-if-stale --threshold 20m` in `_session_start.md` |
| 4 — Auto-assign on --claim | bd linear sync (native, state_map) | Linear assignee = bd assignee; mapped via `bd config set linear.state_map.*` |
