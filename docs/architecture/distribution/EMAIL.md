# Email Distribution Architecture

**Status:** ✅ IMPLEMENTED
**Provider:** Salesforge (via Warmforge-warmed mailboxes)
**Rate Limit:** 50/day/domain (fully warmed)
**Last Updated:** January 22, 2026

---

## Executive Summary

Email is the primary outreach channel. Domains are pre-warmed via Warmforge before client assignment (see RESOURCE_POOL.md). Clients receive fully warmed domains at 50/day capacity from day 1.

**Key Principle:** Send window (9-11 AM) is based on optimal open rates, not volume fitting. If capacity is insufficient, add domains — never widen the window.

---

## CEO Decisions (2026-01-20)

| Decision | Choice |
|----------|--------|
| Send window | **9-11 AM recipient local time** (optimal open rates) |
| Capacity strategy | **Add domains** if insufficient, never widen window |
| Timezone granularity | **State-level for Australia** |
| Domain health - Good | <2% bounce, <0.05% complaint → 50/day |
| Domain health - Warning | 2-5% bounce, 0.05-0.1% complaint → 35/day + alert |
| Domain health - Critical | >5% bounce, >0.1% complaint → pause + alert |
| **Sender identity** | **Neutral pool domains + display name/signature branding** |
| Display name format | `{First} from {Company}` (e.g., "John from Sparro") |
| Pool domain naming | Neutral names (e.g., `outreach-mail.com`), not agency-branded |

---

## Sender Identity Architecture

### Why Not Aliases?

Email aliases (showing client's domain while sending from ours) **damage deliverability**. SPF/DKIM/DMARC alignment fails when the From header domain doesn't match the sending server. Spam filters detect this inconsistency.

**Solution:** Use neutral pool domains with client branding via display name + signature.

### What Recipients See

**Inbox view:**
```
John from Sparro          Quick question about your Q2 pipeline
```

**Full email:**
```
From: "John from Sparro" <john.s@outreach-mail.com>
Subject: Quick question about your Q2 pipeline

Hi Sarah,

[Personalized content written in client's voice]

—
John Smith
Business Development Manager

Sparro | Performance Marketing That Delivers
📞 1300 123 456 | 🌐 sparro.com.au
📍 Sydney, Australia
```

### Pool Domain Naming

| Type | Example | Purpose |
|------|---------|---------|
| ❌ Agency-branded | agencyxos-growth.com | Reveals agency, not client |
| ✅ Neutral | outreach-mail.com | Professional, doesn't distract |
| ✅ Neutral | businessreach.io | Generic, trustworthy |

### Persona System

Each client has multiple **personas** (sender identities):

```python
# client_personas table
{
    "client_id": "uuid",
    "persona_name": "John Smith",
    "persona_first_name": "John",
    "persona_title": "Business Development Manager",
    "persona_email_prefix": "john.s",  # → john.s@outreach-mail.com
    "persona_calendly_url": "https://calendly.com/john-sparro/intro",
}
```

**Personas per tier:**
| Tier | Personas |
|------|----------|
| Ignition | 2-3 |
| Velocity | 3-4 |
| Dominance | 4-6 |

### Client Branding Data

Collected during onboarding:

```python
# client.branding (JSONB)
{
    "company_name": "Sparro",
    "tagline": "Performance Marketing That Delivers",
    "website": "https://sparro.com.au",
    "phone": "1300 123 456",
    "address": "Sydney, Australia",
    "logo_url": "https://sparro.com.au/logo.png",
    "linkedin_url": "https://linkedin.com/company/sparro",
    "calendly_url": "https://calendly.com/sparro/intro"
}
```

### Signature Generation

```python
# src/engines/signature.py

def generate_signature(client: Client, persona: Persona) -> str:
    """Generate signature from client branding + persona."""
    lines = [
        "—",
        persona.name,
        persona.title,
        "",
        client.branding.company_name,
    ]

    if client.branding.tagline:
        lines.append(client.branding.tagline)

    contact_parts = []
    if client.branding.phone:
        contact_parts.append(f"📞 {client.branding.phone}")
    if client.branding.website:
        domain = client.branding.website.replace("https://", "").replace("http://", "")
        contact_parts.append(f"🌐 {domain}")

    if contact_parts:
        lines.append(" | ".join(contact_parts))

    if client.branding.address:
        lines.append(f"📍 {client.branding.address}")

    return "\n".join(lines)
```

### Display Name Generation

```python
def get_display_name(client: Client, persona: Persona) -> str:
    """Generate From display name."""
    return f"{persona.first_name} from {client.branding.company_name}"
```

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Salesforge integration | ✅ | `src/integrations/salesforge.py` |
| Email engine | ✅ | `src/engines/email.py` |
| Outreach flow | ✅ | `src/orchestration/flows/outreach_flow.py` |
| Domain health service | ✅ | `src/services/domain_health_service.py` |
| Domain capacity service | ✅ | `src/services/domain_capacity_service.py` |
| Timezone service | ✅ | `src/services/timezone_service.py` |
| Persona model | ✅ | `src/models/client_persona.py` |
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

Clients receive **fully warmed domains** from the resource pool (see RESOURCE_POOL.md). No per-client warmup ramp — domains are warmed at platform level before assignment.

| Domain Status | Limit/Domain |
|---------------|--------------|
| Fully warmed | 50/day |
| Health warning | 35/day |
| Critical | 0 (paused) |

### Capacity by Tier (from RESOURCE_POOL.md)

| Tier | Domains | Daily Capacity | Response Buffer (10%) | Net Outbound |
|------|---------|----------------|----------------------|--------------|
| Ignition | 3 | 150/day | 15 reserved | 135/day |
| Velocity | 5 | 250/day | 25 reserved | 225/day |
| Dominance | 9 | 450/day | 45 reserved | 405/day |

**Response Buffer:** 10% of capacity reserved for reply-to-reply emails (SDK-generated responses).

---

## Domain Capacity Service

```python
# src/services/domain_capacity_service.py

from datetime import datetime
from uuid import UUID

async def get_domain_capacity(
    db: AsyncSession,
    resource_pool_id: UUID,
) -> dict:
    """
    Get current capacity for a domain.

    Domains are pre-warmed before client assignment.
    Capacity is reduced only if health metrics degrade.
    """
    domain = await db.get(ResourcePool, resource_pool_id)
    health = await check_domain_health(db, domain.resource_value)

    # Capacity based on health status
    if health['status'] == 'critical':
        daily_limit = 0  # Paused
    elif health['status'] == 'warning':
        daily_limit = 35  # Reduced
    else:
        daily_limit = 50  # Full capacity

    used_today = await _count_domain_sends_today(db, domain.resource_value)

    return {
        'domain': domain.resource_value,
        'daily_limit': daily_limit,
        'used_today': used_today,
        'remaining': max(0, daily_limit - used_today),
        'health_status': health['status'],
        'bounce_rate': health['bounce_rate'],
        'complaint_rate': health['complaint_rate'],
    }
```

**Note:** Platform-level warmup (InfraForge → Warmforge pipeline) is handled separately. See RESOURCE_POOL.md for buffer strategy and auto-provisioning.

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
recipient_tz = lead.company_hq_timezone or 'Australia/Sydney'

# Schedule for 9-11 AM recipient time
send_time = get_optimal_send_time(recipient_tz)
```

### Australian Timezone Mapping (State-Level)

Primary market is Australia. State-level granularity required.

```python
# src/engines/timezone_engine.py

AUSTRALIAN_STATE_TIMEZONES = {
    # Eastern (AEST/AEDT)
    "New South Wales": "Australia/Sydney",
    "NSW": "Australia/Sydney",
    "Victoria": "Australia/Melbourne",
    "VIC": "Australia/Melbourne",
    "Tasmania": "Australia/Hobart",
    "TAS": "Australia/Hobart",
    "Australian Capital Territory": "Australia/Sydney",
    "ACT": "Australia/Sydney",

    # Queensland (AEST - no DST)
    "Queensland": "Australia/Brisbane",
    "QLD": "Australia/Brisbane",

    # Central (ACST/ACDT)
    "South Australia": "Australia/Adelaide",
    "SA": "Australia/Adelaide",

    # Central (ACST - no DST)
    "Northern Territory": "Australia/Darwin",
    "NT": "Australia/Darwin",

    # Western (AWST)
    "Western Australia": "Australia/Perth",
    "WA": "Australia/Perth",
}

def detect_australian_timezone(state: str | None) -> str:
    """
    Detect timezone from Australian state.

    Args:
        state: State name or abbreviation

    Returns:
        IANA timezone string
    """
    if not state:
        return "Australia/Sydney"  # Default to Sydney

    return AUSTRALIAN_STATE_TIMEZONES.get(state, "Australia/Sydney")


def get_optimal_send_time(timezone: str) -> datetime:
    """
    Calculate optimal send time (9-11 AM recipient local).

    Returns next available slot within 9-11 AM window,
    skipping weekends.
    """
    import random
    from datetime import datetime, timedelta
    import pytz

    tz = pytz.timezone(timezone)
    now_local = datetime.now(tz)

    # Random minute within 9-11 AM window
    target_hour = 9
    target_minute = random.randint(0, 119)  # 0-119 mins = 9:00-10:59

    target = now_local.replace(
        hour=target_hour + (target_minute // 60),
        minute=target_minute % 60,
        second=0,
        microsecond=0,
    )

    # If past today's window, move to tomorrow
    if now_local >= target.replace(hour=11, minute=0):
        target += timedelta(days=1)

    # Skip weekends
    while target.weekday() >= 5:  # Saturday=5, Sunday=6
        target += timedelta(days=1)

    return target
```

### Send Window Enforcement

| Rule | Value |
|------|-------|
| Window start | 9:00 AM recipient local |
| Window end | 11:00 AM recipient local |
| Days | Monday - Friday only |
| Outside window | Queue for next valid slot |

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
# src/services/domain_health_service.py

HEALTH_THRESHOLDS = {
    'bounce': {
        'good': 0.02,      # <2%
        'warning': 0.05,   # 2-5%
        # >5% = critical
    },
    'complaint': {
        'good': 0.0005,    # <0.05%
        'warning': 0.001,  # 0.05-0.1%
        # >0.1% = critical
    },
}

async def check_domain_health(db: AsyncSession, domain: str) -> dict:
    """
    Check domain health metrics over rolling 30-day window.

    Returns:
        {
            'domain': 'agencyxos-growth.com',
            'sends_30d': 1500,
            'bounces_30d': 45,
            'bounce_rate': 0.03,
            'complaints_30d': 2,
            'complaint_rate': 0.001,
            'status': 'warning',  # good, warning, critical
            'action': 'reduce_limit',  # none, reduce_limit, pause, alert
        }
    """
    stats = await get_domain_stats_30d(db, domain)

    bounce_rate = stats['bounces'] / stats['sends'] if stats['sends'] > 0 else 0
    complaint_rate = stats['complaints'] / stats['sends'] if stats['sends'] > 0 else 0

    # Determine status (worst of bounce or complaint)
    if bounce_rate > 0.05 or complaint_rate > 0.001:
        status = 'critical'
        action = 'pause'
    elif bounce_rate > 0.02 or complaint_rate > 0.0005:
        status = 'warning'
        action = 'reduce_limit'
    else:
        status = 'good'
        action = 'none'

    return {
        'domain': domain,
        'sends_30d': stats['sends'],
        'bounces_30d': stats['bounces'],
        'bounce_rate': bounce_rate,
        'complaints_30d': stats['complaints'],
        'complaint_rate': complaint_rate,
        'status': status,
        'action': action,
    }
```

### Health Status Actions

| Status | Bounce Rate | Complaint Rate | Daily Limit | Action |
|--------|-------------|----------------|-------------|--------|
| Good | <2% | <0.05% | 50/day | None |
| Warning | 2-5% | 0.05-0.1% | 35/day | Alert admin |
| Critical | >5% | >0.1% | 0 (paused) | Alert admin, investigate |

### Auto-Recovery

Domains in warning/critical status are re-evaluated daily:
- If metrics improve → restore capacity
- If critical for 7+ days → consider retiring domain

---

## Files Involved

| File | Purpose | Status |
|------|---------|--------|
| `src/integrations/salesforge.py` | API client | ✅ |
| `src/engines/email.py` | Send logic | ✅ |
| `src/engines/smart_prompts.py` | Content generation | ✅ |
| `src/services/timezone_service.py` | Timezone detection | ✅ |
| `src/services/email_events_service.py` | Webhook handling | ✅ |
| `src/services/domain_capacity_service.py` | Capacity tracking | ✅ |
| `src/services/domain_health_service.py` | Health monitoring | ✅ |
| `src/models/client_persona.py` | Persona model | ✅ |
| `src/orchestration/flows/outreach_flow.py` | Batch sending | ✅ |
| `supabase/migrations/042_client_personas.sql` | Personas schema | ✅ |
| `supabase/migrations/044_domain_health.sql` | Domain health schema | ✅ |

---

## Verification Checklist

- [x] Salesforge integration works
- [x] Email engine sends correctly
- [x] Threading headers work
- [x] Webhooks received
- [x] Bounce handling works
- [x] Australian timezone detection (state-level)
- [x] Domain health monitoring (good/warning/critical)
- [x] Domain capacity tracking
- [x] Health-based limit reduction
- [x] Persona model implemented
- [ ] Signature generation (not yet wired)
- [ ] Display name format "{First} from {Company}" (pending integration)

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
