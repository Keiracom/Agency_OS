-- ============================================================================
-- 20260603_proof_gate_trigger_fixes.sql
--
-- Three fixes in one PR per Dave directive (ref atlas-proof-gate-trigger-fix):
--
--   FIX 1 — Update proof_gate_contract on product_proof_enforcement
--           (gate_roadmap id 8ccca6bc-…). The seeded contract.cmd was
--           'pytest tests/db/test_proof_gate_ledger.py -v', which let
--           a pytest unit test pass for binding evidence. Wrong shape:
--           the proof_gate text on that row demands a LIVE DURABLE-GATE
--           rejection. New contract.cmd points at a shell script that
--           reproduces a real Check A RAISE, with substrings matching
--           the trigger's actual exception text.
--
--   FIX 2 — Add 'negative_evidence' to gate_proof_runs.attestation_kind.
--           For negative_evidence rows: exit_code != 0 is allowed (and
--           required) — the rejection-shape evidence class. No-self-
--           attest is bypassed for this kind so the builder can record
--           the live RAISE they observed against their own gate.
--           binding_reviewer + ci_runner still require exit_code = 0.
--
--   FIX 3 — Wire a SUPERSET_CMD subbranch into Check A so a run_cmd
--           that CONTAINS contract.cmd as substring (but is not equal)
--           raises with a distinct 'superset_cmd' message rather than
--           the generic 'cmd_mismatch'. This closes the substring-match
--           gap permanently in the live trigger — the spike harness
--           (PR #1423) showed the substring weakening was killed by
--           the dogfood + spike pytest pair; this migration makes the
--           trigger itself emit a different RAISE class for that case.
--
--   RECONCILE — Mark proof_gate_ledger (gate_roadmap c842c13b) as
--           status='built', built_by_callsign='atlas' — PR #1420 has
--           been merged for hours but the gate row still shows
--           not_started. Captured via SET LOCAL agency_os.callsign =
--           'atlas' in the same migration tx; trg_03 auto-fills.
--
-- INLINE SELF-TESTS (Dave 2026-06-02 standing precedent): each fix has
-- its own DO-block negative test embedded — migration apply ABORTS if
-- the new trigger or constraint fails to behave as specified. Uses the
-- inner-sentinel-raise / outer-rollback pattern from the BASE PR so
-- transient fixtures never persist (gate_proof_runs is append-only;
-- trg_07 refuses DELETE).
-- ============================================================================

BEGIN;
SET LOCAL agency_os.callsign = 'dave';


-- ----------------------------------------------------------------------------
-- FIX 2a — attestation_kind enum widening (add 'negative_evidence').
-- ----------------------------------------------------------------------------

ALTER TABLE public.gate_proof_runs
    DROP CONSTRAINT IF EXISTS gate_proof_runs_attestation_kind_check;
ALTER TABLE public.gate_proof_runs
    ADD CONSTRAINT gate_proof_runs_attestation_kind_check
        CHECK (attestation_kind = ANY (ARRAY[
            'ci_runner'::text,
            'binding_reviewer'::text,
            'negative_evidence'::text
        ]));


-- ----------------------------------------------------------------------------
-- FIX 2b — exit_code CHECK becomes conditional on attestation_kind.
--    ci_runner / binding_reviewer : exit_code MUST equal 0 (success path).
--    negative_evidence            : exit_code MUST be non-zero (the rejection
--                                   evidence is the trigger having raised).
-- ----------------------------------------------------------------------------

ALTER TABLE public.gate_proof_runs
    DROP CONSTRAINT IF EXISTS gate_proof_runs_exit_code_check;
ALTER TABLE public.gate_proof_runs
    ADD CONSTRAINT gate_proof_runs_exit_code_check
        CHECK (
            (attestation_kind IN ('ci_runner', 'binding_reviewer') AND exit_code = 0)
            OR
            (attestation_kind = 'negative_evidence' AND exit_code <> 0)
        );


-- ----------------------------------------------------------------------------
-- FIX 2c — fn_gate_proof_no_self_attest: builder CAN attest 'negative_evidence'
--    on their own gate (the rejection demonstrates the gate works). All other
--    branches preserved verbatim from the 20260602_widen_binding_reviewer_
--    allowlist amendment (allowlist = ['aiden','max'], per-component
--    ci_runner-required refusal of binding_reviewer).
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.fn_gate_proof_no_self_attest()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    v_builder         TEXT;
    v_required_kind   TEXT;
    binding_allowlist CONSTANT TEXT[] := ARRAY['aiden', 'max'];
BEGIN
    SELECT built_by_callsign, required_attestation_kind
      INTO v_builder, v_required_kind
      FROM public.gate_roadmap
     WHERE id = NEW.gate_roadmap_id;

    IF v_builder IS NULL THEN
        RAISE EXCEPTION
            'gate_proof_runs no-self-attest: gate_roadmap.built_by_callsign is NULL for gate_roadmap_id=%; record the build transition first.',
            NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- FIX 2c: negative_evidence is the rejection-class — by design the
    -- builder records their own observation of the trigger raising. Skip
    -- the no-self-attest gate for this kind only.
    IF NEW.attesting_callsign = v_builder
       AND NEW.attestation_kind <> 'negative_evidence' THEN
        RAISE EXCEPTION
            'gate_proof_runs no-self-attest: attesting_callsign=% matches gate_roadmap.built_by_callsign=% for gate_roadmap_id=%. Building agent cannot attest its own proof.',
            NEW.attesting_callsign, v_builder, NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- binding_reviewer allowlist (unchanged from wnrg amendment).
    IF NEW.attestation_kind = 'binding_reviewer'
       AND NOT (NEW.attesting_callsign = ANY (binding_allowlist)) THEN
        RAISE EXCEPTION
            'gate_proof_runs binding-reviewer-allowlist: attestation_kind=binding_reviewer requires attesting_callsign IN % (got: %).',
            binding_allowlist, NEW.attesting_callsign
            USING ERRCODE = 'check_violation';
    END IF;

    -- Per-component policy (unchanged).
    IF v_required_kind = 'ci_runner' AND NEW.attestation_kind = 'binding_reviewer' THEN
        RAISE EXCEPTION
            'gate_proof_runs required-attestation-kind: gate_roadmap.required_attestation_kind=ci_runner for gate_roadmap_id=%; binding_reviewer proof_runs refused.',
            NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$fn$;


-- ----------------------------------------------------------------------------
-- FIX 3 — fn_verify_before_proven Check A gets a SUPERSET_CMD subbranch.
--    When v_run_cmd ≠ v_expected_cmd, decide which sub-class of mismatch
--    we're refusing:
--      * substring containment   → 'superset_cmd' (today's shape-only flip)
--      * everything else         → 'cmd_mismatch' (pre-existing behaviour)
--    Both still raise check_violation; only the message tokens differ so
--    callers / monitors can distinguish.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.fn_verify_before_proven()
RETURNS trigger LANGUAGE plpgsql AS $fn$
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
        IF NEW.proof_run_id IS NULL THEN
            RAISE EXCEPTION
                'gate_roadmap proven-requires-proof-run: status=proven requires proof_run_id to pin which gate_proof_runs row justified the transition.'
                USING ERRCODE = 'check_violation';
        END IF;

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

            -- Check A — exact cmd match. Distinguishes superset_cmd
            -- (substring containment) from generic cmd_mismatch.
            IF v_expected_cmd IS NULL OR v_expected_cmd = '' THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check A (cmd_unset): contract.cmd is missing/empty for gate_roadmap_id=%.',
                    NEW.id
                    USING ERRCODE = 'check_violation';
            END IF;
            IF v_run_cmd IS DISTINCT FROM v_expected_cmd THEN
                -- FIX 3: superset subbranch.
                IF position(v_expected_cmd IN COALESCE(v_run_cmd, '')) > 0 THEN
                    RAISE EXCEPTION
                        'proof_gate_contract Check A (superset_cmd): gate_proof_runs.run_cmd=% contains but does not equal contract.cmd=% for gate_roadmap_id=%.',
                        v_run_cmd, v_expected_cmd, NEW.id
                        USING ERRCODE = 'check_violation';
                ELSE
                    RAISE EXCEPTION
                        'proof_gate_contract Check A (cmd_mismatch): gate_proof_runs.run_cmd=% does not equal contract.cmd=% for gate_roadmap_id=%.',
                        v_run_cmd, v_expected_cmd, NEW.id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            -- Check B — every expected substring must appear in run_output.
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

            -- Check C — attester != contract.role_sep.builder.
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

        SELECT run_at INTO NEW.last_verified
          FROM public.gate_proof_runs WHERE id = NEW.proof_run_id;
    END IF;
    RETURN NEW;
END;
$fn$;


-- ----------------------------------------------------------------------------
-- FIX 1 — UPDATE the proof_gate_contract on product_proof_enforcement
--    (gate_roadmap id 8ccca6bc) to require a LIVE DURABLE-GATE rejection.
--    contract.cmd is the bash script that runs the live rejection probe.
--    expected_output_contains targets the trigger's own RAISE text.
-- ----------------------------------------------------------------------------

SET LOCAL agency_os.callsign = 'atlas';

UPDATE public.gate_roadmap
   SET proof_gate_contract = '{
        "check_id": "product_proof_enforcement_live_rejection_v1",
        "cmd": "bash scripts/proof_bar/product_proof_enforcement_live_rejection.sh",
        "expected_output_contains": [
            "proof_gate_contract Check A",
            "cmd_mismatch",
            "does not equal contract.cmd"
        ],
        "role_sep": {
            "builder": "head_of_ops",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       notes = COALESCE(notes, '') || E'\n\n[atlas-proof-gate-trigger-fix 2026-06-03] '
            || 'proof_gate_contract replaced: check_id is now '
            || 'product_proof_enforcement_live_rejection_v1. The previous '
            || 'contract (pytest tests/db/test_proof_gate_ledger.py -v) was a '
            || 'shape-only flip — it accepted pytest unit-test evidence when '
            || 'the proof_gate text demanded a live durable-gate rejection. '
            || 'New cmd is the bash script that produces a real Check A RAISE; '
            || 'expected_output_contains targets the trigger''s own exception '
            || 'text. role_sep.builder = head_of_ops (revocation authority).'
 WHERE id = '8ccca6bc-6478-4f8e-a173-0500474d8b41'::uuid;


-- ----------------------------------------------------------------------------
-- RECONCILE — proof_gate_ledger (gate_roadmap c842c13b): PR #1420 merged,
--    code is live, row still shows not_started. Mark built; trg_03 captures
--    built_by_callsign='atlas' from SET LOCAL.
-- ----------------------------------------------------------------------------

UPDATE public.gate_roadmap
   SET status = 'built'
 WHERE component = 'proof_gate_ledger'
   AND status = 'not_started';


-- ============================================================================
-- INLINE SELF-TESTS
-- ============================================================================

-- ── Fix 2 self-test #1: negative_evidence INSERT with exit_code != 0 must
--    succeed; binding_reviewer INSERT with exit_code != 0 must FAIL.
DO $self_test_fix2$
DECLARE
    v_gate_id      uuid := gen_random_uuid();
    v_session_uuid uuid := gen_random_uuid();
    v_msg          text;
BEGIN
    BEGIN  -- outer rollback wrapper
        SET LOCAL agency_os.callsign = 'atlas';
        INSERT INTO public.gate_roadmap (
            id, component, phase, subphase, proof_gate, status,
            required_attestation_kind, owner
        ) VALUES (
            v_gate_id,
            'INLINE_FIX2_SELFTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline fix 2 self-test row',
            'built',
            'binding_reviewer',
            'atlas'
        );

        -- Builder records a negative_evidence row (self-attest allowed for this kind).
        BEGIN
            INSERT INTO public.gate_proof_runs (
                gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
                exit_code, attesting_callsign, attester_session_uuid
            ) VALUES (
                v_gate_id, 'negative_evidence',
                'echo expected to fail', 'self-test negative_evidence row padded for the >=32 length check',
                repeat('a', 64), 2, 'atlas', v_session_uuid::text
            );
        EXCEPTION WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            RAISE EXCEPTION 'FIX2 SELFTEST FAIL: negative_evidence INSERT (exit_code=2) was refused: %', v_msg;
        END;

        -- binding_reviewer with exit_code != 0 must FAIL (column CHECK).
        BEGIN
            INSERT INTO public.gate_proof_runs (
                gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
                exit_code, attesting_callsign, attester_session_uuid
            ) VALUES (
                v_gate_id, 'binding_reviewer',
                'echo should be refused', 'self-test binding_reviewer-with-bad-exit row padded for the >=32 check',
                repeat('b', 64), 1, 'aiden', gen_random_uuid()::text
            );
            RAISE EXCEPTION 'FIX2 SELFTEST FAIL: binding_reviewer INSERT with exit_code=1 was accepted'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg LIKE '%FIX2 SELFTEST FAIL%' THEN
                RAISE EXCEPTION '%', v_msg;
            END IF;
            -- Otherwise: the column CHECK refused as expected.
        END;

        -- Sentinel: success → roll back outer fixtures.
        RAISE EXCEPTION 'FIX2_SELFTEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'FIX2_SELFTEST_OK' THEN
            RAISE NOTICE 'INLINE SELF-TEST FIX 2 PASS: negative_evidence accepted, binding_reviewer+exit_code!=0 refused';
        ELSE
            RAISE EXCEPTION 'INLINE SELF-TEST FIX 2 FAIL: %', v_msg;
        END IF;
    END;
END
$self_test_fix2$;


-- ── Fix 3 self-test: superset_cmd attempt must raise with the
--    superset_cmd token, NOT the generic cmd_mismatch token.
DO $self_test_fix3$
DECLARE
    v_gate_id       uuid := gen_random_uuid();
    v_session_uuid  uuid := gen_random_uuid();
    v_run_id        uuid;
    v_msg           text;
BEGIN
    BEGIN
        SET LOCAL agency_os.callsign = 'atlas';
        INSERT INTO public.gate_roadmap (
            id, component, phase, subphase, proof_gate, proof_gate_contract,
            status, required_attestation_kind, owner
        ) VALUES (
            v_gate_id,
            'INLINE_FIX3_SUPERSET_SELFTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline fix 3 superset self-test row',
            '{
                "check_id": "fix3_superset_selftest",
                "cmd": "EXACTCMD",
                "expected_output_contains": ["SIG"],
                "role_sep": {"builder": "atlas", "attester": ["aiden"]},
                "negative_test_required": true
            }'::jsonb,
            'built',
            'binding_reviewer',
            'atlas'
        );

        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session_uuid, 'inline_fix3_selftest', now());

        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs (
            gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
            exit_code, attesting_callsign, attester_session_uuid
        ) VALUES (
            v_gate_id,
            'binding_reviewer',
            'EXACTCMD --extra-arg',  -- strict superset of contract.cmd
            'self-test output containing SIG padded for the >=32 length check',
            repeat('c', 64),
            0,
            'aiden',
            v_session_uuid::text
        ) RETURNING id INTO v_run_id;

        SET LOCAL agency_os.callsign = 'dave';
        BEGIN
            UPDATE public.gate_roadmap
               SET status = 'proven', proof_run_id = v_run_id
             WHERE id = v_gate_id;
            RAISE EXCEPTION 'FIX3 SELFTEST FAIL: UPDATE proven was accepted; expected superset_cmd RAISE'
                USING ERRCODE = 'check_violation';
        EXCEPTION WHEN check_violation THEN
            GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
            IF v_msg NOT LIKE '%superset_cmd%' THEN
                RAISE EXCEPTION 'FIX3 SELFTEST FAIL: expected superset_cmd token, got: %', v_msg;
            END IF;
        END;

        RAISE EXCEPTION 'FIX3_SELFTEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'FIX3_SELFTEST_OK' THEN
            RAISE NOTICE 'INLINE SELF-TEST FIX 3 PASS: superset_cmd subbranch raises as expected';
        ELSE
            RAISE EXCEPTION 'INLINE SELF-TEST FIX 3 FAIL: %', v_msg;
        END IF;
    END;
END
$self_test_fix3$;


COMMIT;

-- ============================================================================
-- end of 20260603_proof_gate_trigger_fixes.sql
-- ============================================================================
