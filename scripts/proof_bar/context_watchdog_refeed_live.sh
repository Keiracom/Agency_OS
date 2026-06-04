#!/usr/bin/env bash
# context_watchdog_refeed_live.sh
#
# LIVE proof for gate context_watchdog (#1427): the watchdog RE-FEEDS a cleanly-
# idle agent that has queued work (injects the actual next task so it resumes
# real work) rather than only tab-clearing. Bound as proof_gate_contract.cmd.
#
# Runs _refeed_probe.py which drives a real idle test agent through the REAL
# wired decision path against the LIVE tool_call_log DB + a REAL tmux pane:
#   - idle WITH queued work  -> re-fed; FRESH tool_call_log row (real work, not /clear)
#   - idle WITH no work      -> left alone, no thrash (inline negative self-test)
#
# Required run_output substrings (contract Check B):
#   REFED_TASK_INJECTED=true
#   REFED_FRESH_TOOL_CALL=true
#   NEG_IDLE_NO_WORK_LEFT=true
#   REFEED_PROOF_OK
#
# contract.cmd is this bash invocation, so a pytest run_cmd fails Check A.
# Exit 0 on a verified live re-feed + passing negative self-test; 2 otherwise;
# 3 on environment error.
#
# ref: NOVA context_watchdog re-feed (watchdog_reaper) built->proven.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -z "${DATABASE_URL:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi
if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "ERROR: DATABASE_URL not set" >&2
    exit 3
fi
if ! command -v tmux >/dev/null 2>&1; then
    echo "ERROR: tmux not available" >&2
    exit 3
fi

cd "$REPO_ROOT"
OUT="$(DATABASE_URL="$DATABASE_URL" python3 scripts/proof_bar/_refeed_probe.py 2>&1)"
RC=$?
echo "$OUT"

if [[ "$RC" -ne 0 ]]; then
    exit 2
fi

for token in "REFED_TASK_INJECTED=true" "REFED_FRESH_TOOL_CALL=true" \
             "NEG_IDLE_NO_WORK_LEFT=true" "REFEED_PROOF_OK"; do
    if ! echo "$OUT" | grep -F -q -- "$token"; then
        echo "MISSING REQUIRED TOKEN: $token" >&2
        exit 2
    fi
done
exit 0
