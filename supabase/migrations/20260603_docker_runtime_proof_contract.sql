-- ============================================================================
-- 20260603_docker_runtime_proof_contract.sql
--
-- Arms the docker_runtime gate (gate_roadmap id
-- ec883620-ee1c-454b-ba31-0263fd93aaa6, phase 4_infra) for a LIVE built→proven
-- attestation. KEI ref: scout-docker-runtime-live-proof.
--
-- WHAT THIS MIGRATION DOES
--   1. Stamps gate_roadmap.built_by_callsign = 'scout' on the docker_runtime
--      row. It was NULL — which left the attester≠builder gate UNARMED:
--        - trg_04 fn_gate_proof_no_self_attest RAISEs on NULL built_by_callsign
--          ("record the build transition first"), so NO binding_reviewer
--          proof_run could be inserted at all;
--        - the PR #1415 watchdog keys on built_by_callsign for structural
--          attester≠builder enforcement.
--      Per Elliot addendum 2026-06-03 the stamp value is 'scout' (the author of
--      this proof mechanism). The physical infra owner stays atlas in the
--      owner column. OLD.built_by_callsign IS NULL so the trg_03 immutability
--      branch does not fire; the UPDATE-path capture branch only fires on a
--      status transition to 'built', which this UPDATE is not — so the explicit
--      value passes through.
--
--   2. Attaches the structured proof_gate_contract:
--        cmd  = bash scripts/proof_bar/docker_runtime_live_proof.sh
--        expected_output_contains = the five DOCKER_RUNTIME_PROOF tokens that
--          the script emits ONLY after each real `docker build` / `docker run`
--          assertion passes.
--        role_sep.builder = scout, attester = [aiden, max].
--      Because trg_01 Check A pins run_cmd to contract.cmd EXACTLY, a
--      pytest/mocked run_cmd is disqualified structurally (cmd_mismatch). This
--      is the directive's NEGATIVE bar: pytest-only/mocked = disqualified.
--
--   3. Inline DO-block negative self-test (Dave 2026-06-02 standing precedent,
--      same inner-sentinel-raise / outer-rollback pattern as the BASE +
--      trigger-fix migrations — gate_proof_runs is append-only, trg_07 refuses
--      DELETE): asserts trg_01 Check A REFUSES a mismatched-cmd proof_run flip
--      against a docker_runtime-shaped contract. If the trigger fails to block,
--      the migration ABORTS.
--
-- NON-GOALS (by design):
--   - The built→proven flip itself. trg_11 requires BOTH aiden AND max
--     binding_reviewer proof_runs, and trg_08 write_guard means only aiden's
--     and max's own sessions can insert them. The flip is the dual-attest step
--     that follows this PR, not part of it.
--   - Any change to the trigger functions (correct as of #1424).
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1 + 2. Stamp built_by_callsign='scout' and attach the proof_gate_contract.
-- ---------------------------------------------------------------------------

SET LOCAL agency_os.callsign = 'scout';

UPDATE public.gate_roadmap
   SET built_by_callsign = 'scout',
       proof_gate_contract = '{
        "check_id": "docker_runtime_live_v1",
        "cmd": "bash scripts/proof_bar/docker_runtime_live_proof.sh",
        "expected_output_contains": [
            "DOCKER_RUNTIME_PROOF: host_user=elliotbot OK",
            "DOCKER_RUNTIME_PROOF: build OK",
            "DOCKER_RUNTIME_PROOF: run-marker asserted-from-runtime OK",
            "DOCKER_RUNTIME_PROOF: hello-world OK",
            "DOCKER_RUNTIME_PROOF: ALL PASS"
        ],
        "role_sep": {
            "builder": "scout",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[scout-docker-runtime-live-proof 2026-06-03] '
            || 'Stamped built_by_callsign=scout (was NULL — armed trg_04 + PR '
            || '#1415 watchdog; physical infra owner remains atlas). Attached '
            || 'proof_gate_contract check_id=docker_runtime_live_v1. cmd is the '
            || 'live proof_bar script (real docker build + run, asserted from '
            || 'the runtime). expected_output_contains targets the five '
            || 'DOCKER_RUNTIME_PROOF tokens the script emits only after each '
            || 'real assertion passes. trg_01 Check A pins run_cmd to cmd '
            || 'exactly, so pytest/mocked evidence is disqualified. proven-flip '
            || 'requires aiden + max binding_reviewer proof_runs (dual-attest).'
 WHERE id = 'ec883620-ee1c-454b-ba31-0263fd93aaa6'::uuid;


-- ---------------------------------------------------------------------------
-- 3. Inline DO-block negative self-test — trg_01 Check A MUST refuse a
--    mismatched-cmd proof_run flip. Transient fixtures rolled back via the
--    sentinel-raise / outer-EXCEPTION pattern (append-only table; no DELETE).
-- ---------------------------------------------------------------------------

DO $self_test$
DECLARE
    v_gate_id       uuid := gen_random_uuid();
    v_run_id        uuid;
    v_session_uuid  uuid := gen_random_uuid();
    v_msg           text;
BEGIN
    BEGIN  -- outer sub-tx: fixtures roll back when the sentinel below fires
        SET LOCAL agency_os.callsign = 'atlas';
        INSERT INTO public.gate_roadmap (
            id, component, phase, subphase, proof_gate, proof_gate_contract,
            status, required_attestation_kind, owner
        ) VALUES (
            v_gate_id,
            'docker_runtime_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline docker_runtime contract self-test row',
            '{
                "check_id": "docker_runtime_inline_self_test",
                "cmd": "bash scripts/proof_bar/docker_runtime_live_proof.sh",
                "expected_output_contains": ["DOCKER_RUNTIME_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        -- trg_06 session-independence needs a tool_call_log row for the
        -- attester's session_uuid (present in attester, absent in builder).
        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'docker_runtime_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/some_mock_test.py -v',  -- WRONG cmd (the disqualified pytest shape)
            'mocked output claiming DOCKER_RUNTIME_PROOF: ALL PASS but run_cmd is pytest not the script',
            repeat('d', 64),
            0,
            'aiden',
            v_session_uuid::text
        ) RETURNING id INTO v_run_id;

        SET LOCAL agency_os.callsign = 'dave';
        BEGIN  -- inner sub-tx: catches the expected check_violation
            UPDATE public.gate_roadmap
               SET status = 'proven', proof_run_id = v_run_id
             WHERE id = v_gate_id;
            RAISE EXCEPTION
                'DOCKER_RUNTIME_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch (pytest run_cmd != contract.cmd)'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'DOCKER_RUNTIME_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
            -- happy path: Check A raised exactly as expected; fall through
        END;

        RAISE EXCEPTION 'DOCKER_RUNTIME_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'DOCKER_RUNTIME_SELF_TEST_OK' THEN
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
-- end of 20260603_docker_runtime_proof_contract.sql
-- ============================================================================
