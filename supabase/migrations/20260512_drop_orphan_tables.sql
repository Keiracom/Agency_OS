-- Migration: 20260512_drop_orphan_tables.sql
-- Purpose: KEI-9 Wave 2 Item 1 — drop 3 orphan tables identified by the
--          2026-05-12 memory audit (Aiden Supabase section + Elliot synthesis).
--
-- Empirical ORPHAN confirmation (2026-05-12, this PR):
--   grep -rnE "ceo_memory_archive" src/ scripts/ skills/    → 0 matches
--   grep -rnE "\belliot_knowledge\b" src/ scripts/ skills/  → 0 matches
--   grep -rnE "elliot_signoff_queue" src/ scripts/ skills/  → 0 matches
--
-- Audit findings (docs/audits/memory_audit_2026-05-12.md §Pattern B):
--   public.ceo_memory_archive       — 14 rows / 64 kB, no archival writer.
--                                     Clean orphan; likely populated by a
--                                     script that no longer exists.
--   public.elliot_knowledge         — 659 rows / 2.6 MB embeddings.
--                                     TWO triggers still attached:
--                                       trg_score_knowledge_insert
--                                       trg_score_knowledge_update
--                                     Both call trigger_score_knowledge().
--                                     Built end-to-end and never invoked
--                                     from src/ — silent infrastructure.
--   public.elliot_signoff_queue     — 52 rows / 168 kB.
--                                     Human-in-the-loop gate pattern,
--                                     obsoleted by Telegram concur flow.
--
-- Why drop now: per Pattern B teaching, orphan tables with attached
-- infrastructure (triggers, embeddings, scoring functions) are a latent
-- fire — if any writer is ever wired to elliot_knowledge accidentally,
-- the scoring trigger fires silently and accrues compute cost. Retiring
-- the surface forecloses that path.
--
-- Order matters:
--   1. DROP TRIGGERs on elliot_knowledge (clean removal of the scoring path)
--   2. DROP FUNCTION trigger_score_knowledge() (cleanup; the only caller is
--      the triggers we just dropped — CASCADE is unnecessary but defensive)
--   3. DROP TABLE for each of the three (IF EXISTS so the migration is
--      idempotent + safe to re-run)
--
-- All operations use IF EXISTS so re-runs are no-ops. Reversal requires
-- restore from backup (Supabase point-in-time recovery) — there is no
-- DOWN migration because the audit established zero production callers.
--
-- Created: 2026-05-12

-- ─────────────────────────────────────────────────────────────────────────────
-- Step 1: drop the two triggers attached to elliot_knowledge
-- ─────────────────────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_score_knowledge_insert ON public.elliot_knowledge;
DROP TRIGGER IF EXISTS trg_score_knowledge_update ON public.elliot_knowledge;

-- ─────────────────────────────────────────────────────────────────────────────
-- Step 2: drop the trigger function (zero callers after step 1)
-- ─────────────────────────────────────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.trigger_score_knowledge() CASCADE;

-- ─────────────────────────────────────────────────────────────────────────────
-- Step 3: drop the three orphan tables
-- ─────────────────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS public.ceo_memory_archive;
DROP TABLE IF EXISTS public.elliot_knowledge;
DROP TABLE IF EXISTS public.elliot_signoff_queue;
