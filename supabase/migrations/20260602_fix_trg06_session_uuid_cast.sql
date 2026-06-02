-- 20260602_fix_trg06_session_uuid_cast.sql
--
-- Persists the ::uuid cast fix applied live to prod on 2026-06-02 ~20:50 UTC.
--
-- Bug: fn_gate_proof_session_independence (trg_06) compared
--   tool_call_log.session_uuid (type UUID)
-- against
--   NEW.attester_session_uuid (type TEXT, per gate_proof_runs schema)
-- without a cast. Postgres raises "operator does not exist: uuid = text",
-- blocking all binding_reviewer INSERTs into gate_proof_runs.
--
-- Fix: add ::uuid cast on NEW.attester_session_uuid in both comparisons.
-- No logic change. The trigger remains SOFT (secondary signal only — see
-- original trg_06 comment in 20260602_gate_roadmap_proof_gate.sql).
--
-- Verified in prod: aiden binding_reviewer proof_run for fleet_autostart_recovery
-- (id=3c9bef55-3e4b-4aaa-9da4-ebae7bc9ff08) inserted successfully after fix.
--
-- Authored by AIDEN (governance lens, dispatched by Elliot 2026-06-02).

CREATE OR REPLACE FUNCTION public.fn_gate_proof_session_independence()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    v_builder           TEXT;
    v_count_in_builder  INTEGER;
    v_count_in_attester INTEGER;
BEGIN
    IF NEW.attestation_kind <> 'binding_reviewer' THEN
        RETURN NEW;
    END IF;

    -- Dave-exemption (bootstrap path).
    IF NEW.attesting_callsign = 'dave' THEN
        RETURN NEW;
    END IF;

    SELECT built_by_callsign INTO v_builder
      FROM public.gate_roadmap WHERE id = NEW.gate_roadmap_id;

    -- Cast to uuid: tool_call_log.session_uuid is UUID; attester_session_uuid is TEXT.
    SELECT count(*) INTO v_count_in_builder
      FROM public.tool_call_log
     WHERE callsign     = v_builder
       AND session_uuid = NEW.attester_session_uuid::uuid;

    IF v_count_in_builder > 0 THEN
        RAISE EXCEPTION
            'gate_proof_runs session-independence (soft): attester_session_uuid=% appears in builder=% tool_call_log.',
            NEW.attester_session_uuid, v_builder
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT count(*) INTO v_count_in_attester
      FROM public.tool_call_log
     WHERE callsign     = NEW.attesting_callsign
       AND session_uuid = NEW.attester_session_uuid::uuid;

    IF v_count_in_attester = 0 THEN
        RAISE EXCEPTION
            'gate_proof_runs session-independence (soft): attester_session_uuid=% has no record in attesting_callsign=% tool_call_log.',
            NEW.attester_session_uuid, NEW.attesting_callsign
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$fn$;

-- Verify the cast is present in the live function body.
DO $$
BEGIN
    ASSERT (
        SELECT prosrc FROM pg_proc WHERE proname = 'fn_gate_proof_session_independence'
    ) LIKE '%attester_session_uuid::uuid%',
    'fn_gate_proof_session_independence must contain ::uuid cast after migration';
    RAISE NOTICE '20260602_fix_trg06_session_uuid_cast: ::uuid cast verified in fn_gate_proof_session_independence.';
END $$;
