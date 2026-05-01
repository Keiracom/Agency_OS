#!/usr/bin/env bash
# Governance preflight — F10 fix verification helper.
#
# Validates the full Supabase write path that recorder_hook.sh and
# freeze.py rely on:
#   1. INSERT a synthetic row into public.governance_events via MCP
#   2. SELECT it back by sentinel id
#   3. Skip DELETE — governance_events is append-only by design
#      (REVOKE UPDATE/DELETE is enforced; the sentinel row is left in
#      place and tagged with event_type='preflight_test' for filtering).
#
# Exit 0 on PASS, 1 on FAIL. All MCP raw output is echoed so failures
# are diagnosable without re-running.

set -uo pipefail

MCP_BRIDGE="${MCP_BRIDGE_DIR:-/home/elliotbot/clawd/skills/mcp-bridge}"
SUPABASE_PROJECT_ID="${SUPABASE_PROJECT_ID:-jatzvazlbusedwsnqxzr}"
SENTINEL="$(date -u +%Y%m%dT%H%M%SZ)-$$-$RANDOM"

mcp_sql() {
    local sql="$1"
    local pid_json sql_json args
    pid_json="$(printf '%s' "$SUPABASE_PROJECT_ID" | jq -Rs .)"
    sql_json="$(printf '%s' "$sql" | jq -Rs .)"
    args="$(printf '{"project_id":%s,"query":%s}' "$pid_json" "$sql_json")"
    (cd "$MCP_BRIDGE" && node scripts/mcp-bridge.js call supabase execute_sql "$args")
}

step() { printf '\n[preflight %s] %s\n' "$1" "$2"; }
fail() { printf '[preflight FAIL] %s\n' "$1" >&2; exit 1; }

# Sanity: bridge present + jq available.
[[ -f "$MCP_BRIDGE/scripts/mcp-bridge.js" ]] \
    || fail "MCP bridge missing at $MCP_BRIDGE/scripts/mcp-bridge.js"
command -v jq >/dev/null \
    || fail "jq required (install with: sudo apt-get install -y jq)"
command -v node >/dev/null \
    || fail "node required on PATH"

step 1 "INSERT sentinel ($SENTINEL) into governance_events"
insert_sql="INSERT INTO public.governance_events \
(callsign, event_type, tool_name, event_data) VALUES \
('preflight', 'preflight_test', 'governance_preflight.sh', \
jsonb_build_object('sentinel', '$SENTINEL'));"
insert_out="$(mcp_sql "$insert_sql" 2>&1)"
insert_rc=$?
printf '%s\n' "$insert_out"
[[ $insert_rc -eq 0 ]] || fail "INSERT failed (rc=$insert_rc) — see output above"

step 2 "SELECT sentinel back"
select_sql="SELECT id, callsign, event_type, event_data \
FROM public.governance_events \
WHERE event_type='preflight_test' \
  AND event_data->>'sentinel' = '$SENTINEL' LIMIT 1;"
select_out="$(mcp_sql "$select_sql" 2>&1)"
select_rc=$?
printf '%s\n' "$select_out"
[[ $select_rc -eq 0 ]] || fail "SELECT failed (rc=$select_rc) — see output above"

if ! printf '%s' "$select_out" | grep -q "$SENTINEL"; then
    fail "SELECT did not echo sentinel '$SENTINEL' — write path broken"
fi

step 3 "Skip DELETE — governance_events is append-only by design"
printf 'Sentinel row left in place (event_type=preflight_test) — REVOKE UPDATE/DELETE enforced.\n'

printf '\n[preflight PASS] write path verified — sentinel %s round-tripped.\n' "$SENTINEL"
exit 0
