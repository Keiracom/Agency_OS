-- ============================================================================
-- 20260604_persona_bank_reasoning_headers_proof_contract.sql
--
-- Claims + arms gate_roadmap component persona_bank_reasoning_headers
-- (phase 2_chain) not_started → built, and attaches its proof contract.
-- KEI ref: orion-persona-reasoning-headers.
--
-- WHAT THIS MIGRATION DOES
--   1. not_started → built, built_by_callsign='orion' (trg_03 capture; explicit
--      value matches the SET LOCAL caller). Wires deploy_trigger so the
--      check_no_orphan_merge CI gate stays green.
--   2. Attaches proof_gate_contract: cmd = the live proof_bar script; tokens =
--      the PERSONA_REASONING_PROOF milestones; role_sep builder=orion
--      attester=[aiden,max].
--   3. Inline DO-block Check-A negative self-test (sentinel-raise / outer-
--      rollback; repo_sha set per gate_proof_runs_repo_sha_binding_check).
--
-- PROOF BOUNDARY (recorded in notes — attest against THIS, do not later assume
--   full emission is proven): proven = the persona CONTRACT specifies the five
--   deliberation headers AND the deterministic parser ENFORCES them (real
--   negative test). Live-LLM EMISSION is DEFERRED to a post-LLM-restore chain
--   run (LLM excluded now).
--
-- status stays 'built'; proven-flip requires aiden + max binding_reviewer
-- proof_runs (trg_11 dual-attest). Idempotent via ON CONFLICT (component).
-- ============================================================================

BEGIN;

SET LOCAL agency_os.callsign = 'orion';

UPDATE public.gate_roadmap
   SET status = 'built',
       built_by_callsign = 'orion',
       deploy_trigger = 'migration:20260604_persona_bank_reasoning_headers_proof_contract.sql + ci:check_no_orphan_merge + proof_bar:persona_bank_reasoning_headers_live_proof.sh',
       proof_gate_contract = '{
        "check_id": "persona_bank_reasoning_headers_v1",
        "cmd": "bash scripts/proof_bar/persona_bank_reasoning_headers_live_proof.sh",
        "expected_output_contains": [
            "PERSONA_REASONING_PROOF: personas_carry_schema OK",
            "PERSONA_REASONING_PROOF: parser_extracts_wellformed OK",
            "PERSONA_REASONING_PROOF: parser_rejects_incomplete OK",
            "PERSONA_REASONING_PROOF: ALL PASS"
        ],
        "role_sep": {"builder": "orion", "attester": ["aiden", "max"]},
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[orion-persona-reasoning-headers 2026-06-04] '
            || 'not_started→built. Added the 5-header structured deliberation '
            || 'block (DECISION/CHALLENGE/TRADEOFFS/REJECTED/ATTRIBUTION) to '
            || 'personas/v1_chain/{nova,orion,atlas}.md + a deterministic parser '
            || '(src/keiracom_system/chain/deliberation_headers.py) the Reasoning '
            || 'Listener uses. PROOF BOUNDARY (attest against this): proven = the '
            || 'persona CONTRACT specifies the 5 headers AND the parser ENFORCES '
            || 'them (real negative test: 5 missing-header cases + 1 empty all '
            || 'rejected). Live-LLM EMISSION is DEFERRED to a post-LLM-restore '
            || 'chain run — NOT proven here (LLM excluded). Do not later assume '
            || 'full emission is proven. proven-flip requires aiden + max '
            || 'binding_reviewer proof_runs.'
 WHERE component = 'persona_bank_reasoning_headers';


-- ---------------------------------------------------------------------------
-- Inline Check-A negative self-test — trg_01 MUST refuse a pytest-shaped
-- run_cmd. Transient fixtures roll back via the sentinel pattern.
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
            'persona_reasoning_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline persona_reasoning contract self-test row',
            '{
                "check_id": "persona_reasoning_inline_self_test",
                "cmd": "bash scripts/proof_bar/persona_bank_reasoning_headers_live_proof.sh",
                "expected_output_contains": ["PERSONA_REASONING_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'persona_reasoning_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid, repo_sha
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/some_mock_test.py -v',  -- WRONG cmd (disqualified pytest shape)
            'mocked output claiming PERSONA_REASONING_PROOF: ALL PASS but run_cmd is pytest not the proof_bar',
            repeat('d', 64),
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
                'PERSONA_REASONING_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'PERSONA_REASONING_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
        END;

        RAISE EXCEPTION 'PERSONA_REASONING_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'PERSONA_REASONING_SELF_TEST_OK' THEN
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
-- end of 20260604_persona_bank_reasoning_headers_proof_contract.sql
-- ============================================================================
