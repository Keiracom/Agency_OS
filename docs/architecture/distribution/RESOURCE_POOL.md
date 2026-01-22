# Resource Pool Architecture

**Status:** 🟡 PARTIALLY IMPLEMENTED
**Priority:** HIGH
**Owner:** CTO
**Last Updated:** January 22, 2026

---

## Executive Summary

New clients receive dedicated resources (domains, phone numbers) from a platform-level pool on signup. Resource assignment is automated via onboarding flow.

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| `resource_pool` table | ✅ | Migration 041 |
| `client_resources` table | ✅ | Migration 041 |
| ResourcePool model | ✅ | `src/models/resource_pool.py` |
| ClientResource model | ✅ | `src/models/resource_pool.py` |
| Assignment service | ✅ | `src/services/resource_assignment_service.py` |
| Onboarding integration | ✅ | `assign_resources_to_client()` called |
| Buffer monitoring | ✅ | `check_buffer_and_alert()` |
| Health tracking | ✅ | Phase D additions |
| Domain seeding | 🟡 | Manual via API |
| Campaign auto-inherit | 🟡 | Needs verification |

```
Client signs up
    └── Onboarding flow triggers
        └── resource_assignment_service allocates from pool
            └── client_resources created
                └── Buffer status checked and alerts sent
```

---

## Target State

```
Client signs up
    └── resource_assignment_service allocates from pool
        └── client_resources created (3 domains, 2 phones, 1 LinkedIn seat)
            └── Campaign inherits client's resources automatically
                └── allocator.py uses them
```

---

## Database Schema

### New Table: `resource_pool` (Platform-Level)

```sql
CREATE TABLE resource_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Resource identification
    resource_type TEXT NOT NULL,           -- 'email_domain', 'phone_number', 'linkedin_seat'
    resource_value TEXT NOT NULL UNIQUE,   -- 'agencyxos-growth.com', '+61412345678', 'seat_abc123'
    resource_name TEXT,                    -- Friendly name

    -- Capacity tracking
    max_clients INTEGER DEFAULT 1,         -- How many clients can share this resource
    current_clients INTEGER DEFAULT 0,     -- Currently assigned clients

    -- Status
    status TEXT DEFAULT 'available',       -- 'available', 'assigned', 'warming', 'retired'

    -- Warmup tracking (for email domains)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    warmup_started_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,
    reputation_score INTEGER DEFAULT 0,    -- 0-100

    -- Provider metadata
    provider TEXT,                         -- 'infraforge', 'twilio', 'unipile'
    provider_id TEXT,                      -- External ID

    -- Metadata
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_resource_pool_type_status ON resource_pool(resource_type, status);
CREATE INDEX idx_resource_pool_available ON resource_pool(resource_type)
    WHERE status = 'available' AND current_clients < max_clients;
```

### New Table: `client_resources` (Client-Level)

```sql
CREATE TABLE client_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    resource_pool_id UUID NOT NULL REFERENCES resource_pool(id),

    -- Assignment tracking
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    released_at TIMESTAMPTZ,               -- NULL = still assigned

    -- Usage tracking
    total_sends INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    CONSTRAINT unique_client_resource UNIQUE (client_id, resource_pool_id)
);

-- Indexes
CREATE INDEX idx_client_resources_client ON client_resources(client_id)
    WHERE released_at IS NULL;
```

### Modify: `campaign_resources` (Auto-Inherit)

```sql
-- Add column to link to client_resources
ALTER TABLE campaign_resources
ADD COLUMN client_resource_id UUID REFERENCES client_resources(id);

-- Campaign resources should auto-populate from client_resources
-- when a campaign is created
```

---

## Resource Allocation Rules

### CEO Decisions (2026-01-20)

| Decision | Choice |
|----------|--------|
| Sharing model | **Dedicated** (1 domain = 1 client) |
| Allocation trigger | **Payment confirmed** (Stripe webhook) |
| Churn handling | **30-day hold** then release |
| Upgrade | **Immediate** resource addition |
| Downgrade | **End of billing month** (keep current until then) |
| Buffer strategy | **40% buffer** — auto-purchase when low |

### Per-Tier Allocation (Calculated)

Based on:
- ALS distribution: Hot 10%, Warm 25%, Cool 40%, Cold 25%
- Channel access: Email (all), LinkedIn (Cool+), Voice (Warm+), SMS (Hot only)
- 5-step sequence with reply handling (+10%)
- 22 working days/month

| Tier | Leads | Domains | Mailboxes | Phone Numbers | LinkedIn Seats |
|------|-------|---------|-----------|---------------|----------------|
| Ignition ($2,500) | 1,250 | 3 | 6 | 1 | 4 |
| Velocity ($5,000) | 2,250 | 5 | 10 | 2 | 7 |
| Dominance ($7,500) | 4,500 | 9 | 18 | 3 | 14 |

### Calculation Breakdown

**Email Domains (50/day/domain):**
- Ignition: 2,750 emails/month ÷ 22 days = 125/day → 3 domains
- Velocity: 4,950 emails/month ÷ 22 days = 225/day → 5 domains
- Dominance: 9,900 emails/month ÷ 22 days = 450/day → 9 domains

**Phone Numbers (Voice 50/day + SMS 100/day):**
- Ignition: 26 actions/day → 1 number
- Velocity: 46 actions/day → 2 numbers
- Dominance: 92 actions/day → 3 numbers

**LinkedIn Seats (20 connections/day + messages):**
- Ignition: 56 actions/day → 3 seats
- Velocity: 100 actions/day → 7 seats (with headroom)
- Dominance: 199 actions/day → 14 seats (with headroom)

### Domain Selection Priority

When allocating email domains:

1. **Prefer warmed domains** (warmup_completed_at IS NOT NULL)
2. **Prefer higher reputation** (reputation_score DESC)
3. **Prefer less loaded** (current_clients < max_clients)
4. **Oldest first** (created_at ASC) — more established

```python
def select_domains_for_client(
    pool: list[ResourcePool],
    count: int,
) -> list[ResourcePool]:
    """
    Select best available domains for a new client.
    """
    available = [
        r for r in pool
        if r.resource_type == 'email_domain'
        and r.status in ('available', 'assigned')
        and r.current_clients < r.max_clients
    ]

    # Sort by priority
    available.sort(
        key=lambda r: (
            r.warmup_completed_at is not None,  # Warmed first
            r.reputation_score,                  # Higher reputation
            -r.current_clients,                  # Less loaded
        ),
        reverse=True
    )

    return available[:count]
```

---

## Service: `resource_assignment_service.py`

```python
# src/services/resource_assignment_service.py

async def assign_resources_to_client(
    db: AsyncSession,
    client_id: UUID,
    tier: str,
) -> dict[str, list[UUID]]:
    """
    Assign resources from pool to a new client based on tier.

    Called during onboarding after client creation.

    Args:
        db: Database session
        client_id: New client's UUID
        tier: Pricing tier ('ignition', 'velocity', 'dominance')

    Returns:
        Dict mapping resource_type to list of assigned resource_pool IDs
    """
    allocations = TIER_ALLOCATIONS[tier]
    assigned = {}

    for resource_type, count in allocations.items():
        resources = await _select_best_resources(db, resource_type, count)

        for resource in resources:
            # Create client_resource link
            client_resource = ClientResource(
                client_id=client_id,
                resource_pool_id=resource.id,
            )
            db.add(client_resource)

            # Update pool count
            resource.current_clients += 1
            if resource.current_clients >= resource.max_clients:
                resource.status = 'assigned'

        assigned[resource_type] = [r.id for r in resources]

    await db.commit()
    return assigned


async def release_client_resources(
    db: AsyncSession,
    client_id: UUID,
) -> int:
    """
    Release all resources when client churns.

    Returns:
        Count of released resources
    """
    # Mark client_resources as released
    stmt = (
        update(ClientResource)
        .where(ClientResource.client_id == client_id)
        .where(ClientResource.released_at.is_(None))
        .values(released_at=datetime.utcnow())
    )
    result = await db.execute(stmt)

    # Decrement pool counts
    # ... (update resource_pool.current_clients)

    await db.commit()
    return result.rowcount
```

---

## Buffer Strategy (40% Rule)

### Formula

```
buffer_needed = current_allocated × 0.40
total_warmed = current_allocated + buffer_needed
```

### Example Scenarios

| Active Clients | Domains In Use | Buffer (40%) | Total Warmed Needed |
|----------------|----------------|--------------|---------------------|
| 1 Velocity | 5 | 2 | 7 |
| 2 Velocity | 10 | 4 | 14 |
| 5 mixed | 25 | 10 | 35 |
| 10 mixed | 50 | 20 | 70 |

### Auto-Provisioning Trigger

```python
async def check_buffer_and_provision(db: AsyncSession):
    """
    Check if buffer is below 40%, trigger InfraForge purchase.
    """
    stats = await get_pool_stats(db, resource_type='email_domain')

    allocated = stats['allocated']
    available = stats['available']
    total_warmed = allocated + available

    required_buffer = int(allocated * 0.40)
    actual_buffer = available

    if actual_buffer < required_buffer:
        shortfall = required_buffer - actual_buffer
        await infraforge_client.purchase_domains(count=shortfall)
        await send_admin_alert(
            f"Auto-purchased {shortfall} domains. Buffer was {actual_buffer}, needed {required_buffer}."
        )
```

### Warmup Lead Time

| Phase | Days |
|-------|------|
| Domain purchase | 1 |
| DNS propagation | 1 |
| Warmup start | 14-21 |
| **Total** | **16-23 days** |

**Implication:** Buffer must account for 3-week warmup. If signup rate is high, buffer % may need to increase.

---

## Integration Points

### 1. Onboarding Flow

```python
# src/orchestration/flows/onboarding_flow.py

@task
async def assign_client_resources_task(client_id: UUID, tier: str):
    """Assign resources from pool after client creation."""
    async with get_async_session() as db:
        assigned = await assign_resources_to_client(db, client_id, tier)
        logger.info(f"Assigned resources to client {client_id}: {assigned}")
        return assigned
```

### 2. Campaign Creation

```python
# src/api/routes/campaigns.py

@router.post("/clients/{client_id}/campaigns")
async def create_campaign(client_id: UUID, ...):
    # Auto-populate campaign_resources from client_resources
    client_resources = await get_client_resources(db, client_id)

    for cr in client_resources:
        campaign_resource = CampaignResource(
            campaign_id=campaign.id,
            client_resource_id=cr.id,
            channel=cr.resource_type_to_channel(),
            resource_id=cr.resource_pool.resource_value,
            daily_limit=get_limit_for_resource(cr),
            is_warmed=cr.resource_pool.warmup_completed_at is not None,
        )
        db.add(campaign_resource)
```

### 3. Allocator Engine

No changes needed — allocator already uses `campaign_resources`. The change is upstream (auto-population).

---

## Warmup Schedule Integration

When a domain is assigned to a client, check warmup status:

```python
def get_daily_limit_for_domain(domain: ResourcePool) -> int:
    """
    Get daily limit based on warmup status.
    """
    if domain.warmup_completed_at:
        return 50  # Full capacity

    if not domain.warmup_started_at:
        return 5  # Not started

    days_warming = (datetime.utcnow() - domain.warmup_started_at).days

    if days_warming < 4:
        return 5
    elif days_warming < 8:
        return 10
    elif days_warming < 15:
        return 20
    elif days_warming < 22:
        return 35
    else:
        return 50
```

---

## Capacity Planning

### Current Inventory

| Resource | Count | Status |
|----------|-------|--------|
| Email domains | 3 | Warmed |
| Phone numbers | ? | TBD |
| LinkedIn seats | ? | TBD |

### Scaling Formula

For N clients at Velocity tier:
- Domains needed: N × 3 = 3N
- Phone numbers needed: N × 2 = 2N
- LinkedIn seats needed: N × 1 = N

With resource sharing (max_clients=2):
- Domains needed: ceil(3N / 2) = 1.5N
- Phone numbers needed: ceil(2N / 2) = N
- LinkedIn seats needed: N (no sharing recommended)

---

## Migration Path

### Step 1: Create Tables
```sql
-- Migration 041_resource_pool.sql
CREATE TABLE resource_pool (...);
CREATE TABLE client_resources (...);
ALTER TABLE campaign_resources ADD COLUMN client_resource_id UUID;
```

### Step 2: Seed Existing Resources
```sql
-- Insert existing domains into pool
INSERT INTO resource_pool (resource_type, resource_value, status, warmup_completed_at)
VALUES
    ('email_domain', 'agencyxos-growth.com', 'available', NOW()),
    ('email_domain', 'agencyxos-reach.com', 'available', NOW()),
    ('email_domain', 'agencyxos-leads.com', 'available', NOW());
```

### Step 3: Create Service
```
src/services/resource_assignment_service.py
```

### Step 4: Wire to Onboarding
```
src/orchestration/flows/onboarding_flow.py
```

---

## Files Involved

| File | Status | Purpose |
|------|--------|---------|
| `supabase/migrations/041_resource_pool.sql` | ✅ | Schema + RLS + helper functions |
| `src/models/resource_pool.py` | ✅ | SQLAlchemy models with health tracking |
| `src/services/resource_assignment_service.py` | ✅ | Assignment, release, buffer monitoring |
| `src/orchestration/flows/onboarding_flow.py` | ✅ | Calls assignment service |
| `src/services/domain_health_service.py` | ✅ | Updates health metrics |
| `src/api/routes/campaigns.py` | 🟡 | Auto-populate needs verification |

---

## Verification Checklist

- [x] `resource_pool` table exists (migration 041)
- [x] `client_resources` table exists (migration 041)
- [x] `resource_assignment_service.py` created with full implementation
- [x] Onboarding flow calls assignment service
- [x] Warmup limits respected (model calculates daily limits)
- [x] Release works on client churn (`release_client_resources()`)
- [x] Buffer monitoring (`check_buffer_and_alert()`)
- [x] Health tracking fields (Phase D: bounce_rate, complaint_rate, health_status)
- [ ] Existing domains seeded into pool (manual via API)
- [ ] Campaign creation auto-populates resources (needs verification)
