#!/usr/bin/env bash
# agent_self_claim_loop.sh — KEI-92 / Linear KEI-130 self-claim daemon.
#
# Per-agent loop that closes the idle-loop bleed by polling the phase-gated
# queue and auto-claiming eligible work. Replaces "post READY and wait for
# Elliot dispatch" with self-service: phase-lock (KEI-86) already restricts
# what's eligible, so orchestrator permission is redundant.
#
# Loop steps per Linear KEI-92 spec:
#   1. bd ready → eligible KEIs
#   2. items? → bd claim --callsign=$CALLSIGN (no --id → next available) → log
#   3. zero items? → post [READY:callsign] ONCE → sleep $POLL_SECONDS → retry
#   4. claim race-lost (rc != 0)? → retry from step 1 without re-posting READY
#
# Linear pre-assignment (Elliot override): a KEI assigned to a different
# callsign in Linear is silently skipped via self_assign_on_ready.py's existing
# "unassigned OR assignee == callsign" filter. No extra wiring here.
#
# Usage:
#   agent_self_claim_loop.sh --callsign <name> [--poll-seconds 60]
# Env fallback: CALLSIGN.

set -euo pipefail

POLL_SECONDS="${POLL_SECONDS:-60}"
# Emit [DEGRADED:callsign tg=bd_down] after this many consecutive non-eligible
# non-claimed ticks where the underlying bd binary returned an unusable
# response. Keeps the agent observably-failing instead of silently-running
# (Gate 4 outcome-counter alignment).
DEGRADED_AFTER="${DEGRADED_AFTER:-5}"
CALLSIGN_ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --callsign) CALLSIGN_ARG="$2"; shift 2;;
    --poll-seconds) POLL_SECONDS="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
CALLSIGN="${CALLSIGN_ARG:-${CALLSIGN:-}}"
[[ -n "$CALLSIGN" ]] || { echo "[self-claim-loop] CALLSIGN not set" >&2; exit 2; }

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# ASSIGN_PATH override lets tests inject a stub self_assign_on_ready.py.
ASSIGN="${ASSIGN_PATH:-$REPO_ROOT/scripts/orchestrator/self_assign_on_ready.py}"
TG_BIN="$(command -v tg || true)"
READY_POSTED=0
DEGRADED_POSTED=0
DEGRADED_STREAK=0

while true; do
  result=$(python3 "$ASSIGN" --callsign "$CALLSIGN" 2>/dev/null || echo '{"claimed":false,"reason":"exception"}')
  reason=$(echo "$result" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("reason",""))' 2>/dev/null || echo "")
  case "$reason" in
    claimed)
      issue=$(echo "$result" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("issue_id",""))')
      echo "[self-claim-loop:$CALLSIGN] claimed $issue"
      READY_POSTED=0
      DEGRADED_POSTED=0
      DEGRADED_STREAK=0
      ;;
    no_eligible_work)
      if [[ "$READY_POSTED" = "0" && -n "$TG_BIN" ]]; then
        CALLSIGN="$CALLSIGN" "$TG_BIN" "[READY:$CALLSIGN]" >/dev/null 2>&1 || true
        READY_POSTED=1
      fi
      DEGRADED_STREAK=0
      ;;
    bd_unavailable|exception)
      DEGRADED_STREAK=$((DEGRADED_STREAK + 1))
      if [[ "$DEGRADED_STREAK" -ge "$DEGRADED_AFTER" && "$DEGRADED_POSTED" = "0" && -n "$TG_BIN" ]]; then
        CALLSIGN="$CALLSIGN" "$TG_BIN" "[DEGRADED:$CALLSIGN tg=bd_down]" >/dev/null 2>&1 || true
        DEGRADED_POSTED=1
      fi
      ;;
    race_lost_all|invalid_callsign|*)
      ;;
  esac
  sleep "$POLL_SECONDS"
done
