-- ============================================================================
-- 20260603_backups_dr_proof_contract.sql
--
-- Arms the backups_dr gate (gate_roadmap id
-- 9334d194-a182-45ad-a958-503dcf2a65e6, phase 4_infra) for a LIVE built→proven
-- attestation. KEI ref: orion-backups-dr-live-proof.
--
-- WHAT THIS MIGRATION DOES
--   1. Stamps gate_roadmap.built_by_callsign = 'orion' on the backups_dr row.
--      It was NULL — which left the attester≠builder gate UNARMED:
--        - trg_04 fn_gate_proof_no_self_attest RAISEs on NULL built_by_callsign
--          ("record the build transition first"), so NO binding_reviewer
--          proof_run could be inserted at all.
--      The row's status is already 'built', so the trg_03 capture-on-transition
--      branch does not fire; OLD.built_by_callsign IS NULL so the immutability
--      branch does not fire either — the explicit value passes the anti-spoof
--      branch because it matches the SET LOCAL agency_os.callsign caller below.
--      The physical infra owner stays whatever owner already records.
--
--   2. Attaches the structured proof_gate_contract:
--        cmd  = bash scripts/proof_bar/backups_dr_live_proof.sh
--        expected_output_contains = the BACKUPS_DR_PROOF tokens the script
--          emits ONLY after each real restore-to-staging assertion passes.
--        role_sep.builder = orion, attester = [aiden, max].
--      trg_01 Check A pins gate_proof_runs.run_cmd to contract.cmd EXACTLY, so
--      a pytest/mocked run_cmd is disqualified structurally (cmd_mismatch).
--      Check B requires every token in run_output (a mock cannot produce a real
--      pg_restore row-count match or a queryable restored Weaviate).
--
--   3. Inline DO-block negative self-test (Dave 2026-06-02 standing precedent,
--      same inner-sentinel-raise / outer-rollback pattern as the BASE +
--      docker_runtime contract migrations; gate_proof_runs is append-only,
--      trg_07 refuses DELETE): asserts trg_01 Check A REFUSES a mismatched-cmd
--      proof_run flip against a backups_dr-shaped contract. If the trigger
--      fails to block, the migration ABORTS.
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
-- 1 + 2. Stamp built_by_callsign='orion' and attach the proof_gate_contract.
-- ---------------------------------------------------------------------------

SET LOCAL agency_os.callsign = 'orion';

UPDATE public.gate_roadmap
   SET built_by_callsign = 'orion',
       proof_gate_contract = '{
        "check_id": "backups_dr_live_v1",
        "cmd": "bash scripts/proof_bar/backups_dr_live_proof.sh",
        "expected_output_contains": [
            "BACKUPS_DR_PROOF: db_schema_complete OK",
            "BACKUPS_DR_PROOF: db_restore_to_staging OK",
            "BACKUPS_DR_PROOF: db_rowcounts_match OK",
            "BACKUPS_DR_PROOF: memstore_restore_to_staging OK",
            "BACKUPS_DR_PROOF: memstore_recoverable OK",
            "BACKUPS_DR_PROOF: negative_corrupt_db_rejected OK",
            "BACKUPS_DR_PROOF: negative_corrupt_memstore_rejected OK",
            "BACKUPS_DR_PROOF: ALL PASS"
        ],
        "role_sep": {
            "builder": "orion",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[orion-backups-dr-live-proof 2026-06-03] '
            || 'Stamped built_by_callsign=orion (was NULL — armed trg_04 + the '
            || 'attester≠builder gate). Attached proof_gate_contract '
            || 'check_id=backups_dr_live_v1. cmd is the live proof_bar script: '
            || 'real pg_dump→pg_restore of DR-critical tables into a throwaway '
            || 'docker postgres with EXACT row-count fidelity + full-schema '
            || 'completeness (all public tables enumerated), and a real Weaviate '
            || 'nightly backup extracted + booted as a transient memory-capped '
            || 'node and queried. Negative sub-tests reject a truncated DB dump '
            || 'and a truncated memstore archive. trg_01 Check A pins run_cmd to '
            || 'cmd exactly, so pytest/mocked evidence is disqualified. proven-'
            || 'flip requires aiden + max binding_reviewer proof_runs (dual-'
            || 'attest). FINDINGS: (a) gate note "memory-store backup not done" '
            || 'is STALE — weaviate-backup.timer is active + daily tar.gz '
            || 'artifacts exist; what was never done is the RESTORE DRILL (now '
            || 'built). (b) memory store is Weaviate (live); Hindsight is the '
            || 'ratified MAL target, not yet the live store — flag for cutover. '
            || '(c) offsite target is Vultr Object Store per backup_postgres.sh, '
            || 'NOT Cloudflare R2 as the plan/notes say — plan-vs-impl '
            || 'discrepancy. (d) Weaviate backups are host-local only (not '
            || 'offsite); agent_memories restore requires pgvector in the '
            || 'recovery target.'
 WHERE id = '9334d194-a182-45ad-a958-503dcf2a65e6'::uuid;


-- ---------------------------------------------------------------------------
-- 3. Inline DO-block negative self-test — trg_01 Check A MUST refuse a
--    mismatched-cmd proof_run flip. Transient fixtures roll back via the
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
            'backups_dr_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline backups_dr contract self-test row',
            '{
                "check_id": "backups_dr_inline_self_test",
                "cmd": "bash scripts/proof_bar/backups_dr_live_proof.sh",
                "expected_output_contains": ["BACKUPS_DR_PROOF: ALL PASS"],
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
        VALUES ('aiden', v_session_uuid, 'backups_dr_self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'pytest tests/some_mock_test.py -v',  -- WRONG cmd (the disqualified pytest shape)
            'mocked output claiming BACKUPS_DR_PROOF: ALL PASS but run_cmd is pytest not the script',
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
                'BACKUPS_DR_SELF_TEST FAIL: UPDATE proven accepted; trg_01 was expected to refuse on Check A cmd mismatch (pytest run_cmd != contract.cmd)'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'BACKUPS_DR_SELF_TEST FAIL: unexpected check_violation (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
            -- happy path: Check A raised exactly as expected; fall through
        END;

        RAISE EXCEPTION 'BACKUPS_DR_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'BACKUPS_DR_SELF_TEST_OK' THEN
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
-- end of 20260603_backups_dr_proof_contract.sql
-- ============================================================================
