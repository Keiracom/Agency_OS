#!/usr/bin/env bash
# agent_keepalive.sh — ExecStart wrapper for *-agent.service units (KEI-94).
#
# Type=simple + Restart=always keep-alive for agent claude sessions. Each unit
# blocks on this script until the tmux session terminates; systemd then
# restarts the unit, respawning the session.
#
# Locks worktree (-c) AND callsign (send-keys export) inside the tmux session
# itself, bypassing the tmux server env-inheritance trap that produced phantom
# Elliots in the fleet on 2026-05-16 (Dave directive KEI-94).
#
# Usage:
#     agent_keepalive.sh <tmux_session> <callsign> <worktree>
#
# Example unit ExecStart:
#     ExecStart=/home/elliotbot/clawd/Agency_OS/scripts/agent_keepalive.sh atlas atlas /home/elliotbot/clawd/Agency_OS-atlas
#
# Env (optional):
#     KEEPALIVE_POLL_SECONDS — sleep between has-session checks (default 10)
#     KEEPALIVE_DRY         — print the resolved tmux/send-keys plan and exit 0

set -euo pipefail

session="${1:?usage: agent_keepalive.sh <tmux_session> <callsign> <worktree>}"
callsign="${2:?missing callsign}"
worktree="${3:?missing worktree}"
poll_seconds="${KEEPALIVE_POLL_SECONDS:-10}"

if [[ ! -d "$worktree" ]]; then
    echo "[keepalive] worktree missing: $worktree" >&2
    exit 2
fi

if ! command -v tmux >/dev/null 2>&1; then
    echo "[keepalive] tmux not on PATH" >&2
    exit 2
fi

claude_cmd="export CALLSIGN='$callsign' && cd '$worktree' && exec claude --dangerously-skip-permissions"

if [[ -n "${KEEPALIVE_DRY:-}" ]]; then
    echo "[keepalive] would: tmux new-session -d -s '$session' -c '$worktree'"
    echo "[keepalive] would: tmux send-keys -t '$session' \"$claude_cmd\" Enter"
    exit 0
fi

if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "[keepalive] spawning tmux session=$session callsign=$callsign worktree=$worktree"
    tmux new-session -d -s "$session" -c "$worktree"
    tmux send-keys -t "$session" "$claude_cmd" Enter
else
    echo "[keepalive] tmux session=$session already alive — attaching watcher"
fi

while tmux has-session -t "$session" 2>/dev/null; do
    sleep "$poll_seconds"
done

echo "[keepalive] tmux session=$session terminated — exiting non-zero for systemd restart" >&2
exit 1
