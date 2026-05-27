-- ============================================================================
-- 20260527_keiracom_spawn_attribution_completion_status.sql
--
-- Phase 1 cutover-gate observability extension — adds completion_status
-- column to the keiracom_spawn_attribution table (created by PR #1207's
-- 20260527_keiracom_spawn_attribution.sql).
--
-- Per Aiden's CONCUR-with-clarification on PR #1207 + Elliot dispatch
-- 2026-05-27: closes the observability gate for Dave's first-customer
-- cutover by surfacing cost-of-failure (how much spend went to successful
-- spawns vs fails vs timeouts vs interrupted runs).
--
-- Companion to src/keiracom_system/attribution/logger.py
-- COMPLETION_STATUSES frozenset.
--
-- bd: Agency_OS-uik (this PR is a sibling extension, not a new KEI).
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for
-- public-schema table ALTER.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

ALTER TABLE public.keiracom_spawn_attribution
    ADD COLUMN IF NOT EXISTS completion_status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (completion_status IN ('success', 'fail', 'timeout', 'interrupted', 'unknown'));

-- Group-by-completion_status queries (cost-of-failure breakdown for the
-- daily CEO rollup). Same shape as the existing source_type / task_type /
-- callsign indexes from the parent migration.
CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_completion_status_ts
    ON public.keiracom_spawn_attribution (completion_status, ts DESC);

COMMENT ON COLUMN public.keiracom_spawn_attribution.completion_status IS
    'Phase 1 cutover-gate observability — outcome of the spawn (success/fail/'
    'timeout/interrupted/unknown). Default unknown lets dispatch-time writers '
    'land before completion-classification logic is wired; callers should '
    'patch with the real status once the spawn ends.';
