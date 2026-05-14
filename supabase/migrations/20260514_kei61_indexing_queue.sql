-- KEI-61 Phase A — durable indexing queue (Supabase staging buffer).
-- Per Linear KEI-61 spec + Dave architecture ts ~1778733600.
-- Capture-layer webhooks (Linear/Slack/Git/ceo_memory/tool_log) write to
-- indexing_queue first; worker (Phase B, post KEI-48 Weaviate landing)
-- consumes pending rows. Prevents dropped events during indexer downtime.

CREATE TABLE IF NOT EXISTS public.indexing_queue (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source        TEXT NOT NULL CHECK (source IN ('git', 'slack', 'linear', 'ceo_memory', 'tool_log')),
    payload       JSONB NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    attempts      INTEGER NOT NULL DEFAULT 0,
    error         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at  TIMESTAMPTZ,
    indexed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_indexing_queue_status_created
    ON public.indexing_queue (status, created_at);

COMMENT ON TABLE  public.indexing_queue IS 'KEI-61 durable staging buffer for capture-layer webhooks before LlamaIndex/Weaviate indexing.';
COMMENT ON COLUMN public.indexing_queue.source IS 'webhook source enum: git | slack | linear | ceo_memory | tool_log';
COMMENT ON COLUMN public.indexing_queue.payload IS 'raw webhook payload pre-sanitisation; KEI-57 secret-redaction integration is a follow-up';
COMMENT ON COLUMN public.indexing_queue.status IS 'pending → processing → done | failed (retry by reset to pending)';
COMMENT ON COLUMN public.indexing_queue.attempts IS 'incremented on each worker pickup; retry policy lives in worker (Phase B)';
