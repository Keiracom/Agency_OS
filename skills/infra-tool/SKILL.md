---
name: infra-tool
description: Infrastructure management - Prefect workflows, Railway deployments. Check flow runs, trigger jobs, monitor services.
metadata:
  clawdbot:
    emoji: "🔧"
schema:
  type: object
  required: ["action", "target"]
  properties:
    action:
      type: string
      enum: ["health", "flows", "runs", "trigger", "projects", "deployments"]
    target:
      type: string
      enum: ["prefect", "railway"]
---

# Infrastructure Tool 🔧

Workflow and deployment management.

## Usage

```bash
python3 tools/infra_master.py <action> <target> [options]
```

## Examples

```bash
# Check Prefect health
python3 tools/infra_master.py health prefect

# List flow runs
python3 tools/infra_master.py runs prefect --limit 10

# List failed runs
python3 tools/infra_master.py runs prefect --state FAILED

# Railway projects
python3 tools/infra_master.py projects railway
```

## Replaces

- prefect, railway
