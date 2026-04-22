# C2 Prefect Infrastructure Reaudit — Phase 1.5
**Date:** 2026-04-22 02:36 UTC
**Auditor:** devops-6 sub-agent (Elliot session)
**Scope:** Concurrency limits, zombie flows, callback health, Railway plan, deployment health, flow inventory
**Method:** Live MCP queries (not reusing 2026-04-21 artefact)

## Summary

| Gate | Status | Evidence |
|------|--------|----------|
| 1. Concurrency Limits | PASS | agency-os-pool: concurrency_limit=10, 0 active slots |
| 2. Zombie Flows | PASS | 0 RUNNING, 0 PENDING — no zombies |
| 3. Callback Verification | WARN | 38 stale callbacks (oldest 18 days, 2026-04-04) |
| 4. Railway Plan | PASS | All 5 services running (postgres, reacher, agency-os, prefect-server, prefect-worker) |
| 5. Deployment Health | WARN | 27 total: 15 active, 12 paused. No lifecycle governance. |
| 6. Flow Inventory | PASS | 35 flows registered |

## WARN Details

### Gate 3: Stale Callbacks (38 rows)
- Oldest: 2026-04-04 (campaign_activation — coroutine object error)
- Schema mismatch: crm-sync-flow — column cc.ghl_location_id does not exist
- Recent: pipeline-f-master-flow 2026-04-21 — dm_messages_gate FAIL: 0 draft messages found
- **Action needed:** Cleanup job not running or failing silently.

### Gate 5: Paused Deployments (12/27)
Paused: cis-manual, cis-weekly, daily-learning-scrape, enrichment-flow, outreach-flow, pattern-learning-flow, persona-buffer-flow, pool-daily-allocation-flow, post-onboarding-setup, reply-recovery-flow, voice-outreach-flow, warmup-monitor-flow
Active: batch-campaign-evolution-flow, campaign-evolution-flow, campaign-flow, client-backfill-flow, client-pattern-learning-flow, credit-reset-flow, icp-reextract-flow, intelligence-flow, monthly-replenishment-flow, onboarding-flow, pattern-backfill-flow, pipeline-f-master-flow, pool-campaign-assignment-flow, pool-population-flow, trigger-lead-research-flow
- **Action needed:** Document pause reasons, add lifecycle tracking.

## Test Flows Present (cleanup needed)
- test-fail-flow, test-flow, stage-9-10-pipeline — consuming Prefect resources.
