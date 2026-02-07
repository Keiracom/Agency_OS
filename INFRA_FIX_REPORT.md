# Infrastructure Fix Report
**Generated:** 2026-02-06 ~02:00 UTC  
**Auditor:** FIXER-INFRA subagent

---

## 1. Railway Token Status

### Finding: ❌ EXPIRED/UNAUTHORIZED

**Current Token:** `b71c1fee-8...` (prefix)  
**Error:** `"Not Authorized"` when calling Railway GraphQL API

**Root Cause:** Railway API tokens expire after a period of inactivity or after token rotation.

### User Action Required:
1. Go to [Railway Dashboard](https://railway.app/account/tokens)
2. Create a new API token
3. Update `~/.config/agency-os/.env`:
   ```bash
   Railway_Token=<new_token_here>
   ```
4. Reload env: `source ~/.config/agency-os/.env`
5. Test: `node /home/elliotbot/clawd/skills/mcp-bridge/scripts/mcp-bridge.js call railway list_projects`

---

## 2. Prefect Work Pool Status

### Work Pools Summary

| Pool | Status | Last Polled | Issue |
|------|--------|-------------|-------|
| `agency-os-pool` | ✅ READY | 2026-02-06 01:47 UTC | Healthy |
| `local-pool` | ❌ NOT_READY | 2026-01-30 02:03 UTC | **Worker not running** |

### Finding: `local-pool` is OFFLINE

**Root Cause:** No Prefect worker process running on local machine.

Verified via:
- `ps aux | grep prefect` → No workers found
- `systemctl list-units | grep prefect` → No systemd services

### Fix Options:

**Option A: Start local worker manually**
```bash
cd /home/elliotbot/clawd/infrastructure/prefect_flows
source ~/.config/agency-os/.env
prefect worker start --pool local-pool
```

**Option B: Create systemd service for persistence**
```bash
sudo nano /etc/systemd/system/prefect-local-worker.service
```
```ini
[Unit]
Description=Prefect Local Pool Worker
After=network.target

[Service]
User=elliotbot
WorkingDirectory=/home/elliotbot/clawd/infrastructure/prefect_flows
EnvironmentFile=/home/elliotbot/.config/agency-os/.env
ExecStart=/usr/local/bin/prefect worker start --pool local-pool
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable prefect-local-worker
sudo systemctl start prefect-local-worker
```

**Option C: Migrate to Railway-hosted pool**
Move `daily-learning-scrape` from `local-pool` to `agency-os-pool` (runs on Railway).

---

## 3. Crashed/Stuck Flows

### Finding: daily-learning-scrape is STUCK (not crashed)

**Deployment ID:** `85749b11-866f-4663-8856-c8a5ecff15e6`  
**Status:** `NOT_READY`  
**Work Pool:** `local-pool` (offline)  
**Schedule:** `0 19 * * *` UTC (7 PM daily)

**Symptom:** 10+ runs sitting in `SCHEDULED` state, never executed.

| Run Name | State | Start Time |
|----------|-------|------------|
| vivid-python | SCHEDULED | null |
| qualified-junglefowl | SCHEDULED | null |
| ultramarine-penguin | SCHEDULED | null |
| (+ 7 more...) | SCHEDULED | null |

**Root Cause:** No worker is polling `local-pool`. Runs queue up indefinitely.

### Fix:
Start the local worker (see Section 2) OR reassign deployment to `agency-os-pool`:
```bash
prefect deployment set-work-pool daily-learning-scrape/daily-learning-scrape --work-pool agency-os-pool
```

---

## 4. Paused Deployments

### Summary: 10 of 24 deployments are PAUSED

| Deployment | Purpose | Schedule | Why Paused |
|------------|---------|----------|------------|
| `persona-buffer-flow` | Replenish persona buffer | Webhook-triggered | Pre-launch: no production traffic |
| `warmup-monitor-flow` | Check WarmForge warmups | 6 AM AEST daily | Pre-launch: no domains warming |
| `crm-sync-flow` | CRM safety net | Every 6 hours | Pre-launch: no active CRM sync |
| `pattern-learning-flow` | Weekly pattern learning | 3 AM Sun AEST | Pre-launch: insufficient data |
| `pool-daily-allocation-flow` | Daily lead allocation | 6 AM AEST daily | Pre-launch: no active campaigns |
| `reply-recovery-flow` | Reply safety net | Every 6 hours | Pre-launch: no outreach running |
| `outreach-flow` | Hourly outreach | 8-18 Mon-Fri AEST | Pre-launch: no active campaigns |
| `enrichment-flow` | Daily enrichment | 2 AM AEST daily | Pre-launch: no leads queued |
| `credit-reset-flow` | Hourly credit check | Every hour | Schedule inactive (but flow active) |
| N/A | N/A | N/A | N/A |

**Interpretation:** These are intentionally paused for pre-launch phase. They will be activated when:
1. First paying client onboards
2. WarmForge domains complete warmup
3. Production campaigns go live

---

## 5. Immediate Action Items

### Critical (blocking operations):
1. ⚠️ **Refresh Railway token** - Required for deployment management
2. ⚠️ **Start local Prefect worker** - Required for daily-learning-scrape

### Optional (cleanup):
3. Consider migrating `daily-learning-scrape` to `agency-os-pool` for Railway hosting
4. Cancel the 10+ stuck SCHEDULED runs if stale:
   ```bash
   # Via MCP or API
   prefect flow-run cancel <run_id>
   ```

---

## 6. Health Check Commands

```bash
# Railway (after token refresh)
node /home/elliotbot/clawd/skills/mcp-bridge/scripts/mcp-bridge.js call railway list_projects

# Prefect server
curl $PREFECT_API_URL/health

# Prefect work pools
curl -X POST "$PREFECT_API_URL/work_pools/filter" -H "Content-Type: application/json" -d '{}' | jq '.[].name, .[].status'

# Local worker
ps aux | grep "prefect worker"
```

---

*Report complete. Main agent should relay action items to Dave.*
