-- ============================================================================
-- 20260603_gate_roadmap_audit_non_status.sql
--
-- Closes the gate_roadmap audit gap (KEI Agency_OS-i340). Aiden audit-gap
-- finding via Elliot 2026-06-03.
--
-- PROBLEM
--   fn_gate_roadmap_audit (trg_09) only writes gate_roadmap_history WHEN
--   NEW.status IS DISTINCT FROM OLD.status. Owner / built_by_callsign /
--   proof_gate_contract / required_attestation_kind changes leave ZERO history
--   and no recorded actor — which is how the PR #1415 watchdog silently
--   overwrote `owner` (anomaly observed on PR #1435 + #1436: owner flipped to
--   match a freshly-stamped built_by_callsign with no audit trail).
--
-- FIX
--   1. Additive gate_roadmap_history columns: change_kind (NOT NULL DEFAULT
--      'status' — backfills the 20 existing status rows correctly), old_value,
--      new_value. CHECK pins change_kind to the tracked set. (Verified no code
--      path inserts gate_roadmap_history directly — only this trigger does — so
--      the DEFAULT + CHECK are safe.)
--   2. Rewrite fn_gate_roadmap_audit: keep the status-change row verbatim (now
--      also stamping change_kind='status' + old_value/new_value), AND emit one
--      history row per changed tracked non-status column, each with the actor
--      from current_setting('agency_os.callsign'). new_status is NOT NULL, so
--      non-status rows carry the (unchanged) current status for context.
--   3. Inline DO-block negative self-test: an owner UPDATE with NO status change
--      MUST now produce exactly one change_kind='owner' history row with the
--      correct actor/old/new. Migration ABORTS otherwise. Fixtures roll back via
--      the sentinel-raise pattern (gate_roadmap_history is append-only —
--      trg_10 immutability refuses DELETE).
--
-- SCOPE: current (Supabase) instance, additive + reversible. Independent of the
-- blocked gate_roadmap_migration (357c9c38). No external-service call → no LAW
-- XIII skill update. NOTE: context_watchdog.py reads gate_roadmap_history as an
-- activity signal; non-status rows enrich that signal (benign/more accurate).
-- ============================================================================

BEGIN;
SET LOCAL agency_os.callsign = 'scout';


-- ---------------------------------------------------------------------------
-- 1. Additive history columns.
-- ---------------------------------------------------------------------------

ALTER TABLE public.gate_roadmap_history
    ADD COLUMN IF NOT EXISTS change_kind text NOT NULL DEFAULT 'status',
    ADD COLUMN IF NOT EXISTS old_value   text,
    ADD COLUMN IF NOT EXISTS new_value   text;

ALTER TABLE public.gate_roadmap_history
    DROP CONSTRAINT IF EXISTS gate_roadmap_history_change_kind_check;
ALTER TABLE public.gate_roadmap_history
    ADD CONSTRAINT gate_roadmap_history_change_kind_check
        CHECK (change_kind = ANY (ARRAY[
            'status'::text,
            'owner'::text,
            'built_by_callsign'::text,
            'proof_gate_contract'::text,
            'required_attestation_kind'::text
        ]));

COMMENT ON COLUMN public.gate_roadmap_history.change_kind IS
    'Which field changed: status (legacy path) or a tracked non-status column. '
    'See 20260603_gate_roadmap_audit_non_status.sql.';


-- ---------------------------------------------------------------------------
-- 2. fn_gate_roadmap_audit — log non-status tracked column changes with actor.
--    Status path preserved verbatim (now also stamps change_kind/old/new).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.fn_gate_roadmap_audit()
RETURNS trigger LANGUAGE plpgsql AS $function$
DECLARE
    v_actor text := current_setting('agency_os.callsign', true);
BEGIN
    -- status change — existing behaviour, plus change_kind/old_value/new_value.
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO public.gate_roadmap_history
            (gate_roadmap_id, old_status, new_status, changed_by_callsign,
             proof_run_id, change_kind, old_value, new_value)
        VALUES
            (NEW.id, OLD.status, NEW.status, v_actor,
             NEW.proof_run_id, 'status', OLD.status, NEW.status);
    END IF;

    -- non-status tracked columns — the audit-gap fix. new_status is NOT NULL,
    -- so carry the (unchanged) current status for context.
    IF NEW.owner IS DISTINCT FROM OLD.owner THEN
        INSERT INTO public.gate_roadmap_history
            (gate_roadmap_id, old_status, new_status, changed_by_callsign,
             change_kind, old_value, new_value)
        VALUES (NEW.id, NEW.status, NEW.status, v_actor,
                'owner', OLD.owner, NEW.owner);
    END IF;

    IF NEW.built_by_callsign IS DISTINCT FROM OLD.built_by_callsign THEN
        INSERT INTO public.gate_roadmap_history
            (gate_roadmap_id, old_status, new_status, changed_by_callsign,
             change_kind, old_value, new_value)
        VALUES (NEW.id, NEW.status, NEW.status, v_actor,
                'built_by_callsign', OLD.built_by_callsign, NEW.built_by_callsign);
    END IF;

    IF NEW.proof_gate_contract IS DISTINCT FROM OLD.proof_gate_contract THEN
        INSERT INTO public.gate_roadmap_history
            (gate_roadmap_id, old_status, new_status, changed_by_callsign,
             change_kind, old_value, new_value)
        VALUES (NEW.id, NEW.status, NEW.status, v_actor,
                'proof_gate_contract', OLD.proof_gate_contract::text,
                NEW.proof_gate_contract::text);
    END IF;

    IF NEW.required_attestation_kind IS DISTINCT FROM OLD.required_attestation_kind THEN
        INSERT INTO public.gate_roadmap_history
            (gate_roadmap_id, old_status, new_status, changed_by_callsign,
             change_kind, old_value, new_value)
        VALUES (NEW.id, NEW.status, NEW.status, v_actor,
                'required_attestation_kind', OLD.required_attestation_kind,
                NEW.required_attestation_kind);
    END IF;

    RETURN NEW;  -- AFTER trigger: return value ignored.
END;
$function$;


-- ---------------------------------------------------------------------------
-- 3. Inline negative self-test — owner change (no status change) MUST log a
--    history row with the actor. Fixtures roll back via sentinel-raise
--    (gate_roadmap_history is append-only; trg_10 refuses DELETE).
-- ---------------------------------------------------------------------------

DO $self_test$
DECLARE
    v_gate_id uuid := gen_random_uuid();
    v_cnt     int;
    v_actor   text;
    v_old     text;
    v_new     text;
    v_status  text;
    v_msg     text;
BEGIN
    BEGIN  -- outer sub-tx: fixtures roll back when the sentinel fires
        SET LOCAL agency_os.callsign = 'atlas';
        INSERT INTO public.gate_roadmap (
            id, component, phase, subphase, proof_gate, status, owner
        ) VALUES (
            v_gate_id,
            'gate_roadmap_audit_INLINE_NEGTEST_' || replace(v_gate_id::text, '-', ''),
            '0_foundation', 'gates',
            'inline audit-fix self-test row',
            'built', 'atlas'
        );

        -- owner change, NO status change, under a DISTINCT actor.
        SET LOCAL agency_os.callsign = 'dave';
        UPDATE public.gate_roadmap SET owner = 'scout' WHERE id = v_gate_id;

        SELECT count(*), max(changed_by_callsign), max(old_value),
               max(new_value), max(new_status)
          INTO v_cnt, v_actor, v_old, v_new, v_status
          FROM public.gate_roadmap_history
         WHERE gate_roadmap_id = v_gate_id AND change_kind = 'owner';

        IF v_cnt <> 1 THEN
            RAISE EXCEPTION
                'AUDIT_FIX_SELF_TEST FAIL: expected exactly 1 owner history row, got % (pre-fix this was 0 — the gap).', v_cnt
                USING ERRCODE = 'check_violation';
        END IF;
        IF v_actor IS DISTINCT FROM 'dave'
           OR v_old IS DISTINCT FROM 'atlas'
           OR v_new IS DISTINCT FROM 'scout'
           OR v_status IS DISTINCT FROM 'built' THEN
            RAISE EXCEPTION
                'AUDIT_FIX_SELF_TEST FAIL: owner history row wrong (actor=% old=% new=% status=%)',
                v_actor, v_old, v_new, v_status
                USING ERRCODE = 'check_violation';
        END IF;

        RAISE EXCEPTION 'AUDIT_FIX_SELF_TEST_OK' USING ERRCODE = 'check_violation';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
        IF v_msg = 'AUDIT_FIX_SELF_TEST_OK' THEN
            RAISE NOTICE
                'INLINE SELF-TEST PASS: owner change (no status change) logged to gate_roadmap_history with actor=dave old=atlas new=scout; fixtures rolled back via outer sub-tx';
        ELSE
            RAISE EXCEPTION 'INLINE SELF-TEST FAIL or unexpected error: %', v_msg;
        END IF;
    END;
END
$self_test$;


COMMIT;

-- ============================================================================
-- end of 20260603_gate_roadmap_audit_non_status.sql
-- ============================================================================
