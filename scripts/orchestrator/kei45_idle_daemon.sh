#!/usr/bin/env bash
# KEI-45 Phase A Component 6 — idle daemon fallback for dead Realtime subscription.
#
# Per ratified architecture (Round-3 consensus ts ~1778733900 + Dave ratify
# ts ~1778735200): agents subscribe to Supabase Realtime on session start +
# receive task-event payloads instantly. If a subscription dies silently
# (websocket drop without reconnect, kernel network blip, Supabase Realtime
# brown-out), an agent could remain idle while available work exists.
#
# This daemon polls every 15 minutes (15-min ceiling per Dave verbatim spec)
# and injects bd ready into any agent's tmux pane whose last-Slack-post age
# exceeds the threshold AND public.tasks has available work. KEI-43 systemd
# auto-restart handles agent-process death; this daemon handles
# subscription-died-but-process-alive.
#
# NOT a primary mechanism — Realtime + KEI-63 bd-complete-hook are primary.
# Fires only on subscription-died edge case; if it ever fires under normal
# operation, the Realtime subscription is broken and needs investigation.
#
# Exit codes:
#   0 — daemon cycle completed (no work injected OR work injected)
#   2 — operator misconfig (PROJECT_ID env missing, jq missing, etc.)
#   3 — Supabase query failed (network / auth — retry next tick)

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID="${SUPABASE_PROJECT_ID:-jatzvazlbusedwsnqxzr}"
LAST_POST_STATE="${AGENCY_OS_LAST_POST_STATE:-$HOME/.local/state/agency-os/callsign-last-post.json}"
IDLE_THRESHOLD_MIN="${KEI45_IDLE_THRESHOLD_MIN:-15}"
LOG_FILE="${KEI45_DAEMON_LOG:-/tmp/kei45_idle_daemon.log}"
DRY_RUN="${KEI45_DRY_RUN:-0}"

# Canonical callsign → tmux session map. Mirrors elliot_polling_loop.py:111
# CALLSIGN_TO_TMUX. Update in lockstep if that source changes.
declare -A CALLSIGN_TO_TMUX=(
    [elliot]=elliottbot
    [aiden]=aiden
    [max]=maxbot
    [atlas]=atlas
    [orion]=orion
    [scout]=scout
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { printf '%s [kei45-idle-daemon] %s\n' "$(ts)" "$*" >>"$LOG_FILE"; }

require_cmd() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1 || {
        log "ERROR: required command missing: $cmd"
        exit 2
    }
}

# Return 0 if Supabase reports >=1 task with status='available', else 1.
tasks_available_count() {
    local mcp_bridge="${AGENCY_OS_MCP_BRIDGE:-/home/elliotbot/clawd/skills/mcp-bridge}"
    local query='{"project_id":"'"$PROJECT_ID"'","query":"SELECT COUNT(*) AS n FROM tasks WHERE status = '\''available'\''"}'
    local response
    if ! response=$(cd "$mcp_bridge" && node scripts/mcp-bridge.js call supabase execute_sql "$query" 2>>"$LOG_FILE"); then
        log "WARN: Supabase query failed; assuming no available work"
        return 1
    fi
    # Parse "n" from the response — defensive against MCP wrapping.
    local n
    n=$(printf '%s' "$response" | grep -oE '"n":\s*[0-9]+' | head -1 | grep -oE '[0-9]+' || true)
    [[ "${n:-0}" -gt 0 ]]
}

# Return age in minutes since callsign's last Slack post, or 99999 if unknown.
last_post_age_minutes() {
    local callsign="$1"
    [[ -r "$LAST_POST_STATE" ]] || {
        echo 99999
        return
    }
    local last_iso
    last_iso=$(jq -r --arg cs "$callsign" '.[$cs] // ""' "$LAST_POST_STATE" 2>>"$LOG_FILE")
    [[ -n "$last_iso" ]] || {
        echo 99999
        return
    }
    local now_epoch last_epoch delta_min
    now_epoch=$(date -u +%s)
    last_epoch=$(date -u -d "$last_iso" +%s 2>/dev/null || echo 0)
    [[ "$last_epoch" -gt 0 ]] || {
        echo 99999
        return
    }
    delta_min=$(((now_epoch - last_epoch) / 60))
    echo "$delta_min"
}

inject_bd_ready_into_pane() {
    local callsign="$1"
    local tmux_session="${CALLSIGN_TO_TMUX[$callsign]:-}"
    [[ -n "$tmux_session" ]] || {
        log "WARN: no tmux session mapping for $callsign; skipping"
        return
    }
    if ! tmux has-session -t "$tmux_session" 2>/dev/null; then
        log "WARN: tmux session $tmux_session not running; skipping (KEI-43 systemd should restart)"
        return
    fi
    log "INJECT $callsign (tmux=$tmux_session, idle exceeds ${IDLE_THRESHOLD_MIN}m, tasks available)"
    if [[ "$DRY_RUN" == "1" ]]; then
        log "DRY_RUN — would have injected bd ready into $tmux_session"
        return
    fi
    tmux send-keys -t "$tmux_session" "bd ready  # KEI-45 idle-daemon fallback fire $(ts)" Enter
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

require_cmd jq
require_cmd tmux
require_cmd node

mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
log "tick threshold=${IDLE_THRESHOLD_MIN}m dry_run=$DRY_RUN"

if ! tasks_available_count; then
    log "no available work in tasks table; nothing to inject"
    exit 0
fi

for callsign in "${!CALLSIGN_TO_TMUX[@]}"; do
    age=$(last_post_age_minutes "$callsign")
    if [[ "$age" -ge "$IDLE_THRESHOLD_MIN" ]]; then
        inject_bd_ready_into_pane "$callsign"
    fi
done

log "tick complete"
exit 0
