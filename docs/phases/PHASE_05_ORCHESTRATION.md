# Phase 5: Orchestration (Prefect)

**Status:** ✅ Complete  
**Tasks:** 12  
**Dependencies:** Phase 4 complete  
**Checkpoint:** CEO approval required

---

## Overview

Set up Prefect for workflow orchestration. This is the glue layer that coordinates all engines.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| ORC-001 | Worker entrypoint | Prefect agent service | `src/orchestration/worker.py` | M |
| ORC-002 | Campaign flow + test | Campaign activation | `src/orchestration/flows/campaign_flow.py`, `tests/test_flows/test_campaign_flow.py` | M |
| ORC-003 | Enrichment flow + test | Daily enrichment with billing check | `src/orchestration/flows/enrichment_flow.py`, `tests/test_flows/test_enrichment_flow.py` | L |
| ORC-004 | Outreach flow + test | Hourly outreach | `src/orchestration/flows/outreach_flow.py`, `tests/test_flows/test_outreach_flow.py` | L |
| ORC-005 | Reply recovery flow | Safety net (6-hourly) | `src/orchestration/flows/reply_recovery_flow.py` | M |
| ORC-006 | Enrichment tasks | Prefect tasks with JIT checks | `src/orchestration/tasks/enrichment_tasks.py` | M |
| ORC-007 | Scoring tasks | Prefect tasks | `src/orchestration/tasks/scoring_tasks.py` | M |
| ORC-008 | Outreach tasks | Prefect tasks with JIT checks | `src/orchestration/tasks/outreach_tasks.py` | M |
| ORC-009 | Reply tasks | Prefect tasks | `src/orchestration/tasks/reply_tasks.py` | M |
| ORC-010 | Scheduled jobs | Cron schedules | `src/orchestration/schedules/scheduled_jobs.py` | M |
| ORC-011 | Prefect config | Deployment config | `prefect.yaml` | S |
| ORC-012 | Prefect Dockerfile | Server container | `Dockerfile.prefect` | S |

---

## Layer Rules

Orchestration is **Layer 4 (Top)**:
- CAN import from everything below
- Coordinates engines, never imported by them

---

## Flow Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PREFECT SERVER                        │
│                   (Railway Service)                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    PREFECT AGENT                         │
│                   (Worker Service)                       │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Campaign    │  │ Enrichment  │  │ Outreach    │     │
│  │ Flow        │  │ Flow        │  │ Flow        │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ┌─────────────┐                                        │
│  │ Reply       │                                        │
│  │ Recovery    │                                        │
│  └─────────────┘                                        │
└─────────────────────────────────────────────────────────┘
```

---

## Flow Schedules

| Flow | Schedule | Purpose |
|------|----------|---------|
| Enrichment | Daily 2am | Enrich new leads |
| Outreach | Hourly | Send outreach messages |
| Reply Recovery | Every 6 hours | Safety net for missed webhooks |

---

## JIT Validation

All outreach tasks must check status before executing:

```python
@task
async def send_email_task(lead_id: UUID):
    # JIT validation
    lead = await db.get(Lead, lead_id)
    if lead.status == 'unsubscribed':
        return  # Skip
    if lead.campaign.status != 'active':
        return  # Skip
    if lead.client.subscription_status != 'active':
        return  # Skip
    
    # Proceed with send
    await email_engine.send(db, lead_id)
```

---

## Checkpoint 3 Criteria

- [ ] Prefect server running
- [ ] Worker connects to server
- [ ] Flows registered
- [ ] JIT validation in all tasks
- [ ] Billing checks in enrichment flow
