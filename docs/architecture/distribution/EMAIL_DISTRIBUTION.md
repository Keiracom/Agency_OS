# Email Distribution Architecture

**Status:** 🟡 PARTIALLY IMPLEMENTED
**Provider:** Salesforge (via Warmforge-warmed mailboxes)
**Rate Limit:** 50/day/domain (post-warmup)

---

## Executive Summary

Email is the primary outreach channel. Domains are warmed via Warmforge, sent via Salesforge. Gradual warmup and recipient-timezone sending are required but not fully implemented.

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Salesforge integration | ✅ | `src/integrations/salesforge.py` |
| Email engine | ✅ | `src/engines/email.py` |
| Outreach flow | ✅ | `src/orchestration/flows/outreach_flow.py` |
| Domain pool | ❌ | Not implemented (see RESOURCE_POOL.md) |
| Gradual warmup | ❌ | Binary check only (`is_warmed` flag) |
| Recipient timezone | ❌ | Uses campaign timezone |
| Threading | ✅ | In-Reply-To headers work |

---

## Architecture Flow

```
Day 0: Client Signup
    └── Resource pool assigns 3 domains (from RESOURCE_POOL.md)
        └── Domains already warmed via Warmforge

Day 1: Campaign Starts
    └── Outreach flow queries leads due for Step 1
        └── Allocator selects domain (round-robin)
            └── Warmup limiter checks domain capacity
                └── Email engine generates content (Smart Prompt)
                    └── Salesforge sends email
                        └── Activity logged
                            └── Webhook receives open/click/reply
```

---

## Rate Limiting

### Per-Domain Limits

| Warmup Day | Limit/Domain | With 3 Domains |
|------------|--------------|----------------|
| 1-3 | 5 | 15/day |
| 4-7 | 10 | 30/day |
| 8-14 | 20 | 60/day |
| 15-21 | 35 | 105/day |
| 22+ | 50 | 150/day |

### Capacity Calculation

For Velocity tier (2,250 leads):
- Email steps: 2 (Step 1 + Step 4)
- Total emails/month: ~3,800 (with attrition)
- Days to distribute: 22 working days
- Required capacity: 173/day
- 3 domains at 50/day = 150/day

**Gap:** Need 4 domains for Velocity tier, not 3.

---

## Warmup Scheduler Service

```python
# src/services/warmup_scheduler.py

from datetime import datetime
from uuid import UUID

WARMUP_SCHEDULE = [
    (0, 3, 5),     # Days 0-3: 5/day
    (4, 7, 10),    # Days 4-7: 10/day
    (8, 14, 20),   # Days 8-14: 20/day
    (15, 21, 35),  # Days 15-21: 35/day
    (22, 999, 50), # Days 22+: 50/day
]


def get_warmup_daily_limit(domain_created_at: datetime) -> int:
    """
    Get daily send limit based on domain age.

    Args:
        domain_created_at: When domain was created/warmup started

    Returns:
        Daily send limit for this domain
    """
    days_active = (datetime.utcnow() - domain_created_at).days

    for start_day, end_day, limit in WARMUP_SCHEDULE:
        if start_day <= days_active <= end_day:
            return limit

    return 50  # Default to max if past schedule


async def get_domain_capacity(
    db: AsyncSession,
    resource_pool_id: UUID,
) -> dict:
    """
    Get current capacity for a domain.

    Returns:
        {
            'domain': 'agencyxos-growth.com',
            'daily_limit': 50,
            'used_today': 23,
            'remaining': 27,
            'warmup_day': 45,
            'is_fully_warmed': True,
        }
    """
    domain = await db.get(ResourcePool, resource_pool_id)

    warmup_start = domain.warmup_started_at or domain.created_at
    warmup_day = (datetime.utcnow() - warmup_start).days
    daily_limit = get_warmup_daily_limit(warmup_start)

    # Get today's usage from activities
    used_today = await _count_domain_sends_today(db, domain.resource_value)

    return {
        'domain': domain.resource_value,
        'daily_limit': daily_limit,
        'used_today': used_today,
        'remaining': max(0, daily_limit - used_today),
        'warmup_day': warmup_day,
        'is_fully_warmed': warmup_day >= 22,
    }
```

---

## Recipient Timezone Sending

### Current (Wrong)

```python
# Uses campaign.timezone for all leads
send_time = calculate_send_time(campaign.timezone)  # Always Sydney
```

### Target (Correct)

```python
# Uses recipient's timezone detected from company HQ
recipient_tz = lead.company_hq_timezone or lead.company_hq_country_timezone or campaign.timezone

# Schedule for 9-11 AM recipient time
send_time = get_optimal_send_time(recipient_tz)
```

### Timezone Detection

Added during enrichment:

```python
# src/engines/scout.py - enrichment

COUNTRY_TIMEZONES = {
    "Australia": "Australia/Sydney",
    "New Zealand": "Pacific/Auckland",
    "United States": "America/New_York",
    "United Kingdom": "Europe/London",
    "Singapore": "Asia/Singapore",
    # ... etc
}

def detect_recipient_timezone(lead_data: dict) -> str:
    """
    Detect timezone from company location.
    """
    country = lead_data.get("company_hq_country")
    state = lead_data.get("company_hq_state")

    # Australia has multiple timezones
    if country == "Australia" and state:
        state_tz = {
            "Western Australia": "Australia/Perth",
            "Queensland": "Australia/Brisbane",
            "South Australia": "Australia/Adelaide",
        }
        return state_tz.get(state, "Australia/Sydney")

    return COUNTRY_TIMEZONES.get(country, "Australia/Sydney")
```

---

## Threading Architecture

### Follow-Up Emails

Step 4 (Day 8) must thread with Step 1:

```python
# When sending Step 4
step_1_activity = await get_step_activity(lead_id, step=1, channel='email')

if step_1_activity and step_1_activity.message_id:
    # Thread under original email
    in_reply_to = step_1_activity.message_id
    references = [step_1_activity.message_id]
    subject = f"Re: {step_1_activity.subject}"
else:
    # No threading if Step 1 not found
    in_reply_to = None
    references = None
    subject = generate_new_subject()
```

### Database Fields

```sql
-- activities table has threading columns
message_id TEXT,        -- Our Message-ID
in_reply_to TEXT,       -- Parent Message-ID
thread_id TEXT,         -- Thread grouping
```

---

## Bounce/Complaint Handling

### Webhooks

Salesforge sends webhooks for:
- `email.delivered`
- `email.opened`
- `email.clicked`
- `email.bounced`
- `email.complained`
- `email.unsubscribed`

### Bounce Handling

```python
# src/services/email_events_service.py

async def handle_bounce(db: AsyncSession, event: dict):
    """
    Handle email bounce.

    1. Mark lead as bounced in lead_pool
    2. Add to suppression_list
    3. Stop sequence for this lead
    4. Track for domain health
    """
    email = event['recipient']
    lead = await get_lead_by_email(db, email)

    if lead:
        # Update lead status
        lead.pool_status = 'bounced'

        # Add to suppression
        await add_to_suppression(db, email, 'bounce', lead.client_id)

    # Track domain health
    domain = event['sender'].split('@')[-1]
    await track_domain_bounce(db, domain)
```

### Domain Health Monitoring

```python
async def check_domain_health(db: AsyncSession, domain: str) -> dict:
    """
    Check domain health metrics.

    Returns:
        {
            'domain': 'agencyxos-growth.com',
            'sends_30d': 1500,
            'bounces_30d': 45,
            'bounce_rate': 0.03,
            'complaints_30d': 2,
            'complaint_rate': 0.001,
            'health': 'good',  # good, warning, critical
        }
    """
    # If bounce_rate > 5%, reduce limits
    # If complaint_rate > 0.1%, pause domain
```

---

## Files Involved

| File | Purpose | Status |
|------|---------|--------|
| `src/integrations/salesforge.py` | API client | ✅ |
| `src/engines/email.py` | Send logic | ✅ |
| `src/engines/smart_prompts.py` | Content generation | ✅ |
| `src/services/email_events_service.py` | Webhook handling | ✅ |
| `src/services/warmup_scheduler.py` | Warmup limits | ❌ CREATE |
| `src/orchestration/flows/outreach_flow.py` | Batch sending | 🟡 Needs warmup integration |

---

## Verification Checklist

- [x] Salesforge integration works
- [x] Email engine sends correctly
- [x] Threading headers work
- [x] Webhooks received
- [x] Bounce handling works
- [ ] Domain pool allocation (RESOURCE_POOL.md)
- [ ] Gradual warmup limits enforced
- [ ] Recipient timezone detection
- [ ] 9-11 AM send window enforced
- [ ] Domain health monitoring
- [ ] Capacity alerts

---

## Configuration

### Environment Variables

```bash
SALESFORGE_API_KEY=sf_live_xxx
SALESFORGE_API_URL=https://api.salesforge.ai/public/v2
```

### Settings

```python
# src/config/settings.py

# Email limits
email_max_per_domain_day: int = 50
email_warmup_enabled: bool = True

# Send window (recipient timezone)
email_send_window_start: int = 9   # 9 AM
email_send_window_end: int = 11    # 11 AM
email_weekdays_only: bool = True
```
