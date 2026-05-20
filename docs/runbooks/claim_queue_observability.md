# Claim-Queue Observability — KEI-136

Better Stack heartbeat-based alerting on claim-queue stalls.

## What this delivers

- `public.claim_queue_metrics_v` — read-only single-row aggregate over `public.tasks`.
- `scripts/orchestrator/claim_queue_metrics_export.py` — runs every 60s, pings BS heartbeat when healthy, **skips** ping when stalled.
- Better Stack alerts via existing severity-routing wired by KEI-20 (Orion). Missed heartbeats fire to `#ceo` via the critical policy.

## Why heartbeat-skip is the alert mechanism

Heartbeat creation in Better Stack is one-time operator-gated (BS Slack OAuth not API-creatable per the existing pattern in `scripts/orchestrator/betterstack_setup.py` docstring). Once the heartbeat exists with `period=60s, grace=240s` (5min total tolerance), the exporter's contract is simple: **ping when healthy, silence when stalled**. BS does the alerting.

This inverts the usual "fire alert from app" pattern — but matches the existing KEI-20 wiring, doesn't require BS API monitor creation, and the absence-of-signal semantics make it survive process restarts gracefully.

## Stall criteria

Implemented in `is_stalled()`:

1. **Available aging past SLA:** `available_count > 0` AND `oldest_available_age_sec > STALL_THRESHOLD_SEC` (default 300). Work waiting unclaimed for >5min.
2. **Active task idle past SLA:** `max_idle_seconds NOT NULL` AND `max_idle_seconds > STALL_THRESHOLD_SEC`. Some active row hasn't heartbeated in >5min.

NULL `max_idle_seconds` is **fail-open** — not treated as stall — because `tasks.heartbeat_at` is currently unpopulated in production. Turning NULL into an alert would page on baseline state.

## One-time Better Stack setup (operator)

1. **Create the heartbeat in BS dashboard** (API not available for OAuth-linked teams):
   - Name: `claim-queue-stall`
   - Period: `60 seconds`
   - Grace: `240 seconds`
   - Group: `Keiracom Agent Team`
   - Severity policy: critical (routes to `#ceo`) — same `policy_id` as `elliot-polling-loop`.

2. **Copy the heartbeat URL** from BS (format: `https://uptime.betterstack.com/api/v1/heartbeat/<TOKEN>`).

3. **Append to env:**
   ```bash
   echo "CLAIM_QUEUE_HEARTBEAT_URL=https://uptime.betterstack.com/api/v1/heartbeat/<TOKEN>" \
     >> ~/.config/agency-os/.env
   ```

4. **Install the timer:**
   ```bash
   bash scripts/install_claim_queue_metrics.sh
   ```

5. **Verify ping in BS dashboard:** within 60-90s the heartbeat should show "received" with no missed pings.

## Manual metric query

```sql
SELECT * FROM public.claim_queue_metrics_v;
```

Sample healthy:
```
 available_count | active_count | blocked_count | oldest_available_age_sec | oldest_active_age_sec | max_idle_seconds | computed_at
-----------------+--------------+---------------+--------------------------+-----------------------+------------------+-----------------------------
               0 |            2 |             1 |                          |                   300 |                  | 2026-05-18 22:37:58.112607+00
```

Sample stalled (alert pending):
```
 available_count | active_count | blocked_count | oldest_available_age_sec | oldest_active_age_sec | max_idle_seconds | computed_at
-----------------+--------------+---------------+--------------------------+-----------------------+------------------+-----------------------------
               5 |            1 |             0 |                      600 |                   120 |                  | 2026-05-18 22:37:58.112607+00
```

## Alert response — when BS pages #ceo on missed heartbeat

1. **Query the view manually** to confirm stall vs exporter failure:
   ```bash
   psql "$DATABASE_URL" -c "SELECT * FROM public.claim_queue_metrics_v;"
   ```

2. **Check exporter logs:**
   ```bash
   journalctl --user -u claim_queue_metrics.service -n 50 --no-pager
   ```

3. **Identify root cause:**
   - `available_count > 0 AND oldest_available_age_sec > 300` → no agent claiming. Check `fleet_supervisor` is running + agents alive.
   - `max_idle_seconds > 300` → an active task has stalled. Check `journalctl --user -u <agent>` for the claimed agent.
   - Exporter log says `fetch_metrics failed` → DB unreachable. Check Supabase pooler.
   - Exporter log says `CLAIM_QUEUE_HEARTBEAT_URL unset` → operator step 3 missed.

## Reverting

Disable the timer; the BS heartbeat then fires (intended — false alert until heartbeat is deleted in BS dashboard):

```bash
systemctl --user disable --now claim_queue_metrics.timer
```

To silence without uninstalling, unset the env var and restart the timer:

```bash
sed -i '/^CLAIM_QUEUE_HEARTBEAT_URL=/d' ~/.config/agency-os/.env
systemctl --user restart claim_queue_metrics.timer
```

The exporter exits clean when the URL is unset.

## References

- `supabase/migrations/20260518_kei136_claim_queue_metrics_view.sql` — view definition.
- `scripts/orchestrator/claim_queue_metrics_export.py` — exporter logic.
- `systemd/claim_queue_metrics.service` + `.timer` — 60s cadence.
- `scripts/install_claim_queue_metrics.sh` — installer.
- `tests/scripts/test_claim_queue_metrics_export.py` — 13 tests covering stall criteria + fail-open paths.
- KEI-20 (Orion) — Better Stack severity-routing wiring this depends on.
- KEI-136 Linear: <https://linear.app/keiracom/issue/KEI-136>
