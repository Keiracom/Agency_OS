-- ============================================================================
-- 20260603_weaviate_offsite_backup_proof_contract.sql
--
-- Creates + arms the weaviate_offsite_backup gate (phase 4_infra). Closes the
-- ratified HARD GATE (ceo:vultr_infrastructure_ratified: weaviate_snapshot
-- offsite = Cloudflare R2, hard gate before ceo_memory decommission). The
-- offsite pipeline existed (KEI-242) but was NEVER WIRED — 0 snapshots had ever
-- reached R2, so there was NO offsite memory-store backup. This row formalizes
-- the now-wired + proven offsite round-trip. KEI ref: orion-weaviate-offsite-r2.
--
-- WHAT THIS MIGRATION DOES
--   1. Creates gate_roadmap component='weaviate_offsite_backup', phase='4_infra',
--      status='built', built_by_callsign='orion' (trg_03 capture on the
--      status='built' INSERT under SET LOCAL agency_os.callsign='orion').
--   2. Attaches proof_gate_contract: cmd=the live round-trip proof_bar script,
--      expected_output_contains=the WEAVIATE_OFFSITE_PROOF tokens emitted only
--      after each real assertion (snapshot→R2 upload, R2 object confirmed,
--      fetch-back + structural restore-verify, too-small-snapshot guard).
--      role_sep builder=orion attester=[aiden, max].
--   3. Inline DO-block Check-A negative self-test (sentinel-raise / outer-
--      rollback; append-only table). Migration ABORTS if trg_01 fails to block.
--
-- status stays 'built'; proven-flip requires aiden + max binding_reviewer
-- proof_runs (trg_11 dual-attest). Idempotent via ON CONFLICT (component).
-- ============================================================================

BEGIN;

SET LOCAL agency_os.callsign = 'orion';

INSERT INTO public.gate_roadmap
    (component, phase, proof_gate, proof_gate_contract, status,
     required_attestation_kind, built_by_callsign, owner, notes)
VALUES (
    'weaviate_offsite_backup',
    '4_infra',
    'Weaviate snapshot reaches Cloudflare R2 offsite and is restorable end-to-end: snapshot -> R2 upload -> fetch-back -> structural restore-verify (ratified hard gate)',
    '{
        "check_id": "weaviate_offsite_backup_live_v1",
        "cmd": "bash scripts/proof_bar/weaviate_offsite_backup_live_proof.sh",
        "expected_output_contains": [
            "WEAVIATE_OFFSITE_PROOF: modules_present OK",
            "WEAVIATE_OFFSITE_PROOF: timer_wired OK",
            "WEAVIATE_OFFSITE_PROOF: snapshot_uploaded_to_r2 OK",
            "WEAVIATE_OFFSITE_PROOF: r2_object_confirmed OK",
            "WEAVIATE_OFFSITE_PROOF: restore_verify_recoverable OK",
            "WEAVIATE_OFFSITE_PROOF: negative_small_snapshot_refused OK",
            "WEAVIATE_OFFSITE_PROOF: ALL PASS"
        ],
        "role_sep": {"builder": "orion", "attester": ["aiden", "max"]},
        "negative_test_required": true
    }'::jsonb,
    'built',
    'binding_reviewer',
    'orion',
    'orion',
    'KEI orion-weaviate-offsite-r2 2026-06-03 (Head-of-Ops directive, surfaced to Dave). Closes the backups_dr finding: Weaviate snapshots were HOST-LOCAL-ONLY — the ratified R2 offsite hard gate (ceo:vultr_infrastructure_ratified) was UNMET (0 snapshots in R2). The offsite pipeline existed (KEI-242: weaviate_snapshot.py/r2.py/restore_verify.py) but was never wired to a timer. This wires weaviate-snapshot.timer (daily 04:30 UTC → R2), converts restore_verify to STRUCTURAL recoverability (the on-host :8099 boot hit the raft node-identity node1:8300 never-ready failure; Weaviate recovery is node-replacement), and proves the round-trip live. Target corrected from the dispatch: R2 not Vultr Object Store (Vultr = daily_image only) — caught via canonical-key query. proven-flip requires aiden + max binding_reviewer proof_runs.'
)
ON CONFLICT (component) DO UPDATE
   SET proof_gate_contract = EXCLUDED.proof_gate_contract,
       proof_gate          = EXCLUDED.proof_gate;


-- ---------------------------------------------------------------------------
-- Inline Check-A negative self-test.
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
            'weaviate_offsite_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline weaviate_offsite contract self-test row',
            '{
                "check_id": "weaviate_offsite_inline_self_test",
                "cmd": "bash scripts/proof_bar/weaviate_offsite_backup_live_proof.sh",
                "expected_output_contains": ["WEAVIATE_OFFSITE_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'weaviate_offsite_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/some_mock_test.py -v',  -- WRONG cmd (disqualified pytest shape)
            'mocked output claiming WEAVIATE_OFFSITE_PROOF: ALL PASS but run_cmd is pytest not the script',
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
                'WEAVIATE_OFFSITE_SELF_TEST FAIL: UPDATE proven accepted; trg_01 expected to refuse on Check A cmd mismatch'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'WEAVIATE_OFFSITE_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
        END;

        RAISE EXCEPTION 'WEAVIATE_OFFSITE_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'WEAVIATE_OFFSITE_SELF_TEST_OK' THEN
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
-- end of 20260603_weaviate_offsite_backup_proof_contract.sql
-- ============================================================================
