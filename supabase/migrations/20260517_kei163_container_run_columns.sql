-- KEI-163: container lifecycle monitor — final state columns on public.tasks
-- Apply before exercising the column-persist path in any environment.
ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS container_exit_code INT,
  ADD COLUMN IF NOT EXISTS container_ended_at  TIMESTAMPTZ;

COMMENT ON COLUMN public.tasks.container_exit_code IS
  'KEI-163: final exit code from the dispatcher-spawned container. NULL while still running or never spawned.';
COMMENT ON COLUMN public.tasks.container_ended_at IS
  'KEI-163: timestamp the container exit was observed by the monitor. NULL while running.';
