-- KEI-97 — Zombie task detection: agent process heartbeats.
--
-- A higher-cadence (30s) per-agent-process heartbeat layer that complements
-- KEI-105's per-task heartbeats. CEO fleet-check consults this to flag
-- zombies (tmux pane responsive but agent process dead and not pinging).

CREATE TABLE IF NOT EXISTS public.fleet_agents (
    callsign        text        PRIMARY KEY,
    last_heartbeat  timestamptz NOT NULL DEFAULT NOW()
);

-- Idempotent: ALTER ADD COLUMN keeps the migration safe if a stub table
-- pre-exists without the heartbeat column.
ALTER TABLE public.fleet_agents
    ADD COLUMN IF NOT EXISTS last_heartbeat timestamptz NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS fleet_agents_heartbeat_idx
    ON public.fleet_agents (last_heartbeat);

COMMENT ON TABLE  public.fleet_agents IS 'KEI-97 per-agent-process heartbeats (30s cadence). last_heartbeat older than 90s = dead.';
COMMENT ON COLUMN public.fleet_agents.last_heartbeat IS 'Updated by fleet-heartbeat@<callsign>.timer every 30s.';
