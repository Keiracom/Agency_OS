#!/usr/bin/env bash
# systemd_agent_supervisor.sh — ExecStart wrapper for *-agent.service units (KEI-43).
#
# Idempotently ensures a tmux session is running the agent_session_launcher for
# the given callsign, then blocks until that session terminates. Exits non-zero
# on session death so systemd Restart=on-failure brings the agent back.
#
# Usage:
#     scripts/systemd_agent_supervisor.sh <callsign> <tmux-session-name> <worktree-path>
#
# Canonical map (must stay in sync with scripts/orchestrator/elliot_polling_loop.py
# CALLSIGN_TO_TMUX):
#     elliot  -> elliottbot  -> /home/elliotbot/clawd/Agency_OS
#     aiden   -> aiden       -> /home/elliotbot/clawd/Agency_OS-aiden
#     max     -> maxbot      -> /home/elliotbot/clawd/Agency_OS-max
#     atlas   -> atlas       -> /home/elliotbot/clawd/Agency_OS-atlas
#     orion   -> orion       -> /home/elliotbot/clawd/Agency_OS-orion
#     scout   -> scout       -> /home/elliotbot/clawd/Agency_OS-scout

set -euo pipefail

callsign="${1:?usage: systemd_agent_supervisor.sh <callsign> <tmux-session> <worktree>}"
tmux_session="${2:?missing tmux session name}"
worktree="${3:?missing worktree path}"
poll_seconds="${SUPERVISOR_POLL_SECONDS:-30}"

if [[ ! -d "$worktree" ]]; then
    echo "[supervisor] worktree missing: $worktree" >&2
    exit 2
fi

launcher="$worktree/scripts/agent_session_launcher.sh"
if [[ ! -x "$launcher" ]]; then
    echo "[supervisor] launcher missing or not executable: $launcher" >&2
    exit 2
fi

if ! command -v tmux >/dev/null 2>&1; then
    echo "[supervisor] tmux not on PATH" >&2
    exit 2
fi

if ! tmux has-session -t "$tmux_session" 2>/dev/null; then
    echo "[supervisor] spawning tmux session=$tmux_session callsign=$callsign worktree=$worktree"
    tmux new-session -d -s "$tmux_session" -c "$worktree" \
        "exec '$launcher' '$callsign'"
else
    echo "[supervisor] tmux session=$tmux_session already alive — attaching watcher"
fi

while tmux has-session -t "$tmux_session" 2>/dev/null; do
    sleep "$poll_seconds"
done

echo "[supervisor] tmux session=$tmux_session terminated — exiting non-zero for systemd restart" >&2
exit 1
