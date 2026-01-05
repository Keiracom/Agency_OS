# Allocator Engine — Channel & Resource Assignment

**File:** `src/engines/allocator.py`  
**Purpose:** Assign channels and resources based on ALS tier and rate limits  
**Layer:** 3 - engines

---

## Channel Access by ALS Tier

| Channel | Cold (20-34) | Cool (35-59) | Warm (60-84) | Hot (85-100) |
|---------|--------------|--------------|--------------|--------------|
| Email | ✅ | ✅ | ✅ | ✅ |
| LinkedIn | ❌ | ✅ | ✅ | ✅ |
| Voice AI | ❌ | ❌ | ✅ | ✅ |
| SMS | ❌ | ❌ | ❌ | ✅ |
| Direct Mail | ❌ | ❌ | ❌ | ✅ |

---

## Resource-Level Rate Limits

| Resource | Limit | Period | Key Format |
|----------|-------|--------|------------|
| LinkedIn seat | 17 | per day | `ratelimit:linkedin:{seat_id}:daily` |
| Email domain | 50 | per day | `ratelimit:email:{domain}:daily` |
| SMS number | 100 | per day | `ratelimit:sms:{number}:daily` |
| Voice number | 50 | per day | `ratelimit:voice:{number}:daily` |

---

## Round-Robin Resource Selection

```python
async def select_resource(
    self,
    channel: ChannelType,
    client_id: UUID
) -> Resource | None:
    """
    Select least-used resource that hasn't hit rate limit.
    
    1. Get all resources for client + channel
    2. Filter out rate-limited resources
    3. Sort by daily usage (ascending)
    4. Return first available
    """
    resources = await self.get_client_resources(client_id, channel)
    
    for resource in sorted(resources, key=lambda r: r.daily_usage):
        if not await self.is_rate_limited(resource):
            return resource
    
    return None  # All resources exhausted
```

---

## WHEN Pattern Integration (Phase 16)

```python
async def get_optimal_send_time(
    self,
    db: AsyncSession,
    client_id: UUID,
    channel: ChannelType
) -> datetime:
    """
    Get optimal send time from learned WHEN patterns.
    
    Falls back to default schedule if no patterns exist.
    """
    pattern = await db.execute(
        select(ConversionPattern)
        .where(ConversionPattern.client_id == client_id)
        .where(ConversionPattern.pattern_type == 'when')
        .where(ConversionPattern.channel == channel)
    )
    
    if pattern and pattern.confidence > 0.6:
        return self.next_occurrence(
            pattern.optimal_day,
            pattern.optimal_hour
        )
    
    return self.default_schedule(channel)
```

---

## HOW Pattern Integration (Phase 16)

```python
async def get_channel_sequence(
    self,
    db: AsyncSession,
    client_id: UUID,
    als_tier: str
) -> list[ChannelType]:
    """
    Get optimal channel sequence from learned HOW patterns.
    
    Falls back to tier-based defaults if no patterns exist.
    """
    pattern = await db.execute(
        select(ConversionPattern)
        .where(ConversionPattern.client_id == client_id)
        .where(ConversionPattern.pattern_type == 'how')
    )
    
    if pattern and pattern.confidence > 0.6:
        return pattern.winning_sequence
    
    return self.default_sequence(als_tier)
```

---

## API

```python
class AllocatorEngine:
    async def allocate(
        self,
        db: AsyncSession,
        lead_id: UUID,
        client_id: UUID
    ) -> AllocationResult:
        """
        Determine channels, resources, and timing for a lead.
        
        Returns:
            AllocationResult with channels, resources, send_time
        """
        ...
    
    async def check_rate_limit(
        self,
        resource_type: str,
        resource_id: str
    ) -> bool:
        """Check if resource has hit daily limit."""
        ...
    
    async def increment_usage(
        self,
        resource_type: str,
        resource_id: str
    ) -> int:
        """Increment usage counter, return new count."""
        ...
```
