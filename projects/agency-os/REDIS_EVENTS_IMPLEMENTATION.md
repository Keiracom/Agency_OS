# Redis Event System — Implementation Plan for Agency OS

**Date:** 2025-01-29  
**Status:** Ready for Implementation  
**Priority:** P1 — High-leverage infrastructure improvement

---

## 1. Assessment Summary

### Current State
The existing `src/integrations/redis.py` is well-architected with:
- ✅ Async Redis client with connection pooling (20 connections)
- ✅ Versioned cache keys (`v1:` prefix)
- ✅ Rate limiting (resource-level, daily resets)
- ✅ AI spend tracking (daily budget circuit breaker)
- ✅ Enrichment cache (90-day TTL)

### What's Missing
- ❌ Pub/Sub — No event publishing/subscribing
- ❌ Streams — No event logging or replay capability
- ❌ Sorted Sets for priority queues — Unused

### Pain Points Identified
1. **Polling-based enrichment:** Daily flows query DB for leads with `status=NEW`
2. **No real-time coordination:** Campaign activation queues leads, but enrichment flow runs on schedule
3. **No audit trail:** Actions are logged to DB, but no event stream for debugging/replay

---

## 2. Pub/Sub vs Streams: Decision

| Feature | Pub/Sub | Streams |
|---------|---------|---------|
| **Pattern** | Fire-and-forget broadcast | Append-only log |
| **Delivery** | At-most-once (if subscriber offline, message lost) | At-least-once (persisted, replayable) |
| **Consumer Groups** | ❌ No | ✅ Yes |
| **Message Retention** | None | Configurable |
| **Backpressure** | None | Built-in |
| **Use Case** | Real-time notifications | Event sourcing, audit |

### Recommendation: **Streams First**

**Why:**
1. **Reliability** — Messages persist if workers are down (Upstash survives Railway deploys)
2. **Replay** — Debug issues by replaying event sequences
3. **Consumer Groups** — Scale workers horizontally without duplication
4. **Audit Trail** — Every event is immutable evidence

**Pub/Sub Later** — Use for ephemeral notifications (dashboard updates) once Streams foundation is solid.

---

## 3. Highest-Leverage Pattern: Event-Driven Enrichment

### Current Flow (Polling)
```
Lead Created → DB status=NEW → [wait for scheduled flow] → Poll DB → Enrich
```
- **Latency:** Minutes to hours depending on schedule
- **Efficiency:** DB queries for leads that may not need enrichment

### Target Flow (Event-Driven)
```
Lead Created → Publish to Stream → Worker consumes → Enrich immediately
```
- **Latency:** Seconds
- **Efficiency:** Only process events, no polling

### Events to Implement (Phase 1)
| Event | Trigger | Subscribers |
|-------|---------|-------------|
| `lead.created` | Lead insert | Enrichment worker |
| `lead.enriched` | Scout engine completes | Scoring worker |
| `lead.scored` | ALS calculated | Outreach scheduler |
| `campaign.activated` | Campaign status change | Lead processor |

---

## 4. Upstash-Specific Considerations

### Constraints
- **Max message size:** 1MB (Upstash limit) — Store event metadata, not full payloads
- **Streams retention:** Configurable via `MAXLEN` — Use approximate trimming (`MAXLEN ~`)
- **Consumer groups:** Fully supported ✅
- **Connection model:** HTTP-based for serverless, or standard Redis protocol

### Best Practices for Upstash
```python
# Use MAXLEN ~ for efficient trimming (approximate is faster)
await redis.xadd("events:leads", fields, maxlen=10000, approximate=True)

# Use blocking reads with timeout to avoid hammering Upstash
await redis.xreadgroup(groupname="enrichment", consumername="worker-1", 
                       streams={"events:leads": ">"}, block=5000)
```

### Rate Limits
- Upstash free tier: 10K commands/day
- Paid: Unlimited but pay-per-command
- **Recommendation:** Batch events where possible, use pipeline for multiple ops

---

## 5. Implementation Spec

### 5.1 Stream Schema

```
Stream: events:leads
┌────────────────────────────────────────────────────────┐
│ ID: 1706540000000-0                                    │
│ Fields:                                                │
│   event_type: "lead.created"                           │
│   lead_id: "uuid"                                      │
│   client_id: "uuid"                                    │
│   campaign_id: "uuid"                                  │
│   domain: "example.com"                                │
│   timestamp: "2025-01-29T10:00:00Z"                    │
│   correlation_id: "uuid" (for tracing)                 │
└────────────────────────────────────────────────────────┘

Consumer Groups:
  - enrichment-workers (processes lead.created → enrich)
  - scoring-workers (processes lead.enriched → score)
```

### 5.2 Code Structure

```
src/
├── integrations/
│   ├── redis.py              # Existing (unchanged)
│   └── events/
│       ├── __init__.py
│       ├── publisher.py      # Event publishing
│       ├── consumer.py       # Consumer group management
│       ├── schemas.py        # Event type definitions
│       └── handlers/
│           ├── __init__.py
│           ├── lead_handlers.py
│           └── campaign_handlers.py
```

### 5.3 Core Implementation

#### `src/integrations/events/schemas.py`
```python
"""Event schemas for Redis Streams."""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    # Lead events
    LEAD_CREATED = "lead.created"
    LEAD_ENRICHED = "lead.enriched"
    LEAD_SCORED = "lead.scored"
    LEAD_CONTACTED = "lead.contacted"
    
    # Campaign events
    CAMPAIGN_ACTIVATED = "campaign.activated"
    CAMPAIGN_PAUSED = "campaign.paused"
    
    # Outreach events
    EMAIL_SENT = "outreach.email.sent"
    EMAIL_OPENED = "outreach.email.opened"
    EMAIL_REPLIED = "outreach.email.replied"


class BaseEvent(BaseModel):
    """Base event structure."""
    event_type: EventType
    correlation_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1"  # Schema versioning
    
    def to_stream_fields(self) -> dict[str, str]:
        """Convert to Redis stream fields (all strings)."""
        data = self.model_dump(mode="json")
        return {k: str(v) if v is not None else "" for k, v in data.items()}


class LeadCreatedEvent(BaseEvent):
    event_type: EventType = EventType.LEAD_CREATED
    lead_id: UUID
    client_id: UUID
    campaign_id: UUID
    domain: str | None = None
    email: str | None = None


class LeadEnrichedEvent(BaseEvent):
    event_type: EventType = EventType.LEAD_ENRICHED
    lead_id: UUID
    client_id: UUID
    enrichment_source: str  # cache, apollo, apify, clay
    confidence: float
    fields_enriched: list[str]


class CampaignActivatedEvent(BaseEvent):
    event_type: EventType = EventType.CAMPAIGN_ACTIVATED
    campaign_id: UUID
    client_id: UUID
    lead_count: int
```

#### `src/integrations/events/publisher.py`
```python
"""Event publisher for Redis Streams."""
import json
import logging
from typing import Any

from src.integrations.redis import get_redis
from src.integrations.events.schemas import BaseEvent

logger = logging.getLogger(__name__)

# Stream names (versioned for migration safety)
STREAM_LEADS = "v1:events:leads"
STREAM_CAMPAIGNS = "v1:events:campaigns"
STREAM_OUTREACH = "v1:events:outreach"

# Stream retention (approximate, auto-trim)
STREAM_MAXLEN = 100_000


class EventPublisher:
    """Publish events to Redis Streams."""
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def publish(
        self, 
        stream: str, 
        event: BaseEvent,
        maxlen: int = STREAM_MAXLEN,
    ) -> str:
        """
        Publish event to stream.
        
        Args:
            stream: Stream name (e.g., "v1:events:leads")
            event: Event instance
            maxlen: Max stream length (auto-trims older entries)
            
        Returns:
            Stream entry ID (e.g., "1706540000000-0")
        """
        redis = await self._get_redis()
        
        fields = event.to_stream_fields()
        
        # XADD with approximate maxlen for efficiency
        entry_id = await redis.xadd(
            stream,
            fields,
            maxlen=maxlen,
            approximate=True,
        )
        
        logger.info(
            f"Published {event.event_type} to {stream} [{entry_id}] "
            f"correlation_id={event.correlation_id}"
        )
        
        return entry_id
    
    async def publish_lead_event(self, event: BaseEvent) -> str:
        """Publish to leads stream."""
        return await self.publish(STREAM_LEADS, event)
    
    async def publish_campaign_event(self, event: BaseEvent) -> str:
        """Publish to campaigns stream."""
        return await self.publish(STREAM_CAMPAIGNS, event)


# Global publisher instance
publisher = EventPublisher()
```

#### `src/integrations/events/consumer.py`
```python
"""Consumer group management for Redis Streams."""
import asyncio
import logging
from typing import Any, Callable, Coroutine

from src.integrations.redis import get_redis
from src.integrations.events.publisher import STREAM_LEADS, STREAM_CAMPAIGNS

logger = logging.getLogger(__name__)


class EventConsumer:
    """
    Consume events from Redis Streams using consumer groups.
    
    Consumer groups ensure:
    - Each message delivered to only one consumer in group
    - Messages persist until acknowledged
    - Failed messages can be claimed and retried
    """
    
    def __init__(
        self,
        stream: str,
        group: str,
        consumer: str,
    ):
        self.stream = stream
        self.group = group
        self.consumer = consumer
        self._redis = None
        self._running = False
    
    async def _get_redis(self):
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis
    
    async def ensure_group(self) -> None:
        """Create consumer group if it doesn't exist."""
        redis = await self._get_redis()
        try:
            await redis.xgroup_create(
                self.stream,
                self.group,
                id="0",  # Read from beginning
                mkstream=True,  # Create stream if doesn't exist
            )
            logger.info(f"Created consumer group {self.group} on {self.stream}")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group {self.group} already exists")
            else:
                raise
    
    async def consume(
        self,
        handler: Callable[[str, dict[str, Any]], Coroutine[Any, Any, bool]],
        block_ms: int = 5000,
        count: int = 10,
    ) -> None:
        """
        Consume events and process with handler.
        
        Args:
            handler: Async function(entry_id, fields) -> bool (success)
            block_ms: Block timeout in milliseconds
            count: Max messages per read
        """
        await self.ensure_group()
        redis = await self._get_redis()
        self._running = True
        
        logger.info(
            f"Starting consumer {self.consumer} in group {self.group} "
            f"on stream {self.stream}"
        )
        
        while self._running:
            try:
                # Read new messages (> means undelivered only)
                messages = await redis.xreadgroup(
                    groupname=self.group,
                    consumername=self.consumer,
                    streams={self.stream: ">"},
                    count=count,
                    block=block_ms,
                )
                
                if not messages:
                    continue
                
                for stream_name, entries in messages:
                    for entry_id, fields in entries:
                        try:
                            # Process message
                            success = await handler(entry_id, fields)
                            
                            if success:
                                # Acknowledge message (removes from pending)
                                await redis.xack(self.stream, self.group, entry_id)
                                logger.debug(f"ACK {entry_id}")
                            else:
                                # Don't ack — will be available for retry
                                logger.warning(f"Handler returned False for {entry_id}")
                                
                        except Exception as e:
                            logger.error(f"Error processing {entry_id}: {e}")
                            # Don't ack — message stays in pending list
                            
            except asyncio.CancelledError:
                logger.info(f"Consumer {self.consumer} cancelled")
                break
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(1)  # Backoff on error
    
    def stop(self) -> None:
        """Stop consuming."""
        self._running = False


# Factory functions for common consumers
def create_enrichment_consumer(worker_id: str) -> EventConsumer:
    """Create consumer for enrichment processing."""
    return EventConsumer(
        stream=STREAM_LEADS,
        group="enrichment-workers",
        consumer=f"enrichment-{worker_id}",
    )


def create_scoring_consumer(worker_id: str) -> EventConsumer:
    """Create consumer for scoring processing."""
    return EventConsumer(
        stream=STREAM_LEADS,
        group="scoring-workers",
        consumer=f"scoring-{worker_id}",
    )
```

#### `src/integrations/events/handlers/lead_handlers.py`
```python
"""Event handlers for lead events."""
import logging
from typing import Any
from uuid import UUID

from src.integrations.events.schemas import EventType
from src.orchestration.tasks.enrichment_tasks import enrich_lead_task

logger = logging.getLogger(__name__)


async def handle_lead_created(entry_id: str, fields: dict[str, Any]) -> bool:
    """
    Handle lead.created event — trigger enrichment.
    
    Args:
        entry_id: Stream entry ID
        fields: Event fields from stream
        
    Returns:
        True if handled successfully
    """
    event_type = fields.get("event_type")
    
    if event_type != EventType.LEAD_CREATED.value:
        logger.debug(f"Skipping {event_type} (not lead.created)")
        return True  # Ack non-matching events
    
    lead_id = fields.get("lead_id")
    if not lead_id:
        logger.error(f"Missing lead_id in {entry_id}")
        return True  # Ack malformed events (don't retry forever)
    
    try:
        # Trigger enrichment (Prefect task)
        result = await enrich_lead_task(UUID(lead_id))
        
        logger.info(
            f"Enriched lead {lead_id} via {result.get('enrichment_source')} "
            f"(correlation: {fields.get('correlation_id')})"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to enrich lead {lead_id}: {e}")
        # Return False to NOT ack — will be retried
        return False
```

### 5.4 Integration Points

#### Publishing from API (Lead Creation)
```python
# In src/api/routes/leads.py

from src.integrations.events.publisher import publisher
from src.integrations.events.schemas import LeadCreatedEvent

@router.post("/leads")
async def create_lead(lead_data: LeadCreate, db: AsyncSession = Depends(get_db)):
    # ... create lead in DB ...
    
    # Publish event
    event = LeadCreatedEvent(
        lead_id=lead.id,
        client_id=lead.client_id,
        campaign_id=lead.campaign_id,
        domain=lead.domain,
    )
    await publisher.publish_lead_event(event)
    
    return lead
```

#### Publishing from Prefect Flow
```python
# In src/orchestration/flows/campaign_flow.py

from src.integrations.events.publisher import publisher
from src.integrations.events.schemas import CampaignActivatedEvent

@flow
async def campaign_activation_flow(campaign_id: UUID):
    # ... existing activation logic ...
    
    # Publish event at end
    event = CampaignActivatedEvent(
        campaign_id=campaign_id,
        client_id=client_id,
        lead_count=leads_data["lead_count"],
    )
    await publisher.publish_campaign_event(event)
```

### 5.5 Worker Process

Create a standalone worker script for Railway:

#### `src/workers/enrichment_worker.py`
```python
"""
Enrichment worker — consumes lead.created events.

Run: python -m src.workers.enrichment_worker
"""
import asyncio
import logging
import os
import signal

from src.integrations.events.consumer import create_enrichment_consumer
from src.integrations.events.handlers.lead_handlers import handle_lead_created

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    worker_id = os.getenv("RAILWAY_REPLICA_ID", "local-1")
    consumer = create_enrichment_consumer(worker_id)
    
    # Graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, consumer.stop)
    
    logger.info(f"Starting enrichment worker {worker_id}")
    await consumer.consume(handle_lead_created)
    logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. Migration Path

### Phase 1: Shadow Mode (Week 1)
1. Deploy event publishing alongside existing flows
2. Publish events but don't consume them yet
3. Monitor stream growth and event patterns

### Phase 2: Dual-Run (Week 2)
1. Deploy enrichment worker
2. Run both: scheduled Prefect flow + event-driven worker
3. Compare results, tune worker

### Phase 3: Cut Over (Week 3)
1. Disable scheduled Prefect enrichment flow
2. Event-driven only
3. Keep scheduled flow as fallback (runs hourly, catches any missed events)

### Rollback Plan
- Re-enable Prefect scheduled flow
- Workers can be stopped without data loss (messages persist)
- No DB changes required

---

## 7. Monitoring & Observability

### Stream Health Checks
```python
async def check_stream_health() -> dict:
    """Add to existing health check."""
    redis = await get_redis()
    
    # Stream lengths
    leads_len = await redis.xlen(STREAM_LEADS)
    
    # Pending messages per group
    groups = await redis.xinfo_groups(STREAM_LEADS)
    
    return {
        "streams": {
            "leads": {
                "length": leads_len,
                "groups": [
                    {
                        "name": g["name"],
                        "consumers": g["consumers"],
                        "pending": g["pending"],
                        "last_delivered_id": g["last-delivered-id"],
                    }
                    for g in groups
                ],
            },
        },
    }
```

### Metrics to Track
- **Stream length** — Growing unboundedly = consumers can't keep up
- **Pending count** — High = messages failing to process
- **Consumer lag** — Time between publish and consume

---

## 8. Implementation Effort

| Task | Effort | Owner |
|------|--------|-------|
| Create `src/integrations/events/` structure | 2h | Dev |
| Implement publisher + schemas | 2h | Dev |
| Implement consumer + handlers | 3h | Dev |
| Add publishing to lead creation API | 1h | Dev |
| Create enrichment worker | 2h | Dev |
| Railway worker deployment config | 1h | DevOps |
| Testing + shadow mode | 4h | QA |
| Documentation | 1h | Dev |
| **Total** | **~16h** | — |

---

## 9. Decision Checklist

- [x] Streams over Pub/Sub (reliability, replay)
- [x] Start with lead.created → enrichment pattern (highest leverage)
- [x] Upstash compatible (MAXLEN ~, XREADGROUP)
- [x] Consumer groups for horizontal scaling
- [x] Schema versioning for future evolution
- [x] Correlation IDs for tracing
- [x] Graceful migration path (shadow → dual → cutover)

---

## 10. Next Steps

1. **Approve this plan** — Review with Dave
2. **Create branch** — `feature/redis-event-streams`
3. **Implement Phase 1** — Publisher + schemas (no consumers yet)
4. **Deploy shadow mode** — Events flow but aren't consumed
5. **Implement Phase 2** — Enrichment worker + handlers
6. **Test end-to-end** — Lead creation → enrichment
7. **Cutover** — Disable scheduled flow, event-driven only

---

*This plan transforms Agency OS from poll-based to event-driven architecture, unlocking real-time reactivity while maintaining reliability through Redis Streams.*
