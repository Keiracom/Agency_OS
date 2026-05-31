#!/usr/bin/env bash
# check_phase_ready.sh — exits 0 ONLY when every gate in <phase> is status='pass'.
#
# Reads .gates/manifest.json for the gate list of the named phase, then
# queries gate_ledger for the LATEST status of each gate (whatever that
# gate's most recent run produced). Pass requires ALL gates pass. Fail
# prints which gates are not passing + their latest status.
#
# Usage:
#   scripts/gates/check_phase_ready.sh <phase>
#
# Env:
#   DATABASE_URL — Postgres DSN.
#   GATES_MANIFEST — Optional manifest path. Default: .gates/manifest.json.

set -euo pipefail

phase="${1:-}"
if [[ -z "$phase" ]]; then
    echo "check_phase_ready: usage: $0 <phase>" >&2
    exit 64
fi

DSN="${DATABASE_URL:-${SUPABASE_DB_URL:-}}"
if [[ -z "$DSN" ]]; then
    echo "check_phase_ready: missing DATABASE_URL" >&2
    exit 65
fi
DSN="${DSN/+asyncpg/}"

if ! command -v jq >/dev/null 2>&1 || ! command -v psql >/dev/null 2>&1; then
    echo "check_phase_ready: jq + psql required" >&2
    exit 65
fi

manifest="${GATES_MANIFEST:-.gates/manifest.json}"
if [[ ! -f "$manifest" ]]; then
    echo "check_phase_ready: manifest not found: $manifest" >&2
    exit 65
fi

# Gates active in this phase.
gates=$(jq -r --arg p "$phase" '.phases[$p] // [] | .[]' "$manifest")
if [[ -z "$gates" ]]; then
    echo "check_phase_ready: no gates registered for phase '${phase}'" >&2
    exit 65
fi

failing=()
pending=()
passing=()

while IFS= read -r gate_id; do
    [[ -z "$gate_id" ]] && continue
    latest_status=$(psql "$DSN" -tAc \
        "SELECT status FROM public.gate_ledger
         WHERE gate_id = '${gate_id}' AND phase = '${phase}'
         ORDER BY recorded_at DESC LIMIT 1;" 2>/dev/null || echo '')
    latest_status="${latest_status// /}"
    case "$latest_status" in
        pass) passing+=("$gate_id") ;;
        fail) failing+=("$gate_id") ;;
        *)    pending+=("$gate_id ($latest_status)") ;;
    esac
done <<<"$gates"

echo "phase '${phase}':"
echo "  pass:    ${passing[*]:-(none)}"
echo "  fail:    ${failing[*]:-(none)}"
echo "  pending: ${pending[*]:-(none)}"

if ((${#failing[@]} > 0 || ${#pending[@]} > 0)); then
    exit 1
fi
exit 0
