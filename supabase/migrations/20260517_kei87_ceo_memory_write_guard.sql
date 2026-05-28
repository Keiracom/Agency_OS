-- KEI-87 — Cross-cutting ceo_memory write-guard (GOV-12 mechanical).
--
-- Closes the 400+-key gates-as-comments hole Aiden's audit (PR #917 review)
-- surfaced: prior to this migration any callsign with DATABASE_URL could
-- UPDATE/INSERT a 'ceo:*' key. The 'ceo:' prefix signalled intent but was
-- NOT enforced.
--
-- ⚠ DEPLOYMENT ORDER (do NOT apply this migration until step 1 lands):
--   1. Migrate ALL existing 'ceo:*' writer call-sites to the wrapper at
--      src/governance/ceo_memory_writer.py — see the README in that module.
--      The wrapper issues `SET LOCAL agency_os.callsign = '<callsign>'`
--      inside the same transaction as the UPDATE/INSERT.
--   2. Apply this migration (adds trigger + raises EXCEPTION when the var
--      is missing or not in the allowlist).
--   3. Verify positive + negative paths (tests in tests/governance/).
--   4. Tighten allowlist by amending the trigger if narrower-than-default
--      gating is required (Phase 0.5 follow-up KEI).
--
-- Initial allowlist (intentionally permissive — every callsign is allowed;
-- the gate exists so MISSING var = denied). The 'who counts as CEO' tightening
-- is a separate follow-up so this PR can ship the mechanism without breaking
-- existing writers mid-flight.
--
-- ⚠ PROD STATE (verified by Nova 2026-05-28 via pg_trigger/pg_proc query):
-- this trigger + function are NOT YET APPLIED in the Supabase prod DB
-- (jatzvazlbusedwsnqxzr) — there is no write-guard on ceo_memory today. Do NOT
-- apply this migration until deployment step 1 (call-site migration to the
-- ceo_memory_writer wrapper) is complete fleet-wide; applying it now would
-- begin rejecting EVERY ceo:* write from any callsite that doesn't SET LOCAL
-- agency_os.callsign to an allowlisted value — a fleet-wide write outage.

CREATE OR REPLACE FUNCTION public.ceo_memory_write_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    caller text;
BEGIN
    -- Only guard 'ceo:' prefix keys; orchestrator-mutated prefixes
    -- (completion:* / directive_*_status / heartbeat:* / business_universe_*)
    -- are explicitly NOT in scope (Aiden's audit excluded those).
    IF NEW.key NOT LIKE 'ceo:%' THEN
        RETURN NEW;
    END IF;

    caller := current_setting('agency_os.callsign', true);
    IF caller IS NULL OR caller = '' THEN
        RAISE EXCEPTION 'KEI-87 ceo_memory write-guard: agency_os.callsign session-var must be SET LOCAL before writing key %; missing var refused.', NEW.key
            USING ERRCODE = 'check_violation';
    END IF;

    -- Per 3-way ratified spec (elliot+max+aiden 2026-05-17 ts ~1779010883):
    -- allowlist = (elliot, dave). Aiden's PR #922 review caught the prior
    -- permissive-first draft as scope-delta from ratified shape. Tightened.
    -- 'john' added (Elliot 2026-05-28): John's exit-cycle (src/keiracom_system/
    -- chat/exit_cycle.py, KEI-?/#1268) captures ratified decisions to ceo_memory
    -- by design — John is an intended ceo_memory writer, so the callsign belongs
    -- on the allowlist (masking as 'elliot' would lose attribution).
    IF caller NOT IN ('elliot', 'dave', 'john') THEN
        RAISE EXCEPTION 'KEI-87 ceo_memory write-guard: agency_os.callsign=% is not in (elliot, dave, john) — refused write on key %', caller, NEW.key
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS ceo_memory_write_guard ON public.ceo_memory;

CREATE TRIGGER ceo_memory_write_guard
    BEFORE INSERT OR UPDATE
    ON public.ceo_memory
    FOR EACH ROW
    EXECUTE FUNCTION public.ceo_memory_write_guard();

COMMENT ON FUNCTION public.ceo_memory_write_guard() IS
    'KEI-87 GOV-12 mechanical write-guard for ceo:* keys. Requires agency_os.callsign session var (set by src/governance/ceo_memory_writer.py wrapper). Permissive allowlist by default — tighten via follow-up KEI.';
