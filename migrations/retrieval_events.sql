-- KEI-49 — retrieval_events table for observability.
--
-- Every agent_query.query() call writes one row here so we can:
--   * see which agent asks what, how often
--   * spot reranker-bypass spikes (cold-start, container OOM)
--   * find top-5 unmatched queries (citation_required=True returning "")
--
-- Indexed by (agent, occurred_at DESC) for per-agent dashboards and by
-- (occurred_at DESC) WHERE bypass_rerank=true for fault-finding views.
-- Schema is forward-compatible with Scout's design spec §9.

CREATE TABLE IF NOT EXISTS public.retrieval_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  agent           TEXT NOT NULL,
  query_text      TEXT NOT NULL,
  collections     TEXT[] NOT NULL,
  k_initial       INT  NOT NULL,
  k_returned      INT  NOT NULL,
  elapsed_ms      INT  NOT NULL,
  bypass_rerank   BOOLEAN NOT NULL DEFAULT FALSE,
  top_citation_id TEXT,
  top_score       NUMERIC(4,3)
);

CREATE INDEX IF NOT EXISTS retrieval_events_agent_occurred
  ON public.retrieval_events (agent, occurred_at DESC);

CREATE INDEX IF NOT EXISTS retrieval_events_bypass_occurred
  ON public.retrieval_events (occurred_at DESC) WHERE bypass_rerank = TRUE;

COMMENT ON TABLE public.retrieval_events IS
  'KEI-49 retrieval observability — one row per agent_query.query() call.';
COMMENT ON COLUMN public.retrieval_events.query_text IS
  'Truncated to 200 chars by the writer (src/retrieval/agent_query.py).';
COMMENT ON COLUMN public.retrieval_events.bypass_rerank IS
  'True when FlashRank failed/disabled; raw ANN scores returned. PR1 always TRUE pending KEI for reranker wiring.';
