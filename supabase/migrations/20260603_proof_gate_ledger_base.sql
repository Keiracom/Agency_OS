-- ============================================================================
-- 20260603_proof_gate_ledger_base.sql
--
-- proof_gate_ledger BASE — Phase 1 nucleus.
-- KEI ref: atlas-proof-gate-ledger-base-build.
-- gate_roadmap row: id = 8ccca6bc-6478-4f8e-a173-0500474d8b41 (per
-- ceo:keiracom:proof_gate_ledger_design_v1, Aiden 2026-06-03).
--
-- BASE SCOPE ONLY — reasoning_capture (the amendment) is NOT in this PR; it
-- follows after Aiden fixes Max's three gaps post context cycle.
--
-- WHAT THIS MIGRATION DOES
--   1. Adds gate_roadmap.proof_gate_contract jsonb (additive, nullable).
--      Existing free-prose proof_gate text rows are NOT auto-migrated —
--      migration is a follow-on (per dispatch brief).
--   2. Updates fn_verify_before_proven (trg_01) to enforce, when
--      NEW.proof_gate_contract IS NOT NULL, three runtime checks against
--      the proof_run NEW.proof_run_id points at:
--        - Check A: gate_proof_runs.run_cmd = contract.cmd (exact match)
--        - Check B: gate_proof_runs.run_output contains EVERY substring in
--          contract.expected_output_contains (AND-semantics)
--        - Check C: gate_proof_runs.attesting_callsign != contract
--          .role_sep.builder (role separation)
--      Any check fails → RAISE EXCEPTION (rollback, no status flip).
--      trg_01 still fires before trg_11 (alphabetical name order), so the
--      contract gate runs ahead of the dual-attest gate on proven-flip.
--   3. Seeds the proof_gate_ledger dogfood row with status='built' and a
--      proof_gate_contract that points at the four named pytest tests
--      this PR ships (the load-bearing contract tokens from the design
--      doc). proven-flip is the binding_reviewer pair's job, not this PR.
--   4. Inline DO-block self-test (Dave addendum precedent from the
--      20260602 gate_roadmap_proof_gate migration): the migration apply
--      ITSELF asserts the new trigger refuses a mismatched proof_run. If
--      the trigger fails to block, the migration aborts.
--
-- NON-GOALS (deliberate, by brief):
--   - reasoning_records table + DB CHECK source='temporal_activity'.
--   - capture_hop_reasoning Temporal activity.
--   - Auto-migration of existing free-prose proof_gate rows.
--   - proven-flip of the proof_gate_ledger dogfood row itself — that's a
--     separate binding_reviewer attestation step.
--
-- The dogfood contract.cmd value MUST match the runtime command an
-- attester will run on the dogfood row, character-for-character. If the
-- cmd shape changes later, follow-on migrations must replace the contract
-- in place (proof_gate_contract is a column on a row, not immutable).
-- ============================================================================

BEGIN;
SET LOCAL agency_os.callsign = 'dave';


-- ---------------------------------------------------------------------------
-- 1. proof_gate_contract column (additive).
-- ---------------------------------------------------------------------------

ALTER TABLE public.gate_roadmap
    ADD COLUMN IF NOT EXISTS proof_gate_contract jsonb;

COMMENT ON COLUMN public.gate_roadmap.proof_gate_contract IS
    'Structured proof contract enforced by fn_verify_before_proven (trg_01) '
    'on status→proven flips. Shape: {check_id text, cmd text, '
    'expected_output_contains text[], role_sep {builder text, attester text[]}, '
    'negative_test_required boolean}. NULL = legacy free-prose proof_gate row, '
    'trigger keeps existing behaviour. See 20260603_proof_gate_ledger_base.sql.';


-- ---------------------------------------------------------------------------
-- 2. fn_verify_before_proven — Phase 1 contract Checks A/B/C added.
--    Old behaviour (proof_run_id set + linked + exit_code=0) is preserved
--    unchanged; the new checks fire only when proof_gate_contract IS NOT NULL.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.fn_verify_before_proven()
RETURNS trigger LANGUAGE plpgsql AS $function$
DECLARE
    v_contract       jsonb;
    v_run_cmd        text;
    v_run_output     text;
    v_attesting_cs   text;
    v_expected_cmd   text;
    v_expected_subs  text[];
    v_builder        text;
    v_substr         text;
BEGIN
    IF NEW.status = 'proven' AND (OLD.status IS NULL OR OLD.status IS DISTINCT FROM 'proven') THEN
        -- Existing check #1: proof_run_id must be set.
        IF NEW.proof_run_id IS NULL THEN
            RAISE EXCEPTION
                'gate_roadmap proven-requires-proof-run: status=proven requires proof_run_id to pin which gate_proof_runs row justified the transition.'
                USING ERRCODE = 'check_violation';
        END IF;

        -- Existing check #2: proof_run linked + exit_code=0.
        IF NOT EXISTS (
            SELECT 1 FROM public.gate_proof_runs
             WHERE id              = NEW.proof_run_id
               AND gate_roadmap_id = NEW.id
               AND exit_code       = 0
        ) THEN
            RAISE EXCEPTION
                'gate_roadmap proven-requires-proof-run: proof_run_id=% missing, not linked to gate_roadmap_id=%, or failed (exit_code != 0).',
                NEW.proof_run_id, NEW.id
                USING ERRCODE = 'check_violation';
        END IF;

        -- ── Phase 1 nucleus: proof_gate_contract Checks A/B/C ─────────────
        v_contract := NEW.proof_gate_contract;
        IF v_contract IS NOT NULL THEN
            SELECT run_cmd, run_output, attesting_callsign
              INTO v_run_cmd, v_run_output, v_attesting_cs
              FROM public.gate_proof_runs
             WHERE id = NEW.proof_run_id;

            v_expected_cmd  := v_contract->>'cmd';
            v_expected_subs := ARRAY(
                SELECT jsonb_array_elements_text(v_contract->'expected_output_contains')
            );
            v_builder       := v_contract->'role_sep'->>'builder';

            -- Check A — exact cmd match.
            IF v_expected_cmd IS NULL OR v_expected_cmd = '' THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check A (cmd_unset): contract.cmd is missing/empty for gate_roadmap_id=%.',
                    NEW.id
                    USING ERRCODE = 'check_violation';
            END IF;
            IF v_run_cmd IS DISTINCT FROM v_expected_cmd THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check A (cmd_mismatch): gate_proof_runs.run_cmd=% does not equal contract.cmd=% for gate_roadmap_id=%.',
                    v_run_cmd, v_expected_cmd, NEW.id
                    USING ERRCODE = 'check_violation';
            END IF;

            -- Check B — every expected substring must appear in run_output
            -- (AND-semantics, ordering irrelevant, case-sensitive).
            IF v_expected_subs IS NULL OR cardinality(v_expected_subs) = 0 THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check B (no_expected_substrings): contract.expected_output_contains is empty for gate_roadmap_id=%.',
                    NEW.id
                    USING ERRCODE = 'check_violation';
            END IF;
            FOREACH v_substr IN ARRAY v_expected_subs LOOP
                IF position(v_substr IN COALESCE(v_run_output, '')) = 0 THEN
                    RAISE EXCEPTION
                        'proof_gate_contract Check B (output_substring_missing): gate_proof_runs.run_output missing required substring "%" for gate_roadmap_id=%.',
                        v_substr, NEW.id
                        USING ERRCODE = 'check_violation';
                END IF;
            END LOOP;

            -- Check C — attester callsign must not match contract.role_sep.builder.
            -- (text → text comparison; builder is a single callsign by schema.)
            IF v_builder IS NULL OR v_builder = '' THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check C (builder_unset): contract.role_sep.builder is missing/empty for gate_roadmap_id=%.',
                    NEW.id
                    USING ERRCODE = 'check_violation';
            END IF;
            IF v_attesting_cs = v_builder THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check C (attester_eq_builder): gate_proof_runs.attesting_callsign=% matches contract.role_sep.builder=% for gate_roadmap_id=%.',
                    v_attesting_cs, v_builder, NEW.id
                    USING ERRCODE = 'check_violation';
            END IF;
        END IF;
        -- ── /Phase 1 nucleus ───────────────────────────────────────────────

        SELECT run_at INTO NEW.last_verified
          FROM public.gate_proof_runs WHERE id = NEW.proof_run_id;
    END IF;
    RETURN NEW;
END;
$function$;

-- trg_01 already binds fn_verify_before_proven (BEFORE UPDATE on gate_roadmap);
-- no DROP/CREATE TRIGGER needed — the CREATE OR REPLACE FUNCTION above is
-- enough to pick up the new body on the existing trigger.


-- ---------------------------------------------------------------------------
-- 3. Populate the dogfood proof_gate_contract on gate_roadmap row
--    id = 8ccca6bc-6478-4f8e-a173-0500474d8b41 (per
--    ceo:keiracom:proof_gate_ledger_design_v1).
--
--    NOTE: that row is component = 'product_proof_enforcement' (the
--    product-layer twin of proof_gate_ledger, ratified 2026-06-03).
--    The design re-uses the same dogfood: proving the ledger enforcement
--    mechanism (via the four named pytest tests in
--    tests/db/test_proof_gate_ledger.py) IS the proof that the product
--    twin's "durable chokepoint refuses to mark done without a recorded
--    run mechanically satisfying the locked contract" promise holds.
--
--    UPDATE — not INSERT — so the existing proof_gate text + owner +
--    notes stay intact; we only attach the structured contract.
-- ---------------------------------------------------------------------------

SET LOCAL agency_os.callsign = 'atlas';

UPDATE public.gate_roadmap
   SET proof_gate_contract = '{
        "check_id": "proof_gate_ledger_enforcement_v1",
        "cmd": "pytest tests/db/test_proof_gate_ledger.py -v",
        "expected_output_contains": [
            "test_negative_mismatched_output_raises PASSED",
            "test_negative_cmd_mismatch_raises PASSED",
            "test_negative_attester_ne_builder_raises PASSED",
            "test_positive_control_accepted PASSED"
        ],
        "role_sep": {
            "builder": "atlas",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[atlas-proof-gate-ledger-base-build 2026-06-03] '
            || 'Attached structured proof_gate_contract (check_id='
            || 'proof_gate_ledger_enforcement_v1). Four named pytest tests '
            || 'in tests/db/test_proof_gate_ledger.py are the load-bearing '
            || 'contract tokens. proven-flip requires aiden + max '
            || 'binding_reviewer proof_runs whose run_cmd matches '
            || 'contract.cmd exactly AND whose run_output contains every '
            || 'expected_output_contains substring (Checks A + B + C in '
            || 'fn_verify_before_proven, this migration).'
 WHERE id = '8ccca6bc-6478-4f8e-a173-0500474d8b41'::uuid;


-- ---------------------------------------------------------------------------
-- 4. Inline DO-block self-test (Dave 2026-06-02 standing addendum precedent).
--    Migration apply MUST fail if trg_01 fails to refuse a mismatched
--    proof_run flip. Uses a temp gate_roadmap row + temp tool_call_log row
--    (both rolled-back via SAVEPOINT — no production-state mutation).
-- ---------------------------------------------------------------------------

-- Cleanup strategy: gate_proof_runs is append-only (trg_07 refuses DELETE),
-- so we cannot DELETE fixtures after a successful self-test. Instead we
-- wrap the entire fixture+test in an OUTER PL/pgSQL sub-transaction and
-- raise a sentinel exception on success — the outer EXCEPTION handler
-- rolls back ALL fixture INSERTs (PL/pgSQL semantics: caught exceptions
-- roll back the work done inside the BEGIN…END that raised).

DO $self_test$
DECLARE
    v_gate_id       uuid := gen_random_uuid();
    v_run_id        uuid;
    v_session_uuid  uuid := gen_random_uuid();
    v_msg           text;
BEGIN
    BEGIN  -- outer sub-tx: fixtures get rolled back when sentinel below fires
        ----- 4a. Test fixture setup -----------------------------------------
        SET LOCAL agency_os.callsign = 'atlas';
        INSERT INTO public.gate_roadmap (
            id, component, phase, subphase, proof_gate, proof_gate_contract,
            status, required_attestation_kind, owner
        ) VALUES (
            v_gate_id,
            'proof_gate_ledger_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline DO-block self-test row',
            '{
                "check_id": "inline_self_test",
                "cmd": "EXACTCMD_FOR_SELF_TEST",
                "expected_output_contains": ["MUST_APPEAR_EXACTLY"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        -- trg_06 (session-independence) needs a tool_call_log row for the
        -- attester's session_uuid.
        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'self_test_inline', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'WRONG_CMD_THAT_DOES_NOT_MATCH_CONTRACT',
            'output text padded out so the column CHECK length>=32 passes — but does not contain the required substring',
            repeat('a', 64),  -- 64-char fake sha (CEO Q2: trigger does not recompute)
            0,
            'aiden',
            v_session_uuid::text
        ) RETURNING id INTO v_run_id;

        ----- 4b. Negative test — mismatched proven-flip MUST raise ----------
        SET LOCAL agency_os.callsign = 'dave';
        BEGIN  -- inner sub-tx: catches the expected check_violation
            UPDATE public.gate_roadmap
               SET status = 'proven', proof_run_id = v_run_id
             WHERE id = v_gate_id;
            -- If we reach here, the trigger failed to block.
            RAISE EXCEPTION
                'PROOF_GATE_LEDGER_SELF_TEST FAIL: UPDATE proven was accepted but trg_01 was expected to refuse on Check A cmd mismatch'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%proof_gate_contract Check A%' THEN
                RAISE EXCEPTION
                    'PROOF_GATE_LEDGER_SELF_TEST FAIL: unexpected check_violation message (wanted Check A cmd_mismatch): %', v_msg
                    USING ERRCODE = 'check_violation';
            END IF;
            -- happy path — Check A raised exactly as expected; fall through
        END;

        -- Raise sentinel so the outer EXCEPTION handler rolls back fixtures.
        RAISE EXCEPTION 'PROOF_GATE_LEDGER_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'PROOF_GATE_LEDGER_SELF_TEST_OK' THEN
            RAISE NOTICE
                'INLINE SELF-TEST PASS: trg_01 refused mismatched proof_run as expected; fixtures rolled back via outer sub-tx';
        ELSE
            -- Real failure during fixture setup OR the negative test itself.
            RAISE EXCEPTION 'INLINE SELF-TEST FAIL or unexpected error: %', v_msg;
        END IF;
    END;
END
$self_test$;


COMMIT;

-- ============================================================================
-- end of 20260603_proof_gate_ledger_base.sql
-- ============================================================================
