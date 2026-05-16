-- KEI-74 — Three-store completion sync: queue + triggers.
--
-- On any tasks.status change to ('done', 'cancelled') OR any new
-- task_verifications row, fan out 3 INSERTs into completion_sync_queue
-- (one per sink). A worker drains the queue and writes to Linear /
-- ceo_memory / Drive Manual with retry. Solves the never-built outbound
-- sync gap identified in KEI-70+Q1 deliberation 2026-05-16.

CREATE TABLE IF NOT EXISTS public.completion_sync_queue (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id        TEXT NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    target_sink    TEXT NOT NULL CHECK (target_sink IN ('linear', 'ceo_memory', 'drive_manual')),
    target_status  TEXT NOT NULL,
    attempts       INT NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    processed      BOOLEAN NOT NULL DEFAULT FALSE,
    error_message  TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unprocessed work index — worker SELECT path.
CREATE INDEX IF NOT EXISTS idx_completion_sync_queue_unprocessed
    ON public.completion_sync_queue (created_at)
    WHERE processed = FALSE;

-- Dedupe partial index — at most one unprocessed row per (task_id, target_sink).
-- Re-emits after success are allowed (new row); retries dedupe via this constraint.
CREATE UNIQUE INDEX IF NOT EXISTS uq_completion_sync_queue_pending
    ON public.completion_sync_queue (task_id, target_sink)
    WHERE processed = FALSE;

CREATE OR REPLACE FUNCTION public.fn_enqueue_completion_sync(p_task_id TEXT, p_status TEXT)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO public.completion_sync_queue (task_id, target_sink, target_status)
    SELECT p_task_id, sink, p_status
    FROM unnest(ARRAY['linear', 'ceo_memory', 'drive_manual']::text[]) AS sink
    ON CONFLICT (task_id, target_sink) WHERE processed = FALSE DO UPDATE SET updated_at = NOW();
END;
$$;

-- Trigger 1 — tasks.status change to a terminal state fans out 3 sink rows.
CREATE OR REPLACE FUNCTION public.trg_tasks_status_to_sync_queue()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IN ('done', 'cancelled') AND NEW.status IS DISTINCT FROM OLD.status THEN
        PERFORM public.fn_enqueue_completion_sync(NEW.id, NEW.status);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tasks_completion_sync ON public.tasks;
CREATE TRIGGER trg_tasks_completion_sync
    AFTER UPDATE OF status ON public.tasks
    FOR EACH ROW EXECUTE FUNCTION public.trg_tasks_status_to_sync_queue();

-- Trigger 2 — task_verifications INSERT belt+braces (catches verification-gated closures).
CREATE OR REPLACE FUNCTION public.trg_verifications_to_sync_queue()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_status TEXT;
BEGIN
    SELECT status INTO v_status FROM public.tasks WHERE id = NEW.task_id;
    IF v_status IN ('done', 'cancelled') THEN
        PERFORM public.fn_enqueue_completion_sync(NEW.task_id, v_status);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_verifications_completion_sync ON public.task_verifications;
CREATE TRIGGER trg_verifications_completion_sync
    AFTER INSERT ON public.task_verifications
    FOR EACH ROW EXECUTE FUNCTION public.trg_verifications_to_sync_queue();

COMMENT ON TABLE public.completion_sync_queue IS
    'KEI-74 three-store completion fan-out queue. One row per (task, sink) pending; '
    'worker drains via SELECT FOR UPDATE SKIP LOCKED. Auto-populated by triggers on '
    'tasks.status change + task_verifications INSERT.';
