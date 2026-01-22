# Database Layer — Agency OS

**Purpose:** Supabase PostgreSQL with SQLAlchemy async ORM for multi-tenant lead generation SaaS
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-21

---

## Overview

Agency OS uses **Supabase PostgreSQL** as the primary database with **SQLAlchemy async** for ORM operations. The database layer (Layer 1) is the foundation of the import hierarchy and can only import from `src/exceptions.py`.

Key characteristics:
- **Multi-tenancy:** Client isolation via `client_id` foreign keys
- **Soft deletes:** All deletions set `deleted_at` instead of hard DELETE (Rule 14)
- **UUID primary keys:** All tables use UUID v4 via `gen_random_uuid()`
- **Connection pooling:** Transaction pooler (port 6543) with pool_size=5, max_overflow=10

---

## Code Locations

### SQLAlchemy Models (20 files)

| Model | File | Purpose |
|-------|------|---------|
| `Base` | `src/models/base.py` | Declarative base class |
| `TimestampMixin` | `src/models/base.py` | `created_at`, `updated_at` columns |
| `SoftDeleteMixin` | `src/models/base.py` | `deleted_at` column for soft deletes |
| `UUIDMixin` | `src/models/base.py` | UUID primary key |
| `Client` | `src/models/client.py` | Tenant/organization with subscription |
| `User` | `src/models/user.py` | User profile linked to Supabase Auth |
| `Membership` | `src/models/membership.py` | User-Client many-to-many with roles |
| `Campaign` | `src/models/campaign.py` | Outreach campaign configuration |
| `CampaignResource` | `src/models/campaign.py` | Campaign resource allocation |
| `CampaignSequence` | `src/models/campaign.py` | Multi-step sequence configuration |
| `Lead` | `src/models/lead.py` | Lead with ALS score and enrichment |
| `LeadPool` | `src/models/lead_pool.py` | Platform-wide lead repository |
| `LeadSocialPost` | `src/models/lead_social_post.py` | Scraped social posts for personalization |
| `GlobalSuppression` | `src/models/lead.py` | Platform-wide suppression list |
| `ClientSuppression` | `src/models/lead.py` | Client-specific suppression list |
| `DomainSuppression` | `src/models/lead.py` | Domain-level suppression |
| `Activity` | `src/models/activity.py` | Outreach activity log |
| `ActivityStats` | `src/models/activity.py` | Aggregated activity statistics |
| `ConversionPattern` | `src/models/conversion_patterns.py` | Conversion Intelligence patterns |
| `ConversionPatternHistory` | `src/models/conversion_patterns.py` | Pattern version history |
| `ResourcePool` | `src/models/resource_pool.py` | Platform resource pool (domains, phones) |
| `ClientResource` | `src/models/resource_pool.py` | Client-resource assignment |
| `ClientPersona` | `src/models/client_persona.py` | Sender identity for outreach |
| `LinkedInCredential` | `src/models/linkedin_credential.py` | LinkedIn credentials (legacy) |
| `LinkedInSeat` | `src/models/linkedin_seat.py` | LinkedIn seat for multi-seat support |
| `LinkedInConnection` | `src/models/linkedin_connection.py` | LinkedIn connection tracking |
| `ClientIntelligence` | `src/models/client_intelligence.py` | Scraped client data for SDK |
| `SDKUsageLog` | `src/models/sdk_usage_log.py` | SDK Brain usage and cost tracking |

### Pydantic Models (non-SQLAlchemy)

| Model | File | Purpose |
|-------|------|---------|
| `URLValidationResult` | `src/models/url_validation.py` | URL validation result (Pydantic) |
| `SocialProfiles` | `src/models/social_profile.py` | Social media profile aggregate (Pydantic) |
| `LinkedInCompanyProfile` | `src/models/social_profile.py` | LinkedIn company data (Pydantic) |
| `InstagramProfile` | `src/models/social_profile.py` | Instagram data (Pydantic) |
| `FacebookPageProfile` | `src/models/social_profile.py` | Facebook page data (Pydantic) |
| `GoogleBusinessProfile` | `src/models/social_profile.py` | Google Business data (Pydantic) |

### Database Connection

| Component | File | Purpose |
|-----------|------|---------|
| Engine | `src/integrations/supabase.py` | Async SQLAlchemy engine |
| Session | `src/integrations/supabase.py` | Session factory and context manager |
| Supabase Client | `src/integrations/supabase.py` | Supabase client for Auth/Realtime |

---

## Base Classes and Mixins

All SQLAlchemy models inherit from `Base` and use mixins for common functionality.

### Base Class

```python
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    type_annotation_map = {UUID: PGUUID(as_uuid=True)}

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case + plural)."""
```

### TimestampMixin

```python
class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at: Mapped[datetime]  # server_default=func.now()
    updated_at: Mapped[datetime]  # onupdate=func.now()
```

### SoftDeleteMixin (Rule 14)

```python
class SoftDeleteMixin:
    """Mixin for soft delete functionality (Rule 14)."""
    deleted_at: Mapped[datetime | None]  # NULL = not deleted

    @property
    def is_deleted(self) -> bool: ...
    def soft_delete(self) -> None: ...
    def restore(self) -> None: ...
```

### UUIDMixin

```python
class UUIDMixin:
    """Mixin for UUID primary key."""
    id: Mapped[UUID]  # server_default=func.gen_random_uuid()
```

### Standard Model Pattern

```python
class MyModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Model with UUID pk, timestamps, and soft delete."""
    __tablename__ = "my_models"

    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"))
    # ... other fields
```

---

## Enums

All enums are defined in `src/models/base.py` and match PostgreSQL ENUM types.

### Subscription & Billing

| Enum | Values | Purpose |
|------|--------|---------|
| `TierType` | `ignition`, `velocity`, `dominance` | Subscription tiers |
| `SubscriptionStatus` | `trialing`, `active`, `past_due`, `cancelled`, `paused` | Subscription state |

### Access Control

| Enum | Values | Purpose |
|------|--------|---------|
| `MembershipRole` | `owner`, `admin`, `member`, `viewer` | Team roles |
| `PermissionMode` | `autopilot`, `co_pilot`, `manual` | Automation level |

### Campaign & Lead

| Enum | Values | Purpose |
|------|--------|---------|
| `CampaignStatus` | `draft`, `active`, `paused`, `completed` | Campaign lifecycle |
| `LeadStatus` | `new`, `enriched`, `scored`, `in_sequence`, `converted`, `unsubscribed`, `bounced` | Lead lifecycle |

### Channels & Communication

| Enum | Values | Purpose |
|------|--------|---------|
| `ChannelType` | `email`, `sms`, `linkedin`, `voice`, `mail` | Outreach channels |
| `IntentType` | `meeting_request`, `interested`, `question`, `not_interested`, `unsubscribe`, `out_of_office`, `auto_reply` | Reply classification |

### System

| Enum | Values | Purpose |
|------|--------|---------|
| `WebhookEventType` | `lead.created`, `lead.enriched`, etc. | Webhook events |
| `AuditAction` | `create`, `update`, `delete`, `login`, etc. | Audit log actions |
| `PatternType` | `who`, `what`, `when`, `how` | Conversion Intelligence patterns |
| `ResourceType` | `email_domain`, `phone_number`, `linkedin_seat` | Resource pool types |
| `ResourceStatus` | `available`, `assigned`, `warming`, `retired` | Resource lifecycle |
| `HealthStatus` | `good`, `warning`, `critical` | Domain health status |

---

## Key Relationships

### Core Hierarchy

```
Client (tenant)
├── Membership ←→ User (many-to-many with roles)
├── Campaign
│   ├── Lead
│   │   ├── Activity (outreach log)
│   │   └── LeadSocialPost (scraped posts)
│   ├── CampaignResource (rate limits)
│   └── CampaignSequence (sequence steps)
├── LeadPool (lead repository)
├── ClientResource → ResourcePool
├── ClientPersona (sender identities)
├── LinkedInSeat (LinkedIn accounts)
│   └── LinkedInConnection (connection requests)
├── ConversionPattern (intelligence patterns)
└── ClientIntelligence (scraped client data)
```

### Multi-Tenancy Pattern

All tenant-scoped data includes `client_id`:

```python
# Lead belongs to a client
client_id: Mapped[UUID] = mapped_column(
    ForeignKey("clients.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
```

### Compound Uniqueness

Prevent duplicates within tenant scope:

```python
# One lead per email per client
__table_args__ = (
    UniqueConstraint("client_id", "email", name="unique_lead_per_client"),
)
```

---

## Soft Delete Pattern (Rule 14)

**Rule 14: Never use hard DELETE, always use soft delete with `deleted_at`.**

### Query Pattern

```python
# Always filter out soft-deleted records
query = select(Lead).where(Lead.deleted_at.is_(None))

# Include deleted records (admin only)
query = select(Lead)  # No filter
```

### Delete Pattern

```python
# WRONG - hard delete
await session.delete(lead)

# CORRECT - soft delete
lead.soft_delete()  # Sets deleted_at = datetime.utcnow()
await session.commit()
```

### Restore Pattern

```python
lead.restore()  # Sets deleted_at = None
await session.commit()
```

---

## Migration Strategy

### Migration Location

All migrations are in `supabase/migrations/` with numbered prefixes:

```
001_foundation.sql          # Initial schema (enums, extensions)
002_clients_users.sql       # Core tables
003_campaigns.sql           # Campaign tables
004_leads_suppression.sql   # Lead tables
...
045_auto_sequences.sql      # Latest migration
```

### Migration Rules

1. **Sequential numbering:** Use next available number (e.g., `046_feature.sql`)
2. **Idempotent:** Use `IF NOT EXISTS` for creates
3. **No data loss:** Prefer `ALTER` over `DROP/CREATE`
4. **RLS policies:** Include in migration when adding tables

### Running Migrations

```bash
# Apply migrations via Supabase CLI
supabase db push

# Or apply manually
psql $DATABASE_URL -f supabase/migrations/XXX_feature.sql
```

---

## Layer 1 Import Rules

**Models (Layer 1) can ONLY import from:**

```python
# ALLOWED
from src.exceptions import DatabaseError
from src.models.base import Base, TimestampMixin, SoftDeleteMixin

# NOT ALLOWED (violates Rule 12)
from src.engines.scorer import calculate_score      # Layer 3
from src.integrations.apollo import ApolloClient    # Layer 2
from src.orchestration.flows import run_flow        # Layer 4
```

### TYPE_CHECKING Pattern

Use `TYPE_CHECKING` for relationship type hints without import cycles:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.client import Client
    from src.models.campaign import Campaign

class Lead(Base):
    client: Mapped["Client"] = relationship(...)
```

---

## Key Rules

1. **Rule 11:** Session passed as argument to engines (not instantiated inside)
2. **Rule 12:** Models can only import from exceptions
3. **Rule 14:** Soft deletes only (`deleted_at` column)
4. **Rule 19:** Connection pool limits: pool_size=5, max_overflow=10

### Session Usage Pattern

```python
# CORRECT - Session from context manager
async with get_db_session() as session:
    result = await session.execute(query)

# CORRECT - FastAPI dependency
async def my_endpoint(db: AsyncSession = Depends(get_db)):
    ...

# WRONG - Creating session in engine
class MyEngine:
    def __init__(self):
        self.session = create_session()  # NEVER DO THIS
```

---

## Connection Configuration

### Pool Settings

```python
# In src/integrations/supabase.py
pool_size=5          # Base connections
max_overflow=10      # Burst connections
statement_cache_size=0  # Required for Supavisor
```

### Connection String

```
# Transaction Pooler (port 6543) - for application
postgresql+asyncpg://postgres.xxx:password@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres

# Direct Connection (port 5432) - for migrations
postgresql://postgres.xxx:password@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
```

---

## Cross-References

| Topic | Document |
|-------|----------|
| Import hierarchy | [`IMPORT_HIERARCHY.md`](./IMPORT_HIERARCHY.md) |
| Development rules | [`RULES.md`](./RULES.md) |
| Technology decisions | [`DECISIONS.md`](./DECISIONS.md) |
| Email distribution | [`../distribution/EMAIL.md`](../distribution/EMAIL.md) |
| LinkedIn distribution | [`../distribution/LINKEDIN.md`](../distribution/LINKEDIN.md) |
| Architecture overview | [`../ARCHITECTURE_INDEX.md`](../ARCHITECTURE_INDEX.md) |
| Gaps and TODOs | [`../TODO.md`](../TODO.md) |

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
