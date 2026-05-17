-- KEI-86 — Phase-lock enforcement for bd ready + bd claim (KEI-117 mechanical gate).
--
-- Adds public.tasks.phase (numeric(3,1)) plus a ceo_memory key 'ceo:phase_lock'
-- holding the current_phase_max integer. The tasks_cli.py shim's cmd_ready
-- filters and cmd_claim refuses based on these values; this migration only
-- shapes the data.
--
-- Phase map (Elliot interim per Dave KEI-117/118, 2026-05-17):
--   0    — memory foundation (KEI-86, KEI-107, KEI-108, KEI-116, KEI-117)
--   0.5  — Model A stability (KEI-45, KEI-66, KEI-74…79, KEI-84)
--   1+   — everything else (default to 1 for legacy rows)
--
-- Default for NEW rows is 0 per Linear KEI-86 spec.

ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS phase numeric(3,1);

-- Backfill: explicit Phase 0 for memory KEIs.
UPDATE public.tasks
   SET phase = 0
 WHERE id IN ('KEI-86', 'KEI-107', 'KEI-108', 'KEI-116', 'KEI-117');

-- Backfill: Phase 0.5 for stability KEIs.
UPDATE public.tasks
   SET phase = 0.5
 WHERE id IN ('KEI-45', 'KEI-66', 'KEI-74', 'KEI-75', 'KEI-76',
              'KEI-77', 'KEI-78', 'KEI-79', 'KEI-84');

-- Backfill: every legacy row that wasn't named above defaults to Phase 1
-- so the gate hides it under lock=0 (which is the current default).
UPDATE public.tasks
   SET phase = 1
 WHERE phase IS NULL;

-- Lock in the spec default for future rows and forbid NULL.
ALTER TABLE public.tasks
  ALTER COLUMN phase SET DEFAULT 0,
  ALTER COLUMN phase SET NOT NULL;

-- Seed the phase lock at 0 (current state — Phase 0 only).
--
-- GOV-12 exception (Dave-approved 2026-05-17, option c): this migration
-- adds READ-side enforcement only. The WRITE side (advancing
-- current_phase_max) shares the gates-as-comments hole that all 400+
-- ceo_memory keys carry today. Mechanical write-guard is tracked as the
-- cross-cutting follow-up Linear KEI-87 (RLS or BEFORE UPDATE trigger on
-- the 'ceo:' prefix). KEI-86 ships unblocked; KEI-87 closes the surface.
INSERT INTO public.ceo_memory (key, value)
VALUES ('ceo:phase_lock', '{"current_phase_max": 0}'::jsonb)
ON CONFLICT (key) DO NOTHING;

COMMENT ON COLUMN public.tasks.phase IS
  'KEI-86 phase tier (0, 0.5, 1, 2, 3, 4, 5). Visibility + claim gated by ceo_memory key ceo:phase_lock.';
