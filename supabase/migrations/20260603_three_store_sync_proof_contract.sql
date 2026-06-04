-- ============================================================================
-- 20260603_three_store_sync_proof_contract.sql
--
-- Arms the three_store_sync gate (gate_roadmap id
-- 4d791647-ead7-444c-b639-1b683a82c85c, phase 4_infra) for a LIVE built→proven
-- attestation. KEI ref: scout-three-store-sync-live-proof.
--
-- proof_gate prose: "bd/Postgres/Linear stay consistent through
-- create+complete+cancel; reconciler catches injected drift; no loop".
--
-- WHAT THIS MIGRATION DOES
--   1. Stamps gate_roadmap.built_by_callsign = 'scout' on the three_store_sync
--      row (was NULL — which left the attester≠builder gate UNARMED: trg_04
--      RAISEs on NULL built_by_callsign, and the PR #1415 watchdog keys on it).
--      Per the docker_runtime precedent (#1435) the stamp value is 'scout'
--      (author of this proof mechanism). OLD.built_by_callsign IS NULL so the
--      trg_03 immutability branch does not fire and the explicit value passes.
--
--   2. Attaches the structured proof_gate_contract:
--        cmd  = bash scripts/proof_bar/three_store_sync_live_proof.sh
--        expected_output_contains = the five THREE_STORE_PROOF tokens the
--          script emits ONLY after each live assertion passes.
--        role_sep.builder = scout, attester = [aiden, max].
--      trg_01 Check A pins run_cmd to contract.cmd EXACTLY, so a pytest/mocked
--      run_cmd is disqualified structurally (cmd_mismatch). This matters here
--      because the existing tests/scripts/test_reconcile_three_stores.py suite
--      is entirely mock-based; the directive's NEGATIVE bar requires the live
--      script, not that suite.
--
--   3. Inline DO-block negative self-test (same inner-sentinel-raise /
--      outer-rollback pattern as #1435 + the BASE/trigger-fix migrations):
--      asserts trg_01 Check A REFUSES a pytest-shaped mismatched-cmd proof_run
--      flip against a three_store_sync-shaped contract. Migration ABORTS if the
--      trigger fails to block.
--
-- WHAT THE LIVE PROOF COVERS (and a documented scope note)
--   The proof_bar script runs the REAL reconciler (scripts/reconcile_three_-
--   stores.py) against the THREE REAL stores and asserts: (a) all three are
--   read and real KEIs reconcile (in_all_three>0); (b) the production
--   detect_drift catches injected drift (missing_bd + field_drift); (c) no loop
--   — a real dry-run mutates nothing (public.tasks count + max(updated_at)
--   unchanged), proving the KEI-237 flag-only design.
--
--   SCOPE NOTE for attesters: the prose clause "consistent through
--   create+complete+cancel" implies a write round-trip. A live write round-trip
--   would require WRITING Linear, which is forbidden (Linear read-only LAW,
--   PreToolUse-hook-blocked) and architecturally superseded (Postgres-is-SSOT,
--   Linear demoted 2026-06-02). A public.tasks probe INSERT also fires
--   fn_emit_sync_event_postgres (a 'create' sync_event) — the exact feedback
--   path the "no loop" clause guards against. The reconciler IS the cross-store
--   consistency-verification mechanism for this gate; proving it live (read all
--   three + catch drift + flag-only/no-loop) is the faithful, executable proof.
--   Injected drift is therefore added to the live-fetched join in memory, never
--   to a store. Surfaced to Elliot 2026-06-03 before this PR.
--
-- NON-GOALS: the built→proven flip itself (trg_11 needs BOTH aiden AND max
--   binding_reviewer proof_runs; trg_08 write_guard means only their own
--   sessions can insert them — the dual-attest step after this PR). No change to
--   the trigger functions (correct as of #1424).
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1 + 2. Stamp built_by_callsign='scout' and attach the proof_gate_contract.
-- ---------------------------------------------------------------------------

SET LOCAL agency_os.callsign = 'scout';

UPDATE public.gate_roadmap
   SET built_by_callsign = 'scout',
       proof_gate_contract = '{
        "check_id": "three_store_sync_live_v1",
        "cmd": "bash scripts/proof_bar/three_store_sync_live_proof.sh",
        "expected_output_contains": [
            "THREE_STORE_PROOF: stores_read all-three nonzero OK",
            "THREE_STORE_PROOF: no-loop reconciler-zero-writes OK",
            "THREE_STORE_PROOF: stores-reconcile in_all_three OK",
            "THREE_STORE_PROOF: injected-drift-caught missing_bd+field_drift OK",
            "THREE_STORE_PROOF: ALL PASS"
        ],
        "role_sep": {
            "builder": "scout",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[scout-three-store-sync-live-proof 2026-06-03] '
            || 'Stamped built_by_callsign=scout (was NULL — armed trg_04 + PR '
            || '#1415 watchdog). Attached proof_gate_contract '
            || 'check_id=three_store_sync_live_v1. cmd is the live proof_bar '
            || 'script: runs the real reconcile_three_stores.py against all 3 '
            || 'REAL stores (bd/Postgres/Linear), asserts stores reconcile '
            || '(in_all_three>0), the production detect_drift catches injected '
            || 'missing_bd + field_drift, and the dry-run is flag-only (no loop: '
            || 'zero public.tasks writes). trg_01 Check A pins run_cmd to cmd '
            || 'exactly, so pytest/mocked evidence is disqualified. Scope note: '
            || 'the create+complete+cancel lifecycle clause is not live-'
            || 'executable under the Linear read-only LAW (Postgres-is-SSOT); '
            || 'see migration header. proven-flip requires aiden + max '
            || 'binding_reviewer proof_runs (dual-attest).'
 WHERE id = '4d791647-ead7-444c-b639-1b683a82c85c'::uuid;


-- ---------------------------------------------------------------------------
-- 3. Inline DO-block negative self-test — trg_01 Check A MUST refuse a
--    pytest-shaped mismatched-cmd proof_run flip. Transient fixtures roll back
--    via the sentinel-raise / outer-EXCEPTION pattern (append-only table; no
--    DELETE).
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
            'three_store_sync_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline three_store_sync contract self-test row',
            '{
                "check_id": "three_store_sync_inline_self_test",
                "cmd": "bash scripts/proof_bar/three_store_sync_live_proof.sh",
                "expected_output_contains": ["THREE_STORE_PROOF: ALL PASS"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'three_store_sync_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/scripts/test_reconcile_three_stores.py -v',  -- WRONG (disqualified pytest shape)
            'mocked output claiming THREE_STORE_PROOF: ALL PASS but run_cmd is pytest not the live script',
            repeat('e', 64),
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
                'THREE_STORE_SYNC_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch (pytest run_cmd != contract.cmd)'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'THREE_STORE_SYNC_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
            -- happy path: Check A raised exactly as expected; fall through
        END;

        RAISE EXCEPTION 'THREE_STORE_SYNC_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'THREE_STORE_SYNC_SELF_TEST_OK' THEN
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
-- end of 20260603_three_store_sync_proof_contract.sql
-- ============================================================================
