-- agent_checkpoints — context_checkpoint_resume storage (gate_roadmap 952c8d0d).
-- Writer fires BEFORE watchdog /clear; reader injects into REVIVED message.
-- Open/consumed semantics + partial index for fast 'is there an open checkpoint
-- for callsign X' lookup.

CREATE TABLE IF NOT EXISTS public.agent_checkpoints (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    callsign         TEXT         NOT NULL,
    task_id          TEXT,
    artifact_pointer JSONB        NOT NULL DEFAULT '{}'::jsonb,
    position_text    TEXT         NOT NULL CHECK (length(trim(position_text)) > 0),
    pane_tail        TEXT,
    captured_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    captured_by      TEXT         NOT NULL CHECK (captured_by IN ('watchdog', 'stop_hook', 'manual')),
    consumed_at      TIMESTAMPTZ,
    consumed_reason  TEXT
);

COMMENT ON TABLE public.agent_checkpoints IS
    'Mid-task checkpoints captured BEFORE watchdog /clear, replayed into the '
    'REVIVED message on the same cycle. gate_roadmap 952c8d0d / '
    'continuous_operation_hooks resume-without-redo mechanism.';

-- Open-checkpoint lookup: covers fetch_open_checkpoint() with a single index seek.
CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_open
    ON public.agent_checkpoints (callsign, captured_at DESC)
 WHERE consumed_at IS NULL;
