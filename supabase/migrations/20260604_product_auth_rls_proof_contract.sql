-- ============================================================================
-- 20260604_product_auth_rls_proof_contract.sql
--
-- Arms the product_auth_rls gate (gate_roadmap component product_auth_rls,
-- phase 6_product) for built→proven under the merge→deploy→prove rule.
-- KEI ref: scout-product-auth-rls-proof.
--
-- proof_gate prose: "real signup creates tenant; cross-tenant read returns zero
-- rows (RLS proven)".
--
-- The proof_bar (scripts/proof_bar/product_auth_rls_live_proof.sh) exercises the
-- REAL auth/RLS stack with ZERO production mutation (rolled back): inserting
-- auth.users fires handle_new_user (real signup → user + client + membership),
-- then under SET ROLE authenticated (a role WITHOUT bypassrls) with auth.uid()
-- driven from request.jwt.claims it asserts a POSITIVE CONTROL (userA sees >=1
-- own row — the non-vacuity guard) AND cross-tenant isolation (0 of tenant B's
-- rows). The connection role (postgres) has bypassrls, so the read MUST run as
-- authenticated or it would be a vacuous green.
--
--   1. Stamps built_by_callsign='scout'.
--   2. Wires deploy_trigger (rls-policies on the table = the deployed artifact).
--   3. Attaches proof_gate_contract: cmd = the proof_bar, role_sep builder=scout
--      attester=[aiden,max]. trg_01 Check A pins run_cmd → pytest/mocked
--      disqualified.
--   4. Inline negative self-test (sentinel-raise / outer-rollback) incl. repo_sha
--      per gate_proof_runs_repo_sha_binding_check.
-- ============================================================================

BEGIN;
SET LOCAL agency_os.callsign = 'scout';

UPDATE public.gate_roadmap
   SET built_by_callsign = 'scout',
       deploy_trigger = 'rls-policies:public.client_customers + ci:check_no_orphan_merge + proof_bar:product_auth_rls_live_proof.sh',
       proof_gate_contract = '{
        "check_id": "product_auth_rls_live_v1",
        "cmd": "bash scripts/proof_bar/product_auth_rls_live_proof.sh",
        "expected_output_contains": [
            "PRODUCT_AUTH_RLS_PROOF: signup-creates-tenant OK",
            "PRODUCT_AUTH_RLS_PROOF: positive-control own-rows-visible OK",
            "PRODUCT_AUTH_RLS_PROOF: cross-tenant-zero OK",
            "PRODUCT_AUTH_RLS_PROOF: ALL PASS"
        ],
        "role_sep": {
            "builder": "scout",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[scout-product-auth-rls-proof 2026-06-04] '
            || 'Attached proof_gate_contract check_id=product_auth_rls_live_v1. '
            || 'cmd is the live proof_bar: real signup (handle_new_user) creates '
            || 'tenant; under SET ROLE authenticated (no bypassrls) a positive '
            || 'control (own rows visible) + cross-tenant-zero prove RLS '
            || 'isolation non-vacuously. trg_01 Check A pins run_cmd → '
            || 'pytest/mocked disqualified.'
 WHERE id = (SELECT id FROM public.gate_roadmap WHERE component = 'product_auth_rls');


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
            'product_auth_rls_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline product_auth_rls contract self-test row',
            '{
                "check_id": "product_auth_rls_inline_self_test",
                "cmd": "bash scripts/proof_bar/product_auth_rls_live_proof.sh",
                "expected_output_contains": ["PRODUCT_AUTH_RLS_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'product_auth_rls_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid, repo_sha
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/test_rls_mock.py -v',  -- WRONG (disqualified pytest shape)
            'mocked output claiming PRODUCT_AUTH_RLS_PROOF: ALL PASS but run_cmd is pytest not the proof_bar',
            repeat('c', 64),
            0,
            'aiden',
            v_session_uuid::text,
            'selftest0000000000000000000000000000000c'  -- repo_sha_binding_check: len>=7
        ) RETURNING id INTO v_run_id;

        SET LOCAL agency_os.callsign = 'dave';
        BEGIN
            UPDATE public.gate_roadmap
               SET status = 'proven', proof_run_id = v_run_id
             WHERE id = v_gate_id;
            RAISE EXCEPTION
                'PRODUCT_AUTH_RLS_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'PRODUCT_AUTH_RLS_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
        END;

        RAISE EXCEPTION 'PRODUCT_AUTH_RLS_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'PRODUCT_AUTH_RLS_SELF_TEST_OK' THEN
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
-- end of 20260604_product_auth_rls_proof_contract.sql
-- ============================================================================
