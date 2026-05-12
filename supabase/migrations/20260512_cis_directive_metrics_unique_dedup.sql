-- Migration: cis_directive_metrics dedup + UNIQUE index
-- Wave 1 Item 2 (Dave directive ts 1778565940, Elliot dispatch ts 1778566186,
-- confirm-to-execute ts 1778566xxx).
--
-- Problem (audit Surprise — Aiden Stream 1 section, 2026-05-12):
--   scripts/three_store_save.py INSERTs into public.cis_directive_metrics with
--   no ON CONFLICT clause. Replay-save during directive retry creates duplicate
--   rows. Empirical state at migration time: 195 total rows, 175 distinct
--   (directive_id, directive_ref) keys → 20 duplicate-pair rows (all with
--   directive_ref=NULL, i.e. numeric directives replayed).
--
-- Fix:
--   1. Dedup: keep the latest row per (directive_id, directive_ref) by
--      completed_date DESC NULLS LAST, created_at DESC tiebreak.
--   2. Add UNIQUE index with NULLS NOT DISTINCT semantics so future replays
--      can use INSERT ... ON CONFLICT (directive_id, directive_ref) DO UPDATE.
--      Compound key is required because non-numeric directives use directive_id=0
--      + a non-null directive_ref ('D1.8', 'CD-PLAYER-V1', etc.); a bare
--      directive_id UNIQUE would collapse all those into one row.
--   3. Postgres 15+ NULLS NOT DISTINCT — Supabase runs 15.x.
--
-- Re-runnable: dedup is idempotent (no rows to remove on second run); index is
-- IF NOT EXISTS.

-- Step 1: deduplicate. Keep latest by completed_date DESC NULLS LAST, then
-- created_at DESC. CTE numbers rows per group; delete all but row_number=1.
WITH ranked AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY directive_id, directive_ref
            ORDER BY completed_date DESC NULLS LAST, created_at DESC
        ) AS rn
    FROM public.cis_directive_metrics
)
DELETE FROM public.cis_directive_metrics
WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

-- Step 2: add UNIQUE index. NULLS NOT DISTINCT means two rows with the same
-- directive_id and both directive_ref=NULL count as a conflict (correct for
-- numeric directives where directive_ref is always NULL).
CREATE UNIQUE INDEX IF NOT EXISTS
    cis_directive_metrics_directive_uniq
    ON public.cis_directive_metrics (directive_id, directive_ref)
    NULLS NOT DISTINCT;

-- Step 3: dedupe verification — runtime sanity check that the index can be
-- created. If duplicates remain (shouldn't), this raises in the same txn.
DO $$
DECLARE
    dup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO dup_count
    FROM (
        SELECT 1
        FROM public.cis_directive_metrics
        GROUP BY directive_id, directive_ref
        HAVING COUNT(*) > 1
    ) t;
    IF dup_count > 0 THEN
        RAISE EXCEPTION 'cis_directive_metrics still has % duplicate keys after dedup', dup_count;
    END IF;
END $$;
