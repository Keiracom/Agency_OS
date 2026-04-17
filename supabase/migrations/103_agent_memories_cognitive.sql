-- Cognitive Assistant schema extension for agent_memories.
-- Extends the v1 typed-memory table with the columns needed for:
--   • Pillar 1 Lifecycle: state machine + supersession + contradiction links
--   • Pillar 2 Quality: confidence + trust enum
--   • Pillar 3 Retrieval: access_count + last_accessed_at + embedding (semantic)
--   • Pillar 5 Governance: provenance jsonb (who/method/source)
--   • Pillar 6 Integration: cross-references to directive_id / pr_number / ceo_memory_key + promoted_from_id
--   • Dave's SIGNOFF_QUEUE workflow: category + signoff_status + business_score + learning_score
--
-- Embedding column is vector(1536) for OpenAI text-embedding-3-small.
-- Backfill of embeddings for existing rows happens via a separate script
-- (one-time, batched, rate-limited). This migration only adds the column.
--
-- Ratified 2026-04-17 in the Agency OS supergroup as part of the Cognitive
-- Assistant architecture (see docs/memory_interface.md for full design).

-- =====================================================================
-- Enum check values (kept inline as CHECK constraints for v1 — can be
-- promoted to proper Postgres ENUM types later if churn settles)
-- =====================================================================

-- Lifecycle state column — drives retrieval visibility defaults.
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS state text NOT NULL DEFAULT 'confirmed';

ALTER TABLE public.agent_memories
  DROP CONSTRAINT IF EXISTS agent_memories_state_check;
ALTER TABLE public.agent_memories
  ADD CONSTRAINT agent_memories_state_check
  CHECK (state IN ('tentative', 'confirmed', 'superseded', 'contradicted', 'archived'));

-- Quality signals.
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS confidence float NOT NULL DEFAULT 1.0;

ALTER TABLE public.agent_memories
  DROP CONSTRAINT IF EXISTS agent_memories_confidence_check;
ALTER TABLE public.agent_memories
  ADD CONSTRAINT agent_memories_confidence_check
  CHECK (confidence >= 0.0 AND confidence <= 1.0);

ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS trust text NOT NULL DEFAULT 'agent_extracted';

ALTER TABLE public.agent_memories
  DROP CONSTRAINT IF EXISTS agent_memories_trust_check;
ALTER TABLE public.agent_memories
  ADD CONSTRAINT agent_memories_trust_check
  CHECK (trust IN ('dave_confirmed', 'dave_observed', 'agent_extracted', 'raw_ingest'));

-- Retrieval signals.
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS access_count int NOT NULL DEFAULT 0;
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS last_accessed_at timestamptz;
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Relationship columns (self-FKs).
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS supersedes_id uuid
    REFERENCES public.agent_memories(id) ON DELETE SET NULL;
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS contradicted_by_id uuid
    REFERENCES public.agent_memories(id) ON DELETE SET NULL;
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS promoted_from_id uuid
    REFERENCES public.agent_memories(id) ON DELETE SET NULL;

-- Governance / provenance.
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS provenance jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Integration cross-refs (nullable).
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS directive_id text;
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS pr_number int;
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS ceo_memory_key text;

-- Dave's SIGNOFF_QUEUE workflow columns.
ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS category text;
ALTER TABLE public.agent_memories
  DROP CONSTRAINT IF EXISTS agent_memories_category_check;
ALTER TABLE public.agent_memories
  ADD CONSTRAINT agent_memories_category_check
  CHECK (category IS NULL OR category IN
    ('daily', 'decision', 'learning', 'research', 'evaluation', 'audit'));

ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS signoff_status text NOT NULL DEFAULT 'approved';
ALTER TABLE public.agent_memories
  DROP CONSTRAINT IF EXISTS agent_memories_signoff_status_check;
ALTER TABLE public.agent_memories
  ADD CONSTRAINT agent_memories_signoff_status_check
  CHECK (signoff_status IN ('pending', 'approved', 'rejected'));

ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS business_score int;
ALTER TABLE public.agent_memories
  DROP CONSTRAINT IF EXISTS agent_memories_business_score_check;
ALTER TABLE public.agent_memories
  ADD CONSTRAINT agent_memories_business_score_check
  CHECK (business_score IS NULL OR (business_score >= 0 AND business_score <= 100));

ALTER TABLE public.agent_memories
  ADD COLUMN IF NOT EXISTS learning_score int;
ALTER TABLE public.agent_memories
  DROP CONSTRAINT IF EXISTS agent_memories_learning_score_check;
ALTER TABLE public.agent_memories
  ADD CONSTRAINT agent_memories_learning_score_check
  CHECK (learning_score IS NULL OR (learning_score >= 0 AND learning_score <= 100));

-- =====================================================================
-- Indexes — support the new filter and retrieval patterns
-- =====================================================================

-- Semantic similarity (cosine) — IVFFLAT is fine at our row count; can move
-- to HNSW later if retrieval latency degrades at 1M+ rows.
CREATE INDEX IF NOT EXISTS agent_memories_embedding_idx
  ON public.agent_memories
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS agent_memories_state_idx
  ON public.agent_memories (state);

CREATE INDEX IF NOT EXISTS agent_memories_category_idx
  ON public.agent_memories (category) WHERE category IS NOT NULL;

CREATE INDEX IF NOT EXISTS agent_memories_signoff_status_idx
  ON public.agent_memories (signoff_status);

CREATE INDEX IF NOT EXISTS agent_memories_access_count_idx
  ON public.agent_memories (access_count DESC);

CREATE INDEX IF NOT EXISTS agent_memories_directive_idx
  ON public.agent_memories (directive_id) WHERE directive_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS agent_memories_pr_number_idx
  ON public.agent_memories (pr_number) WHERE pr_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS agent_memories_supersedes_idx
  ON public.agent_memories (supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS agent_memories_contradicted_by_idx
  ON public.agent_memories (contradicted_by_id) WHERE contradicted_by_id IS NOT NULL;

-- =====================================================================
-- Backfill trust for pre-existing rows based on metadata.source
-- The 79 copy-forward rows from elliot_internal.memories had a 'source' tag.
-- Rows whose provenance indicates Dave gave the fact directly are upgraded
-- to dave_confirmed. All others stay agent_extracted (the default).
-- =====================================================================

UPDATE public.agent_memories
SET trust = 'dave_confirmed'
WHERE typed_metadata->>'migrated_from' = 'elliot_internal.memories'
  AND typed_metadata->>'original_type' IN ('dave_confirmed', 'core_fact', 'fact');
