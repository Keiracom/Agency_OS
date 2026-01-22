# Campaign Lifecycle — Agency OS

**Purpose:** Defines campaign structure, lifecycle states, AI suggestions, lead allocation, and sequence generation for multi-channel outreach.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-21

---

## Overview

A **Campaign** in Agency OS represents a targeted outreach initiative for a client. Campaigns define:
- **Target audience** - Industries, titles, company sizes, locations
- **Channel mix** - Allocation percentages across email, SMS, LinkedIn, voice, and mail
- **Sequence** - Multi-step outreach cadence with timing
- **Scheduling** - Working hours, days, timezone, daily limits

Campaigns can be **AI-suggested** (auto-generated based on client ICP during onboarding) or **custom** (manually created by the client).

### Lifecycle States

| Status | Description | Transitions To |
|--------|-------------|----------------|
| `DRAFT` | Campaign created but not active | `ACTIVE` |
| `ACTIVE` | Campaign running outreach | `PAUSED`, `COMPLETED` |
| `PAUSED` | Campaign temporarily stopped | `ACTIVE`, `COMPLETED` |
| `COMPLETED` | Campaign finished (terminal) | None |

---

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| Campaign Model | `src/models/campaign.py` | SQLAlchemy model with all fields |
| Campaign API | `src/api/routes/campaigns.py` | CRUD, status, sequences, resources |
| Activation Flow | `src/orchestration/flows/campaign_flow.py` | Prefect flow for campaign activation |
| AI Suggester | `src/engines/campaign_suggester.py` | Claude-powered campaign suggestions |
| Lead Allocator | `src/services/lead_allocator_service.py` | Assign leads from pool to campaigns |
| Sequence Generator | `src/services/sequence_generator_service.py` | Auto-generate default 5-step sequence |
| Tier Config | `src/config/tiers.py` | Campaign slot limits per tier |

---

## Campaign Lifecycle

### 1. Creation (DRAFT)

Campaigns are created in `DRAFT` status. Two creation paths:

**A. Manual Creation (Custom Campaign)**
```
POST /clients/{client_id}/campaigns
```
- Client provides name, description, targets, channel allocation
- Auto-generates default 5-step sequence via `SequenceGeneratorService`
- Sets `uses_default_sequence=True`

**B. AI-Suggested Creation (Onboarding)**
```
GET  /clients/{client_id}/campaigns/suggestions    # Generate suggestions
POST /clients/{client_id}/campaigns/suggestions/create  # Create from suggestions
```
- Analyzes client ICP via Claude AI
- Suggests optimal segments with lead allocation percentages
- Creates campaigns with `campaign_type=ai_suggested`

### 2. Activation (DRAFT -> ACTIVE)

Activation triggers the Prefect flow `campaign_activation`:

```python
# src/orchestration/flows/campaign_flow.py
@flow(name="campaign_activation")
async def campaign_activation_flow(campaign_id):
    # 1. Validate campaign configuration
    campaign_data = await validate_campaign_task(campaign_id)

    # 2. JIT validate client (subscription + credits)
    client_data = await validate_client_status_task(client_id)

    # 3. Activate campaign (status -> ACTIVE)
    await activate_campaign_task(campaign_id)

    # 4. Get campaign leads
    leads_data = await get_campaign_leads_task(campaign_id)

    # 5. Trigger enrichment for new leads
    await trigger_enrichment_task(lead_ids, campaign_id)
```

**Validation Requirements:**
- Campaign must have a name
- Client subscription must be `active` or `trialing`
- Client must have credits remaining > 0

### 3. Pausing (ACTIVE -> PAUSED)

```
POST /clients/{client_id}/campaigns/{campaign_id}/pause
```
- Stops outreach while preserving state
- Leads remain assigned to campaign
- Can be resumed later

### 4. Completion (ACTIVE/PAUSED -> COMPLETED)

```
PATCH /clients/{client_id}/campaigns/{campaign_id}/status
{"status": "completed"}
```
- Terminal state - cannot transition out
- All leads remain for reporting
- Campaign no longer processes outreach

---

## AI Campaign Suggestions

The `CampaignSuggesterEngine` uses Claude AI to analyze client ICP and suggest optimal campaign segments.

### How It Works

```python
# src/engines/campaign_suggester.py

1. Load client ICP data:
   - icp_industries, icp_titles, icp_company_sizes
   - icp_locations, icp_pain_points, icp_keywords

2. Get tier campaign limits:
   ai_slots, custom_slots = get_campaign_slots(tier_name)
   # Ignition: 3 AI + 2 custom
   # Velocity: 6 AI + 4 custom
   # Dominance: 12 AI + 8 custom

3. Generate prompt with client context

4. Call Claude (claude-3-5-haiku-latest):
   - Returns JSON array of campaign suggestions
   - Each with name, targets, allocation %, reasoning

5. Validate allocations sum to 100%
```

### Suggestion Output Structure

```python
@dataclass
class CampaignSuggestion:
    name: str                    # "C-Suite Tech Leaders"
    description: str             # "CTOs and CIOs at mid-market SaaS"
    target_industries: list[str] # ["SaaS", "Technology"]
    target_titles: list[str]     # ["CTO", "CIO", "VP Engineering"]
    target_company_sizes: list[str]  # ["51-200", "201-500"]
    target_locations: list[str]  # ["Australia"]
    lead_allocation_pct: int     # 40
    ai_reasoning: str            # "Highest decision-making authority..."
    priority: int                # 1 = highest
```

### Campaign Slots by Tier

| Tier | AI-Suggested | Custom | Total |
|------|--------------|--------|-------|
| Ignition | 3 | 2 | 5 |
| Velocity | 6 | 4 | 10 |
| Dominance | 12 | 8 | 20 |

---

## Lead Allocation

The `LeadAllocatorService` handles assigning leads from the platform pool to campaigns.

### Allocation Flow

```python
# src/services/lead_allocator_service.py

async def allocate_leads(client_id, icp_criteria, count, campaign_id):
    # 1. Build ICP matching query
    conditions = ["lp.pool_status = 'available'"]

    if icp_criteria.get("industries"):
        conditions.append("lp.company_industry = ANY(:industries)")

    if icp_criteria.get("titles"):
        conditions.append("lp.title ILIKE '%' || :title || '%'")

    # ... more criteria

    # 2. Filter for unassigned leads
    conditions.append("lp.client_id IS NULL")

    # 3. Find and lock matching leads
    SELECT ... FROM lead_pool
    WHERE {conditions}
    ORDER BY enrichment_confidence DESC
    FOR UPDATE SKIP LOCKED
    LIMIT :count

    # 4. Assign to client/campaign
    UPDATE lead_pool
    SET client_id = :client_id,
        campaign_id = :campaign_id,
        pool_status = 'assigned'
```

### ICP Matching Criteria

| Criterion | Field Matched |
|-----------|---------------|
| `industries` | `company_industry` |
| `countries` | `company_country` |
| `employee_min/max` | `company_employee_count` |
| `seniorities` | `seniority` |
| `titles` | `title` (ILIKE pattern) |
| `technologies` | `company_technologies` (array overlap) |
| `email_status` | `email_status` (default: "verified") |

### Exclusive Assignment

- Each lead can only belong to ONE client at a time
- `FOR UPDATE SKIP LOCKED` prevents race conditions
- `lead_pool.client_id IS NULL` ensures availability
- Converted leads stay with client forever

---

## Sequence Generation

The `SequenceGeneratorService` creates the default 5-step outreach sequence for new campaigns.

### Default 5-Step Sequence

| Step | Day | Channel | Purpose | Skip If |
|------|-----|---------|---------|---------|
| 1 | 0 | Email | Introduction | - |
| 2 | 3 | Voice | Connect | `phone_missing` |
| 3 | 5 | LinkedIn | Connect | `linkedin_url_missing` |
| 4 | 8 | Email | Value-add | - |
| 5 | 12 | SMS | Breakup | `phone_missing` |

### Sequence Model

```python
class CampaignSequence(Base):
    campaign_id: UUID
    step_number: int          # 1-20
    channel: ChannelType      # EMAIL, SMS, LINKEDIN, VOICE, MAIL
    delay_days: int           # Days from previous step
    subject_template: str     # For email only
    body_template: str        # {{SMART_PROMPT}} placeholder
    skip_if_replied: bool     # Stop sequence on reply
    skip_if_bounced: bool     # Skip email steps on bounce
    purpose: str              # intro, connect, value_add, breakup
    skip_if: str              # phone_missing, linkedin_url_missing
```

### Template Placeholders

- `{{SMART_PROMPT}}` - AI-generated personalized content
- `{{SMART_PROMPT_SUBJECT}}` - AI-generated email subject

### Channel Availability

The sequence generator adapts based on client resources:

```python
def get_available_channels_for_client(
    has_email_domain: bool,  # Email always first
    has_phone_number: bool,  # Voice + SMS
    has_linkedin_seat: bool, # LinkedIn
) -> list[ChannelType]
```

---

## Campaign Metrics

Campaigns track denormalized metrics for performance:

| Metric | Description |
|--------|-------------|
| `total_leads` | Total leads assigned to campaign |
| `leads_contacted` | Leads with at least 1 touch |
| `leads_replied` | Leads who responded |
| `leads_converted` | Leads marked as converted |
| `reply_rate` | `(leads_replied / leads_contacted) * 100` |
| `conversion_rate` | `(leads_converted / leads_contacted) * 100` |

---

## Key Rules

### Channel Allocation

- **Must sum to 100%** - Enforced by database constraint
- Allocation determines channel distribution across leads
- Example: 60% email, 20% LinkedIn, 20% voice

```python
__table_args__ = (
    CheckConstraint(
        "allocation_email + allocation_sms + allocation_linkedin + "
        "allocation_voice + allocation_mail = 100",
        name="valid_allocation",
    ),
)
```

### Daily Limits

- Default: 50 outreach actions/day
- Max: 500 (enforced by constraint)
- Configured per campaign

```python
daily_limit: int = Field(50, ge=1, le=500)
```

### Scheduling

- Campaigns respect working hours (default: 9 AM - 5 PM)
- Work days configurable (default: Mon-Fri, [1,2,3,4,5])
- Timezone-aware (default: Australia/Sydney)

### Status Transitions

Valid transitions are enforced in API:

```python
valid_transitions = {
    DRAFT: [ACTIVE],
    ACTIVE: [PAUSED, COMPLETED],
    PAUSED: [ACTIVE, COMPLETED],
    COMPLETED: [],  # Terminal
}
```

### Multi-Tenancy

- All campaign queries filter by `client_id`
- Campaigns soft-deleted via `deleted_at` timestamp
- No hard deletes (Rule 14)

---

## Configuration

### Campaign Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | Required | Campaign name |
| `status` | enum | `DRAFT` | Lifecycle status |
| `campaign_type` | str | `custom` | `ai_suggested` or `custom` |
| `lead_allocation_pct` | int | 100 | % of client leads |
| `permission_mode` | enum | None | Override client default |
| `daily_limit` | int | 50 | Max daily outreach |
| `timezone` | str | `Australia/Sydney` | Scheduling timezone |
| `work_hours_start` | time | 09:00 | Start of work hours |
| `work_hours_end` | time | 17:00 | End of work hours |
| `work_days` | list[int] | [1,2,3,4,5] | Mon-Fri |
| `sequence_steps` | int | 5 | Number of sequence steps |
| `sequence_delay_days` | int | 3 | Default delay between steps |
| `uses_default_sequence` | bool | True | Use auto-generated sequence |

### Target Fields

| Field | Type | Description |
|-------|------|-------------|
| `target_industries` | list[str] | Target industries |
| `target_titles` | list[str] | Target job titles |
| `target_company_sizes` | list[str] | Company size ranges |
| `target_locations` | list[str] | Geographic targets |

---

## Cross-References

| Topic | Document |
|-------|----------|
| Lead Scoring (ALS) | [`SCORING.md`](./SCORING.md) |
| Tier Limits | [`TIERS_AND_BILLING.md`](./TIERS_AND_BILLING.md) |
| Email Distribution | [`../distribution/EMAIL.md`](../distribution/EMAIL.md) |
| SMS Distribution | [`../distribution/SMS.md`](../distribution/SMS.md) |
| LinkedIn Distribution | [`../distribution/LINKEDIN.md`](../distribution/LINKEDIN.md) |
| Voice Distribution | [`../distribution/VOICE.md`](../distribution/VOICE.md) |
| Lead Pool Architecture | [`../flows/LEAD_POOL.md`](../flows/LEAD_POOL.md) (if exists) |
| Onboarding Flow | [`../flows/ONBOARDING.md`](../flows/ONBOARDING.md) (if exists) |

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
