#!/usr/bin/env bash
# gate_recall.sh — proves Hindsight recall returns ≥1 result with non-zero score.
#
# Real-output gate (not "service running"): POSTs an actual query and inspects
# the response payload. Skipped when HINDSIGHT_URL is absent so CI without
# infra access produces an honest skipped status rather than a fake pass.
#
# Env:
#   HINDSIGHT_URL    Hindsight retrieve endpoint (e.g. http://127.0.0.1:8120).
#   HINDSIGHT_QUERY  Optional query string. Default: "smoke recall probe".
#   HINDSIGHT_BANK   Optional bank name. Default: "fleet_decisions".

set -euo pipefail
GATE_ID="gate_recall"
# shellcheck source=./_lib.sh
. "$(dirname "$0")/_lib.sh"

_require_env HINDSIGHT_URL

query="${HINDSIGHT_QUERY:-smoke recall probe}"
bank="${HINDSIGHT_BANK:-fleet_decisions}"

if ! command -v curl >/dev/null 2>&1; then
    _emit_skip "$GATE_ID" "curl not installed"
fi
if ! command -v jq >/dev/null 2>&1; then
    _emit_skip "$GATE_ID" "jq not installed"
fi

payload=$(jq -nc \
    --arg q "$query" \
    --arg b "$bank" \
    '{query: $q, bank: $b, limit: 5}')

response="$(curl -fsS -m 15 -H 'Content-Type: application/json' \
    -X POST "${HINDSIGHT_URL%/}/retrieve" \
    --data "$payload" 2>&1 || echo '__HTTP_FAIL__')"

if [[ "$response" == "__HTTP_FAIL__" ]]; then
    _emit_fail "$GATE_ID" "$(jq -nc --arg q "$query" '{reason: "http call failed", query: $q}')"
fi

# Expect a JSON array (or {results:[...]}) with at least one row that has a
# non-zero score. Accept either shape because the Hindsight API has evolved.
count="$(jq -r '
    if type == "array" then length
    elif (.results // null) | type == "array" then (.results | length)
    else 0 end
' <<<"$response" 2>/dev/null || echo 0)"

max_score="$(jq -r '
    [ if type == "array" then .[] else (.results // []) | .[] end
      | (.score // .similarity // 0) | tonumber ]
    | (max // 0)
' <<<"$response" 2>/dev/null || echo 0)"

if [[ "$count" -ge 1 ]] && awk -v s="$max_score" 'BEGIN{exit !(s+0>0)}'; then
    evidence=$(jq -nc --argjson c "$count" --argjson m "$max_score" --arg q "$query" \
        '{result_count: $c, max_score: $m, query: $q}')
    _emit_pass "$GATE_ID" "$evidence"
else
    evidence=$(jq -nc --argjson c "$count" --argjson m "$max_score" --arg q "$query" \
        '{result_count: $c, max_score: $m, query: $q, reason: "no result with non-zero score"}')
    _emit_fail "$GATE_ID" "$evidence"
fi
