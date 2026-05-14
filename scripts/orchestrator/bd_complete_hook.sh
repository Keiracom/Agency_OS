#!/usr/bin/env bash
# bd_complete_hook.sh — KEI-63: post-close hook wrapper for bd close.
#
# Usage:
#   scripts/orchestrator/bd_complete_hook.sh [bd close args...]
#
# What it does:
#   1. Runs `bd close "$@"` (marks task done — bd's own logic).
#   2. If bd close succeeds, fires the post-close hook:
#      a. Runs `bd ready --claim --json` to atomically claim the next task.
#      b. If a task is claimed: injects `bd claim <id>` into the agent's
#         canonical tmux pane so the agent transitions directly to new work
#         within ~2 seconds. Zero idle gap. No manual dispatch.
#      c. If no task is available: logs idle:no_work to the structured log.
#   3. Always exits 0 (hook failure never blocks bd from completing).
#
# Integration path:
#   Agents call this script instead of `bd close` directly. Works with the
#   existing CALLSIGN_TO_TMUX mapping from elliot_polling_loop.py.
#
# Callsign resolution order (first wins):
#   1. $CALLSIGN env var
#   2. IDENTITY.md in the worktree root (field: CALLSIGN: <name>)
#   3. git user.name (fallback — less reliable)
#
# KEI-63 spec: Dave verbatim #ceo ts ~1778728600.
# Linear: https://linear.app/keiracom/issue/KEI-66
# bd: Agency_OS-3nri4k

set -euo pipefail

# ── config ───────────────────────────────────────────────────────────────────

BD_BIN="${AGENCY_OS_BD_BIN:-${HOME}/.local/bin/bd}"
LOG_FILE="${AGENCY_OS_BD_HOOK_LOG:-/home/elliotbot/clawd/logs/kei63-completion-hook.log}"
# Worktree root: default is the repo root adjacent to this script.
WORKTREE_ROOT="${AGENCY_OS_WORKTREE_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Canonical callsign → tmux session map (mirrors CALLSIGN_TO_TMUX in
# elliot_polling_loop.py and auto_session_recovery.py — single source-of-truth
# is the Python constant; this map must stay in sync with it).
declare -A CALLSIGN_TO_TMUX=(
    ["elliot"]="elliottbot"
    ["aiden"]="aiden"
    ["max"]="maxbot"
    ["atlas"]="atlas"
    ["orion"]="orion"
    ["scout"]="scout"
)

# ── helpers ───────────────────────────────────────────────────────────────────

_log() {
    local level="$1"; shift
    printf '%s [%s] bd_complete_hook: %s\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$*" \
        | tee -a "$LOG_FILE" >&2
}

_resolve_callsign() {
    # 1. Env var
    if [[ -n "${CALLSIGN:-}" ]]; then
        printf '%s' "$CALLSIGN"
        return
    fi
    # 2. IDENTITY.md in worktree root
    local identity_file="${WORKTREE_ROOT}/IDENTITY.md"
    if [[ -f "$identity_file" ]]; then
        local cs
        cs=$(grep -m1 '^\*\*CALLSIGN:\*\*' "$identity_file" | sed 's/.*\*\*CALLSIGN:\*\*[[:space:]]*//' | tr -d '[:space:]')
        if [[ -n "$cs" ]]; then
            printf '%s' "${cs,,}"  # lowercase
            return
        fi
    fi
    # 3. git user.name fallback
    git config --get user.name 2>/dev/null | tr '[:upper:]' '[:lower:]' || true
}

_resolve_tmux_session() {
    local callsign="$1"
    echo "${CALLSIGN_TO_TMUX[$callsign]:-}"
}

_inject_next_task() {
    local callsign="$1"
    local session="$2"

    # Atomically claim the next available task (KEI-22 SKIP LOCKED semantics
    # live inside bd claim — the hook just calls it and reads result).
    local claim_out
    claim_out=$("$BD_BIN" ready --claim --json 2>/dev/null) || true

    if [[ -z "$claim_out" ]] || [[ "$claim_out" == "null" ]] || [[ "$claim_out" == "[]" ]]; then
        _log "INFO" "callsign=${callsign} session=${session} idle:no_work — no unblocked tasks available"
        printf '%s {"event":"idle_no_work","callsign":"%s","ts":"%s"}\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$callsign" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            >> "$LOG_FILE"
        return
    fi

    # Extract the claimed task id from JSON (handles both object and single-element array).
    local task_id
    task_id=$(printf '%s' "$claim_out" | python3 -c "
import json, sys
data = json.load(sys.stdin)
if isinstance(data, list) and data:
    data = data[0]
print(data.get('id','') if isinstance(data, dict) else '')
" 2>/dev/null) || true

    if [[ -z "$task_id" ]]; then
        _log "WARN" "callsign=${callsign} bd ready --claim returned unparseable JSON: ${claim_out:0:120}"
        return
    fi

    _log "INFO" "callsign=${callsign} session=${session} injecting next task: ${task_id}"
    printf '%s {"event":"task_injected","callsign":"%s","task_id":"%s","ts":"%s"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$callsign" "$task_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        >> "$LOG_FILE"

    # Check the tmux session exists before injecting.
    if ! tmux has-session -t "$session" 2>/dev/null; then
        _log "WARN" "tmux session '${session}' not found — cannot inject task ${task_id}"
        return
    fi

    # Inject the claim command into the agent's pane. The agent reads it and
    # begins work. SKIP LOCKED in bd claim ensures only one agent wins on
    # simultaneous completions.
    tmux send-keys -t "${session}:0" "bd claim ${task_id}" Enter
    _log "INFO" "callsign=${callsign} injected 'bd claim ${task_id}' into tmux session ${session}"
}

# ── main ─────────────────────────────────────────────────────────────────────

# Step 1: run bd close with all original args. Must succeed before hook fires.
"$BD_BIN" close "$@"
BD_EXIT=$?

if [[ $BD_EXIT -ne 0 ]]; then
    _log "ERROR" "bd close exited ${BD_EXIT} — skipping post-close hook"
    exit $BD_EXIT
fi

# Step 2: fire the hook (non-blocking on failure — always exit 0).
{
    callsign=$(_resolve_callsign)
    if [[ -z "$callsign" ]]; then
        _log "WARN" "could not resolve callsign — skipping next-task injection"
        exit 0
    fi

    session=$(_resolve_tmux_session "$callsign")
    if [[ -z "$session" ]]; then
        _log "WARN" "callsign '${callsign}' not in CALLSIGN_TO_TMUX — skipping injection"
        exit 0
    fi

    _inject_next_task "$callsign" "$session"
} || _log "WARN" "post-close hook encountered an error (bd close already succeeded — task is closed)"

exit 0
