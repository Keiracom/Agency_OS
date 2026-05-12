# Wave 2 Research — Symlink Migration Implementation Sketch

## Phase 1 — extract canonical content (outside any worktree)

```bash
# Create canonical home (mirror's config/.env pattern)
mkdir -p ~/.config/agency-os/{modules,hooks}
mkdir -p ~/.local/state/agency-os

# Seed from main worktree (already byte-identical to all others)
cp -a /home/elliotbot/clawd/Agency_OS/.claude/modules/. ~/.config/agency-os/modules/
cp -a /home/elliotbot/clawd/Agency_OS/.claude/hooks/.   ~/.config/agency-os/hooks/
mv /home/elliotbot/clawd/Agency_OS/HEARTBEAT.md         ~/.local/state/agency-os/HEARTBEAT.md
```

## Phase 2 — atomic per-worktree swap

The risk: session-start hooks read `.claude/modules/*.md` at process start. If we rename-then-symlink, a session starting mid-rename sees a missing file. Use the standard atomic-replace pattern (`ln -sfn` + temp dir):

```bash
for wt in Agency_OS Agency_OS-aiden Agency_OS-max Agency_OS-orion Agency_OS-scout; do
  cd /home/elliotbot/clawd/$wt
  # 1) Preserve original as .bak (rollback path)
  mv .claude/modules .claude/modules.bak
  mv .claude/hooks   .claude/hooks.bak
  mv HEARTBEAT.md    HEARTBEAT.md.bak
  # 2) Atomic symlink creation (-n = don't follow existing link if any)
  ln -sn ~/.config/agency-os/modules .claude/modules
  ln -sn ~/.config/agency-os/hooks   .claude/hooks
  ln -sn ~/.local/state/agency-os/HEARTBEAT.md HEARTBEAT.md
done
# Atlas opts out of the userpromptsubmit hook — symlink the *directory* only
# AFTER removing that one hook from the canonical (or use per-file symlinks for atlas)
```

For `MEMORY.md` (deprecated): no symlink — just `git rm` in a PR after confirming nothing reads it.

## Phase 3 — smoke + rollback

```bash
# Smoke: every worktree should still resolve session-start reads
for wt in Agency_OS Agency_OS-*; do
  test -r /home/elliotbot/clawd/$wt/.claude/modules/_session_start.md \
    || echo "FAIL: $wt session_start unreadable"
done
# After 24h of clean runs, remove .bak:
find /home/elliotbot/clawd/Agency_OS{,-*}/.claude -maxdepth 2 -name '*.bak' -exec rm -rf {} +
find /home/elliotbot/clawd/Agency_OS{,-*} -maxdepth 2 -name 'HEARTBEAT.md.bak' -delete
```

Rollback (if smoke fails): symlinks are easy to revert — `rm symlink && mv target.bak target`. Zero data loss because originals are preserved as `.bak`.

## Phase 4 — CI guard (for files that STAY in repo)

`CLAUDE.md` is kept in-repo. Add a GitHub Actions check (pattern from Aiden's PR #768 migration-completeness guard) that fails CI when any branch's `CLAUDE.md` md5 differs from `origin/main`'s:

```yaml
- name: governance-equality-guard
  run: |
    main_hash=$(git show origin/main:CLAUDE.md | md5sum | awk '{print $1}')
    head_hash=$(md5sum CLAUDE.md | awk '{print $1}')
    [ "$main_hash" = "$head_hash" ] || {
      echo "::error::CLAUDE.md diverged from origin/main"
      exit 1
    }
```

Same pattern for any other file class we deliberately leave duplicated rather than symlink.

## Gotchas list

1. **`.claude/modules/` symlinked to outside repo** means `git status` in each worktree shows the modules dir as untracked. Add `.claude/modules/` to `.gitignore` *in the same PR* that creates the symlinks.
2. **Hooks that write to HEARTBEAT.md** — symlink target is shared across all callsigns. If two sessions write concurrently, last-writer-wins. Add `flock` to the writer if ordering matters.
3. **Atlas's missing `session_store_userpromptsubmit.sh`** — symlinking the whole `.claude/hooks/` dir would re-add it, contradicting atlas's intentional opt-out. Either symlink per-file (skip that one for atlas) or sync atlas's settings.json first to include the matcher (per `settings_json_reconcile.md` recommendation).
