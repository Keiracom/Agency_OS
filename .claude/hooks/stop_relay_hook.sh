#!/usr/bin/env bash
# Change 1 — Stop hook auto-relay.
#
# Fires on every Stop event (assistant turn completion). Writes the
# assistant's final response to the outbox for Telegram delivery.
#
# Scope rules:
#   - Final response text only (not internal reasoning/tool output)
#   - Top-level session only (sub-agents don't relay)
#   - Fail-open: relay failure never blocks the turn
#   - Writes to outbox (existing watcher handles delivery + timeout)
#   - De-dup: skips if identical content was written to outbox in last 30s
#
# stdin: Claude Code Stop event JSON
#   { "message": { "content": "..." }, "reason": "..." }

set -u

CALLSIGN="${CALLSIGN:-}"
if [[ -z "$CALLSIGN" && -r ./IDENTITY.md ]]; then
    CALLSIGN="$(grep -m1 -oE '\[(ATLAS|ELLIOT|AIDEN|ORION|SCOUT|MAX)\]' ./IDENTITY.md 2>/dev/null \
        | tr -d '[]' | tr '[:upper:]' '[:lower:]')"
fi
CALLSIGN="${CALLSIGN:-elliot}"

# Sub-agents: skip relay (they return results to parent)
if [[ -n "${CLAUDE_AGENT_ID:-}" ]]; then
    exit 0
fi

RELAY_DIR="/tmp/telegram-relay-${CALLSIGN}"
OUTBOX="${RELAY_DIR}/outbox"
mkdir -p "$OUTBOX" 2>/dev/null || true

# Read Stop event from stdin; fall back to temp file if stdin was consumed
# by a prior hook in the same chain (governance_router.py saves it)
PAYLOAD="$(cat || true)"
if [[ -z "$PAYLOAD" && -f /tmp/.stop_event_payload.json ]]; then
    PAYLOAD="$(cat /tmp/.stop_event_payload.json 2>/dev/null || true)"
fi
if [[ -z "$PAYLOAD" ]]; then
    exit 0
fi

# Extract final response text.
# FIX 3 DOCUMENTATION: Claude Code Stop event payload contains ONLY the final
# assistant response in .message.content — NOT internal reasoning, tool calls,
# or planning text. This is per Claude Code hook spec:
# https://docs.anthropic.com/en/docs/claude-code/hooks#hook-types
# The Stop event fires after the assistant's turn completes. The "message"
# field contains the rendered response that would display in the terminal.
# Internal reasoning (thinking blocks) is never included in this field.
TEXT=""
if command -v jq >/dev/null 2>&1; then
    TEXT="$(printf '%s' "$PAYLOAD" | jq -r '.last_assistant_message // .message.content // .response // .text // ""' 2>/dev/null || echo "")"
fi

# Skip empty responses
if [[ -z "$TEXT" || ${#TEXT} -lt 3 ]]; then
    exit 0
fi

# De-dup: check if identical content was written to outbox in last 30s
HASH="$(printf '%s' "$TEXT" | md5sum | cut -c1-8)"
DEDUP_MARKER="/tmp/.relay_dedup_${CALLSIGN}_${HASH}"
if [[ -f "$DEDUP_MARKER" ]]; then
    MARKER_AGE=$(( $(date +%s) - $(stat -c %Y "$DEDUP_MARKER" 2>/dev/null || echo 0) ))
    if [[ $MARKER_AGE -lt 30 ]]; then
        # Same content relayed within 30s — skip (agent already called tg manually)
        exit 0
    fi
fi

# FIX 1: Determine destination chat_id from last_chat_id state file
# (not hardcoded group — prevents DM responses leaking to group)
GROUP_CHAT_ID="-1003926592540"
LAST_CHAT_FILE="${RELAY_DIR}/last_chat_id"
DEST_CHAT_ID="$GROUP_CHAT_ID"  # fallback to group

if [[ -f "$LAST_CHAT_FILE" ]]; then
    LAST_CHAT="$(cat "$LAST_CHAT_FILE" 2>/dev/null | tr -d '[:space:]')"
    if [[ -n "$LAST_CHAT" ]]; then
        DEST_CHAT_ID="$LAST_CHAT"
    fi
fi

# Write to outbox (existing watcher delivers to TG)
TS="$(date -u +%Y%m%d_%H%M%S)"
RAND="$(head -c4 /dev/urandom | od -An -tx4 | tr -d ' ')"
FNAME="${TS}_${RAND}.json"

# Truncate if too long for TG (4096 char limit)
if [[ ${#TEXT} -gt 4000 ]]; then
    TEXT="${TEXT:0:3990}... [truncated]"
fi

# Tag with callsign prefix
TAGGED="[${CALLSIGN^^}] ${TEXT}"

cat > "${OUTBOX}/${FNAME}" << ENDJSON
{
    "type": "text",
    "chat_id": ${DEST_CHAT_ID},
    "text": $(printf '%s' "$TAGGED" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '"%s"' "$TAGGED")
}
ENDJSON

# Phase 1b dual-write: also push to Redis queue (fail-open)
python3 -c "
import json, os, sys
try:
    import redis
    url = os.environ.get('REDIS_URL', '')
    if not url:
        sys.exit(0)
    r = redis.Redis.from_url(url, decode_responses=True)
    callsign = '${CALLSIGN}'.lower()
    payload = json.dumps({
        'type': 'text',
        'chat_id': ${DEST_CHAT_ID},
        'text': json.loads(sys.stdin.read())
    })
    r.lpush(f'relay:outbox:{callsign}', payload)
except Exception:
    pass  # fail-open: Redis failure never blocks relay
" <<< "$(printf '%s' "$TAGGED" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))' 2>/dev/null)" 2>/dev/null || true

# Write de-dup marker
touch "$DEDUP_MARKER" 2>/dev/null || true

exit 0
