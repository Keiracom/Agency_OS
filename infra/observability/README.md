# Phoenix Export Loop — systemd deploy

Runs `scripts/phoenix_export_loop.py` as a systemd user service. Polls
`public.governance_events` every 60s and ships new rows to the Phoenix
Auditor on Railway as OTLP spans.

## Install

```bash
mkdir -p ~/.config/systemd/user
cp infra/observability/agency-os-phoenix-export.service \
   ~/.config/systemd/user/agency-os-phoenix-export.service
mkdir -p /home/elliotbot/clawd/state
systemctl --user daemon-reload
systemctl --user enable --now agency-os-phoenix-export.service
```

## Verify

```bash
systemctl --user status agency-os-phoenix-export.service
journalctl --user -u agency-os-phoenix-export.service -n 30
cat /home/elliotbot/clawd/state/phoenix_watermark.txt
```

Expected log output (steady state):
```
[phoenix-export] INFO: Phoenix export loop started — interval=60s, batch_limit=500, watermark_path=/home/elliotbot/clawd/state/phoenix_watermark.txt
[phoenix-export] INFO: cycle: fetched=N exported=N watermark_advanced=2026-05-01T...
```

## Verify spans land in Phoenix

```bash
curl -s "https://auditor-phoenix-production.up.railway.app/v1/projects/UHJvamVjdDoy/spans" \
  | jq '.data | length'
```

Number should grow over time.

## Tunables (override in unit file or .env)

| Env | Default | Purpose |
|-----|---------|---------|
| `PHOENIX_OTLP_ENDPOINT` | (none, must be set) | Phoenix OTLP HTTP traces endpoint |
| `PHOENIX_PROJECT` | `agency-os-governance` | Phoenix project bucket for spans |
| `PHOENIX_EXPORT_INTERVAL_S` | `60` | Poll cadence |
| `PHOENIX_EXPORT_BATCH_LIMIT` | `500` | Max events per cycle |
| `PHOENIX_WATERMARK_PATH` | `/home/elliotbot/clawd/state/phoenix_watermark.txt` | State file location |

## Stop / disable

```bash
systemctl --user stop agency-os-phoenix-export.service
systemctl --user disable agency-os-phoenix-export.service
```

The watermark file persists — disabling + re-enabling resumes from the
last shipped event, no replay.
