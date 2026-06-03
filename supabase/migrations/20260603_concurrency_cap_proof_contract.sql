-- ============================================================================
-- 20260603_concurrency_cap_proof_contract.sql
--
-- Formalizes the concurrency cap (PR #1433 — merged + enabled + live-smoke-
-- verified, ceo:decision:concurrency_cap_2026-06-04) as a PROVEN-eligible
-- gate_roadmap row. Head-of-Ops directive 2026-06-03: it was reported proven
-- without a ledger row — this creates the row + arms it for dual-attest.
-- KEI ref: orion-concurrency-cap-live-proof.
--
-- WHAT THIS MIGRATION DOES
--   1. Creates gate_roadmap component='concurrency_cap', phase='0_foundation',
--      status='built', required_attestation_kind='binding_reviewer'. Under
--      SET LOCAL agency_os.callsign='orion', trg_03 auto-captures
--      built_by_callsign='orion' on the status='built' INSERT (and the explicit
--      value matches the caller, so anti-spoof passes).
--   2. Attaches the structured proof_gate_contract:
--        cmd  = bash scripts/proof_bar/concurrency_cap_live_proof.sh
--        expected_output_contains = the CONCURRENCY_CAP_PROOF tokens the script
--          emits ONLY after each real enforcement assertion passes (production
--          reservation Lua run against the LIVE Redis).
--        role_sep.builder = orion, attester = [aiden, max].
--      trg_01 Check A pins gate_proof_runs.run_cmd to contract.cmd EXACTLY, so
--      a pytest/mocked run_cmd is disqualified; Check B requires every token.
--   3. Inline DO-block negative self-test (Dave 2026-06-02 standing precedent):
--      asserts trg_01 Check A REFUSES a mismatched-cmd proof_run flip. Migration
--      ABORTS if the trigger fails to block.
--
-- status stays 'built'. The built→proven flip requires aiden + max
-- binding_reviewer proof_runs (trg_11 dual-attest); that is the step AFTER this.
-- Idempotent: ON CONFLICT (component) refreshes the contract.
-- ============================================================================

BEGIN;

SET LOCAL agency_os.callsign = 'orion';

INSERT INTO public.gate_roadmap
    (component, phase, proof_gate, proof_gate_contract, status,
     required_attestation_kind, built_by_callsign, owner, notes)
VALUES (
    'concurrency_cap',
    '0_foundation',
    'concurrency cap enforces the N=6 ceiling with deliberator+reviewer stage-pair reservation; overflow acquire refused; measured peak RSS+swap under the RAM ceiling',
    '{
        "check_id": "concurrency_cap_live_v1",
        "cmd": "bash scripts/proof_bar/concurrency_cap_live_proof.sh",
        "expected_output_contains": [
            "CONCURRENCY_CAP_PROOF: wiring OK",
            "CONCURRENCY_CAP_PROOF: deliberators_reserved OK",
            "CONCURRENCY_CAP_PROOF: reviewers_coreside OK",
            "CONCURRENCY_CAP_PROOF: gated_ceiling_holds OK",
            "CONCURRENCY_CAP_PROOF: overflow_refused OK",
            "CONCURRENCY_CAP_PROOF: deliberator_never_starved OK",
            "CONCURRENCY_CAP_PROOF: ram_ceiling OK",
            "CONCURRENCY_CAP_PROOF: ALL PASS"
        ],
        "role_sep": {"builder": "orion", "attester": ["aiden", "max"]},
        "negative_test_required": true
    }'::jsonb,
    'built',
    'binding_reviewer',
    'orion',
    'orion',
    'KEI orion-concurrency-cap-live-proof 2026-06-03 (Head-of-Ops directive). Formalizes the merged+enabled concurrency cap (PR #1433, ceo:decision:concurrency_cap_2026-06-04) as a ledger-proven gate. proof_gate_contract.cmd is a LIVE enforcement proof: the production reservation Lua (src/dispatcher/concurrency_cap.py ACQUIRE_LUA/RELEASE_LUA) executed against the live Redis on an isolated proof: key namespace — asserts the 2 deliberators are reserved, the 2 reviewers co-reside, the gated ceiling holds (total=5), the overflow acquire at N=6 is REFUSED (load-bearing negative), no role starvation, and measured worst-case peak RSS+swap stays under the RAM ceiling (scripts/measure_session_rss.py). proven-flip requires aiden + max binding_reviewer proof_runs.'
)
ON CONFLICT (component) DO UPDATE
   SET proof_gate_contract = EXCLUDED.proof_gate_contract,
       proof_gate          = EXCLUDED.proof_gate;


-- ---------------------------------------------------------------------------
-- Inline DO-block negative self-test — trg_01 Check A MUST refuse a
-- mismatched-cmd proof_run flip (sentinel-raise / outer-rollback; append-only
-- table, trg_07 refuses DELETE).
-- ---------------------------------------------------------------------------

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
            'concurrency_cap_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline concurrency_cap contract self-test row',
            '{
                "check_id": "concurrency_cap_inline_self_test",
                "cmd": "bash scripts/proof_bar/concurrency_cap_live_proof.sh",
                "expected_output_contains": ["CONCURRENCY_CAP_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'concurrency_cap_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/some_mock_test.py -v',  -- WRONG cmd (disqualified pytest shape)
            'mocked output claiming CONCURRENCY_CAP_PROOF: ALL PASS but run_cmd is pytest not the script',
            repeat('d', 64),
            0,
            'aiden',
            v_session_uuid::text
        ) RETURNING id INTO v_run_id;

        SET LOCAL agency_os.callsign = 'dave';
        BEGIN
            UPDATE public.gate_roadmap
               SET status = 'proven', proof_run_id = v_run_id
             WHERE id = v_gate_id;
            RAISE EXCEPTION
                'CONCURRENCY_CAP_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'CONCURRENCY_CAP_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
        END;

        RAISE EXCEPTION 'CONCURRENCY_CAP_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'CONCURRENCY_CAP_SELF_TEST_OK' THEN
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
-- end of 20260603_concurrency_cap_proof_contract.sql
-- ============================================================================
