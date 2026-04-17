-- Extend match_agent_memories RPC to include tentative rows and return state.
--
-- Rationale (diagnostic FM-2 + ingest gate):
-- Auto-captured memories default to state='tentative'. If RPC filters them
-- out entirely, they can never be surfaced → can never be promoted to
-- 'confirmed' via retrieval reinforcement → stuck at tentative forever.
-- Python applies a trust-weight discount to tentative rows; if they still
-- surface top-N they earn the access_count bump that promotes them.
--
-- Change: drop the state='confirmed' filter; return state column; keep
-- embedding IS NOT NULL + similarity threshold filters.

-- DROP first: PostgreSQL won't allow CREATE OR REPLACE when the RETURNS TABLE
-- signature changes (we added the `state` column).
DROP FUNCTION IF EXISTS match_agent_memories(vector, int, float);

CREATE FUNCTION match_agent_memories(
  query_embedding vector(1536),
  match_count int DEFAULT 5,
  match_threshold float DEFAULT 0.3
)
RETURNS TABLE (
  id uuid,
  source_type text,
  content text,
  tags text[],
  created_at timestamptz,
  callsign text,
  access_count int,
  state text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    am.id,
    am.source_type,
    am.content,
    am.tags,
    am.created_at,
    am.callsign,
    am.access_count,
    am.state,
    1 - (am.embedding <=> query_embedding) AS similarity
  FROM public.agent_memories am
  WHERE am.embedding IS NOT NULL
    AND am.state NOT IN ('superseded', 'contradicted', 'archived')
    AND 1 - (am.embedding <=> query_embedding) > match_threshold
  ORDER BY am.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
