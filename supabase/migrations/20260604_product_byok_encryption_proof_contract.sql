-- ============================================================================
-- 20260604_product_byok_encryption_proof_contract.sql
--
-- Arms the product_byok_encryption gate (gate_roadmap component
-- product_byok_encryption, phase 6_product) for built→proven under the
-- merge→deploy→prove rule. KEI ref: scout-product-byok-encryption-proof.
--
-- proof_gate prose: "customer key stored encrypted, retrieved, used for a real
-- model call; plaintext never in DB".
--
-- The proof_bar (scripts/proof_bar/product_byok_encryption_live_proof.sh) drives
-- the REAL KEI-116 encryption-at-rest service (src/security/customer_api_keys.py,
-- pgcrypto pgp_sym_encrypt/decrypt): store_key → read raw encrypted_key bytea
-- (assert plaintext bytes absent) → decrypt_key roundtrip → lookup_by_hash →
-- plus the module's own "refuse to store with no master key" negative control.
-- Test row self-cleaned (DELETE on exit); verified zero leaked rows.
--
-- HONEST BOUNDARY (documented for attesters): proves the encryption-at-rest
-- clauses (stored encrypted / retrieved / plaintext-never-in-DB). The "used for
-- a real model call" clause is the LLM/launcher path (product_litellm_router
-- domain), out of this security gate's scope + clear of launcher services.
-- Uses a TEST master key (prod CUSTOMER_KEY_ENCRYPTION_KEY absent from the proof
-- env; the at-rest property is key-agnostic — pgp_sym takes any passphrase).
--
--   1. Stamps built_by_callsign='scout'.
--   2. Wires deploy_trigger (the KEI-116 security service = deployed artifact).
--   3. Attaches proof_gate_contract (role_sep builder=scout attester=[aiden,max]);
--      trg_01 Check A pins run_cmd → pytest/mocked disqualified.
--   4. Inline negative self-test incl. repo_sha (gate_proof_runs_repo_sha_binding_check).
-- ============================================================================

BEGIN;
SET LOCAL agency_os.callsign = 'scout';

UPDATE public.gate_roadmap
   SET built_by_callsign = 'scout',
       deploy_trigger = 'security-service:src/security/customer_api_keys.py + ci:check_no_orphan_merge + proof_bar:product_byok_encryption_live_proof.sh',
       proof_gate_contract = '{
        "check_id": "product_byok_encryption_live_v1",
        "cmd": "bash scripts/proof_bar/product_byok_encryption_live_proof.sh",
        "expected_output_contains": [
            "PRODUCT_BYOK_PROOF: stored-encrypted OK",
            "PRODUCT_BYOK_PROOF: plaintext-never-in-db OK",
            "PRODUCT_BYOK_PROOF: retrieved-roundtrip OK",
            "PRODUCT_BYOK_PROOF: refuse-unencrypted-negative-control OK",
            "PRODUCT_BYOK_PROOF: ALL PASS"
        ],
        "role_sep": {
            "builder": "scout",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[scout-product-byok-encryption-proof 2026-06-04] '
            || 'Attached proof_gate_contract check_id=product_byok_encryption_live_v1. '
            || 'cmd drives the real KEI-116 customer_api_keys encryption service '
            || '(pgp_sym_encrypt): store→raw-bytea-has-no-plaintext→decrypt '
            || 'roundtrip→hash-lookup + refuse-unencrypted negative control; '
            || 'self-cleaned test row. HONEST BOUNDARY: proves encryption-at-rest; '
            || 'the "used for a real model call" clause is the LLM/launcher path '
            || '(out of scope). Test master key (prod key absent; property is '
            || 'key-agnostic). trg_01 Check A pins run_cmd → pytest/mocked '
            || 'disqualified.'
 WHERE id = (SELECT id FROM public.gate_roadmap WHERE component = 'product_byok_encryption');


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
            'product_byok_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline product_byok_encryption contract self-test row',
            '{
                "check_id": "product_byok_inline_self_test",
                "cmd": "bash scripts/proof_bar/product_byok_encryption_live_proof.sh",
                "expected_output_contains": ["PRODUCT_BYOK_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'product_byok_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid, repo_sha
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/test_byok_mock.py -v',  -- WRONG (disqualified pytest shape)
            'mocked output claiming PRODUCT_BYOK_PROOF: ALL PASS but run_cmd is pytest not the proof_bar',
            repeat('d', 64),
            0,
            'aiden',
            v_session_uuid::text,
            'selftest0000000000000000000000000000000d'  -- repo_sha_binding_check: len>=7
        ) RETURNING id INTO v_run_id;

        SET LOCAL agency_os.callsign = 'dave';
        BEGIN
            UPDATE public.gate_roadmap
               SET status = 'proven', proof_run_id = v_run_id
             WHERE id = v_gate_id;
            RAISE EXCEPTION
                'PRODUCT_BYOK_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'PRODUCT_BYOK_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
        END;

        RAISE EXCEPTION 'PRODUCT_BYOK_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'PRODUCT_BYOK_SELF_TEST_OK' THEN
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
-- end of 20260604_product_byok_encryption_proof_contract.sql
-- ============================================================================
