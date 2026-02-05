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

## Purpose (CEO Summary)

This is Elliot's "control panel" for Agency OS — the SaaS product that is Keiracom's primary revenue vehicle. It provides quick health checks and management operations without diving into the codebase.

**What it controls:**
- **Backend:** FastAPI on Railway (Python orchestration, 15+ API integrations)
- **Frontend:** Next.js on Vercel (React dashboard)
- **Database:** Supabase Postgres (leads, campaigns, clients)
- **Orchestration:** Prefect (background workflows)

**Why it exists:** Dave needs visibility into product health without running git commands or SSH'ing into servers. This tool bridges that gap.

---

## Keiracom Core Logic Integration

### How This Tool Fits Into Agency OS Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AGENCY OS STACK                         │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Vercel)  ←→  Backend (Railway)  ←→  DB (Supabase)│
│         ↑                      ↑                    ↑       │
│         │                      │                    │       │
│    ui-check              status/test          audit-schema  │
│         │                      │                    │       │
└─────────┴──────────────────────┴────────────────────┴───────┘
                    agency-product-tool
```

### Action → System Mapping

| Action | Checks | Business Impact |
|--------|--------|-----------------|
| `status` | Git state, deploy health | "Is production current?" |
| `prs` | Open pull requests | "What's waiting for Dave's review?" |
| `test` | Backend test suite | "Will this break production?" |
| `audit-env` | Environment variables | "Are all API keys configured?" |
| `audit-schema` | Database tables | "Is the schema up to date?" |
| `ui-check` | Frontend components | "Are all UI files present?" |

---

## Cost Structure ($AUD)

**This tool itself is FREE** — it only reads local/remote state.

**Infrastructure costs it monitors:**

| Service | Monthly Cost (AUD) | Notes |
|---------|-------------------|-------|
| Railway (Backend) | ~$31/mo | Starter plan, scales with usage |
| Vercel (Frontend) | ~$31/mo | Pro plan for preview deploys |
| Supabase (DB) | ~$39/mo | Pro plan, 8GB storage |
| Prefect (Orchestration) | Self-hosted | Runs on Railway |

**Total monitored infrastructure:** ~$101 AUD/month base

---

## Usage

```bash
python3 tools/agency_master.py <action>
```

## Actions & Examples

**Conceptual Summary:** Each action queries either local git state, GitHub API, or our deployed services to return health status.

### Check Deployment Status
```bash
# Shows: current branch, commit, deploy state
# Cost: Free (reads git)
python3 tools/agency_master.py status
```

### List Open PRs
```bash
# Shows: PRs awaiting Dave's review
# Cost: Free (GitHub API)
python3 tools/agency_master.py prs
```

### Run Tests
```bash
# Runs: pytest on backend
# Cost: Free (local execution)
python3 tools/agency_master.py test
```

### Audit Environment
```bash
# Shows: which API keys are configured vs missing
# Cost: Free (reads .env)
python3 tools/agency_master.py audit-env
```

### Audit Schema
```bash
# Shows: Supabase table list
# Cost: Free (Supabase API)
python3 tools/agency_master.py audit-schema
```

### Check UI Components
```bash
# Shows: frontend file inventory
# Cost: Free (reads filesystem)
python3 tools/agency_master.py ui-check
```

---

## Governance Compliance

- **LAW I:** Read this file before first use each session
- **LAW II:** Infrastructure costs noted in $AUD
- **LAW III:** No cost-incurring actions (read-only tool)
- **LAW IV:** Full conceptual summaries with architecture diagram

---

## Replaces

- agency-os (archived)
- agency-os-ui (archived)
- Manual git/railway/vercel CLI commands
