#!/usr/bin/env bash
# agent_keepalive.sh — ExecStart wrapper for *-agent.service units (KEI-94 + KEI-140).
#
# BOUNDED-SPAWN DISCIPLINE — every keepalive respawn starts from zero by
# default; no Claude conversation-context carryover. Dave directive 2026-05-27
# governance fix: keepalive had autonomous restart authority + agents
# respawned with accumulated context, violating the bounded-spawn principle.
# State carryover now requires explicit --preserve-context <justification>
# override + logged event to /tmp/keepalive_override_log.jsonl.
#
# Type=simple + Restart=always keep-alive for agent claude sessions. Each unit
# blocks on this script until the tmux session terminates; systemd then
# restarts the unit, respawning the session.
#
# Locks worktree (-c) AND callsign (send-keys export) inside the tmux session
# itself, bypassing the tmux server env-inheritance trap that produced phantom
# Elliots in the fleet on 2026-05-16 (Dave directive KEI-94).
#
# KEI-140 — supervised restart:
#   Previous behaviour: tmux + claude persisted across `systemctl restart` because
#   the keepalive was killed but the tmux session it spawned was not. Restart was
#   a no-op for claude — operator's "reset all" did nothing visible.
#   Fix: install a SIGTERM trap that kills the pane's leader PID (which IS the
#   claude process, since the spawn line uses `exec claude`). Killing the pane
#   leader terminates the pane → terminates the tmux session → keepalive's
#   `tmux has-session` loop drops out → keepalive exits → systemd restarts the
#   unit → fresh tmux + fresh claude. Operator sees claude's banner.
#
#   Defense-in-depth: the poll loop also verifies the pane leader's /proc/<pid>/comm
#   contains 'claude'. If a stranded shell ever ended up holding the pane (could
#   happen if `exec claude` failed mid-line), re-issue the claude_cmd via send-keys
#   so the pane recovers.
#
# Usage:
#     agent_keepalive.sh <tmux_session> <callsign> <worktree> [--preserve-context "<justification>"]
#
# Default (per Dave 2026-05-27): claude respawns FRESH on every restart.
# Override: --preserve-context "<reason>" → uses `claude --continue` to
# resume prior conversation; emits one JSONL event per spawn to
# /tmp/keepalive_override_log.jsonl with timestamp + callsign + justification.
#
# Example unit ExecStart:
#     ExecStart=/home/elliotbot/clawd/Agency_OS/scripts/agent_keepalive.sh atlas atlas /home/elliotbot/clawd/Agency_OS-atlas
#
# Env (optional):
#     KEEPALIVE_POLL_SECONDS — sleep between has-session checks (default 10)
#     KEEPALIVE_DRY         — print the resolved tmux/send-keys plan and exit 0
#     KEEPALIVE_OVERRIDE_LOG — override JSONL log path (default /tmp/keepalive_override_log.jsonl)

set -euo pipefail

session="${1:?usage: agent_keepalive.sh <tmux_session> <callsign> <worktree> [--preserve-context <justification>]}"
callsign="${2:?missing callsign}"
worktree="${3:?missing worktree}"
poll_seconds="${KEEPALIVE_POLL_SECONDS:-10}"
override_log="${KEEPALIVE_OVERRIDE_LOG:-/tmp/keepalive_override_log.jsonl}"

# Dave 2026-05-27 bounded-spawn discipline — fresh context by default.
# --preserve-context "<justification>" opts INTO state carryover (claude
# --continue). Justification is required + non-empty + persisted to JSONL.
preserve_context=""
preserve_justification=""
shift 3 || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --preserve-context)
            preserve_context="1"
            preserve_justification="${2:-}"
            if [[ -z "$preserve_justification" ]]; then
                echo "[keepalive] --preserve-context requires a non-empty justification string" >&2
                exit 2
            fi
            shift 2
            ;;
        *)
            echo "[keepalive] unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

if [[ ! -d "$worktree" ]]; then
    echo "[keepalive] worktree missing: $worktree" >&2
    exit 2
fi

if ! command -v tmux >/dev/null 2>&1; then
    echo "[keepalive] tmux not on PATH" >&2
    exit 2
fi

# Dave 2026-05-27 bounded-spawn — fresh context default ─────────────────────
# Default claude invocation: NO --continue, NO --resume. Every respawn = a
# new bounded task with zero conversation-context carryover from the prior
# session. Each respawn re-reads CLAUDE.md + IDENTITY.md + session-start
# hooks fresh — the only state that survives is on-disk (git, filesystem,
# ceo_memory). This is the canonical bounded-spawn invariant.
#
# --preserve-context override: caller explicitly opts INTO state carryover
# (claude --continue resumes the last session UUID). One JSONL event written
# to $override_log per spawn cycle, carrying the justification + ts + callsign
# so reviewers can audit when context carried forward + why.
if [[ -n "$preserve_context" ]]; then
    # Log the override BEFORE spawning so a crashed spawn still leaves a
    # trail. Append-only JSONL — one event per spawn.
    mkdir -p "$(dirname "$override_log")" 2>/dev/null || true
    override_event=$(printf '{"ts":"%s","callsign":"%s","session":"%s","worktree":"%s","justification":%s}' \
        "$(date -u +%FT%TZ)" "$callsign" "$session" "$worktree" \
        "$(printf '%s' "$preserve_justification" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")
    # Trailing newline appended via printf '%s\n' so $() command substitution
    # doesn't strip it — each event lands on its own JSONL line.
    printf '%s\n' "$override_event" >> "$override_log" 2>/dev/null || true
    echo "[keepalive] --preserve-context override active; justification logged to $override_log" >&2
    claude_invocation="claude --continue --dangerously-skip-permissions"
else
    claude_invocation="claude --dangerously-skip-permissions"
fi

# KEI-94 — in-pane respawn loop. The pane process is a `while true` shell;
# claude runs as its child. When claude exits (clean shutdown, /clear path,
# OOM, crash) the shell loops back, sleeps a moment to avoid a busy spawn
# storm if claude crashes immediately, then re-spawns claude in the same
# pane. The tmux session survives Claude exits — no full unit restart
# needed. systemd's Restart=always remains the outer safety net for cases
# where the wrapper itself dies.
claude_cmd="export CALLSIGN='$callsign' && cd '$worktree' && while true; do $claude_invocation; echo \"[keepalive] claude exited at \$(date -u +%FT%TZ), respawning in 2s\" >&2; sleep 2; done"

if [[ -n "${KEEPALIVE_DRY:-}" ]]; then
    echo "[keepalive] would: tmux new-session -d -s '$session' -c '$worktree'"
    echo "[keepalive] would: tmux send-keys -t '$session' \"$claude_cmd\" Enter"
    exit 0
fi

# KEI-140 — SIGTERM trap. systemd's `systemctl restart` sends SIGTERM to the
# keepalive process. By default this kills the keepalive but leaves the tmux
# session (and claude inside it) running, so the restart is invisible.
# The trap kills the pane's leader PID — which IS claude (we exec'd into it) —
# so the session unwinds: claude dies → pane dies → tmux session dies → next
# unit start spawns a fresh session + claude. Operator sees claude's banner.
_kill_claude_on_term() {
    echo "[keepalive] received SIGTERM/SIGINT — killing pane leader so restart respawns claude" >&2
    if tmux has-session -t "$session" 2>/dev/null; then
        local pane_pid
        pane_pid=$(tmux list-panes -t "$session" -F '#{pane_pid}' 2>/dev/null | head -1 || true)
        if [[ -n "$pane_pid" ]] && [[ -d "/proc/$pane_pid" ]]; then
            kill -TERM "$pane_pid" 2>/dev/null || true
            # Give claude a moment to clean up before the pane is reaped.
            sleep 1
        fi
    fi
    exit 0
}
trap _kill_claude_on_term TERM INT

# KEI-125 — systemd watchdog integration. Unit declares Type=notify +
# WatchdogSec=30s; we notify --ready once tmux is up, then ping
# WATCHDOG=1 in a background loop at half the watchdog interval so a
# missed ping or two is tolerated. If THIS script hangs (the tmux poll
# below stops issuing pings), systemd kills + restarts the unit → fresh
# tmux + claude. agent_failover_notify.sh then posts to #ceo.
_watchdog_loop() {
    while :; do
        systemd-notify WATCHDOG=1 2>/dev/null || true
        sleep 15
    done
}

if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "[keepalive] spawning tmux session=$session callsign=$callsign worktree=$worktree"
    tmux new-session -d -s "$session" -c "$worktree"
    tmux send-keys -t "$session" "$claude_cmd" Enter
else
    echo "[keepalive] tmux session=$session already alive — attaching watcher"
fi

# KEI-94 defense-in-depth: poll loop verifies that `claude` (or its in-pane
# respawn-loop shell) is alive inside the pane's process tree. The pane leader
# under the KEI-94 loop is bash (the `while true` wrapper); claude is bash's
# child. So we walk children of the pane leader and look for claude. If no
# claude child exists AND the pane leader itself isn't bash-running-the-loop
# (i.e. the pane has been hijacked by a stranded shell prompt), re-issue the
# claude_cmd via send-keys to recover. Cheap: one tmux + one pgrep per
# `poll_seconds`.
_pane_running_claude() {
    local pane_pid
    pane_pid=$(tmux list-panes -t "$session" -F '#{pane_pid}' 2>/dev/null | head -1 || true)
    [[ -n "$pane_pid" ]] || return 1
    [[ -d "/proc/$pane_pid" ]] || return 1
    # Walk the process tree under the pane leader. If claude appears anywhere,
    # we're healthy. (Looking at pane leader alone would miss the KEI-94
    # bash-loop-wrapping-claude topology.)
    if pgrep -f -P "$pane_pid" claude >/dev/null 2>&1; then
        return 0
    fi
    # Pane leader itself running claude (legacy `exec claude` topology) also
    # counts as healthy — supports gradual rollout.
    if [[ -r "/proc/$pane_pid/comm" ]] && grep -q claude "/proc/$pane_pid/comm" 2>/dev/null; then
        return 0
    fi
    return 1
}

# KEI-125: signal systemd we're ready (Type=notify requires this) + start
# the WATCHDOG ping loop in the background. The trap above kills $! on exit
# so the background loop doesn't outlive the keepalive.
systemd-notify --ready 2>/dev/null || true
_watchdog_loop &
_watchdog_pid=$!
# shellcheck disable=SC2064  # intentional $_watchdog_pid expansion at trap-set time
trap "kill ${_watchdog_pid} 2>/dev/null; _kill_claude_on_term" TERM INT

while tmux has-session -t "$session" 2>/dev/null; do
    if ! _pane_running_claude; then
        echo "[keepalive] pane leader is not claude — re-issuing claude_cmd" >&2
        tmux send-keys -t "$session" "$claude_cmd" Enter
    fi
    sleep "$poll_seconds"
done

# Tear down watchdog before exiting so the background pinger doesn't keep
# emitting WATCHDOG=1 after this script is gone (would race the unit-stop).
kill "${_watchdog_pid}" 2>/dev/null || true

echo "[keepalive] tmux session=$session terminated — exiting non-zero for systemd restart" >&2
exit 1
