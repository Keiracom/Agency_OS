-- ============================================================================
-- 20260604_product_gtm_proof_contract.sql
--
-- Arms the product_gtm gate (gate_roadmap id
-- f3f42557-40f5-4602-8239-ca09fa1da9e3, phase 6_product) for a built→proven
-- attestation under the merge→deploy→prove rule. KEI ref: scout-product-gtm-proof.
--
-- proof_gate prose: "1-pager + launch comms approved and ready".
--
-- product_gtm is a DOCS/ARTIFACT-readiness gate, not a runtime service. The
-- proof_bar (scripts/proof_bar/product_gtm_proof.sh) asserts the READY half —
-- the launch kit artifact (docs/launch/KEI-131_gtm_launch_kit.md) exists at the
-- committed repo_sha and contains the complete 1-pager (§1 incl. Pricing + CTA)
-- + launch comms (§2 email, §3 social). The APPROVED half is the Aiden+Max
-- dual-attest itself. Interpretation surfaced to Elliot before this PR.
--
-- WHAT THIS MIGRATION DOES
--   1. Stamps built_by_callsign='scout' (was NULL — arms trg_04 + PR #1415
--      watchdog; owner already scout).
--   2. Attaches proof_gate_contract: cmd = the proof_bar script, the
--      PRODUCT_GTM_PROOF tokens, role_sep builder=scout attester=[aiden,max].
--      trg_01 Check A pins run_cmd to cmd exactly → pytest/mocked disqualified.
--   3. Inline DO-block negative self-test (sentinel-raise / outer-rollback):
--      trg_01 Check A refuses a pytest-shaped run_cmd. ABORTS otherwise.
--
-- NON-GOALS: the flip itself (trg_11 needs aiden+max binding_reviewer proof_runs;
--   trg_08 write_guard means only their sessions insert them). No trigger changes.
-- ============================================================================

BEGIN;
SET LOCAL agency_os.callsign = 'scout';

UPDATE public.gate_roadmap
   SET built_by_callsign = 'scout',
       proof_gate_contract = '{
        "check_id": "product_gtm_ready_v1",
        "cmd": "bash scripts/proof_bar/product_gtm_proof.sh",
        "expected_output_contains": [
            "PRODUCT_GTM_PROOF: one-pager complete OK",
            "PRODUCT_GTM_PROOF: launch-comms complete OK",
            "PRODUCT_GTM_PROOF: artifact committed repo_sha=",
            "PRODUCT_GTM_PROOF: ALL PASS"
        ],
        "role_sep": {
            "builder": "scout",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[scout-product-gtm-proof 2026-06-04] '
            || 'Stamped built_by_callsign=scout. Attached proof_gate_contract '
            || 'check_id=product_gtm_ready_v1. cmd is the artifact-readiness '
            || 'proof_bar over docs/launch/KEI-131_gtm_launch_kit.md (1-pager + '
            || 'launch comms; asserts sections present + committed at repo_sha). '
            || 'READY is mechanically proven; APPROVED = the aiden+max dual-'
            || 'attest. trg_01 Check A pins run_cmd → pytest/mocked disqualified.'
 WHERE id = 'f3f42557-40f5-4602-8239-ca09fa1da9e3'::uuid;


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
            'product_gtm_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline product_gtm contract self-test row',
            '{
                "check_id": "product_gtm_inline_self_test",
                "cmd": "bash scripts/proof_bar/product_gtm_proof.sh",
                "expected_output_contains": ["PRODUCT_GTM_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'product_gtm_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid, repo_sha
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/test_gtm_mock.py -v',  -- WRONG (disqualified pytest shape)
            'mocked output claiming PRODUCT_GTM_PROOF: ALL PASS but run_cmd is pytest not the proof_bar',
            repeat('f', 64),
            0,
            'aiden',
            v_session_uuid::text,
            'selftest0000000000000000000000000000000a'  -- repo_sha_binding_check: len>=7
        ) RETURNING id INTO v_run_id;

        SET LOCAL agency_os.callsign = 'dave';
        BEGIN
            UPDATE public.gate_roadmap
               SET status = 'proven', proof_run_id = v_run_id
             WHERE id = v_gate_id;
            RAISE EXCEPTION
                'PRODUCT_GTM_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'PRODUCT_GTM_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
        END;

        RAISE EXCEPTION 'PRODUCT_GTM_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'PRODUCT_GTM_SELF_TEST_OK' THEN
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
-- end of 20260604_product_gtm_proof_contract.sql
-- ============================================================================
