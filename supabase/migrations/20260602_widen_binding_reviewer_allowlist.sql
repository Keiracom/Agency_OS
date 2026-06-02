-- ============================================================================
-- 20260602_widen_binding_reviewer_allowlist.sql
--
-- KEI Agency_OS-wnrg — Dave directive 2026-06-02 (AMENDED in-place).
--
-- ORIGINAL intent: widen binding_reviewer allowlist from ('dave','elliot') to
-- ('dave','elliot','aiden','max') so deliberators can write attestations.
--
-- AMENDED intent (Dave 2026-06-02 second directive — PR #1402 amendment):
--   1. Narrow the binding_reviewer allowlist to ('aiden','max') ONLY.
--      Elliot is removed (orchestrator-only role). Dave bootstrap is RETIRED
--      from this function (except genuine emergency, which would require a
--      future migration to re-add). The dave-bootstrap exemption inside
--      fn_gate_proof_session_independence (trg_06) is NOT touched — it stays
--      as written so a future dave re-addition to the allowlist works
--      without a second migration. Per Dave verbatim: "do NOT remove the
--      dave exemption from fn_gate_proof_session_independence".
--   2. Add a new trigger (trg_11) that enforces DUAL ATTESTATION: a row
--      cannot transition to status='proven' unless BOTH aiden AND max have
--      written binding_reviewer proof_runs for it. One signer is insufficient.
--
-- The structurally-narrow PR #1402 (widen-to-4) is REPLACED by this amended
-- migration (narrow-to-2 + dual-attest). Same file, same branch, force-push.
-- The PR body has been updated to reflect the new shape.
--
-- ⚠ DO NOT APPLY until 2-of-N binding review lands on the PR. Aiden applies.
-- ⚠ EXISTING 'proven' rows on gate_roadmap (gate_mechanism, persona_config,
--   temporal_runtime) are NOT affected. trg_11 fires only on transitions
--   INTO 'proven' from non-'proven'; the bootstrap rows are already 'proven'
--   and have proof_run_id set, so trg_11 is a no-op for them. The
--   immutability of gate_proof_runs (trg_07) prevents anyone from
--   retroactively invalidating the dave-attested bootstrap rows.
-- ============================================================================


-- ─── Part 1 — narrow the allowlist + retire dave/elliot ────────────────────
-- CREATE OR REPLACE FUNCTION — full replacement preserving every other branch
-- of the original fn_gate_proof_no_self_attest unchanged. The ONLY structural
-- changes from the original (in 20260602_gate_roadmap_proof_gate.sql) are:
--   - the constant array literal: ARRAY['aiden', 'max']
--   - the inline comment text (rewritten to avoid the strings 'dave' / 'elliot'
--     in quoted-array form so the negative ASSERTs in Part 1 verification
--     remain unambiguous).
--
-- All four guards remain intact in the same order:
--   1. v_builder IS NULL refuse
--   2. attesting_callsign == v_builder refuse (the core no-self-attest)
--   3. binding_reviewer allowlist refuse (← narrowing site)
--   4. required_attestation_kind='ci_runner' refuses binding_reviewer

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

    IF NEW.attesting_callsign = v_builder THEN
        RAISE EXCEPTION
            'gate_proof_runs no-self-attest: attesting_callsign=% matches gate_roadmap.built_by_callsign=% for gate_roadmap_id=%. Building agent cannot attest its own proof.',
            NEW.attesting_callsign, v_builder, NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- KEI Agency_OS-wnrg amendment 2026-06-02: allowlist narrowed to deliberators
    -- only. The no-self-attest check above still fires when a deliberator IS
    -- the builder (e.g. aiden cannot binding-attest persona_config because
    -- aiden built it). Combined with the dual-attest trigger (trg_11),
    -- BOTH deliberators must sign before status=proven is allowed.
    IF NEW.attestation_kind = 'binding_reviewer'
       AND NOT (NEW.attesting_callsign = ANY (binding_allowlist)) THEN
        RAISE EXCEPTION
            'gate_proof_runs binding-reviewer-allowlist: attestation_kind=binding_reviewer requires attesting_callsign IN % (got: %).',
            binding_allowlist, NEW.attesting_callsign
            USING ERRCODE = 'check_violation';
    END IF;

    -- Per-component policy: ci_runner-required components refuse binding_reviewer.
    IF v_required_kind = 'ci_runner' AND NEW.attestation_kind = 'binding_reviewer' THEN
        RAISE EXCEPTION
            'gate_proof_runs required-attestation-kind: gate_roadmap.required_attestation_kind=ci_runner for gate_roadmap_id=%; binding_reviewer proof_runs refused.',
            NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$fn$;


-- ─── Part 1A — new trigger trg_11 — dual-attest enforcement ────────────────
-- Blocks gate_roadmap.status='proven' transitions unless BOTH aiden AND max
-- have already written binding_reviewer proof_runs for the row.
--
-- Why a separate trigger (not folded into trg_01): trg_01 enforces "a
-- proof_run is pinned via proof_run_id". trg_11 enforces "the deliberator
-- pair has BOTH signed". These are independent invariants that can fail
-- independently; separating them gives precise error messages and is
-- consistent with the existing one-invariant-per-trigger pattern in
-- 20260602_gate_roadmap_proof_gate.sql.
--
-- Trigger fires alphabetically AFTER trg_01..trg_10 because of the naming.
-- For an UPDATE that touches status, trg_01 fires first (proof_run_id check),
-- then trg_02 (forward-only), then trg_03 (capture_builder immutability),
-- finally trg_11 (dual-attest). All four must pass.

CREATE OR REPLACE FUNCTION public.fn_gate_proven_dual_attest()
RETURNS trigger LANGUAGE plpgsql AS $fn$
BEGIN
    IF NEW.status = 'proven' AND (OLD.status IS DISTINCT FROM 'proven') THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.gate_proof_runs
             WHERE gate_roadmap_id    = NEW.id
               AND attesting_callsign = 'aiden'
               AND attestation_kind   = 'binding_reviewer'
        ) THEN
            RAISE EXCEPTION
                'gate dual-attest: aiden binding_reviewer proof run required before proven for gate_roadmap_id=%.',
                NEW.id
                USING ERRCODE = 'check_violation';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM public.gate_proof_runs
             WHERE gate_roadmap_id    = NEW.id
               AND attesting_callsign = 'max'
               AND attestation_kind   = 'binding_reviewer'
        ) THEN
            RAISE EXCEPTION
                'gate dual-attest: max binding_reviewer proof run required before proven for gate_roadmap_id=%.',
                NEW.id
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_11_gate_proven_dual_attest ON public.gate_roadmap;
CREATE TRIGGER trg_11_gate_proven_dual_attest
    BEFORE UPDATE ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_proven_dual_attest();


-- ─── Part 1 verification — ASSERT block ────────────────────────────────────
-- Apply-time ASSERTs covering:
--   (a) allowlist literal contains 'aiden' (quoted-array form)
--   (b) allowlist literal contains 'max'   (quoted-array form)
--   (c) allowlist literal does NOT contain 'elliot' (Elliot removed)
--   (d) allowlist literal does NOT contain 'dave'   (Dave retired from allowlist)
--   (e) trg_11_gate_proven_dual_attest exists on gate_roadmap
-- Any failure → migration ROLLBACKs.

DO $$
BEGIN
    -- (a)+(b) presence checks against the quoted-array form so we don't
    -- accidentally match the letters appearing in unrelated identifiers.
    ASSERT (SELECT prosrc FROM pg_proc WHERE proname='fn_gate_proof_no_self_attest')
      LIKE '%''aiden''%', 'fn_gate_proof_no_self_attest must include ''aiden'' in allowlist array';
    ASSERT (SELECT prosrc FROM pg_proc WHERE proname='fn_gate_proof_no_self_attest')
      LIKE '%''max''%', 'fn_gate_proof_no_self_attest must include ''max'' in allowlist array';

    -- (c)+(d) negative checks — the quoted strings 'elliot' and 'dave' must
    -- NOT appear in the function body. (Comments using the words Elliot or
    -- Dave in title case are fine — LIKE is case-sensitive and the negative
    -- pattern uses the quoted lowercase form that only appears in array
    -- literals or string comparisons.)
    ASSERT (SELECT prosrc FROM pg_proc WHERE proname='fn_gate_proof_no_self_attest')
      NOT LIKE '%''elliot''%', 'fn_gate_proof_no_self_attest must NOT include ''elliot'' — orchestrator role only';
    ASSERT (SELECT prosrc FROM pg_proc WHERE proname='fn_gate_proof_no_self_attest')
      NOT LIKE '%''dave''%', 'fn_gate_proof_no_self_attest must NOT include ''dave'' — bootstrap exemption retired here (still present in trg_06)';

    -- (e) trg_11 must exist and be wired to gate_roadmap
    ASSERT (SELECT count(*) FROM pg_trigger
              WHERE tgrelid = 'public.gate_roadmap'::regclass
                AND tgname  = 'trg_11_gate_proven_dual_attest') = 1,
           'trg_11_gate_proven_dual_attest must exist on gate_roadmap';

    RAISE NOTICE 'KEI Agency_OS-wnrg verification: allowlist narrowed to (aiden, max); elliot and dave removed from binding_allowlist; trg_11 dual-attest trigger present.';
END $$;


-- ─── Part 1B — inline negative test ────────────────────────────────────────
-- Dispatch ask: attempt UPDATE gate_roadmap SET status='proven' on a row
-- with zero proof_runs → must RAISE check_violation.
--
-- This exercises the COMBINED gate (trg_01 fires first since proof_run_id is
-- NULL; trg_11 never gets to run because trg_01 already refused). What the
-- test proves: a roadmap row with no backing proof_run CANNOT be moved to
-- 'proven', period. Either trg_01 or trg_11 raises; the migration ROLLBACKs
-- if neither does.
--
-- Setup INSERTs are wrapped in a BEGIN/EXCEPTION subtransaction so that the
-- expected refusal automatically rolls back the test fixture — no rows
-- leak into gate_roadmap or gate_proof_runs.

DO $$
DECLARE
    test_id          UUID;
    test_failed      BOOLEAN := FALSE;
    suffix           TEXT    := substr(gen_random_uuid()::text, 1, 8);
    inner_savepoint  TEXT;
BEGIN
    BEGIN  -- subtransaction (savepoint) — any exception inside rolls back
        -- Setup: nova builds a fresh row, NO proof_runs attached.
        PERFORM set_config('agency_os.callsign', 'nova', true);
        INSERT INTO public.gate_roadmap (component, phase, proof_gate, status, owner, notes)
        VALUES ('__wnrg_test_zero_proofs_' || suffix || '__',
                'test', 'test-pending', 'built', 'nova',
                'KEI Agency_OS-wnrg negative test — rolled back via subtransaction.')
        RETURNING id INTO test_id;

        -- Try to flip directly to 'proven' with proof_run_id still NULL.
        -- trg_01 should raise (proof_run_id IS NULL). If it doesn't,
        -- trg_11 should raise (no aiden + max attestations). Either way:
        -- check_violation. If NEITHER raises → test_failed gets set →
        -- outer migration RAISES on the assertion below.
        BEGIN
            UPDATE public.gate_roadmap SET status='proven' WHERE id=test_id;
            -- if we reach here, no trigger refused — escape and fail.
            RAISE EXCEPTION '__wnrg_negative_test_did_not_block__';
        EXCEPTION
            WHEN check_violation THEN
                -- expected — some trigger refused. Continue.
                NULL;
            WHEN raise_exception THEN
                IF SQLERRM = '__wnrg_negative_test_did_not_block__' THEN
                    test_failed := TRUE;
                ELSE
                    RAISE;
                END IF;
        END;

        -- Force the outer subtransaction to roll back via a known marker.
        RAISE EXCEPTION '__wnrg_test_rollback_setup__';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM = '__wnrg_test_rollback_setup__' THEN
                NULL;  -- expected; setup rolled back, no DB pollution
            ELSE
                RAISE;
            END IF;
    END;

    IF test_failed THEN
        RAISE EXCEPTION
            'KEI Agency_OS-wnrg NEGATIVE TEST FAILED: zero-proof-runs row was UPDATEd to status=proven without any trigger refusing. proof-gate is INSECURE.';
    END IF;

    RAISE NOTICE 'KEI Agency_OS-wnrg negative test PASSED: zero-proof-runs UPDATE to status=proven was refused as expected.';
END $$;


-- ============================================================================
-- ─── Part 2 — KNOWN FROZEN ATTRIBUTION: fleet_autostart_recovery ────────────
--
-- KNOWN FROZEN ATTRIBUTION: fleet_autostart_recovery
--   gate_roadmap.id            = 'e4d7d19d-b125-448a-87f5-589113d23463'
--   gate_roadmap.built_by_callsign = 'elliot'   (set 2026-06-02 by orchestrator-as-owner)
--   gate_roadmap.owner         = 'elliot'
--   Actual implementer         = scout
--
-- The capture_builder trigger (fn_gate_roadmap_capture_builder, trg_03) froze
-- this assignment at the moment elliot's session-var wrote the row's
-- status='built' transition. The trigger has no way to distinguish
-- "orchestrator owner recording the build" from "implementing worker
-- recording the build" — it captures the session-var caller, no more.
--
-- CONSEQUENCE (under the AMENDED allowlist):
--   - elliot cannot serve as binding_reviewer anywhere (elliot is removed
--     from the binding_allowlist; orchestrator-only role).
--   - For fleet_autostart_recovery specifically, the dual-attest requirement
--     means BOTH aiden AND max must write binding_reviewer proof_runs before
--     status='proven' is allowed. Neither aiden nor max built this row, so
--     the no-self-attest check (trg_04 step 2) does not refuse them.
--
-- CORRECTION PATH: aiden writes one binding_reviewer proof_run, max writes
-- a second binding_reviewer proof_run, then status='proven' transition is
-- allowed by both trg_01 and trg_11. The proof_run_id field on gate_roadmap
-- must point to ONE of the two (either is acceptable for the trg_01 pin
-- since both are valid proof_runs for the row).
--
-- NOTE: No UPDATE is issued to fix built_by_callsign here. The capture_builder
-- trigger explicitly raises when an UPDATE attempts to change a non-NULL
-- built_by_callsign. Frozen is frozen — by design. The fix is downstream
-- (different attesters), not upstream (rewrite history).
-- ============================================================================


-- ============================================================================
-- ─── Part 3 — PREVENTION: owner != builder default pattern ──────────────────
--
-- PREVENTION: built_by_callsign should be set by the IMPLEMENTING agent
-- (worker) at the moment they record status='built'. NOT by the
-- orchestrator/owner observing the work.
--
-- Orchestrators that record a build transition they witnessed but did not
-- author MUST SET LOCAL agency_os.callsign=<actual-worker-callsign> for the
-- specific UPDATE that flips status to 'built'. Example:
--
--     SET LOCAL agency_os.callsign = 'scout';          -- the implementer
--     UPDATE public.gate_roadmap
--        SET status = 'built'
--      WHERE component = 'fleet_autostart_recovery'
--        AND status <> 'built';
--     -- built_by_callsign is now frozen to 'scout' for this row.
--
-- The immutability check inside fn_gate_roadmap_capture_builder cannot tell
-- "owner set this" from "builder set this" — what gets captured is whatever
-- agency_os.callsign held at the moment of the BEFORE INSERT/UPDATE trigger
-- firing. So the discipline lives at the application layer, not the DB layer.
--
-- AGENTS: never set built_by_callsign via an orchestrator-session (elliot's
-- session) unless elliot was actually the implementer. If elliot is the
-- orchestrator dispatching the work, switch session-var to the implementer's
-- callsign for the build-transition UPDATE, then restore.
--
-- WHY NOT A CHECK CONSTRAINT: A CHECK (built_by_callsign != 'elliot' OR
-- component IN (...)) would require maintaining a static enum of
-- "components where elliot is legitimately the builder", which drifts the
-- moment a new elliot-authored component lands. Comment + discipline
-- (this section) is the lower-friction choice; revisit if drift recurs at
-- volume.
--
-- DUAL-ATTEST IMPLICATIONS (KEI Agency_OS-wnrg amendment, this migration):
--   - The owner != builder pattern is even more important now. If the
--     orchestrator session-var leaks into the build transition AND that
--     orchestrator is also one of the deliberators (aiden/max), the
--     deliberator becomes the builder and can no longer attest their own
--     work. That breaks the dual-attest contract for that row.
--   - Discipline: deliberators (aiden, max) MUST NOT be the session-var
--     caller for build-transition UPDATEs unless they actually built the
--     work. Use scout / nova / orion / other workers as the implementers.
-- ============================================================================


-- ─── End-of-migration NOTICE for the operator ──────────────────────────────
DO $$
BEGIN
    RAISE NOTICE 'KEI Agency_OS-wnrg AMENDED applied: binding_allowlist narrowed to (aiden, max) only. elliot removed (orchestrator role). dave retired from this function (trg_06 dave exemption preserved). trg_11_gate_proven_dual_attest added — both aiden AND max binding_reviewer proof_runs required for status=proven. fleet_autostart_recovery frozen attribution documented in §2; prevention pattern + dual-attest implications documented in §3.';
END $$;
