#!/usr/bin/env bash
# Stop-hook companion: auto-emit [READY:<callsign>] marker if the agent's final
# response did not already include one. Mechanical replacement for the
# discipline-dependent "agent remembers to type [READY:<callsign>]" pattern.
#
# Layer-3-at-conversation-end fix per Dave directive ts ~1778589925 + Scout
# design at docs/wave2/stop_hook_design.md (commit 6b4e6904).
#
# Ordering: registered in .claude/settings.json AFTER governance_router.py
# (which consumes stdin and saves to /tmp/.stop_event_payload.json) AND AFTER
# stop_relay_hook.sh (same temp-file fallback consumer). Read order MUST come
# after both — this script uses the same fallback path.
#
# Fail-open everywhere: exit 0 on every path. Relay failure must never block
# the assistant turn from ending.

set -u

# 1. Resolve callsign — CALLSIGN env preferred; IDENTITY.md fallback.
CALLSIGN="${CALLSIGN:-}"
if [[ -z "$CALLSIGN" && -r ./IDENTITY.md ]]; then
    CALLSIGN="$(grep -m1 -oE '\*\*CALLSIGN:\*\* [A-Za-z]+' ./IDENTITY.md 2>/dev/null \
        | awk '{print $NF}' | tr '[:upper:]' '[:lower:]')"
fi
CALLSIGN="${CALLSIGN:-unknown}"

# 2. Skip sub-agents — parent surfaces results; double-emit otherwise.
if [[ -n "${CLAUDE_AGENT_ID:-}" ]]; then
    exit 0
fi

# 3. Read Stop payload — stdin first; fallback to temp-file written by
#    governance_router.py upstream in the Stop chain. Path is overridable via
#    STOP_EVENT_PAYLOAD_TEMP_PATH (tests use this; prod defaults to the
#    canonical /tmp path that governance_router writes).
TEMP_PATH="${STOP_EVENT_PAYLOAD_TEMP_PATH:-/tmp/.stop_event_payload.json}"  # NOSONAR — canonical Stop-hook payload location set by upstream governance_router.py, not user-supplied
PAYLOAD="$(cat 2>/dev/null || true)"
if [[ -z "$PAYLOAD" && -f "$TEMP_PATH" ]]; then
    PAYLOAD="$(cat "$TEMP_PATH" 2>/dev/null || true)"
fi
[[ -z "$PAYLOAD" ]] && exit 0

# 4. Extract final assistant response body. Keys discovered empirically per
#    stop_relay_hook.sh:43-50 — not in public Claude Code docs.
BODY=""
if command -v jq >/dev/null 2>&1; then
    BODY="$(printf '%s' "$PAYLOAD" | jq -r \
        '.last_assistant_message // .message.content // .response // .text // ""' \
        2>/dev/null || true)"
fi

# 5. De-dup — if body already contains [READY:<callsign>] (case-insensitive)
#    OR with bracketed callsign prefix, skip emit.
SHOUTY="$(echo "$CALLSIGN" | tr '[:lower:]' '[:upper:]')"
if echo "$BODY" | grep -qi -E "\[READY:(${CALLSIGN}|${SHOUTY})\]"; then
    exit 0
fi

# 6. Emit via slack relay. Fail-open: || true swallows any error.
if command -v tg >/dev/null 2>&1; then
    tg "[READY:${CALLSIGN}]" >/dev/null 2>&1 || true
else
    /home/elliotbot/clawd/venv/bin/python3 \
        /home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py \
        -g "[READY:${CALLSIGN}]" >/dev/null 2>&1 || true
fi

exit 0
