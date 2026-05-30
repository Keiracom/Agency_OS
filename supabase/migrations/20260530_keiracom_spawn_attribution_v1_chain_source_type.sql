-- ============================================================================
-- 20260530_keiracom_spawn_attribution_v1_chain_source_type.sql
--
-- V1-battery prep hotfix (Atlas, Elliot smoke-test dispatch 2026-05-30 ~12:35
-- AEST). api_agent_cold_start writes source_type='v1_chain' for each chain
-- hop INSERT into keiracom_spawn_attribution, but the parent migration
-- 20260527_keiracom_spawn_attribution.sql CHECK constraint only allowed
-- {slack, pr, cron, inbox, unknown}. Smoke caught the CheckViolation —
-- attribution rows were silently failing for every V1 chain hop, breaking
-- the per-task A$10 ceiling read path (which sums cost_aud WHERE task_id
-- = ... ORDER BY ts).
--
-- v1_chain is a legitimate first-class source for the V1 chain agents'
-- per-hop telemetry. Adding to the constraint is the right fix (not
-- silently downgrading the source_type to 'unknown' in app code).
--
-- Companion: src/keiracom_system/attribution/logger.py SOURCE_TYPES
-- frozenset must be expanded to match.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for
-- public-schema constraint ALTER.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

ALTER TABLE public.keiracom_spawn_attribution
    DROP CONSTRAINT IF EXISTS keiracom_spawn_attribution_source_type_check;

ALTER TABLE public.keiracom_spawn_attribution
    ADD CONSTRAINT keiracom_spawn_attribution_source_type_check
    CHECK (source_type IN ('slack', 'pr', 'cron', 'inbox', 'unknown', 'v1_chain'));
