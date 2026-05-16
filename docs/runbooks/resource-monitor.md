# Resource governance — Weaviate cgroup cap + RAM monitoring (KEI-56)

**Linear:** [KEI-56](https://linear.app/keiracom/issue/KEI-56) · **Author:** Atlas · **Driver:** Dave verbatim — "we crashed the server once already from an uncapped process. we must not repeat this."

Three layers of defence against host OOM:

1. **Hard cgroup caps** — Weaviate (2.5G via KEI-48 `weaviate_capped.sh`), Cognee (3G via KEI-44 `cognee_capped.sh`), agent sessions (per `*-agent.service` from KEI-43).
2. **Continuous monitor** — `resource-monitor.service` writes a snapshot every 60s to `public.audit_logs.resource_snapshot` and alerts `#ceo` when any cgroup ≥ 90% of its cap.
3. **Pre-deployment check** — `preflight_resources.py` blocks a new service from starting when `MemAvailable < 2GB`.

## resource_snapshot JSON schema

`public.audit_logs.resource_snapshot` JSONB blob, one row per cycle:

```json
{
  "total_mb": 7935,
  "used_mb": 5239,
  "free_mb": 2696,
  "load_avg": [0.5, 1.0, 1.5],
  "disk_used_pct": 39,
  "cgroups": {
    "weaviate-922166.scope": {"memory_mb": 45, "memory_max_mb": 2560, "pct_of_cap": 1.8},
    "cognee.service":         {"memory_mb": 412, "memory_max_mb": 3072, "pct_of_cap": 13.4}
  },
  "thresholds_breached": [
    {"unit": "cognee.service", "pct": 91.1, "memory_mb": 2799}
  ],
  "captured_at": "2026-05-14T08:19:30.943+00:00"
}
```

`thresholds_breached` is populated when any cgroup ≥ `RESOURCE_MONITOR_WARN_PCT` (default 90%). Each breach triggers one `#ceo` post per onset (deduped while the breach persists; cleared once the cgroup drops back under threshold).

## Install (one-time, post-merge)

```bash
# 1. Migration (already-applied to live Supabase at install time; idempotent).
psql "$DATABASE_URL_MIGRATIONS" < /home/elliotbot/clawd/Agency_OS/supabase/migrations/20260514_audit_logs_resource_snapshot.sql

# 2. Install monitor systemd unit.
install -D -m 0644 \
    /home/elliotbot/clawd/Agency_OS/infra/systemd/agents/resource-monitor.service \
    /home/elliotbot/.config/systemd/user/resource-monitor.service
mkdir -p /home/elliotbot/clawd/logs
systemctl --user daemon-reload
systemctl --user enable --now resource-monitor.service
systemctl --user status resource-monitor.service   # confirm Active=running

# 3. Smoke (one cycle, prints + writes one row).
python3 /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/resource_monitor.py --once
```

## Preflight check (use before starting any new resource-intensive service)

```bash
# Defaults: 2 GB headroom required. Exit 0 = OK to start. Exit 1 = blocked.
python3 /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/preflight_resources.py \
    --headroom-mb 2048 \
    --service weaviate
echo "exit=$?"
```

Wire as systemd `ExecStartPre=` to block service start when host is under pressure:

```ini
[Service]
ExecStartPre=/home/elliotbot/clawd/venv/bin/python3 /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/preflight_resources.py --headroom-mb 2048 --service weaviate
ExecStart=...
```

## Tuning env vars

| Env | Default | Purpose |
|---|---|---|
| `RESOURCE_MONITOR_INTERVAL_SECONDS` | `60` | Snapshot cadence |
| `RESOURCE_MONITOR_WARN_PCT` | `90` | Cgroup breach threshold |
| `RESOURCE_MONITOR_DISK_PATH` | `/home/elliotbot/clawd` | Disk-usage probe path |
| `RESOURCE_MONITOR_CGROUP_ROOT` | `/sys/fs/cgroup/user.slice` | Root of cgroup walk |

## Verification snapshot (install-time, 2026-05-14)

```
$ python3 scripts/orchestrator/resource_monitor.py --once
2026-05-14 08:20:25,352 INFO: resource_monitor starting (interval=60s, warn_pct=90%, disk=/home/elliotbot/clawd, once=True)
(silent — no breaches, snapshot written)

$ psql -c "SELECT action, resource_snapshot->>'total_mb', resource_snapshot->>'used_mb', resource_snapshot->>'free_mb' FROM public.audit_logs WHERE action='resource_snapshot' ORDER BY created_at DESC LIMIT 1"
action=resource_snapshot total_mb=7935 used_mb=5239 free_mb=2696

$ python3 scripts/orchestrator/preflight_resources.py --service weaviate
2026-05-14 08:19:31,086 INFO: preflight OK: weaviate — available=2796MB >= required=2048MB
```

## Related

- KEI-43 — agent auto-start systemd services (merged `afdb692a`). Each agent has its own cgroup; the monitor picks them up automatically.
- KEI-44 — Cognee 3 GB memory cap (merged `3b133132`). Same `*_capped.sh` pattern as Weaviate; the monitor reads `/sys/fs/cgroup/user.slice/.../memory.{current,max}` for both.
- KEI-48 — Weaviate install (merged `a97ebebb`). Weaviate runs under `MemoryMax=2.5G` via `weaviate_capped.sh`.
- Spec source: Linear KEI-56 description (3 fix parts: cgroup cap, continuous monitoring, pre-deployment check).
