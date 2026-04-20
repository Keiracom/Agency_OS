-- Migration 103: Cognitive Assistant schema extension for agent_memories.
-- Applied via MCP 2026-04-17. Committed to repo post-hoc per LISTENER-GOV-F2.
-- Ratified by Dave 2026-04-17 (verbal), post-hoc written 2026-04-18.

-- Lifecycle state column
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS state text NOT NULL DEFAULT 'confirmed';
ALTER TABLE public.agent_memories DROP CONSTRAINT IF EXISTS agent_memories_state_check;
ALTER TABLE public.agent_memories ADD CONSTRAINT agent_memories_state_check
  CHECK (state IN ('tentative', 'confirmed', 'superseded', 'contradicted', 'archived'));

-- Quality signals
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS confidence float NOT NULL DEFAULT 1.0;
ALTER TABLE public.agent_memories DROP CONSTRAINT IF EXISTS agent_memories_confidence_check;
ALTER TABLE public.agent_memories ADD CONSTRAINT agent_memories_confidence_check
  CHECK (confidence >= 0.0 AND confidence <= 1.0);

ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS trust text NOT NULL DEFAULT 'agent_extracted';
ALTER TABLE public.agent_memories DROP CONSTRAINT IF EXISTS agent_memories_trust_check;
ALTER TABLE public.agent_memories ADD CONSTRAINT agent_memories_trust_check
  CHECK (trust IN ('dave_confirmed', 'dave_observed', 'agent_extracted', 'raw_ingest'));

-- Retrieval signals
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS access_count int NOT NULL DEFAULT 0;
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS last_accessed_at timestamptz;
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Relationship columns (self-FKs)
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS supersedes_id uuid
  REFERENCES public.agent_memories(id) ON DELETE SET NULL;
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS contradicted_by_id uuid
  REFERENCES public.agent_memories(id) ON DELETE SET NULL;
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS promoted_from_id uuid
  REFERENCES public.agent_memories(id) ON DELETE SET NULL;

-- Governance / provenance
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS provenance jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Integration cross-refs
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS directive_id text;
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS pr_number int;
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS ceo_memory_key text;

-- Dave's SIGNOFF_QUEUE workflow columns
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS category text;
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS signoff_status text NOT NULL DEFAULT 'approved';
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS business_score int;
ALTER TABLE public.agent_memories ADD COLUMN IF NOT EXISTS learning_score int;

-- Indexes
CREATE INDEX IF NOT EXISTS agent_memories_state_idx ON public.agent_memories (state);
CREATE INDEX IF NOT EXISTS agent_memories_access_count_idx ON public.agent_memories (access_count DESC);
