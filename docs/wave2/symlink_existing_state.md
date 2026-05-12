# Wave 2 Research — Existing Symlink State

**Command run:** `find /home/elliotbot/clawd/Agency_OS{,-aiden,-max,-atlas,-orion,-scout} -maxdepth 4 -type l 2>/dev/null`

## Findings

**Zero governance files are currently symlinked across any worktree.** Every `.claude/modules/*.md`, `CLAUDE.md`, `MEMORY.md`, `HEARTBEAT.md`, `IDENTITY.md`, `.claude/settings.json`, and `.claude/hooks/*.sh` is a regular file in every worktree — no shared canonical exists.

Existing symlinks are confined to three non-governance areas:

1. **`config/.env`** — main worktree only. `/home/elliotbot/clawd/Agency_OS/config/.env` → external location (typical: `~/.config/agency-os/.env`). Pattern we should mirror for governance.
2. **`.venv/lib64`** — main worktree only. Standard Python venv internal symlink to `lib`.
3. **`frontend/node_modules/*`** — main worktree only, thousands of links from npm/pnpm hoisting. Ignore.

The find command at maxdepth 4 produced ~3000 hits, almost all in `frontend/node_modules/`. After filtering, only the two non-node_modules links above are relevant.

## Broken / dead symlinks

`find -L .../Agency_OS{,-*} -maxdepth 4 -type l` (the `-L` flag exposes broken targets) inside `Agency_OS-scout` returned **no broken governance symlinks** — but the worktrees other than main have **no `config/.env` link at all**, which matches the `feedback_systemd_worktree_main.md` memory ("Systemd services read from Elliot worktree only"). Non-main worktrees access `.env` via absolute path through main's link, not via their own link.

## Implication for the migration

Greenfield. The symlink design doesn't need to coexist with any existing partial-link infrastructure. The `config/.env` pattern (main-worktree-anchored to external location) is a known-working template for what we'd do with `.claude/modules/` and `.claude/hooks/`.
