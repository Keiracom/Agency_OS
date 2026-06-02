-- Fleet liveness ground-truth — on-box checker writes per-agent status every
-- 5 minutes so the read-side fleet_check_query can score callsigns GREEN/RED.
--
-- Authored by SCOUT (dispatch from Elliot 2026-06-02). Sibling to
-- fleet_heartbeat_writer (per-process 30s self-ping) and tasks.heartbeat_at
-- (per-active-task 15min ping). This table is observability ground truth:
-- a checker outside each agent process probes tmux + NATS + backend + DB
-- and writes the result, so a wedged agent cannot fake liveness by
-- pinging itself.

CREATE TABLE IF NOT EXISTS public.fleet_liveness (
    callsign             TEXT        NOT NULL,
    checked_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tmux_alive           BOOLEAN     NOT NULL DEFAULT FALSE,
    nats_last_publish_at TIMESTAMPTZ,
    backend_health       TEXT,
    active_task_id       TEXT,
    PRIMARY KEY (callsign, checked_at)
);

CREATE INDEX IF NOT EXISTS fleet_liveness_callsign_checked_at_desc_idx
    ON public.fleet_liveness (callsign, checked_at DESC);

COMMENT ON TABLE public.fleet_liveness IS
    'Ground-truth per-agent liveness snapshot, written every 5 minutes by '
    'scripts/orchestrator/fleet_liveness_checker.py. Read by fleet_check_query '
    'to score callsigns GREEN/RED. Append-only — historical rows retained '
    'for drift analysis.';

COMMENT ON COLUMN public.fleet_liveness.tmux_alive IS
    'TRUE when "tmux has-session -t <callsign>" (or <callsign>bot fallback) '
    'returns 0. Outside-process check — wedged agents cannot fake this.';

COMMENT ON COLUMN public.fleet_liveness.nats_last_publish_at IS
    'Timestamp of the most recent message on keiracom.agent.status.<callsign>. '
    'NULL when stream is empty for that callsign or NATS is unreachable.';

COMMENT ON COLUMN public.fleet_liveness.backend_health IS
    'Trimmed response body from http://localhost:8000/health (max 256 chars). '
    'NULL on connection failure or non-2xx response.';

COMMENT ON COLUMN public.fleet_liveness.active_task_id IS
    'ID of the task currently claimed by this callsign with status=active, '
    'or NULL when the agent is idle.';

-- Seed nova into agent_profiles so personalised bd ready ordering works for
-- the worker tier. Per dispatch — nova was omitted from the original KEI-53
-- seed (which only covered the 6 callsigns alive at the time).
INSERT INTO public.agent_profiles
    (callsign, configured_model, context_tags)
VALUES
    ('nova', 'claude-sonnet-4-6', ARRAY['build', 'pr', 'python'])
ON CONFLICT (callsign) DO NOTHING;
