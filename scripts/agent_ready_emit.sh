#!/usr/bin/env bash
# agent_ready_emit.sh — Emit [READY:<callsign>] via NATS (supervisor v2) or
# Slack (legacy). KEI-221 (b)+(c) — Slack → NATS migration helper.
#
# Routing decision: AGENT_ROUTING_<CALLSIGN_UPPER> env var.
#   value == "v2"  → nats pub keiracom.agent.status.<callsign> '{"state":"ready",…}'
#   anything else  → tg "[READY:<callsign>]"  (legacy Slack path)
#
# Why a helper: two existing call-sites emit ready markers via `tg` directly
# (scripts/orchestrator/agent_self_claim_loop.sh + scripts/hooks/emit_ready_marker.sh).
# Centralising the route-decision here keeps the cutover atomic — flip
# AGENT_ROUTING_<CALLSIGN>=v2 in .env and both call-sites switch in lockstep.
#
# Usage:
#   agent_ready_emit.sh <callsign>
#
# Exit codes:
#   0  emission attempted (success OR fail-open in legacy path)
#   2  usage error (missing callsign)
#
# Fail-open: legacy `tg` path already wraps in `|| true` upstream, so failures
# never block the caller. NATS path returns the publisher's exit code so the
# supervisor can be alerted if NATS is down.

set -u

CALLSIGN="${1:-}"
if [[ -z "$CALLSIGN" ]]; then
    echo "usage: $0 <callsign>" >&2
    exit 2
fi

CALLSIGN_LOWER="$(echo "$CALLSIGN" | tr '[:upper:]' '[:lower:]')"
CALLSIGN_UPPER="$(echo "$CALLSIGN" | tr '[:lower:]' '[:upper:]')"

FLAG_VAR="AGENT_ROUTING_${CALLSIGN_UPPER}"
ROUTING="${!FLAG_VAR:-}"

NATS_BIN="${NATS_BIN:-$(command -v nats || true)}"
TG_BIN="${TG_BIN:-$(command -v tg || true)}"

if [[ "$ROUTING" == "v2" && -n "$NATS_BIN" ]]; then
    PAYLOAD="$(printf '{"state":"ready","callsign":"%s","ts":%s}' \
        "$CALLSIGN_LOWER" "$(date +%s)")"
    "$NATS_BIN" pub "keiracom.agent.status.${CALLSIGN_LOWER}" "$PAYLOAD" \
        >/dev/null 2>&1
    exit $?
fi

if [[ -n "$TG_BIN" ]]; then
    CALLSIGN="$CALLSIGN_LOWER" "$TG_BIN" "[READY:${CALLSIGN_LOWER}]" \
        >/dev/null 2>&1 || true
fi
exit 0
