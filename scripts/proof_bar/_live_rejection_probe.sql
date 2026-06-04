-- _live_rejection_probe.sql — invoked by product_proof_enforcement_live_rejection.sh.
--
-- Sets up a transient gate_roadmap row + matching tool_call_log row + a
-- non-matching binding_reviewer proof_run, then attempts to flip the gate
-- 'proven'. trg_01 fn_verify_before_proven Check A REJECTS the flip because
-- run_cmd != contract.cmd. The RAISE message is the proof contents.
--
-- Hard rollback via ROLLBACK at the end — no production state mutation.
-- The DO block raises check_violation from inside the UPDATE; psql aborts
-- the tx and prints the verbatim ERROR. The shell wrapper captures it.

BEGIN;
DO $$
DECLARE
    v_gate_id       uuid := gen_random_uuid();
    v_session_uuid  uuid := gen_random_uuid();
    v_run_id        uuid;
BEGIN
    SET LOCAL agency_os.callsign = 'atlas';
    INSERT INTO public.gate_roadmap (
        id, component, phase, subphase, proof_gate, proof_gate_contract,
        status, required_attestation_kind, owner
    ) VALUES (
        v_gate_id,
        'live_rejection_probe_' || replace(v_gate_id::text, '-', ''),
        '0_foundation', 'gates',
        'live rejection probe transient row',
        '{
            "check_id": "live_rejection_probe",
            "cmd": "EXACT_CONTRACT_CMD_FOR_LIVE_REJ",
            "expected_output_contains": ["SIG_TOKEN"],
            "role_sep": {"builder": "atlas", "attester": ["aiden"]},
            "negative_test_required": true
        }'::jsonb,
        'built',
        'binding_reviewer',
        'atlas'
    );

    INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
    VALUES ('aiden', v_session_uuid, 'live_rejection_probe', now());

    SET LOCAL agency_os.callsign = 'aiden';
    INSERT INTO public.gate_proof_runs (
        gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
        exit_code, attesting_callsign, attester_session_uuid, repo_sha
    ) VALUES (
        v_gate_id,
        'binding_reviewer',
        'NON_MATCHING_RUN_CMD',
        'live rejection probe output padded out for the >=32 length check — SIG_TOKEN — end',
        encode(sha256(v_gate_id::text::bytea), 'hex'),
        0,
        'aiden',
        v_session_uuid::text,
        -- repo_sha placeholder: required by the binding-row constraint (R1,
        -- merge_to_proven bind-gate). Irrelevant here — this probe tests
        -- Check A (cmd_mismatch), which raises before repo_sha is read.
        'liverej_repo_sha_unused_for_check_a'
    ) RETURNING id INTO v_run_id;

    SET LOCAL agency_os.callsign = 'dave';
    UPDATE public.gate_roadmap
       SET status = 'proven', proof_run_id = v_run_id
     WHERE id = v_gate_id;
    -- Unreachable in the happy-rejection path: trg_01 raises check_violation above.
    RAISE EXCEPTION 'INTERNAL: live_rejection_probe — trigger did NOT block the mismatched flip';
END
$$;
ROLLBACK;
