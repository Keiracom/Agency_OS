-- Agency_OS-avii: crash-recovery columns for public.tasks
-- retry_count tracks how many times the work-loop reconcile re-queued this
-- task after a lease expiry (crashed agent); dead_lettered_at is set when
-- retry_count >= 3 and the task is moved to the Valkey dead-letter queue.

ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS retry_count      INT         NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS dead_lettered_at TIMESTAMPTZ;

COMMENT ON COLUMN public.tasks.retry_count IS
    'Crash-recovery retry count (incremented by work-loop reconcile on lease expiry). Capped at 3.';
COMMENT ON COLUMN public.tasks.dead_lettered_at IS
    'Set when retry_count >= 3 and task is moved to dead-letter queue.';
