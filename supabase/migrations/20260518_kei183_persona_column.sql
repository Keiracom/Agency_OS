-- KEI-183: Supervisor v2 — persona column + index on public.tasks
-- Adds lane assignment column for per-callsign task routing.
-- NULL = unassigned-lane (Tier 1 deliberator default pick).

ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS persona TEXT;

COMMENT ON COLUMN public.tasks.persona IS
    'KEI-183: lane assignment, NULL = unassigned-lane (Tier 1 deliberator default pick)';

CREATE INDEX IF NOT EXISTS idx_tasks_persona
    ON public.tasks (persona)
    WHERE status = 'available';

-- Backfill: extract [CALLSIGN] prefix from title (lowercase) into persona.
-- Matches titles of the form "[CALLSIGN] ..." (e.g. "[ELLIOT] feat: ...").
UPDATE public.tasks
SET persona = LOWER(SUBSTRING(title FROM '^\[([A-Z]+)\]'))
WHERE persona IS NULL
  AND title ~ '^\[';
