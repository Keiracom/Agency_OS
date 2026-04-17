-- agent_memories: typed memory store for multi-agent knowledge compounding.
-- No embeddings in v1 — text + tag + type filters via PostgREST. Embeddings
-- deferred until measured retrieval-miss evidence justifies adding pgvector.

CREATE TABLE IF NOT EXISTS public.agent_memories (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  callsign         text NOT NULL,
  source_type      text NOT NULL,
  content          text NOT NULL,
  typed_metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,
  tags             text[] NOT NULL DEFAULT '{}',
  valid_from       timestamptz NOT NULL DEFAULT now(),
  valid_to         timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_memories_callsign_idx    ON public.agent_memories (callsign);
CREATE INDEX IF NOT EXISTS agent_memories_source_type_idx ON public.agent_memories (source_type);
CREATE INDEX IF NOT EXISTS agent_memories_tags_idx        ON public.agent_memories USING GIN (tags);
CREATE INDEX IF NOT EXISTS agent_memories_created_at_idx  ON public.agent_memories (created_at DESC);
CREATE INDEX IF NOT EXISTS agent_memories_valid_from_idx  ON public.agent_memories (valid_from DESC);
CREATE INDEX IF NOT EXISTS agent_memories_valid_to_idx    ON public.agent_memories (valid_to) WHERE valid_to IS NOT NULL;

-- No SQL function needed — simple PostgREST filters cover v1.
