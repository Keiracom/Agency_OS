#!/usr/bin/env bash
# rehearsal_ready.sh — exits 0 ONLY when every gate in every active phase is pass.
#
# This is THE gate that unlocks a rehearsal run. It iterates every phase in
# .gates/manifest.json and asserts that the latest gate_ledger row for each
# gate in that phase has status='pass'. Any fail/pending → nonzero exit with
# a full report.
#
# Per Dave directive 2026-05-30: this script's exit code MUST be respected
# before any rehearsal fires.
#
# Env:
#   DATABASE_URL — Postgres DSN.
#   GATES_MANIFEST — Optional manifest path. Default: .gates/manifest.json.

set -euo pipefail

DSN="${DATABASE_URL:-${SUPABASE_DB_URL:-}}"
if [[ -z "$DSN" ]]; then
    echo "rehearsal_ready: missing DATABASE_URL" >&2
    exit 65
fi
DSN="${DSN/+asyncpg/}"

if ! command -v jq >/dev/null 2>&1 || ! command -v psql >/dev/null 2>&1; then
    echo "rehearsal_ready: jq + psql required" >&2
    exit 65
fi

manifest="${GATES_MANIFEST:-.gates/manifest.json}"
if [[ ! -f "$manifest" ]]; then
    echo "rehearsal_ready: manifest not found: $manifest" >&2
    exit 65
fi

phases=$(jq -r '.phases | keys[]' "$manifest" 2>/dev/null || echo '')
if [[ -z "$phases" ]]; then
    echo "rehearsal_ready: manifest has no phases" >&2
    exit 65
fi

overall_rc=0
echo "rehearsal_ready: checking all phases in ${manifest}"

while IFS= read -r phase; do
    [[ -z "$phase" ]] && continue
    if "$(dirname "$0")/check_phase_ready.sh" "$phase"; then
        echo "  ✓ ${phase}: all gates pass"
    else
        overall_rc=1
        # check_phase_ready already printed the breakdown.
    fi
done <<<"$phases"

if (( overall_rc == 0 )); then
    echo "rehearsal_ready: ALL phases green — rehearsal unlocked"
else
    echo "rehearsal_ready: AT LEAST ONE PHASE NOT PASSING — rehearsal BLOCKED" >&2
fi

exit "$overall_rc"
