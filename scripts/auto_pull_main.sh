#!/usr/bin/env bash
# auto_pull_main.sh — keep Elliot + Aiden worktrees' main branches in sync with origin/main.
#
# Runs every 5 minutes via the agency-os-auto-pull-main.timer systemd unit.
# Behavior per worktree:
#   - skip if path doesn't exist (operator removed it)
#   - skip if not on main (feature-branch work in progress)
#   - skip if working tree dirty (uncommitted changes — operator's intent)
#   - skip if rebase / merge / cherry-pick in progress (operator mid-flight)
#   - else: git fetch origin main + git merge --ff-only origin/main
#
# All output goes to systemd-journal (no TG spam unless the user adds it).
# Failures are non-fatal — the next 5-min cycle retries.
#
# Why this exists: 2026-05-09 session had two stale-main rebase incidents
# (PR #657 force-push, smoke test ran on pre-#637 code) because the worktree
# wasn't kept in sync. This eliminates the failure class.

set -uo pipefail

WORKTREES=(
    "/home/elliotbot/clawd/Agency_OS"
    "/home/elliotbot/clawd/Agency_OS-aiden"
)

for wt in "${WORKTREES[@]}"; do
    [ -d "$wt/.git" ] || [ -f "$wt/.git" ] || { echo "SKIP $wt: not a git worktree"; continue; }
    branch=$(git -C "$wt" symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED")
    if [ "$branch" != "main" ]; then
        echo "SKIP $wt: on $branch (only auto-pull when on main)"
        continue
    fi
    if [ -n "$(git -C "$wt" status --porcelain)" ]; then
        echo "SKIP $wt: working tree dirty"
        continue
    fi
    git_dir=$(git -C "$wt" rev-parse --git-dir)
    if [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ] \
       || [ -f "$git_dir/MERGE_HEAD" ] || [ -f "$git_dir/CHERRY_PICK_HEAD" ]; then
        echo "SKIP $wt: rebase/merge/cherry-pick in progress"
        continue
    fi
    if ! git -C "$wt" fetch --quiet origin main 2>&1; then
        echo "FAIL $wt: fetch origin main failed"
        continue
    fi
    before=$(git -C "$wt" rev-parse HEAD)
    if git -C "$wt" merge --ff-only --quiet origin/main 2>&1; then
        after=$(git -C "$wt" rev-parse HEAD)
        if [ "$before" != "$after" ]; then
            echo "PULLED $wt: $before → $after"
        else
            echo "OK $wt: already at $before"
        fi
    else
        echo "FAIL $wt: ff-only merge refused (history diverged?)"
    fi
done
