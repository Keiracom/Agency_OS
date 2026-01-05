# Redis Integration

**File:** `src/integrations/redis.py`  
**Purpose:** Caching and rate limiting (NOT task queues)  
**Provider:** Upstash

---

## What Redis IS Used For

| Use Case | Key Pattern | TTL |
|----------|-------------|-----|
| Enrichment cache | `v1:enrichment:{domain}:{hash}` | 90 days |
| DataForSEO cache | `v1:dataforseo:{domain}` | 30 days |
| Rate limit counters | `ratelimit:{type}:{id}:daily` | 24 hours |
| AI spend tracking | `ai_spend:{client_id}:daily` | 24 hours |
| Session data | `session:{session_id}` | 1 hour |

---

## What Redis IS NOT Used For

- ❌ Task queues (use Prefect)
- ❌ Background job processing (use Prefect)
- ❌ Workflow orchestration (use Prefect)

---

## Cache Versioning

All keys include version prefix for safe migrations:

```python
CACHE_VERSION = "v1"

def cache_key(category: str, identifier: str) -> str:
    return f"{CACHE_VERSION}:{category}:{identifier}"
```

---

## Rate Limiting Pattern

```python
class RedisClient:
    async def check_rate_limit(
        self,
        resource_type: str,
        resource_id: str,
        limit: int
    ) -> bool:
        """
        Check if resource has hit daily limit.
        Returns True if rate limited.
        """
        key = f"ratelimit:{resource_type}:{resource_id}:daily"
        current = await self.redis.get(key)
        return int(current or 0) >= limit
    
    async def increment_rate_limit(
        self,
        resource_type: str,
        resource_id: str
    ) -> int:
        """Increment counter, set TTL to midnight."""
        key = f"ratelimit:{resource_type}:{resource_id}:daily"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expireat(key, self._next_midnight())
        results = await pipe.execute()
        return results[0]
```

---

## AI Spend Limiter

```python
DAILY_AI_SPEND_LIMIT = 100.00  # AUD

async def check_ai_spend(self, client_id: UUID) -> bool:
    """Check if client has exceeded daily AI spend."""
    key = f"ai_spend:{client_id}:daily"
    current = await self.redis.get(key)
    return float(current or 0) >= DAILY_AI_SPEND_LIMIT

async def record_ai_spend(
    self,
    client_id: UUID,
    amount: float
) -> float:
    """Record AI spend, return new total."""
    key = f"ai_spend:{client_id}:daily"
    pipe = self.redis.pipeline()
    pipe.incrbyfloat(key, amount)
    pipe.expireat(key, self._next_midnight())
    results = await pipe.execute()
    return results[0]
```

---

## Connection

```python
from redis.asyncio import Redis

class RedisClient:
    def __init__(self, url: str):
        self.redis = Redis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def close(self):
        await self.redis.close()
```

---

## Upstash Configuration

- **Region:** Sydney (ap-southeast-2) for low latency
- **Plan:** Pay-as-you-go or Pro for higher limits
- **Max connections:** 1000 (Pro)
