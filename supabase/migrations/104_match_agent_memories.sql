-- RPC function for embedding cosine similarity search on agent_memories.
-- Used by memory_listener.py for semantic retrieval.
-- Requires pgvector extension (already installed).

CREATE OR REPLACE FUNCTION match_agent_memories(
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
    1 - (am.embedding <=> query_embedding) AS similarity
  FROM public.agent_memories am
  WHERE am.state = 'confirmed'
    AND am.embedding IS NOT NULL
    AND 1 - (am.embedding <=> query_embedding) > match_threshold
  ORDER BY am.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
