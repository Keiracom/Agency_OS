-- KEI-100 — Linear/Supabase task ID alignment (Phase 1: add canonical linear_id).
--
-- Background:
--   public.tasks.id is currently a free-form text label. Most rows use the
--   Linear KEI-N as the id, but:
--     * 1 sub-KEI exists with a Beads-suffix form (KEI-54B → Linear KEI-54)
--     * 23 REVIEW-PR-* rows have no Linear issue
--     * Some rows store the canonical KEI only inside the linear_url string
--   This makes "which Linear issue does this row track" ambiguous and forces
--   every consumer to regex-parse linear_url.
--
-- This migration adds a canonical linear_id column populated from the URL
-- (or from the id itself when it already matches KEI-N), with a UNIQUE
-- partial index. A BEFORE INSERT/UPDATE trigger keeps linear_id in sync
-- with linear_url for future writes.
--
-- Phase 2 — dropping the legacy `id` column — is NOT in this migration.
-- That requires coordinated FK migrations across 4 referrers
-- (task_verifications, active_threads, completion_sync_queue, ceo_decisions)
-- plus matching changes in the Beads CLI. Filed as follow-up.

-- 1. Add the canonical linear_id column. Nullable because REVIEW-PR-* rows
--    legitimately have no Linear issue.
ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS linear_id text;

COMMENT ON COLUMN public.tasks.linear_id IS
    'KEI-100 canonical Linear issue id (e.g. KEI-54). NULL for REVIEW-PR-* rows.';

-- 2. Backfill — priority order:
--    a) extract from linear_url if present (authoritative — URL is what Linear emits)
--    b) fall back to id if id already matches '^KEI-[0-9]+$'
--    c) leave NULL for REVIEW-PR-* and other non-Linear rows
UPDATE public.tasks
   SET linear_id = substring(linear_url FROM 'KEI-[0-9]+')
 WHERE linear_id IS NULL
   AND linear_url IS NOT NULL
   AND substring(linear_url FROM 'KEI-[0-9]+') IS NOT NULL;

UPDATE public.tasks
   SET linear_id = id
 WHERE linear_id IS NULL
   AND id ~ '^KEI-[0-9]+$';

-- 3. UNIQUE index — multiple rows MUST NOT claim the same Linear issue.
--    Partial so the 23 REVIEW-PR-* NULLs are allowed.
CREATE UNIQUE INDEX IF NOT EXISTS tasks_linear_id_unique
    ON public.tasks (linear_id)
 WHERE linear_id IS NOT NULL;

-- 4. Sync trigger — future inserts/updates that set linear_url must auto-fill
--    linear_id (when absent). Keeps the two fields aligned without requiring
--    every writer to know the rule.
CREATE OR REPLACE FUNCTION public.tasks_sync_linear_id()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.linear_id IS NULL AND NEW.linear_url IS NOT NULL THEN
        NEW.linear_id := substring(NEW.linear_url FROM 'KEI-[0-9]+');
    END IF;
    IF NEW.linear_id IS NULL AND NEW.id ~ '^KEI-[0-9]+$' THEN
        NEW.linear_id := NEW.id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tasks_sync_linear_id_trg ON public.tasks;
CREATE TRIGGER tasks_sync_linear_id_trg
    BEFORE INSERT OR UPDATE OF linear_url, linear_id, id ON public.tasks
    FOR EACH ROW
    EXECUTE FUNCTION public.tasks_sync_linear_id();
