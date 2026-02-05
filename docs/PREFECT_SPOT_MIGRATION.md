# PREFECT_SPOT_MIGRATION.md
## Bulk Processing Migration to Spot Instances

**Phase:** FIXED_COST_OPTIMIZATION_PHASE_1
**Savings:** ~$25 AUD/month (31% compute reduction)
**Status:** APPROVED — Preparation complete, ready for migration

---

## 1. FLOW TIER CLASSIFICATION

### HIGH-PRIORITY (Railway — Always-On) — $50/mo

These flows require consistent uptime and low latency:

| Flow | Reason | SLA |
|------|--------|-----|
| `lead_enrichment_realtime` | User-triggered, visible latency | <5s response |
| `webhook_handlers/*` | External service callbacks | 100% uptime |
| `campaign_triggers/*` | Time-sensitive sequences | <1min delay |
| `voice_ai_callbacks` | Active call handling | Real-time |
| `email_reply_processor` | Reply detection | <5min delay |

**Label:** `tier: realtime`

### BULK-PROCESSING (Spot Instances) — ~$5/mo

These flows are interruptible and can be retried:

| Flow | Reason | Tolerance |
|------|--------|-----------|
| `abn_bulk_ingestion` | Batch seed data (3.5M records) | 24h window |
| `batch_email_verification` | Nightly Hunter.io verification | 12h window |
| `historical_backfill/*` | Data migration/cleanup | 48h window |
| `analytics_aggregation` | Daily/weekly reports | 24h window |
| `gmb_batch_scraping` | Bulk GMB enrichment | 12h window |
| `intent_signal_refresh` | Ad library scraping | 24h window |

**Label:** `tier: bulk`

---

## 2. PREFECT FLOW TAGGING

### Flow Decorator Pattern

```python
from prefect import flow, task
from prefect.deployments import Deployment

# HIGH-PRIORITY: Railway infrastructure
@flow(
    name="lead_enrichment_realtime",
    description="Real-time lead enrichment (user-triggered)",
    tags=["tier:realtime", "infra:railway"],
)
async def lead_enrichment_realtime(lead_id: str):
    ...

# BULK-PROCESSING: Spot instance eligible
@flow(
    name="abn_bulk_ingestion",
    description="Batch ABN seed data ingestion",
    tags=["tier:bulk", "infra:spot", "interruptible"],
    retries=3,
    retry_delay_seconds=300,  # 5 min between retries
)
async def abn_bulk_ingestion(batch_size: int = 10000):
    ...
```

---

## 3. SPOT INSTANCE DESIGN PATTERNS

### 3.1 Idempotent Tasks

All bulk tasks must be idempotent (safe to re-run):

```python
@task(
    name="process_abn_batch",
    tags=["idempotent"],
)
async def process_abn_batch(batch_id: str, records: list[dict]):
    # Check if already processed
    existing = await db.get_batch_status(batch_id)
    if existing and existing.status == "complete":
        logger.info(f"Batch {batch_id} already processed, skipping")
        return existing.result
    
    # Process with checkpointing
    for i, record in enumerate(records):
        await process_single_record(record)
        
        # Checkpoint every 100 records
        if i % 100 == 0:
            await db.update_batch_progress(batch_id, i)
    
    await db.mark_batch_complete(batch_id)
```

### 3.2 Graceful Termination Handler

Handle SIGTERM (spot preemption warning):

```python
import signal
import asyncio

class SpotTerminationHandler:
    def __init__(self):
        self.terminating = False
        signal.signal(signal.SIGTERM, self._handle_sigterm)
    
    def _handle_sigterm(self, signum, frame):
        logger.warning("SIGTERM received — spot instance preemption")
        self.terminating = True
    
    async def checkpoint_and_exit(self, batch_id: str, progress: int):
        """Save progress before termination."""
        await db.update_batch_progress(batch_id, progress)
        logger.info(f"Checkpointed at record {progress}, exiting gracefully")
        raise SystemExit(0)

# Usage in flow
handler = SpotTerminationHandler()

@flow(tags=["tier:bulk"])
async def bulk_flow():
    for i, item in enumerate(items):
        if handler.terminating:
            await handler.checkpoint_and_exit(batch_id, i)
        await process_item(item)
```

### 3.3 Queue-Based Processing

Bulk jobs pull from Redis queue (not scheduled):

```python
from prefect import flow
from redis import Redis

redis = Redis.from_url(REDIS_URL)

@flow(name="bulk_worker", tags=["tier:bulk"])
async def bulk_worker():
    """
    Generic bulk worker that pulls jobs from queue.
    Runs on spot instance, restarts automatically on preemption.
    """
    while True:
        # Block for up to 30s waiting for job
        job = redis.blpop("bulk:jobs", timeout=30)
        
        if job is None:
            # No jobs, check for termination signal
            if should_shutdown():
                break
            continue
        
        job_data = json.loads(job[1])
        await process_bulk_job(job_data)
```

---

## 4. INFRASTRUCTURE CONFIGURATION

### AWS Spot Instance Config

```yaml
# spot-instance-config.yaml
instance_type: t3.small
spot_price: 0.008  # ~$6/mo if running 24/7
interruption_behavior: terminate

tags:
  tier: bulk
  project: agency-os
  environment: production

user_data: |
  #!/bin/bash
  # Install Prefect worker
  pip install prefect
  
  # Start worker with bulk queue
  prefect worker start \
    --pool bulk-processing \
    --work-queue bulk
```

### GCP Preemptible VM Config

```yaml
# preemptible-vm-config.yaml
machine_type: e2-small
preemptible: true
automatic_restart: false

labels:
  tier: bulk
  project: agency-os

startup_script: |
  #!/bin/bash
  pip install prefect
  prefect worker start --pool bulk-processing
```

---

## 5. DEPLOYMENT MAPPING

| Flow | Current Infra | Target Infra | Pool |
|------|---------------|--------------|------|
| `lead_enrichment_realtime` | Railway | Railway | `default` |
| `webhook_handlers/*` | Railway | Railway | `default` |
| `abn_bulk_ingestion` | Railway | AWS Spot | `bulk-processing` |
| `batch_email_verification` | Railway | AWS Spot | `bulk-processing` |
| `gmb_batch_scraping` | Railway | AWS Spot | `bulk-processing` |
| `analytics_aggregation` | Railway | AWS Spot | `bulk-processing` |

---

## 6. COST PROJECTION

| Component | Current | Proposed | Savings |
|-----------|---------|----------|---------|
| Railway (all flows) | $80/mo | $50/mo | $30/mo |
| AWS Spot (bulk) | $0 | $5/mo | — |
| **Total** | **$80/mo** | **$55/mo** | **$25/mo** |

---

## 7. MIGRATION CHECKLIST

### Phase 1: Tagging (This Sprint)
- [ ] Add `tier: bulk` tags to all batch flows
- [ ] Add `tier: realtime` tags to all critical flows
- [ ] Implement idempotent checkpointing in bulk flows
- [ ] Add SIGTERM handler to bulk workers

### Phase 2: Infrastructure (Next Sprint)
- [ ] Provision AWS Spot instance
- [ ] Configure Prefect work pool `bulk-processing`
- [ ] Deploy bulk worker to spot instance
- [ ] Test failover and recovery

### Phase 3: Cutover
- [ ] Migrate one bulk flow (abn_bulk_ingestion)
- [ ] Monitor for 1 week
- [ ] Migrate remaining bulk flows
- [ ] Decommission Railway bulk compute

---

*Document prepared: 2026-02-04*
*Approved by: Dave (CEO)*
