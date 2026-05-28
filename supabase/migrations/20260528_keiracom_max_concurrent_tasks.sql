-- Work-loop consumer (Agency_OS-s3ye): per-tenant concurrent-spawn ceiling.
--
-- keiracom_tenants had NO max_concurrent_tasks column (verified during the
-- chat context_composer build, 2026-05-28). The tier-gated work-loop consumer
-- reads this ceiling atomically (Lua INCR+compare), so it must exist as a real
-- column — GOV-10 resolve-now-not-later.
--
-- Tier→ceiling per Dave's work-loop dispatch: Solo=2, Pro=6, Team=20.
-- NOTE: keiracom_tenants.tier enum is ('solo','pro','scale') — there is no
-- 'team'. The dispatch's "Team" (top tier) maps to 'scale'=20 here. Naming
-- discrepancy flagged to the orchestrator; this migration follows the existing
-- enum, not the dispatch's label.

BEGIN;

ALTER TABLE public.keiracom_tenants
    ADD COLUMN IF NOT EXISTS max_concurrent_tasks INT NOT NULL DEFAULT 2
        CONSTRAINT keiracom_tenants_max_concurrent_tasks_positive
        CHECK (max_concurrent_tasks > 0);

-- Backfill existing rows from their tier (the DEFAULT 2 already covers solo).
UPDATE public.keiracom_tenants
SET max_concurrent_tasks = CASE tier
    WHEN 'solo'  THEN 2
    WHEN 'pro'   THEN 6
    WHEN 'scale' THEN 20
    ELSE 2
END;

COMMENT ON COLUMN public.keiracom_tenants.max_concurrent_tasks IS
    'Per-tenant concurrent-spawn ceiling for the work-loop consumer (Agency_OS-s3ye). Tier defaults: solo=2, pro=6, scale=20 (dispatch "Team"→scale). Read atomically by the consumer admit Lua.';

COMMIT;
