-- KEI-227 (Linear) / Agency_OS-8c67 (bd) — K1 ID canonicalisation foundation.
--
-- Adds bd_id column to public.tasks so the canonical Linear KEI-N (tasks.id)
-- can be paired with the bd-Dolt Agency_OS-xxx short-code. Subsequent K2
-- (sync_events) joins on either key without an FK violation; tasks_cli.py
-- writers can match bd_id when invoked from `bd update --claim <Agency_OS-xxx>`
-- against rows keyed on KEI-N from reconcile_linear_supabase.py.
--
-- Backfill happens via scripts/backfill_tasks_bd_id.py (dry-run by default,
-- --apply to mutate). Not run in this migration so the column add is reversible.

ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS bd_id TEXT;

-- Unique-when-present: NULL allowed (rows from Linear that haven't been
-- paired with a bd issue yet), but each Agency_OS-xxx maps to at most one
-- Linear KEI-N row.
CREATE UNIQUE INDEX IF NOT EXISTS uq_tasks_bd_id
    ON public.tasks (bd_id)
    WHERE bd_id IS NOT NULL;

-- Lookup index for the `id = %s OR bd_id = %s` pattern in tasks_cli.py.
CREATE INDEX IF NOT EXISTS idx_tasks_bd_id
    ON public.tasks (bd_id)
    WHERE bd_id IS NOT NULL;

COMMENT ON COLUMN public.tasks.bd_id IS
    'KEI-227 — bd-Dolt short-code (Agency_OS-xxx) paired with the canonical '
    'Linear identifier in tasks.id. NULL means no bd-Dolt issue paired yet. '
    'Populated by scripts/backfill_tasks_bd_id.py and by tasks_cli.py writers '
    'when bd ops touch a Linear-keyed row.';
