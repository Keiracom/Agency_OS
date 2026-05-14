-- KEI-54 Stage A — Claude Code tool call log: producer-side schema only.
-- Stage B (index into Weaviate) gated on Atlas KEI-48 Weaviate install.
--
-- Per Dave/Elliot Step 0 ack-via-quiet-proceed ts ~2026-05-14T07:42 UTC.
-- Claim: tasks row KEI-54 status=active claimed_by=aiden @ 07:42:35 UTC.

CREATE TABLE IF NOT EXISTS public.tool_call_log (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    callsign            TEXT         NOT NULL,
    session_uuid        UUID,
    tool_name           TEXT         NOT NULL,
    tool_input          JSONB        NOT NULL DEFAULT '{}'::jsonb,
    tool_output_excerpt TEXT,
    started_at          TIMESTAMPTZ  NOT NULL,
    completed_at        TIMESTAMPTZ,
    duration_ms         INTEGER,
    exit_code           INTEGER,
    indexed             BOOLEAN      NOT NULL DEFAULT FALSE,
    indexed_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.tool_call_log IS
    'KEI-54 Stage A — producer-side capture of Claude Code tool executions '
    'across all 6 callsigns. Stage B worker (post-KEI-48 Weaviate) consumes '
    'rows WHERE indexed=false and pushes to a Weaviate collection for '
    'retrieval/analytics. Until then this is a passive staging buffer.';

COMMENT ON COLUMN public.tool_call_log.tool_output_excerpt IS
    'First ~500 chars of tool output (truncate caller-side to bound row size). '
    'Full output remains in Claude Code logs; this is a retrieval-cache excerpt.';

COMMENT ON COLUMN public.tool_call_log.indexed IS
    'False until Stage B worker copies the row to Weaviate (Atlas KEI-48 + KEI-49 '
    'LlamaIndex). Stage B updates indexed=true + indexed_at=NOW(). Index on this '
    'column lets the worker scan unindexed rows efficiently.';

-- Index for Stage B worker scan: WHERE indexed=false ORDER BY started_at.
-- Partial index keeps it tiny once most rows are indexed.
CREATE INDEX IF NOT EXISTS idx_tool_call_log_pending_index
    ON public.tool_call_log (started_at)
    WHERE indexed = FALSE;

-- Index for per-callsign rollup queries (CLI debug, agent analytics).
CREATE INDEX IF NOT EXISTS idx_tool_call_log_callsign_started
    ON public.tool_call_log (callsign, started_at DESC);
