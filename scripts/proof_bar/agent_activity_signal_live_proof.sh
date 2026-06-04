#!/usr/bin/env bash
# agent_activity_signal_live_proof.sh
#
# LIVE proof for gate_roadmap component agent_activity_signal
# (id = a14565ed, phase 0_foundation).
#
# proof_gate prose: "fleet_liveness_status RED for any agent with 0 tool_call_log
# [activity in the last 10 minutes]".
#
# Exercises the REAL live views (public.agent_activity_signal +
# public.fleet_liveness_status) against the live DB — NOT a mock, NOT pytest.
# Bound as proof_gate_contract.cmd; trg_01 Check A pins run_cmd to EXACTLY:
#     bash scripts/proof_bar/agent_activity_signal_live_proof.sh
# so a pytest/mock run_cmd fails Check A (cmd_mismatch) — the structural
# negative bar.
#
# Two assertions, ZERO production mutation (the synthetic probe row is inserted
# and ROLLED BACK in a single aborted transaction):
#   1. idle-classification consistent — for EVERY live agent_activity_signal
#      row, (calls_last_10m = 0) ⟺ (activity_state = 'idle'). Read-only;
#      proves the classifier on real data.
#   2. RED-for-zero-activity — a synthetic tmux-alive, callsign-matched agent
#      with a fresh checked_at and 0 tool_call_log resolves to fleet_liveness_
#      status = 'RED' (the idle→RED branch). Injected + rolled back.
#
# Exit 0 = both assertions passed. Exit 2 = an assertion failed. Exit 3 = env error.
# ref: scout-agent-activity-signal-proof.

set -u

if [[ -z "${DATABASE_URL:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi
[[ -n "${DATABASE_URL:-}" ]] || { echo "ERROR: DATABASE_URL not set" >&2; exit 3; }
DSN="${DATABASE_URL//postgresql+asyncpg/postgresql}"

PROBE="proofprobe_idle_$$"
fail() { echo "AGENT_ACTIVITY_PROOF: FAIL — $1" >&2; exit "${2:-2}"; }

# Single aborted transaction — the synthetic fleet_liveness row never commits.
SQL_OUT="$(psql "$DSN" -X -v ON_ERROR_STOP=1 2>&1 <<SQL
BEGIN;
DO \$\$
DECLARE
    v_bad    int;
    v_status text;
BEGIN
    -- 1. idle-classification consistency over live data (read-only).
    SELECT count(*) INTO v_bad
      FROM public.agent_activity_signal
     WHERE (calls_last_10m = 0) <> (activity_state = 'idle');
    IF v_bad <> 0 THEN
        RAISE EXCEPTION 'idle-classification mismatch on % live row(s)', v_bad;
    END IF;
    RAISE NOTICE 'TOK idle-classification consistent OK';

    -- 2. RED-for-zero-activity: synthetic idle agent → fleet_liveness_status RED.
    INSERT INTO public.fleet_liveness
        (callsign, tmux_alive, callsign_match, reported_callsign, checked_at)
    VALUES ('${PROBE}', true, true, '${PROBE}', now());

    SELECT status INTO v_status
      FROM public.fleet_liveness_status
     WHERE callsign = '${PROBE}';
    IF v_status IS DISTINCT FROM 'RED' THEN
        RAISE EXCEPTION 'expected RED for 0-tool_call_log agent, got %', COALESCE(v_status, '<null>');
    END IF;
    RAISE NOTICE 'TOK RED-for-zero-activity OK (status=%)', v_status;
END
\$\$;
ROLLBACK;
SQL
)"
RC=$?
echo "----- live view proof (transaction rolled back) -----"
echo "$SQL_OUT"
echo "----- end -----"
[[ $RC -eq 0 ]] || fail "psql proof transaction failed (rc=$RC)" 2
echo "$SQL_OUT" | grep -qF "TOK idle-classification consistent OK" || fail "idle-classification assertion missing"
echo "AGENT_ACTIVITY_PROOF: idle-classification consistent OK"
echo "$SQL_OUT" | grep -qF "TOK RED-for-zero-activity OK"          || fail "RED-for-zero-activity assertion missing"
echo "AGENT_ACTIVITY_PROOF: RED-for-zero-activity OK"

# uniqueness line (distinct run_output → distinct output_sha256 so the
# UNIQUE(gate_roadmap_id, output_sha256) never collides between aiden + max runs).
echo "AGENT_ACTIVITY_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "AGENT_ACTIVITY_PROOF: ALL PASS"
exit 0
