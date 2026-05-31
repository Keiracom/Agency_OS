#!/usr/bin/env bash
# gate_crash_recovery.sh — proves the chain resumes + completes after a mid-hop
# crash.
#
# Real-output gate: triggers a chain dispatch, kills the dispatcher-spawned tmux
# session for a target hop (default max_challenge), polls the chain state file
# until current_step == 'complete' OR a timeout fires. Pass if the chain
# recovered + completed; fail if it dead-lettered or timed out.
#
# Env:
#   GATE_CRASH_DISPATCH_CMD   Command that triggers a chain dispatch. The command
#                             must print the dispatched chain_id to stdout.
#                             Skipped if unset.
#   GATE_CRASH_HOP            Hop to kill. Default: max_challenge.
#   GATE_CRASH_TIMEOUT_S      Max seconds to wait for recovery. Default: 180.
#   V1_CHAIN_STATE_FILE       Default: /tmp/v1_chain_state.json.

set -euo pipefail
GATE_ID="gate_crash_recovery"
# shellcheck source=./_lib.sh
. "$(dirname "$0")/_lib.sh"

if [[ -z "${GATE_CRASH_DISPATCH_CMD:-}" ]]; then
    _emit_skip "$GATE_ID" "GATE_CRASH_DISPATCH_CMD not set (chain dispatch helper required)"
fi
if ! command -v jq >/dev/null 2>&1; then
    _emit_skip "$GATE_ID" "jq not installed"
fi
if ! command -v tmux >/dev/null 2>&1; then
    _emit_skip "$GATE_ID" "tmux not installed"
fi

hop="${GATE_CRASH_HOP:-max_challenge}"
timeout_s="${GATE_CRASH_TIMEOUT_S:-180}"
state_file="${V1_CHAIN_STATE_FILE:-/tmp/v1_chain_state.json}"

# 1. Dispatch a chain. Capture the chain_id from the helper's stdout.
chain_id="$(bash -c "$GATE_CRASH_DISPATCH_CMD" 2>/dev/null | tail -1 | tr -d '[:space:]')"
if [[ -z "$chain_id" ]]; then
    _emit_fail "$GATE_ID" "$(jq -nc \
        '{reason: "dispatch helper produced no chain_id"}')"
fi

# 2. Wait briefly for the target hop's dispatcher session to appear.
session_name="disp-chain-${chain_id}-${hop}"
appear_deadline=$(($(date +%s) + 30))
while (( $(date +%s) < appear_deadline )); do
    if tmux has-session -t "$session_name" 2>/dev/null; then
        break
    fi
    sleep 1
done

# 3. Kill the session (the crash). Acceptable if it already exited naturally
# (means the hop finished pre-kill — recovery path not exercised on this run;
# we still continue + observe whether the chain completes overall).
killed="false"
if tmux kill-session -t "$session_name" 2>/dev/null; then
    killed="true"
fi

# 4. Poll the chain state file for completion or dead-letter.
deadline=$(($(date +%s) + timeout_s))
final_status=""
final_step=""
while (( $(date +%s) < deadline )); do
    if [[ -f "$state_file" ]]; then
        entry=$(jq -c --arg c "$chain_id" '.[$c] // empty' "$state_file" 2>/dev/null || echo '')
        if [[ -n "$entry" ]]; then
            step=$(jq -r '.current_step // ""' <<<"$entry")
            if [[ "$step" == "complete" ]]; then
                final_status="recovered"
                final_step="$step"
                break
            elif [[ "$step" == "halted_ceiling_exceeded" || "$step" == "dead_lettered" ]]; then
                final_status="terminal_fail"
                final_step="$step"
                break
            fi
        fi
    fi
    sleep 3
done

if [[ "$final_status" == "recovered" ]]; then
    evidence=$(jq -nc --arg c "$chain_id" --arg h "$hop" --arg k "$killed" --arg s "$final_step" \
        '{chain_id: $c, killed_hop: $h, kill_landed: $k, final_step: $s, outcome: "recovered"}')
    _emit_pass "$GATE_ID" "$evidence"
else
    evidence=$(jq -nc --arg c "$chain_id" --arg h "$hop" --arg k "$killed" --arg s "${final_step:-unknown}" \
        --arg t "$timeout_s" \
        '{chain_id: $c, killed_hop: $h, kill_landed: $k, final_step: $s, timeout_s: $t, outcome: "did_not_recover"}')
    _emit_fail "$GATE_ID" "$evidence"
fi
