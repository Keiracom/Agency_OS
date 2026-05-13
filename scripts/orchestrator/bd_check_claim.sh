#!/usr/bin/env bash
# bd_check_claim.sh — KEI-22 D6 thin wrapper providing `bd check-claim --branch`.
#
# Per Dave CEO directive ts ~1778667100: pre-commit hook must call this to
# physically refuse commits without an active bd claim. bd itself doesn't
# have `check-claim` as a native subcommand (verified by `bd check-claim
# --help` returning 'unknown command'). We wrap `bd list --json` + filter
# logic that mirrors KEI-22 D5 PreToolUse hook semantics:
#
#   Claim is valid iff there exists a bd issue where:
#     - assignee == <callsign>  (callsign derived from branch prefix or env)
#     - status   == in_progress
#     - external contains 'linear.app' (proves Linear-sourced per Dave rule)
#
# Usage:
#     bd_check_claim.sh --branch <name>      # exits 0 + prints claim id if valid
#     bd_check_claim.sh --branch <name> --quiet
#     CALLSIGN=orion bd_check_claim.sh        # uses env, no branch parse
#
# Exit codes:
#     0 — valid claim found (prints claim id to stdout)
#     1 — no valid claim (prints reason to stderr)
#     2 — bd binary missing or unexpected error
#
# Pattern A: bd binary missing exits 2 (not 0); pre-commit caller can then
# decide whether to fail-open (degrade-soft per D5) or fail-closed. The
# default `.githooks/pre-commit` shipped alongside fails CLOSED on exit 2
# only when AGENCY_OS_BD_HARDFAIL=1 is set, else degrades soft with a
# warning — matches D5's bd-down soft-allow design.

set -u

BRANCH=""
QUIET=0
BD_BIN="${AGENCY_OS_BD_BIN:-bd}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --branch)
            BRANCH="${2:-}"
            shift 2
            ;;
        --quiet)
            QUIET=1
            shift
            ;;
        -h | --help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *)
            echo "error: unknown arg: $1" >&2
            exit 2
            ;;
    esac
done

log() { [[ $QUIET -eq 1 ]] || printf '%s\n' "$*" >&2; }

# Resolve callsign: prefer env CALLSIGN; fall back to branch prefix
# (orion/foo → orion). Branch prefix must be one of the known callsigns.
callsign="${CALLSIGN:-}"
if [[ -z "$callsign" && -n "$BRANCH" ]]; then
    prefix="${BRANCH%%/*}"
    case "$prefix" in
        orion | atlas | scout | elliot | aiden | max)
            callsign="$prefix"
            ;;
    esac
fi
callsign="${callsign,,}"

if [[ -z "$callsign" ]]; then
    log "error: cannot resolve callsign (CALLSIGN env unset + branch=$BRANCH not callsign-prefixed)"
    exit 1
fi

# Empirical probe: bd binary present?
if ! command -v "$BD_BIN" >/dev/null 2>&1; then
    log "warning: $BD_BIN binary not on PATH — Pattern A degrade-soft for caller"
    exit 2
fi

# Pull bd list and filter via embedded Python (avoids jq dependency).
result_json="$("$BD_BIN" list --json 2>/dev/null || echo "[]")"

claim_id="$(
    BD_LIST_JSON="$result_json" CALLSIGN="$callsign" /home/elliotbot/clawd/venv/bin/python3 - <<'PY'
import json
import os
import sys

raw = os.environ.get("BD_LIST_JSON", "[]")
callsign = os.environ.get("CALLSIGN", "").lower()
try:
    data = json.loads(raw or "[]")
except json.JSONDecodeError:
    sys.exit(0)
items = data if isinstance(data, list) else data.get("issues") or data.get("data") or []
for i in items:
    if not isinstance(i, dict):
        continue
    if (i.get("assignee") or "").strip().lower() != callsign:
        continue
    if (i.get("status") or "").lower() != "in_progress":
        continue
    if "linear.app" not in (i.get("external") or "").lower():
        continue
    print(i.get("id", ""))
    sys.exit(0)
sys.exit(0)
PY
)"

if [[ -n "$claim_id" ]]; then
    [[ $QUIET -eq 1 ]] || printf '%s\n' "$claim_id"
    exit 0
fi

log "no_valid_claim: no bd issue assigned to '$callsign' with status=in_progress + Linear external-ref"
exit 1
