---
name: prefect
description: Use when managing scheduled workflows or background jobs. Check flow runs, trigger deployments, monitor pipeline health. Triggers on "flow run", "prefect", "workflow", "scheduled job", "pipeline status", "cron job".
metadata: {"clawdbot":{"emoji":"🔷","always":true,"requires":{"bins":["curl","jq"],"env":["PREFECT_API_URL"]}}}
---

# Prefect 🔷

Prefect workflow orchestration management.

## Setup

```bash
export PREFECT_API_URL="https://prefect-server-production-f9b1.up.railway.app/api"
```

## Health Check

```bash
curl -s "$PREFECT_API_URL/health"
# Returns: true
```

## Usage Examples

```
"List all flows"
"Show recent flow runs"
"Check failed runs"
"Trigger deployment data-pipeline/daily"
"Cancel flow run abc-123"
```

---

## API Reference

Base URL: `$PREFECT_API_URL` (our server: `https://prefect-server-production-f9b1.up.railway.app/api`)

### Flows

**List/Filter Flows**
```bash
curl -s -X POST "$PREFECT_API_URL/flows/filter" \
  -H "Content-Type: application/json" \
  -d '{"limit": 20}' | jq
```

**Get Flow by ID**
```bash
curl -s "$PREFECT_API_URL/flows/{flow_id}" | jq
```

**Get Flow by Name**
```bash
curl -s -X POST "$PREFECT_API_URL/flows/name/{flow_name}" | jq
```

### Flow Runs

**List/Filter Flow Runs**
```bash
# Recent runs
curl -s -X POST "$PREFECT_API_URL/flow_runs/filter" \
  -H "Content-Type: application/json" \
  -d '{"limit": 20, "sort": "START_TIME_DESC"}' | jq

# Failed runs only
curl -s -X POST "$PREFECT_API_URL/flow_runs/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_runs": {
      "state": {"type": {"any_": ["FAILED", "CRASHED"]}}
    },
    "limit": 10,
    "sort": "START_TIME_DESC"
  }' | jq
```

**Get Flow Run by ID**
```bash
curl -s "$PREFECT_API_URL/flow_runs/{flow_run_id}" | jq
```

**Create Flow Run (manual trigger)**
```bash
curl -s -X POST "$PREFECT_API_URL/flow_runs" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_id": "uuid-here",
    "name": "my-manual-run",
    "parameters": {}
  }' | jq
```

**Cancel Flow Run**
```bash
curl -s -X POST "$PREFECT_API_URL/flow_runs/{flow_run_id}/set_state" \
  -H "Content-Type: application/json" \
  -d '{
    "state": {"type": "CANCELLED", "name": "Cancelled"}
  }' | jq
```

### Deployments

**List/Filter Deployments**
```bash
curl -s -X POST "$PREFECT_API_URL/deployments/filter" \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}' | jq
```

**Get Deployment by ID**
```bash
curl -s "$PREFECT_API_URL/deployments/{deployment_id}" | jq
```

**Get Deployment by Name**
```bash
curl -s "$PREFECT_API_URL/deployments/name/{flow_name}/{deployment_name}" | jq
```

**Trigger Deployment Run**
```bash
curl -s -X POST "$PREFECT_API_URL/deployments/{deployment_id}/create_flow_run" \
  -H "Content-Type: application/json" \
  -d '{}' | jq

# With parameters
curl -s -X POST "$PREFECT_API_URL/deployments/{deployment_id}/create_flow_run" \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {"key": "value"},
    "tags": ["manual"]
  }' | jq
```

**Pause/Resume Deployment**
```bash
# Pause
curl -s -X PATCH "$PREFECT_API_URL/deployments/{deployment_id}" \
  -H "Content-Type: application/json" \
  -d '{"paused": true}' | jq

# Resume
curl -s -X PATCH "$PREFECT_API_URL/deployments/{deployment_id}" \
  -H "Content-Type: application/json" \
  -d '{"paused": false}' | jq
```

### Logs

**Get Flow Run Logs**
```bash
curl -s -X POST "$PREFECT_API_URL/logs/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": {
      "flow_run_id": {"any_": ["{flow_run_id}"]}
    },
    "limit": 100,
    "sort": "TIMESTAMP_ASC"
  }' | jq
```

### Work Pools

**List Work Pools**
```bash
curl -s -X POST "$PREFECT_API_URL/work_pools/filter" \
  -H "Content-Type: application/json" \
  -d '{}' | jq
```

**Get Work Pool Status**
```bash
curl -s "$PREFECT_API_URL/work_pools/{work_pool_name}" | jq
```

---

## Filter Operators

Use in POST filter requests:

| Operator | Description | Example |
|----------|-------------|---------|
| `any_` | Match any value | `{"any_": ["FAILED", "CRASHED"]}` |
| `all_` | Match all values | `{"all_": ["tag1", "tag2"]}` |
| `is_null_` | Null check | `{"is_null_": false}` |
| `eq_` | Equals | `{"eq_": "value"}` |
| `before_` | DateTime before | `{"before_": "2024-01-01T00:00:00Z"}` |
| `after_` | DateTime after | `{"after_": "2024-01-01T00:00:00Z"}` |

---

## State Types

| State | Meaning |
|-------|---------|
| `SCHEDULED` | Queued for future |
| `PENDING` | Ready to run |
| `RUNNING` | Currently executing |
| `COMPLETED` | Finished successfully |
| `FAILED` | Error occurred |
| `CANCELLED` | Manually stopped |
| `CRASHED` | Infrastructure failure |
| `PAUSED` | Waiting for input |
| `CANCELLING` | Stop in progress |

---

## CLI Commands

```bash
# Configure CLI
export PREFECT_API_URL="https://prefect-server-production-f9b1.up.railway.app/api"

# Flows
prefect flow ls

# Flow Runs
prefect flow-run ls
prefect flow-run inspect {id}
prefect flow-run cancel {id}

# Deployments
prefect deployment ls
prefect deployment inspect 'flow-name/deployment-name'
prefect deployment run 'flow-name/deployment-name'
prefect deployment run 'flow-name/deployment-name' --param key=value
prefect deployment pause 'flow-name/deployment-name'
prefect deployment resume 'flow-name/deployment-name'

# Work Pools
prefect work-pool ls
prefect work-pool inspect {name}
```

---

## Common Queries

**Dashboard URL**
```
https://prefect-server-production-f9b1.up.railway.app
```

**Count runs by state**
```bash
curl -s -X POST "$PREFECT_API_URL/flow_runs/count" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_runs": {
      "state": {"type": {"any_": ["FAILED"]}}
    }
  }'
```

**Recent activity (last 24h)**
```bash
curl -s -X POST "$PREFECT_API_URL/flow_runs/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_runs": {
      "start_time": {"after_": "'$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)'"}
    },
    "limit": 50,
    "sort": "START_TIME_DESC"
  }' | jq '.[] | {name, state_type, start_time}'
```
