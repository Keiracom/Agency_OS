# Wave 2 Research — Symlinked Governance Audit

**Read fresh 2026-05-12** across all 6 worktrees. **Major refinement of Orion's audit:** the divergences Orion flagged for `.claude/modules/*.md`, `CLAUDE.md`, and `HEARTBEAT.md` have already been reconciled. Scout is no longer the outlier on any of those three. Current state below; recommendations follow.

## Current divergence state

| File class | Worktrees with file | Unique hashes | Status |
|---|---|---|---|
| `.claude/modules/*.md` (13 files) | 6/6 | **1 per file** | converged |
| `CLAUDE.md` | 6/6 | **1** (md5 ab61fbcef…) | converged |
| `MEMORY.md` | 6/6 | **1** (md5 1ffb10f3b…) | converged + deprecated |
| `HEARTBEAT.md` | 6/6 | **1** (md5 ca9ba077f…) | converged |
| `IDENTITY.md` | 5/6 (scout HEAD missing) | 5 (per-callsign) | by design |
| `.claude/hooks/*.sh` (7 files) | 6/6 except atlas missing `session_store_userpromptsubmit.sh` | 1 per shared file | mostly converged |
| `.claude/settings.json` | 6/6 | 2 (atlas forked) | covered in `settings_json_reconcile.md` |

Per-module hash check verified all 13 modules show `1 unique hash across 6 worktrees` — true byte-identity, not just same filename count.

## Per-class recommendation

| File class | Recommendation | Canonical location | Confidence |
|---|---|---|---|
| `.claude/modules/*.md` | **Symlink whole dir** (one symlink per worktree, not 13 each) | `~/.config/agency-os/modules/` (outside any worktree) | High |
| `CLAUDE.md` | **Keep duplicated, add CI guard** — too central to git history to extract | n/a — guard enforces equality across branches | Medium |
| `MEMORY.md` | **Delete entirely**, do not symlink. Deprecated by Supabase `elliot_internal.memories`. | n/a | High |
| `HEARTBEAT.md` | **Symlink to runtime dir** — it's mutable state, not source | `~/.local/state/agency-os/HEARTBEAT.md` | Medium |
| `IDENTITY.md` | **Keep per-worktree, do not symlink** — by-design divergence | n/a | High |
| `.claude/hooks/*.sh` | **Symlink whole dir** with atlas opt-out for `session_store_userpromptsubmit.sh` (matches its settings.json) | `~/.config/agency-os/hooks/` | High |
| `.claude/settings.json` | Force-sync atlas to main (see `settings_json_reconcile.md`); not symlinked because per-callsign overrides are likely future need | n/a | Medium |

## Conflicts to design around

1. **Git tracks the symlink, not the target.** Extracting `CLAUDE.md` out of the repo would break the natural "branch X has its own CLAUDE.md" model. That's the strongest argument against symlinking it.
2. **Hooks writing into symlinked files** (e.g. `HEARTBEAT.md` updated by `session_store_*.sh`) — symlinks follow on write, but **concurrent writes from multiple sessions can race**. Need an O_EXCL or flock pattern in the writer, not a symlink-layer concern.
3. **Stale branch checkout** — if a worktree checks out an old commit and the symlinked target has moved on, the worktree silently sees newer content. For runtime files (HEARTBEAT) that's correct behavior; for source files (modules) it's a footgun.

Net call: extract runtime + modular files, guard source files with CI.
