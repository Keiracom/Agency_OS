-- KEI-105: add heartbeat_at column to public.tasks
-- Agents write heartbeat_at = NOW() periodically while actively working a
-- claimed task. Distinguishes "actively working" from "claimed and abandoned"
-- — pairs with KEI-104 stale-claim auto-release (PR #947).
--
-- Nullable: legacy rows + tasks that have not yet received a heartbeat both
-- correctly report NULL. bd ready and KEI-104 release helpers can compare
-- COALESCE(heartbeat_at, claimed_at) to detect activity.

ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

COMMENT ON COLUMN public.tasks.heartbeat_at IS
  'KEI-105: timestamp of the most recent heartbeat from the claiming agent. NULL when no heartbeat received yet. Updated via bd heartbeat <id> --callsign <X>.';
