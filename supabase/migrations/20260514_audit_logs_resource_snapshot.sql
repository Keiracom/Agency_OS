-- KEI-56 — Resource governance.
-- Adds a resource_snapshot JSONB column to audit_logs so the resource monitor
-- (scripts/orchestrator/resource_monitor.py) can write a 60s rolling snapshot
-- of memory + cgroup + disk + load.
--
-- The column is nullable + no default, so this is an instant DDL on Postgres
-- (no table rewrite). All existing audit_logs rows keep NULL.
--
-- Schema reference (from resource_monitor.py write_snapshot):
--   {
--     "free_mb": int,                       -- MemAvailable from /proc/meminfo
--     "used_mb": int,                       -- MemTotal - MemAvailable
--     "total_mb": int,                      -- MemTotal
--     "load_avg": [1m, 5m, 15m],            -- /proc/loadavg
--     "disk_used_pct": int,                 -- df -h /home/elliotbot/clawd
--     "cgroups": {                          -- systemd-cgtop snapshot
--       "<unit_name>": {
--         "memory_mb": int,
--         "memory_max_mb": int | null,      -- null = no cap
--         "pct_of_cap": float | null
--       }
--     },
--     "thresholds_breached": [...]          -- callouts >=90% or capped
--   }

-- audit_action is an enum; add the new label so action='resource_snapshot' rows insert cleanly.
-- ALTER TYPE ... ADD VALUE IF NOT EXISTS is idempotent + non-transactional, safe to re-run.
ALTER TYPE public.audit_action ADD VALUE IF NOT EXISTS 'resource_snapshot';

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS resource_snapshot JSONB;

COMMENT ON COLUMN public.audit_logs.resource_snapshot IS
  'KEI-56 — Resource governance. 60s-rolling memory/cgroup/disk/load snapshot. '
  'Written by scripts/orchestrator/resource_monitor.py. Schema documented in '
  'docs/runbooks/resource-monitor.md.';
