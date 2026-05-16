-- KEI-79 — bd escalate state machine + ceo_decisions table + trigger.
--
-- Locked from 3-way deliberation 2026-05-16T~12:30Z:
-- - Max state machine + Option D direct-post hybrid (chat_postMessage with
--   completion_sync_queue fallback)
-- - Aiden ceo_decisions table + 1-trigger cascade
-- - Elliot bd escalate CLI + Block Kit format + rate-limit + bd ceo-queue
--
-- bd escalate is agent-code (2-write txn: INSERT ceo_decisions; UPDATE tasks
-- SET status='escalated'). No trigger on tasks→ceo_decisions because the
-- trigger can't see agent context (description, options, escalated_by).
--
-- This trigger fires only on ceo_decisions UPDATE — cascades resolved
-- decisions back to tasks.status (active|cancelled).

CREATE TABLE IF NOT EXISTS public.ceo_decisions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id          TEXT NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    escalated_by     TEXT NOT NULL,
    requested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description      TEXT NOT NULL,
    options          TEXT[],
    status           TEXT NOT NULL DEFAULT 'awaiting'
                         CHECK (status IN ('awaiting','decided','rejected','timeout')),
    slack_ts         TEXT,
    slack_reply_ts   TEXT,
    decision_outcome TEXT,
    dave_choice      TEXT,
    resolved_by      TEXT,
    resolved_at      TIMESTAMPTZ,
    rate_limit_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    tenant_id        TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ceo_decisions_one_awaiting_per_task
    ON public.ceo_decisions (task_id) WHERE status = 'awaiting';

CREATE INDEX IF NOT EXISTS idx_ceo_decisions_awaiting_age
    ON public.ceo_decisions (requested_at) WHERE status = 'awaiting';

CREATE OR REPLACE FUNCTION public.trg_ceo_decisions_to_tasks()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        IF NEW.status = 'decided' THEN
            UPDATE public.tasks SET status = 'active', updated_at = NOW()
             WHERE id = NEW.task_id AND status = 'escalated';
        ELSIF NEW.status IN ('rejected', 'timeout') THEN
            UPDATE public.tasks SET status = 'cancelled', updated_at = NOW()
             WHERE id = NEW.task_id AND status = 'escalated';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_ceo_decisions_cascade ON public.ceo_decisions;
CREATE TRIGGER trg_ceo_decisions_cascade
    AFTER UPDATE OF status ON public.ceo_decisions
    FOR EACH ROW EXECUTE FUNCTION public.trg_ceo_decisions_to_tasks();

-- Extend KEI-74 completion_sync_queue target_sink to include 'ceo_post_retry'
-- per Max Option D direct-post fallback path.
ALTER TABLE public.completion_sync_queue
    DROP CONSTRAINT IF EXISTS completion_sync_queue_target_sink_check;
ALTER TABLE public.completion_sync_queue
    ADD CONSTRAINT completion_sync_queue_target_sink_check
    CHECK (target_sink IN ('linear', 'ceo_memory', 'drive_manual', 'ceo_post_retry'));

COMMENT ON TABLE public.ceo_decisions IS
    'KEI-79 — escalation ledger: bd escalate writes a row, central_listener parses Dave reply, trigger cascades status to tasks.';
