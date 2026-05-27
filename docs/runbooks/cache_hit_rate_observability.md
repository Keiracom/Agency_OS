# Cache Hit-Rate Observability — Runbook

**Filed under:** Agency_OS-if0r (P0)
**Anchor:** Cat 21 lever 15 RATIFIED-CEO LAUNCH-BLOCKER 9
**Owner:** scout (author), Elliot (orchestrator merge)

## What this is

End-to-end pipeline for observing Anthropic prompt-cache effectiveness per spawn per worker per day:

1. **Ingest** — `scripts/cache_hit_rate_ingest.py` scans Claude session JSONL files + upserts per-day per-callsign token aggregates into Supabase `public.keiracom_cache_hit_rates_daily`.
2. **View** — `public.keiracom_cache_hit_rates_v1` computes `hit_rate_percent = cache_read / (cache_read + input_tokens) * 100` at query time + a `below_threshold_80` flag.
3. **Alert** — `scripts/cache_hit_rate_alert.py` queries the view + writes structured JSONL alert lines for any (date, callsign) row below 80%.
4. **CEO rollup integration** — the JSONL log at `/home/elliotbot/clawd/logs/cache-hit-rate-daily.jsonl` is the read source for the (not-yet-existing) `agency_cost_rollup.py` daily CEO post.

## Hit-rate definition

```
hit_rate_percent = cache_read_input_tokens / (cache_read_input_tokens + input_tokens) * 100
```

Excludes `cache_creation_input_tokens` (the first-write cost; paid once per cache block). 95% target tracks the bounded-spawn baseline anchored at Atlas 0.79 AUD per Cat 21 lever 15. 80% is the alert floor — anything below indicates the cache is doing less work than expected (most likely identity/system-prompt churn between spawns invalidating cache blocks).

## Files in this PR

| Path | Purpose | LoC |
|---|---|---:|
| `supabase/migrations/20260527_keiracom_cache_hit_rates.sql` | Table + view + trigger + indexes | ~115 |
| `scripts/cache_hit_rate_ingest.py` | JSONL scanner + Supabase upsert | ~240 |
| `scripts/cache_hit_rate_alert.py` | View reader + threshold alert writer | ~160 |
| `systemd/cache_hit_rate_ingest.service` + `.timer` | Daily ingest at 13:50 UTC | ~30 |
| `systemd/cache_hit_rate_alert.service` + `.timer` | Daily alert at 13:53 UTC | ~30 |
| `tests/scripts/test_cache_hit_rate_ingest.py` | 16 unit tests | ~250 |
| `tests/scripts/test_cache_hit_rate_alert.py` | 7 unit tests | ~145 |
| `docs/runbooks/cache_hit_rate_observability.md` | This runbook | ~100 |

**Verification:** 23/23 unit tests pass; `ruff check` + `ruff format --check` both clean.

## Run manually

```bash
# Aggregate last 7 days + show per-day per-callsign hit rates (no DB write)
python3 scripts/cache_hit_rate_ingest.py --days 7 --dry-run

# Ingest last 30 days into Supabase (requires DATABASE_URL or SUPABASE_DB_URL)
python3 scripts/cache_hit_rate_ingest.py --days 30

# Skip Supabase; write to JSONL log only
python3 scripts/cache_hit_rate_ingest.py --json-only

# Query the view for breaches in the last 1 day (default threshold 80%)
python3 scripts/cache_hit_rate_alert.py

# Tighter floor — alert on anything below 95%
python3 scripts/cache_hit_rate_alert.py --threshold 95 --days 7

# Dry-run (query + print only; no JSONL append)
python3 scripts/cache_hit_rate_alert.py --dry-run
```

## Install systemd units

```bash
cp systemd/cache_hit_rate_ingest.service systemd/cache_hit_rate_ingest.timer \
   systemd/cache_hit_rate_alert.service systemd/cache_hit_rate_alert.timer \
   ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now cache_hit_rate_ingest.timer
systemctl --user enable --now cache_hit_rate_alert.timer

# Verify
systemctl --user list-timers | grep cache_hit_rate
# Expect both timers Active + next-fire stamp matches the OnCalendar lines
```

Timing rationale:
- 13:50 UTC ingest (23:50 AEST) — captures the full day before the CEO rollup.
- 13:53 UTC alert (23:53 AEST) — three minutes after ingest, two minutes before the existing 23:55 daily CEO post window.

## Read the data

```sql
-- Last 7 days, all callsigns
SELECT rollup_date, callsign, spawn_count, hit_rate_percent,
       cache_read_tokens, input_tokens, below_threshold_80
FROM public.keiracom_cache_hit_rates_v1
WHERE rollup_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY rollup_date DESC, callsign;

-- Today's breaches only
SELECT * FROM public.keiracom_cache_hit_rates_v1
WHERE rollup_date = CURRENT_DATE
  AND below_threshold_80 = TRUE;
```

## CEO rollup integration

The dispatch calls for hooking into `agency_cost_rollup.py` daily CEO post. **That script does not yet exist in this repo** (only `openai_cost_rollup.py`). This PR delivers the data path; the integration hook is a one-liner to add once `agency_cost_rollup.py` ships:

```python
# Inside agency_cost_rollup.main():
from pathlib import Path
import json

cache_log = Path("/home/elliotbot/clawd/logs/cache-hit-rate-daily.jsonl")
todays_rows = [
    json.loads(line) for line in cache_log.read_text().splitlines()
    if line and json.loads(line)["rollup_date"] == today_iso
]
# Compute average hit rate + breach count for the daily summary line.
```

**Filed as follow-up KEI candidate** since the hook target doesn't exist.

## Alert escalation path

The alert script writes structured JSONL lines to `/home/elliotbot/clawd/logs/cache-hit-rate-alerts.jsonl`:

```json
{"fired_at":"2026-05-27T13:53:01Z","severity":"warning","kei":"Agency_OS-if0r",
 "title":"cache hit-rate below 80% for atlas on 2026-05-27",
 "rollup_date":"2026-05-27","callsign":"atlas","hit_rate_percent":75.42,
 "threshold_percent":80.0,"spawn_count":4,"cache_read_tokens":1234567,
 "cache_creation_tokens":50000,"input_tokens":402345,"output_tokens":12345,
 "assistant_message_count":42}
```

`tg`-shim Slack escalation OR BetterStack dashboard wiring is a follow-up. The JSONL-log is the V1 escape hatch per the dispatch's "BetterStack dashboard or simple JSONL alerts" wording — minimal V1 that the CEO rollup can read.

## Diagnostic — when hit rate drops

If the alert fires, the most-likely causes (ranked by frequency in this codebase):

1. **Identity/system-prompt churn between spawns.** A worker whose system prompt changes per spawn invalidates the cache block. Fix: stable identity template + memory externalised (the AGENT-SIDE gate items).
2. **TTL expiry mid-burst.** 5-minute TTL (per the INFRASTRUCTURE-SIDE gate) means a sparse spawn pattern can lose the cache between calls. Fix: tighter spawn cadence OR longer cache TTL (the latter requires Anthropic API config change).
3. **New large prompt prefix on first message.** Cache writes are necessary first-spawn cost. If `cache_creation_tokens` is the dominant contributor and `cache_read_tokens` is low for a worker, that worker is mostly cold-starting.

Use the view's `hit_rate_total_input_percent` column (includes creation tokens in denominator) to distinguish cause 2 from cause 3.

## Closes Agency_OS-if0r

Cutover Readiness Gate COST-TELEMETRY item: "per-spawn token logging + per-task-type attribution + daily ceo rollup + real-time dashboard + budget ceiling firing". This PR delivers per-spawn logging (via session JSONL), per-callsign daily aggregation, threshold firing. CEO rollup integration documented for the follow-up KEI.
