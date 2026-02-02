---
name: agency-product-tool
description: Agency OS product management - deployment status, PR management, testing, environment audits, UI component checks.
metadata:
  clawdbot:
    emoji: "🏢"
schema:
  type: object
  required: ["action"]
  properties:
    action:
      type: string
      enum: ["status", "prs", "test", "audit-env", "audit-schema", "ui-check"]
---

# Agency Product Tool 🏢

Agency OS product management.

## Usage

```bash
python3 tools/agency_master.py <action>
```

## Actions

| Action | Description |
|--------|-------------|
| `status` | Check deploy status (git state) |
| `prs` | List open pull requests |
| `test` | Run test suite |
| `audit-env` | Audit environment variables |
| `audit-schema` | List database tables |
| `ui-check` | Check UI component files |

## Examples

```bash
# Check deployment status
python3 tools/agency_master.py status

# List open PRs
python3 tools/agency_master.py prs

# Audit environment
python3 tools/agency_master.py audit-env
```

## Replaces

- agency-os, agency-os-ui
