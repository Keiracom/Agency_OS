#!/usr/bin/env bash
# audit_callsign_env.sh — KEI-72 item (b): scan agent-*.service unit files in
# infra/systemd/agents/ for an Environment=CALLSIGN= declaration. Reports any
# unit that's missing the env declaration. Exit code 0 if all units have it,
# 1 if any are missing (operator action required).
#
# Why this matters: tasks_cli + slack_relay + scripts in the agent process tree
# read CALLSIGN from os.environ. If the systemd unit doesn't set it, the
# process tree inherits an unset value → tasks_cli falls back to
# DEFAULT_CALLSIGN ('unknown') unless rescued by KEI-71 (now blocks the claim).
# KEI-72 (a) gates auto-claim on Step-0-RESTATE; (b) audits the upstream env
# declaration so the gate isn't load-bearing on its own.
#
# Usage:
#   bash scripts/audit_callsign_env.sh [-v]
#   bash scripts/audit_callsign_env.sh --units-dir infra/systemd/agents
#
# Exit codes:
#   0 — all units declare Environment=CALLSIGN=
#   1 — one or more units missing the declaration
#   2 — units-dir not found / operator misconfig

set -euo pipefail

UNITS_DIR="${UNITS_DIR:-infra/systemd/agents}"
VERBOSE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose) VERBOSE=1; shift ;;
        --units-dir)  UNITS_DIR="$2"; shift 2 ;;
        -h|--help)
            sed -n 's/^# //p' "$0" | head -40
            exit 0
            ;;
        *) echo "ERROR: unknown arg $1" >&2; exit 2 ;;
    esac
done

if [[ ! -d "$UNITS_DIR" ]]; then
    echo "ERROR: units dir not found: $UNITS_DIR" >&2
    exit 2
fi

missing=()
ok=()

shopt -s nullglob
for unit in "$UNITS_DIR"/*-agent.service; do
    name="$(basename "$unit" .service)"
    if grep -qE '^Environment=("?)CALLSIGN=' "$unit"; then
        ok+=("$name")
        [[ "$VERBOSE" == "1" ]] && echo "  OK      $name"
    else
        missing+=("$name")
        echo "  MISSING $name  ($unit has no Environment=CALLSIGN= line)"
    fi
done

echo ""
echo "Summary: ${#ok[@]} OK, ${#missing[@]} missing"

if [[ ${#missing[@]} -gt 0 ]]; then
    echo ""
    echo "Fix: add 'Environment=\"CALLSIGN=<callsign>\"' to each [Service] section."
    echo "Example for aiden-agent.service:"
    echo "  [Service]"
    echo "  Environment=\"CALLSIGN=aiden\""
    exit 1
fi

exit 0
