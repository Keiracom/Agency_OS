-- =============================================================================
-- KEI-241  Vultr Postgres Migration — max_concurrent_tasks column
-- Author:  [AIDEN]
-- Date:    2026-05-28
-- Branch:  aiden/vultr-postgres-migration
--
-- DO NOT APPLY until Atlas has provisioned the Vultr Postgres instance AND
-- VULTR_POSTGRES_DSN is set in the environment.
--
-- Apply AFTER 001_schema.sql and 002_triggers.sql.
--
-- Requirement (KEI-241): max_concurrent_tasks must be an explicit column, not
-- derived from the tier enum. The tier enum may evolve independently of the
-- concurrency limit; hard-coding a derivation in application code creates a
-- hidden coupling. Storing the value per row lets overrides be applied without
-- schema changes (e.g. enterprise trial bumps for a single tenant).
--
-- Defaults by tier:
--   solo  →  2
--   pro   →  6
--   scale → 20
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Hard gate: refuse to run on a standby / replica.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'KEI-241 gate: pg_is_in_recovery() = true — this is a standby. '
            'Run only against the primary Vultr Postgres instance.';
    END IF;
END;
$$;

-- ---------------------------------------------------------------------------
-- Add column (idempotent via IF NOT EXISTS).
-- ---------------------------------------------------------------------------
ALTER TABLE public.keiracom_tenants
    ADD COLUMN IF NOT EXISTS max_concurrent_tasks INTEGER NOT NULL DEFAULT 2;

COMMENT ON COLUMN public.keiracom_tenants.max_concurrent_tasks IS
    'KEI-241 — Maximum number of simultaneous active tasks for this tenant. '
    'Defaults: solo=2, pro=6, scale=20. May be overridden per-row for enterprise '
    'trials without a schema change.';

-- ---------------------------------------------------------------------------
-- Seed: update existing rows to tier-appropriate defaults.
--
-- Rows already at the column default (2) are updated even if they happen to be
-- solo-tier so the UPDATE is explicit and auditable. Pro and Scale rows must be
-- bumped from the column default of 2.
-- ---------------------------------------------------------------------------
UPDATE public.keiracom_tenants
   SET max_concurrent_tasks = CASE tier
       WHEN 'solo'  THEN 2
       WHEN 'pro'   THEN 6
       WHEN 'scale' THEN 20
       -- Fallback for any future tier added before this file is updated — keep
       -- at the conservative default of 2 rather than failing.
       ELSE 2
   END
WHERE TRUE;   -- explicit full-table update so the intent is unambiguous
