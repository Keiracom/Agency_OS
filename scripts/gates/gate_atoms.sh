#!/usr/bin/env bash
# gate_atoms.sh — proves new keiracom_atoms rows have landed since last gate run.
#
# Real-output gate: queries Postgres for COUNT(*) WHERE created_at > last_check_ts.
# The "last check" timestamp comes from the most-recent prior PASS for this gate
# in gate_ledger (read via psql); on first run, falls back to NOW() - 24h.
#
# Env:
#   DATABASE_URL or SUPABASE_DB_URL — Postgres DSN. +asyncpg suffix stripped.
#   GATE_ATOMS_TABLE — Optional override. Default: public.keiracom_atoms.
#   GATE_ATOMS_TS_COL — Optional override. Default: created_at.

set -euo pipefail
GATE_ID="gate_atoms"
# shellcheck source=./_lib.sh
. "$(dirname "$0")/_lib.sh"

DSN="${DATABASE_URL:-${SUPABASE_DB_URL:-}}"
if [[ -z "$DSN" ]]; then
    _emit_skip "$GATE_ID" "missing required env: DATABASE_URL or SUPABASE_DB_URL"
fi
DSN="${DSN/+asyncpg/}"

if ! command -v psql >/dev/null 2>&1; then
    _emit_skip "$GATE_ID" "psql not installed"
fi
if ! command -v jq >/dev/null 2>&1; then
    _emit_skip "$GATE_ID" "jq not installed"
fi

atoms_table="${GATE_ATOMS_TABLE:-public.keiracom_atoms}"
ts_col="${GATE_ATOMS_TS_COL:-created_at}"

# Fetch the recorded_at of the most recent passing run of this gate. If no
# prior pass, default to NOW() - INTERVAL '24 hours' so we still measure a
# bounded recent window rather than ALL history.
last_pass_query=$(cat <<SQL
SELECT COALESCE(
    (SELECT recorded_at FROM public.gate_ledger
     WHERE gate_id = '${GATE_ID}' AND status = 'pass'
     ORDER BY recorded_at DESC LIMIT 1),
    NOW() - INTERVAL '24 hours'
)::text;
SQL
)

last_pass="$(psql "$DSN" -tAc "$last_pass_query" 2>/dev/null || echo '')"
if [[ -z "$last_pass" ]]; then
    _emit_fail "$GATE_ID" "$(jq -nc '{reason: "could not read last-pass timestamp from gate_ledger"}')"
fi

new_count="$(psql "$DSN" -tAc \
    "SELECT COUNT(*) FROM ${atoms_table} WHERE ${ts_col} > '${last_pass}'::timestamptz;" \
    2>/dev/null || echo "-1")"

if [[ "$new_count" == "-1" ]]; then
    _emit_fail "$GATE_ID" "$(jq -nc --arg t "$atoms_table" \
        '{reason: "atoms table query failed", table: $t}')"
fi

if (( new_count > 0 )); then
    evidence=$(jq -nc --arg t "$atoms_table" --arg s "$last_pass" --argjson n "$new_count" \
        '{atoms_table: $t, since: $s, new_rows: $n}')
    _emit_pass "$GATE_ID" "$evidence"
else
    evidence=$(jq -nc --arg t "$atoms_table" --arg s "$last_pass" \
        '{atoms_table: $t, since: $s, new_rows: 0, reason: "no new atoms since last pass"}')
    _emit_fail "$GATE_ID" "$evidence"
fi
