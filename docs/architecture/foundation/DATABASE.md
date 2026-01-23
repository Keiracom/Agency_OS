# Database Layer — Agency OS

**Purpose:** Supabase PostgreSQL with SQLAlchemy async ORM for multi-tenant lead generation SaaS
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-23

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

### SQLAlchemy Models (24 files)

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
| `CampaignSuggestion` | `src/models/campaign_suggestion.py` | AI-driven campaign suggestions from CIS |
| `CampaignSuggestionHistory` | `src/models/campaign_suggestion.py` | Suggestion status change audit trail |
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
| `LinkedInCredential` | `src/models/linkedin_credential.py` | LinkedIn credentials for HeyReach |
| `LinkedInSeat` | `src/models/linkedin_seat.py` | LinkedIn seat for multi-seat support |
| `LinkedInConnection` | `src/models/linkedin_connection.py` | LinkedIn connection tracking |
| `ClientIntelligence` | `src/models/client_intelligence.py` | Scraped client data for SDK personalization |
| `SDKUsageLog` | `src/models/sdk_usage_log.py` | SDK Brain usage and cost tracking |
| `DigestLog` | `src/models/digest_log.py` | Daily/weekly digest delivery tracking |
| `IcpRefinementLog` | `src/models/icp_refinement_log.py` | WHO pattern refinement audit trail |

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

Most enums are defined in `src/models/base.py`, with domain-specific enums in their respective model files. All enums match PostgreSQL ENUM types.

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
| `IntentType` | `meeting_request`, `interested`, `question`, `not_interested`, `unsubscribe`, `out_of_office`, `auto_reply`, `referral`, `wrong_person`, `angry_or_complaint` | Reply intent classification |

### System

| Enum | Values | Purpose |
|------|--------|---------|
| `WebhookEventType` | `lead.created`, `lead.enriched`, `lead.scored`, `lead.converted`, `campaign.started`, `campaign.paused`, `campaign.completed`, `reply.received`, `meeting.booked` | Webhook events |
| `AuditAction` | `create`, `update`, `delete`, `login`, `logout`, `export`, `import`, `webhook_sent`, `webhook_failed` | Audit log actions |
| `PatternType` | `who`, `what`, `when`, `how` | Conversion Intelligence patterns |
| `ResourceType` | `email_domain`, `phone_number`, `linkedin_seat` | Resource pool types |
| `ResourceStatus` | `available`, `assigned`, `warming`, `retired` | Resource lifecycle |
| `HealthStatus` | `good`, `warning`, `critical` | Domain health status |

### Campaign Suggestions

| Enum | Values | Purpose |
|------|--------|---------|
| `SuggestionType` | `create_campaign`, `pause_campaign`, `adjust_allocation`, `refine_targeting`, `change_channel_mix`, `update_content`, `adjust_timing` | Types of CIS-driven campaign suggestions |
| `SuggestionStatus` | `pending`, `approved`, `rejected`, `applied`, `expired` | Suggestion lifecycle status |

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

## Model Detail: CampaignSuggestion

**Table:** `campaign_suggestions`
**Purpose:** AI-driven campaign suggestions from Conversion Intelligence System (CIS) pattern analysis

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `client_id` | UUID | FK, NOT NULL, indexed | Reference to owning client |
| `campaign_id` | UUID | FK, nullable | Target campaign (NULL for create suggestions) |
| `suggestion_type` | TEXT | NOT NULL | Type: create_campaign, pause_campaign, adjust_allocation, etc. |
| `status` | TEXT | NOT NULL, default 'pending' | Lifecycle: pending, approved, rejected, applied, expired |
| `title` | TEXT | NOT NULL | Human-readable suggestion title |
| `description` | TEXT | NOT NULL | Detailed suggestion description |
| `rationale` | JSONB | NOT NULL | Pattern-based reasoning |
| `recommended_action` | JSONB | NOT NULL | Specific action to take |
| `confidence` | NUMERIC(3,2) | CHECK 0-1 | CIS confidence score |
| `priority` | INTEGER | CHECK 1-100, default 50 | Priority ranking |
| `pattern_types` | TEXT[] | NOT NULL | Pattern sources (who, what, when, how) |
| `pattern_snapshot` | JSONB | nullable | Frozen pattern data at suggestion time |
| `current_metrics` | JSONB | nullable | Metrics at time of suggestion |
| `projected_improvement` | JSONB | nullable | Expected improvement if applied |
| `generated_at` | TIMESTAMP | NOT NULL, default NOW() | When CIS generated suggestion |
| `reviewed_at` | TIMESTAMP | nullable | When client reviewed |
| `reviewed_by` | UUID | nullable | User who reviewed |
| `applied_at` | TIMESTAMP | nullable | When suggestion was applied |
| `expires_at` | TIMESTAMP | NOT NULL | Auto-expire after 14 days |
| `client_notes` | TEXT | nullable | Client feedback notes |
| `rejection_reason` | TEXT | nullable | Why suggestion was rejected |
| `created_at` | TIMESTAMP | NOT NULL | Record creation time |
| `updated_at` | TIMESTAMP | NOT NULL | Last update time |
| `deleted_at` | TIMESTAMP | nullable | Soft delete marker |

**Relationships:**
- `belongs_to`: Client, Campaign
- `has_many`: CampaignSuggestionHistory

**Indexes:**
- `idx_campaign_suggestions_pending` (client_id, status) WHERE status='pending' AND deleted_at IS NULL

---

## Model Detail: CampaignSuggestionHistory

**Table:** `campaign_suggestion_history`
**Purpose:** Audit trail for suggestion status changes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `suggestion_id` | UUID | FK, NOT NULL, indexed | Reference to suggestion |
| `old_status` | TEXT | nullable | Previous status |
| `new_status` | TEXT | NOT NULL | New status |
| `changed_by` | UUID | nullable | User who made change |
| `change_reason` | TEXT | nullable | Reason for change |
| `changed_at` | TIMESTAMP | NOT NULL, default NOW() | When change occurred |

**Relationships:**
- `belongs_to`: CampaignSuggestion

---

## Model Detail: DigestLog

**Table:** `digest_logs`
**Purpose:** Track daily/weekly digest emails sent to clients (Phase H, Item 44)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `client_id` | UUID | FK, NOT NULL | Reference to client |
| `digest_date` | DATE | NOT NULL | Date the digest covers |
| `digest_type` | TEXT | NOT NULL, default 'daily' | Type: daily, weekly |
| `recipients` | JSONB | NOT NULL | List of email addresses |
| `metrics_snapshot` | JSONB | NOT NULL | Metrics at time of digest |
| `content_summary` | JSONB | NOT NULL | What content was sent |
| `status` | TEXT | NOT NULL, default 'pending' | Delivery status: pending, sent, failed |
| `sent_at` | TIMESTAMP | nullable | When email was sent |
| `error_message` | TEXT | nullable | Error if send failed |
| `opened_at` | TIMESTAMP | nullable | When recipient opened |
| `clicked_at` | TIMESTAMP | nullable | When recipient clicked |
| `created_at` | TIMESTAMP | NOT NULL | Record creation time |
| `updated_at` | TIMESTAMP | NOT NULL | Last update time |

**Relationships:**
- `belongs_to`: Client

**Properties:**
- `is_sent`: Check if digest was successfully sent
- `was_opened`: Check if digest was opened

---

## Model Detail: IcpRefinementLog

**Table:** `icp_refinement_log`
**Purpose:** Audit trail for WHO pattern refinements applied to ICP searches (Phase 19)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `client_id` | UUID | FK, NOT NULL, indexed | Reference to client |
| `pattern_id` | UUID | FK, NOT NULL | Reference to WHO pattern used |
| `base_criteria` | JSONB | NOT NULL | Original ICP criteria before refinement |
| `refined_criteria` | JSONB | NOT NULL | Final criteria after WHO refinement |
| `refinements_applied` | JSONB | NOT NULL | Array of refinement actions taken |
| `confidence` | FLOAT | NOT NULL | WHO pattern confidence at refinement time |
| `applied_at` | TIMESTAMP | NOT NULL | When refinement was applied |
| `deleted_at` | TIMESTAMP | nullable | Soft delete marker |
| `created_at` | TIMESTAMP | NOT NULL | Record creation time |
| `updated_at` | TIMESTAMP | NOT NULL | Last update time |

**Relationships:**
- `belongs_to`: Client, ConversionPattern

**Properties:**
- `refinement_count`: Number of refinements applied
- `fields_refined`: List of field names that were refined

---

## Model Detail: LinkedInCredential

**Table:** `client_linkedin_credentials`
**Purpose:** LinkedIn credential storage for HeyReach automation (Phase 24H)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `client_id` | UUID | FK, NOT NULL, UNIQUE, indexed | Reference to client (one per client) |
| `linkedin_email_encrypted` | TEXT | NOT NULL | AES-256 encrypted LinkedIn email |
| `linkedin_password_encrypted` | TEXT | NOT NULL | AES-256 encrypted LinkedIn password |
| `connection_status` | VARCHAR(50) | NOT NULL, default 'pending' | Status: pending, connecting, awaiting_2fa, connected, failed, disconnected |
| `heyreach_sender_id` | VARCHAR(255) | nullable | HeyReach sender ID after connection |
| `heyreach_account_id` | VARCHAR(255) | nullable | HeyReach account ID |
| `linkedin_profile_url` | TEXT | nullable | LinkedIn profile URL |
| `linkedin_profile_name` | VARCHAR(255) | nullable | LinkedIn display name |
| `linkedin_headline` | TEXT | nullable | LinkedIn headline |
| `linkedin_connection_count` | INTEGER | nullable | Number of LinkedIn connections |
| `two_fa_method` | VARCHAR(50) | nullable | 2FA method: sms, email, authenticator |
| `two_fa_requested_at` | TIMESTAMP | nullable | When 2FA was requested |
| `last_error` | TEXT | nullable | Last error message |
| `error_count` | INTEGER | NOT NULL, default 0 | Number of connection errors |
| `last_error_at` | TIMESTAMP | nullable | When last error occurred |
| `connected_at` | TIMESTAMP | nullable | When connection was established |
| `disconnected_at` | TIMESTAMP | nullable | When account was disconnected |
| `created_at` | TIMESTAMP | NOT NULL | Record creation time |
| `updated_at` | TIMESTAMP | NOT NULL | Last update time |

**Relationships:**
- `belongs_to`: Client (one-to-one)

**Properties:**
- `is_connected`: Check if LinkedIn is successfully connected
- `is_awaiting_2fa`: Check if waiting for 2FA verification
- `has_error`: Check if connection has failed

---

## Model Detail: ClientIntelligence

**Table:** `client_intelligence`
**Purpose:** Scraped client data for SDK personalization (multi-source aggregation)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `client_id` | TEXT | NOT NULL, indexed | Reference to client |
| **Website Data** | | | |
| `website_tagline` | TEXT | nullable | Company tagline from website |
| `website_value_prop` | TEXT | nullable | Value proposition |
| `website_services` | JSONB | nullable | Array of {name, description} |
| `website_case_studies` | JSONB | nullable | Array of case study objects |
| `website_testimonials` | JSONB | nullable | Array of testimonial objects |
| `website_team_bios` | JSONB | nullable | Array of team member objects |
| `website_blog_topics` | TEXT[] | nullable | Common blog topics |
| `website_scraped_at` | TIMESTAMP | nullable | When website was scraped |
| **LinkedIn Data** | | | |
| `linkedin_url` | TEXT | nullable | Company LinkedIn URL |
| `linkedin_follower_count` | INTEGER | nullable | LinkedIn follower count |
| `linkedin_employee_count` | INTEGER | nullable | Employee count from LinkedIn |
| `linkedin_description` | TEXT | nullable | Company description |
| `linkedin_specialties` | TEXT[] | nullable | Company specialties |
| `linkedin_recent_posts` | JSONB | nullable | Recent LinkedIn posts |
| `linkedin_scraped_at` | TIMESTAMP | nullable | When LinkedIn was scraped |
| **Twitter/X Data** | | | |
| `twitter_handle` | TEXT | nullable | Twitter handle |
| `twitter_follower_count` | INTEGER | nullable | Follower count |
| `twitter_bio` | TEXT | nullable | Bio |
| `twitter_recent_posts` | JSONB | nullable | Recent tweets |
| `twitter_topics` | TEXT[] | nullable | Common topics |
| `twitter_scraped_at` | TIMESTAMP | nullable | When Twitter was scraped |
| **Facebook Data** | | | |
| `facebook_url` | TEXT | nullable | Facebook page URL |
| `facebook_follower_count` | INTEGER | nullable | Follower count |
| `facebook_about` | TEXT | nullable | About section |
| `facebook_recent_posts` | JSONB | nullable | Recent posts |
| `facebook_scraped_at` | TIMESTAMP | nullable | When Facebook was scraped |
| **Instagram Data** | | | |
| `instagram_handle` | TEXT | nullable | Instagram handle |
| `instagram_follower_count` | INTEGER | nullable | Follower count |
| `instagram_bio` | TEXT | nullable | Bio |
| `instagram_recent_posts` | JSONB | nullable | Recent posts |
| `instagram_scraped_at` | TIMESTAMP | nullable | When Instagram was scraped |
| **Review Platform Data** | | | |
| `g2_url`, `g2_rating`, `g2_review_count`, `g2_top_reviews`, `g2_ai_summary` | Various | nullable | G2 review data |
| `capterra_url`, `capterra_rating`, `capterra_review_count`, `capterra_top_reviews` | Various | nullable | Capterra review data |
| `trustpilot_url`, `trustpilot_rating`, `trustpilot_review_count`, `trustpilot_top_reviews` | Various | nullable | Trustpilot review data |
| `google_business_url`, `google_rating`, `google_review_count`, `google_top_reviews` | Various | nullable | Google Business review data |
| **Extracted Proof Points** | | | |
| `proof_metrics` | JSONB | nullable | Array of {metric, context, source} |
| `proof_clients` | TEXT[] | nullable | Notable client names |
| `proof_industries` | TEXT[] | nullable | Industries served |
| `common_pain_points` | TEXT[] | nullable | Common pain points addressed |
| `differentiators` | TEXT[] | nullable | Key differentiators |
| **Metadata** | | | |
| `total_scrape_cost_aud` | DECIMAL(10,4) | nullable | Total scraping cost in AUD |
| `last_full_scrape_at` | TIMESTAMP | nullable | When full scrape completed |
| `scrape_errors` | JSONB | nullable | Array of scrape error objects |
| `created_at` | TIMESTAMP | NOT NULL | Record creation time |
| `updated_at` | TIMESTAMP | NOT NULL | Last update time |
| `deleted_at` | TIMESTAMP | nullable | Soft delete marker |

**Properties:**
- `has_website_data`: Check if website data has been scraped
- `has_social_data`: Check if any social media data has been scraped
- `has_review_data`: Check if any review platform data has been scraped
- `needs_refresh`: Check if data is stale (older than 30 days)

**Methods:**
- `get_proof_summary()`: Get a summary of proof points for SDK agents

---

## Model Detail: SDKUsageLog

**Table:** `sdk_usage_log`
**Purpose:** Track SDK Brain usage for cost control and analytics

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `client_id` | UUID | FK, NOT NULL, indexed | Reference to client |
| `lead_id` | UUID | FK, nullable, indexed | Reference to lead (if applicable) |
| `campaign_id` | UUID | FK, nullable | Reference to campaign (if applicable) |
| `user_id` | UUID | FK, nullable | Reference to user (if applicable) |
| `agent_type` | VARCHAR(50) | NOT NULL, indexed | Type: icp_extraction, enrichment, email, voice_kb, objection |
| `model_used` | VARCHAR(100) | NOT NULL | Model ID: claude-sonnet-4-20250514, etc. |
| `input_tokens` | INTEGER | NOT NULL, default 0 | Input tokens used |
| `output_tokens` | INTEGER | NOT NULL, default 0 | Output tokens used |
| `cached_tokens` | INTEGER | NOT NULL, default 0 | Cached tokens (prompt caching) |
| `cost_aud` | NUMERIC(10,6) | NOT NULL, default 0 | Total cost in Australian dollars |
| `turns_used` | INTEGER | NOT NULL, default 1 | Number of agent turns |
| `duration_ms` | INTEGER | NOT NULL, default 0 | Execution duration in milliseconds |
| `tool_calls` | JSONB | NOT NULL | Array of tool calls made |
| `success` | BOOLEAN | NOT NULL, default true | Whether execution succeeded |
| `error_message` | TEXT | nullable | Error message if failed |
| `created_at` | TIMESTAMP | NOT NULL | When execution occurred |
| `deleted_at` | TIMESTAMP | nullable | Soft delete marker |

**Relationships:**
- `belongs_to`: Client, Lead (optional), Campaign (optional), User (optional)

**Properties:**
- `total_tokens`: Total tokens used (input + output)
- `cache_hit_rate`: Percentage of input tokens that were cached

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
