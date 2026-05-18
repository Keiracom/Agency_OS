#!/usr/bin/env bash
# pre_task_signal.sh — KEI-39 pre-execution claim hook.
#
# Emits a `state=starting` event to NATS subject
# keiracom.agent.status.<callsign> before non-trivial Claude Code tool calls
# fire (Bash | Edit | Write | NotebookEdit). Closes the duplicate-dispatch
# class of incident (Streams 3+4 silent transition, 2026-05-13) where subtask
# transitions had no machine-readable signal — supervisors saw an idle agent
# while the agent was mid-tool-call.
#
# Triggered by .claude/settings.json PreToolUse hook chain. Receives the
# standard PreToolUse JSON on stdin: {session_id, tool_name, tool_input, …}.
#
# Dedup: 30s rolling window per (callsign, task_ref). Two tool calls inside
# the window emit only once — keeps the supervisor stream signal-not-spam
# while still flagging every distinct task transition.
#
# task_ref resolution order:
#   1. $TASK_REF env (agent-supplied, e.g. "KEI-39")
#   2. .beads/.active_claim (written by `bd update --claim` integration when
#      present — falls through silently if absent)
#   3. literal "unspecified"
#
# Fail-open everywhere: missing CALLSIGN, missing jq, NATS down, dedup dir
# unwritable — all return exit 0. Hook MUST NEVER block a tool call.

set -u

CALLSIGN="${CALLSIGN:-}"
[[ -z "$CALLSIGN" ]] && exit 0
CALLSIGN_LOWER="$(echo "$CALLSIGN" | tr '[:upper:]' '[:lower:]')"

PAYLOAD="$(cat 2>/dev/null || true)"
TOOL=""
if command -v jq >/dev/null 2>&1; then
    TOOL="$(printf '%s' "$PAYLOAD" | jq -r '.tool_name // ""' 2>/dev/null || true)"
fi

case "$TOOL" in
    Bash|Edit|Write|NotebookEdit) ;;
    *) exit 0 ;;
esac

TASK_REF="${TASK_REF:-}"
if [[ -z "$TASK_REF" && -r .beads/.active_claim ]]; then
    TASK_REF="$(head -1 .beads/.active_claim 2>/dev/null | tr -d '[:space:]')"
fi
TASK_REF="${TASK_REF:-unspecified}"

DEDUP_DIR="${PRE_TASK_SIGNAL_DEDUP_DIR:-/tmp/agency-os-starting}"
mkdir -p "$DEDUP_DIR" 2>/dev/null || exit 0
TASK_KEY="$(printf '%s' "$TASK_REF" | tr -c 'a-zA-Z0-9_-' '_')"
DEDUP_FILE="${DEDUP_DIR}/${CALLSIGN_LOWER}_${TASK_KEY}"
NOW=$(date +%s)
DEDUP_WINDOW="${PRE_TASK_SIGNAL_DEDUP_SECONDS:-30}"
if [[ -r "$DEDUP_FILE" ]]; then
    LAST=$(cat "$DEDUP_FILE" 2>/dev/null || echo 0)
    if (( NOW - LAST < DEDUP_WINDOW )); then
        exit 0
    fi
fi
echo "$NOW" > "$DEDUP_FILE" 2>/dev/null || true

NATS_BIN="${NATS_BIN:-$(command -v nats || true)}"
if [[ -n "$NATS_BIN" ]]; then
    EVENT_JSON="$(printf '{"state":"starting","callsign":"%s","task_ref":"%s","tool":"%s","ts":%s}' \
        "$CALLSIGN_LOWER" "$TASK_REF" "$TOOL" "$NOW")"
    "$NATS_BIN" pub "keiracom.agent.status.${CALLSIGN_LOWER}" "$EVENT_JSON" \
        >/dev/null 2>&1 || true
fi

exit 0
