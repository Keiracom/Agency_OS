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
# Loud SKIP alerting (added per Scout diagnosis f42cc4d4, Aiden PR ts ~1778620800):
# Silent SKIPs masked the PR #782 peak-window staleness for >60 min on 2026-05-12.
# Now: track consecutive-SKIP streak per worktree at
#   $XDG_STATE_HOME/agency-os/auto-pull-main.<basename>.skip-streak
# Reset to 0 on any non-SKIP outcome (PULLED/OK/FAIL). When streak crosses the
# threshold (default 3 consecutive skips = 15 min stale), emit one Slack post
# to #execution with the dirty/branch reason. Repeat-suppressed via flag file
# so we don't spam every 5 min while staleness persists.
#
# Why this exists: 2026-05-09 session had two stale-main rebase incidents
# (PR #657 force-push, smoke test ran on pre-#637 code) because the worktree
# wasn't kept in sync. This eliminates the failure class.

set -uo pipefail

WORKTREES=(
    "/home/elliotbot/clawd/Agency_OS"
    "/home/elliotbot/clawd/Agency_OS-aiden"
)

# Staleness alert config (env-overridable for tests).
SKIP_ALERT_THRESHOLD="${AGENCY_OS_AUTO_PULL_SKIP_THRESHOLD:-3}"
STATE_DIR="${AGENCY_OS_AUTO_PULL_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/agency-os}"
RELAY="${AGENCY_OS_AUTO_PULL_RELAY:-/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py}"

mkdir -p "$STATE_DIR" 2>/dev/null || true

_state_path() {
    # $1 = worktree path. Returns the streak-counter file path.
    local basename
    basename=$(echo "$1" | tr '/' '_' | sed 's/^_//')
    echo "$STATE_DIR/auto-pull-main.${basename}.skip-streak"
}

_alerted_path() {
    echo "$(_state_path "$1").alerted"
}

# KEI-34 v2 Addition 2 — dirty-worktree #ceo escalation flag (distinct from
# .alerted which goes to #execution). Separate state file avoids alert-spam
# both channels.
_alerted_ceo_path() {
    echo "$(_state_path "$1").alerted-ceo"
}

_streak_get() {
    local f
    f=$(_state_path "$1")
    [ -f "$f" ] && cat "$f" 2>/dev/null || echo 0
}

_streak_inc() {
    local f streak
    f=$(_state_path "$1")
    streak=$(_streak_get "$1")
    streak=$((streak + 1))
    echo "$streak" > "$f" 2>/dev/null || true
}

_streak_reset() {
    rm -f "$(_state_path "$1")" "$(_alerted_path "$1")" "$(_alerted_ceo_path "$1")" 2>/dev/null || true
}

_emit_alert() {
    # $1 = worktree, $2 = reason
    local alerted_flag
    alerted_flag=$(_alerted_path "$1")
    [ -f "$alerted_flag" ] && return 0   # already alerted this streak
    local streak msg
    streak=$(_streak_get "$1")
    local minutes=$((streak * 5))
    msg="[PROPOSE:elliot] auto-pull-main staleness — $1 has SKIPed $streak consecutive cycles (~${minutes}m stale). Reason: $2. Resolve the worktree state so origin/main can ff-merge."
    if [ -x "$RELAY" ] || [ -r "$RELAY" ]; then
        /home/elliotbot/clawd/venv/bin/python3 "$RELAY" -g "$msg" >/dev/null 2>&1 || true
    fi
    touch "$alerted_flag" 2>/dev/null || true
}

# KEI-34 v2 Addition 2 — escalate to #ceo on dirty-worktree-skip-streak >=2.
# Distinct alert channel + state flag from the #execution alert. Stale code
# running silently is worse than no code running per Dave verbatim ts ~1778631000.
_emit_dirty_worktree_ceo_alert() {
    # $1 = worktree, $2 = reason (only fires when reason contains "working tree dirty")
    case "$2" in
        *"working tree dirty"*) ;;
        *) return 0 ;;
    esac
    local alerted_ceo_flag
    alerted_ceo_flag=$(_alerted_ceo_path "$1")
    [ -f "$alerted_ceo_flag" ] && return 0   # already alerted #ceo this streak
    local streak msg
    streak=$(_streak_get "$1")
    local minutes=$((streak * 5))
    msg="[PROPOSE:elliot] DIRTY WORKTREE STALE CODE — $1 has had a dirty working tree for $streak consecutive auto-pull cycles (~${minutes}m). The polling loop is running STALE code that does not include recently-merged PRs. Resolve the dirty state immediately (stash or commit) so origin/main can ff-merge and the loop deploys current code. Per Dave verbatim ts ~1778631000."
    if [ -x "$RELAY" ] || [ -r "$RELAY" ]; then
        /home/elliotbot/clawd/venv/bin/python3 "$RELAY" -g "$msg" -c ceo >/dev/null 2>&1 || true
    fi
    touch "$alerted_ceo_flag" 2>/dev/null || true
}

# KEI-34 v2 Addition 2 threshold: 2 consecutive dirty skips is enough.
# Dirty worktree = stale code, separate concern from the 3-cycle generic alert.
DIRTY_WORKTREE_CEO_THRESHOLD="${AGENCY_OS_DIRTY_WORKTREE_CEO_THRESHOLD:-2}"

_handle_skip() {
    # $1 = worktree, $2 = reason
    _streak_inc "$1"
    local streak
    streak=$(_streak_get "$1")
    # Dirty-worktree-specific #ceo escalation at streak >= 2 (Addition 2).
    if [ "$streak" -ge "$DIRTY_WORKTREE_CEO_THRESHOLD" ]; then
        _emit_dirty_worktree_ceo_alert "$1" "$2"
    fi
    if [ "$streak" -ge "$SKIP_ALERT_THRESHOLD" ]; then
        _emit_alert "$1" "$2"
    fi
}

for wt in "${WORKTREES[@]}"; do
    if [ ! -d "$wt/.git" ] && [ ! -f "$wt/.git" ]; then
        echo "SKIP $wt: not a git worktree"
        _handle_skip "$wt" "not a git worktree"
        continue
    fi
    branch=$(git -C "$wt" symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED")
    if [ "$branch" != "main" ]; then
        echo "SKIP $wt: on $branch (only auto-pull when on main)"
        _handle_skip "$wt" "on $branch (only auto-pull when on main)"
        continue
    fi
    if [ -n "$(git -C "$wt" status --porcelain)" ]; then
        echo "SKIP $wt: working tree dirty"
        _handle_skip "$wt" "working tree dirty"
        continue
    fi
    git_dir=$(git -C "$wt" rev-parse --git-dir)
    if [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ] \
       || [ -f "$git_dir/MERGE_HEAD" ] || [ -f "$git_dir/CHERRY_PICK_HEAD" ]; then
        echo "SKIP $wt: rebase/merge/cherry-pick in progress"
        _handle_skip "$wt" "rebase/merge/cherry-pick in progress"
        continue
    fi
    if ! git -C "$wt" fetch --quiet origin main 2>&1; then
        echo "FAIL $wt: fetch origin main failed"
        _streak_reset "$wt"
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
        _streak_reset "$wt"
    else
        echo "FAIL $wt: ff-only merge refused (history diverged?)"
        _streak_reset "$wt"
    fi
done
