#!/usr/bin/env bash
# Governance Phase 1 Track A — A1 Recorder hook
#
# PreToolUse hook. Fires on every tool call and writes one
# `tool_call` event row into public.governance_events via the Supabase
# MCP bridge. Always exits 0 — this hook is observational, never
# blocking. The MCP write runs in the background so the calling agent
# does not wait on the network round-trip.
#
# stdin format (Claude Code PreToolUse):
#   { "tool_name": "Edit", "tool_input": { "file_path": "...", ... }, ... }

set -u

LOG_DIR="${RECORDER_LOG_DIR:-/tmp/agency-os-recorder}"
mkdir -p "$LOG_DIR" 2>/dev/null || true

PAYLOAD="$(cat || true)"

# Resolve callsign: $CALLSIGN env wins; fall back to IDENTITY.md if
# the cwd has one; final fallback "unknown".
callsign="${CALLSIGN:-}"
if [[ -z "$callsign" && -r ./IDENTITY.md ]]; then
    callsign="$(grep -m1 -oE '\[(ATLAS|ELLIOT|AIDEN|ORION|SCOUT)\]' ./IDENTITY.md 2>/dev/null \
        | tr -d '[]' | tr '[:upper:]' '[:lower:]')"
fi
callsign="${callsign:-unknown}"

# Extract tool_name + file_path from PreToolUse payload (jq if present).
tool_name="unknown"
file_path=""
if command -v jq >/dev/null 2>&1 && [[ -n "$PAYLOAD" ]]; then
    tool_name="$(printf '%s' "$PAYLOAD" | jq -r '.tool_name // "unknown"' 2>/dev/null || echo unknown)"
    file_path="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // .tool_input.notebook_path // ""' 2>/dev/null || echo "")"
fi

directive_id="${DIRECTIVE_ID:-}"

# Append local audit line — survives even if Supabase write fails.
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\t%s\t%s\t%s\t%s\n' "$ts" "$callsign" "$tool_name" "$file_path" "$directive_id" \
    >>"$LOG_DIR/recorder.log" 2>/dev/null || true

# Background MCP insert — fire and forget.
MCP_BRIDGE="${MCP_BRIDGE_DIR:-/home/elliotbot/clawd/skills/mcp-bridge}"
if [[ -x "$MCP_BRIDGE/scripts/mcp-bridge.js" || -f "$MCP_BRIDGE/scripts/mcp-bridge.js" ]]; then
    # Build SQL — single-quote escape values via Postgres E'...' syntax.
    esc() { printf "%s" "$1" | sed "s/'/''/g"; }
    sql="INSERT INTO public.governance_events \
(callsign, event_type, tool_name, file_path, directive_id, event_data) \
VALUES ('$(esc "$callsign")', 'tool_call', '$(esc "$tool_name")', \
NULLIF('$(esc "$file_path")', ''), NULLIF('$(esc "$directive_id")', ''), \
'{\"hook\":\"recorder\"}'::jsonb);"
    args="$(printf '{"query":%s}' "$(printf '%s' "$sql" | jq -Rs . 2>/dev/null || printf '"%s"' "$sql")")"
    (
        cd "$MCP_BRIDGE" \
            && node scripts/mcp-bridge.js call supabase execute_sql "$args" \
                >>"$LOG_DIR/mcp.log" 2>&1
    ) &
    disown 2>/dev/null || true
fi

exit 0
