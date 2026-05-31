#!/usr/bin/env bash
# verify.sh — run one gate in a clean shell + write its result to gate_ledger.
#
# Invoked by CI per gate in the active manifest. Constraint (Dave directive):
# the gate result is written by CI, NOT by the PR author — routing is automatic
# because GitHub Actions runs this script, not the agent.
#
# Usage:
#   scripts/gates/verify.sh <gate_id> <phase>
#
# Env (set by the CI workflow):
#   DATABASE_URL       Postgres DSN for writing the ledger row.
#   CI_RUN_ID          GitHub Actions run id.
#   PR_NUMBER          PR number (optional).
#   PR_AUTHOR          PR author callsign (optional — used by routing-violation check).
#
# Additional env passes through to the gate script (HINDSIGHT_URL, etc).
#
# Exit codes mirror the wrapped gate:
#   0 — gate passed
#   1 — gate failed
#   2 — gate skipped (config missing)

set -euo pipefail

gate_id="${1:-}"
phase="${2:-unknown}"
if [[ -z "$gate_id" ]]; then
    echo "verify.sh: missing positional arg <gate_id>" >&2
    exit 64
fi

dir="$(cd "$(dirname "$0")" && pwd)"
script="${dir}/${gate_id}.sh"
if [[ ! -x "$script" ]]; then
    echo "verify.sh: gate script not executable or missing: $script" >&2
    exit 64
fi

# Run the gate in a clean shell with env -i, passing through ONLY the env vars
# the gate needs. The whitelist is conservative — Postgres, Hindsight, gate
# tuning vars, plus PATH/HOME/USER so shell built-ins resolve.
result_file="$(mktemp)"
trap 'rm -f "$result_file"' EXIT

set +e
env -i \
    PATH="${PATH}" \
    HOME="${HOME:-/tmp}" \
    USER="${USER:-runner}" \
    DATABASE_URL="${DATABASE_URL:-}" \
    SUPABASE_DB_URL="${SUPABASE_DB_URL:-}" \
    HINDSIGHT_URL="${HINDSIGHT_URL:-}" \
    HINDSIGHT_QUERY="${HINDSIGHT_QUERY:-}" \
    HINDSIGHT_BANK="${HINDSIGHT_BANK:-}" \
    GATE_ATOMS_TABLE="${GATE_ATOMS_TABLE:-}" \
    GATE_ATOMS_TS_COL="${GATE_ATOMS_TS_COL:-}" \
    GATE_GIT_REPO="${GATE_GIT_REPO:-}" \
    GATE_GIT_REF="${GATE_GIT_REF:-}" \
    GATE_CRASH_DISPATCH_CMD="${GATE_CRASH_DISPATCH_CMD:-}" \
    GATE_CRASH_HOP="${GATE_CRASH_HOP:-}" \
    GATE_CRASH_TIMEOUT_S="${GATE_CRASH_TIMEOUT_S:-}" \
    V1_CHAIN_STATE_FILE="${V1_CHAIN_STATE_FILE:-}" \
    bash "$script" >"$result_file"
rc=$?
set -e

# Print the gate's stdout (canonical JSON line) to OUR stdout so CI logs see it.
cat "$result_file"

# Map exit code to ledger status.
case "$rc" in
    0) status="pass" ;;
    1) status="fail" ;;
    2) status="skipped" ;;
    *) status="fail" ;;
esac

# Routing violation check: if PR_AUTHOR matches the gate evidence's `agent`
# field (no current gate emits one — placeholder for future agent-named
# evidence), mark routing violation. For now, the routing guarantee comes
# from GitHub Actions running this script, not the agent that wrote the
# code — so the violation case is structurally impossible in CI.
routing_status="ok"
if [[ -n "${PR_AUTHOR:-}" ]]; then
    evidence_agent="$(jq -r '.evidence.agent // empty' <"$result_file" 2>/dev/null || echo '')"
    if [[ -n "$evidence_agent" && "$evidence_agent" == "$PR_AUTHOR" ]]; then
        routing_status="ROUTING_VIOLATION"
        status="fail"
    fi
fi

# Write a ledger row. Skipped IF DATABASE_URL absent so the gate result still
# exits accurately even when the ledger is unwritable (CI logs are the
# fallback evidence).
if [[ -n "${DATABASE_URL:-}" ]] && command -v psql >/dev/null 2>&1; then
    DSN="${DATABASE_URL/+asyncpg/}"
    evidence_payload="$(cat "$result_file")"
    # Wrap the gate's JSON line + routing status into a single JSONB payload.
    enriched="$(jq -nc --argjson g "$evidence_payload" --arg r "$routing_status" \
        '$g + {routing: $r}' 2>/dev/null || echo "$evidence_payload")"
    psql "$DSN" -v ON_ERROR_STOP=1 -tAc \
        "INSERT INTO public.gate_ledger (gate_id, phase, ci_run_id, pr_number, status, evidence)
         VALUES (
            '${gate_id}', '${phase}',
            $( [[ -n "${CI_RUN_ID:-}" ]] && printf "'%s'" "${CI_RUN_ID}" || echo NULL ),
            $( [[ -n "${PR_NUMBER:-}" ]] && printf "%s" "${PR_NUMBER}" || echo NULL ),
            '${status}',
            '$(echo "${enriched}" | sed "s/'/''/g")'::jsonb
         );" >/dev/null || echo "verify.sh: gate_ledger insert failed for gate=${gate_id}" >&2
fi

exit $rc
