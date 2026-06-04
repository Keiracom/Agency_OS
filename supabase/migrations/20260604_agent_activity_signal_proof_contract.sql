-- ============================================================================
-- 20260604_agent_activity_signal_proof_contract.sql
--
-- Arms the agent_activity_signal gate (gate_roadmap id a14565ed,
-- phase 0_foundation) for a built→proven attestation under the
-- merge→deploy→prove rule. KEI ref: scout-agent-activity-signal-proof.
--
-- proof_gate prose: "fleet_liveness_status RED for any agent with 0
-- tool_call_log [activity in the last 10 minutes]".
--
-- The proof_bar (scripts/proof_bar/agent_activity_signal_live_proof.sh)
-- exercises the REAL live views with ZERO production mutation: it asserts
-- (1) idle-classification consistency over live agent_activity_signal data,
-- and (2) a synthetic tmux-alive/callsign-matched agent with 0 tool_call_log
-- resolves to fleet_liveness_status='RED' (injected + rolled back).
--
--   1. Re-affirms built_by_callsign='scout' (already scout from #1426).
--   2. Attaches proof_gate_contract: cmd = the proof_bar, AGENT_ACTIVITY_PROOF
--      tokens, role_sep builder=scout attester=[aiden,max]. trg_01 Check A
--      pins run_cmd exactly → pytest/mocked disqualified.
--   3. Inline negative self-test (sentinel-raise / outer-rollback): trg_01
--      Check A refuses a pytest-shaped run_cmd. Includes repo_sha per the
--      gate_proof_runs_repo_sha_binding_check constraint.
--
-- NON-GOALS: the flip itself (aiden+max binding_reviewer proof_runs via
--   trg_08 write_guard + trg_11). No trigger/view changes.
-- ============================================================================

BEGIN;
SET LOCAL agency_os.callsign = 'scout';

UPDATE public.gate_roadmap
   SET built_by_callsign = 'scout',
       proof_gate_contract = '{
        "check_id": "agent_activity_signal_live_v1",
        "cmd": "bash scripts/proof_bar/agent_activity_signal_live_proof.sh",
        "expected_output_contains": [
            "AGENT_ACTIVITY_PROOF: idle-classification consistent OK",
            "AGENT_ACTIVITY_PROOF: RED-for-zero-activity OK",
            "AGENT_ACTIVITY_PROOF: ALL PASS"
        ],
        "role_sep": {
            "builder": "scout",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[scout-agent-activity-signal-proof 2026-06-04] '
            || 'Attached proof_gate_contract check_id=agent_activity_signal_live_v1. '
            || 'cmd is the live proof_bar: exercises the real agent_activity_signal '
            || '+ fleet_liveness_status views, asserts idle-classification '
            || 'consistency on live data and RED-for-zero-tool_call_log via a '
            || 'rolled-back synthetic injection (zero production mutation). '
            || 'trg_01 Check A pins run_cmd → pytest/mocked disqualified.'
 WHERE id = (SELECT id FROM public.gate_roadmap WHERE component = 'agent_activity_signal');


-- Inline negative self-test — trg_01 Check A MUST refuse a pytest-shaped run_cmd.
DO $self_test$
DECLARE
    v_gate_id       uuid := gen_random_uuid();
    v_run_id        uuid;
    v_session_uuid  uuid := gen_random_uuid();
    v_msg           text;
BEGIN
    BEGIN
        SET LOCAL agency_os.callsign = 'atlas';
        INSERT INTO public.gate_roadmap (
            id, component, phase, subphase, proof_gate, proof_gate_contract,
            status, required_attestation_kind, owner
        ) VALUES (
            v_gate_id,
            'agent_activity_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline agent_activity_signal contract self-test row',
            '{
                "check_id": "agent_activity_inline_self_test",
                "cmd": "bash scripts/proof_bar/agent_activity_signal_live_proof.sh",
                "expected_output_contains": ["AGENT_ACTIVITY_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'agent_activity_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid, repo_sha
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/test_activity_mock.py -v',  -- WRONG (disqualified pytest shape)
            'mocked output claiming AGENT_ACTIVITY_PROOF: ALL PASS but run_cmd is pytest not the proof_bar',
            repeat('a', 64),
            0,
            'aiden',
            v_session_uuid::text,
            'selftest0000000000000000000000000000000b'  -- repo_sha_binding_check: len>=7
        ) RETURNING id INTO v_run_id;

        SET LOCAL agency_os.callsign = 'dave';
        BEGIN
            UPDATE public.gate_roadmap
               SET status = 'proven', proof_run_id = v_run_id
             WHERE id = v_gate_id;
            RAISE EXCEPTION
                'AGENT_ACTIVITY_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'AGENT_ACTIVITY_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
        END;

        RAISE EXCEPTION 'AGENT_ACTIVITY_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'AGENT_ACTIVITY_SELF_TEST_OK' THEN
            RAISE NOTICE
                'INLINE SELF-TEST PASS: trg_01 Check A refused pytest-shaped run_cmd; fixtures rolled back via outer sub-tx';
        ELSE
            RAISE EXCEPTION 'INLINE SELF-TEST FAIL or unexpected error: %', v_msg;
        END IF;
    END;
END
$self_test$;

COMMIT;

-- ============================================================================
-- end of 20260604_agent_activity_signal_proof_contract.sql
-- ============================================================================
