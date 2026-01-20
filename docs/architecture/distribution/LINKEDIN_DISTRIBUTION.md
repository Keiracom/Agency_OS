# LinkedIn Distribution Architecture

**Status:** 🟡 PARTIALLY IMPLEMENTED
**Provider:** Unipile (LinkedIn automation API)
**Rate Limit:** 20 connections/day/seat (LinkedIn enforced)

---

## Executive Summary

LinkedIn is Step 3 in the default sequence (Day 5 - connection request). Uses Unipile for automation with humanized timing to avoid account flags. LinkedIn has the strictest rate limits of all channels.

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Unipile integration | ✅ | `src/integrations/unipile.py` |
| LinkedIn engine | ✅ | `src/engines/linkedin.py` |
| Timing engine | ✅ | `src/engines/timing.py` |
| Outreach flow integration | 🟡 | Flow exists but LinkedIn untested |
| LinkedIn seat pool | ❌ | Not implemented (see RESOURCE_POOL.md) |
| Connection tracking | 🟡 | Basic implementation |
| Message follow-up | 🟡 | After connection accepted |

---

## Architecture Flow

```
Day 5: LinkedIn Step Due
    └── Outreach flow queries leads due for Step 3
        └── Check if lead has LinkedIn URL
            └── Allocator selects LinkedIn seat (round-robin)
                └── Timing engine calculates humanized delay
                    └── LinkedIn engine sends connection request
                        └── Activity logged
                            └── Webhook receives accept/ignore
                                └── If accepted: send follow-up message
```

---

## LinkedIn-Specific Constraints

### Platform Limits (Enforced by LinkedIn)

| Action | Daily Limit | Weekly Limit |
|--------|-------------|--------------|
| Connection requests | 20-25 | 100 |
| Profile views | 100 | 500 |
| Messages (1st degree) | 50 | — |
| InMail (paid) | 25/month | — |

**Our Conservative Limits:**
- 20 connections/day/seat (safety margin)
- 80 connections/week/seat

### Account Safety

LinkedIn can flag/restrict accounts for:
- Sending too many requests too fast
- Pattern-based activity (same time daily)
- High ignore/rejection rate
- Suspicious profile viewing patterns

---

## Timing Engine Integration

### Humanized Delays

```python
# src/engines/timing.py

class TimingEngine:
    """
    Generates human-like delays between LinkedIn actions.
    """

    def get_delay_seconds(self) -> float:
        """
        Beta distribution for natural clustering.
        Returns 8-45 minute delays.
        """
        beta_value = random.betavariate(2, 5)
        range_minutes = 45 - 8
        delay_minutes = 8 + (beta_value * range_minutes)
        jitter = random.uniform(-2, 2)
        return max(8, delay_minutes + jitter) * 60

    def get_start_jitter_seconds(self) -> int:
        """
        Randomize start time (0-120 min after business hours start).
        """
        return random.randint(0, 120) * 60
```

### Daily Schedule

```
Business hours: 8 AM - 6 PM (recipient timezone)
Max actions/hour: 8

Example day:
09:23 - Action 1
09:41 - Action 2
10:15 - Action 3
10:38 - Action 4
... (8-45 min gaps)
```

---

## LinkedIn Seat Pool

### Allocation per Tier

| Tier | LinkedIn Seats |
|------|----------------|
| Ignition | 0 |
| Velocity | 1 |
| Dominance | 2 |

### Capacity

At 20 connections/day/seat:
- Velocity: 1 seat × 20 = 20 connections/day
- Monthly: 20 × 22 days = 440 connection capacity

For 2,250 leads with 1 LinkedIn step:
- Needed: ~2,000 connections/month
- Capacity: 440 ❌ **INSUFFICIENT**

**Problem:** LinkedIn is the bottleneck. Options:
1. Skip LinkedIn for some leads (tier-based)
2. Add more seats (cost)
3. Use LinkedIn as optional channel

**Recommendation:** LinkedIn only for Hot/Warm leads (top 50%).

---

## Connection Request Flow

### Step 1: Find Profile

```python
async def find_linkedin_profile(
    lead: Lead,
) -> str | None:
    """
    Find LinkedIn profile URL.

    Priority:
    1. lead.linkedin_url (from enrichment)
    2. Search by name + company
    """
    if lead.linkedin_url:
        return lead.linkedin_url

    # Search (uses API quota)
    results = await unipile.search_people(
        first_name=lead.first_name,
        last_name=lead.last_name,
        company=lead.company_name,
    )

    if results:
        return results[0]['profile_url']

    return None
```

### Step 2: Send Connection

```python
async def send_connection_request(
    seat_id: str,
    profile_url: str,
    note: str | None = None,  # 300 char limit
) -> dict:
    """
    Send LinkedIn connection request.

    Args:
        seat_id: LinkedIn seat from pool
        profile_url: Target profile
        note: Connection message (optional, 300 chars max)

    Returns:
        {
            'request_id': 'req_xxx',
            'status': 'pending',
        }
    """
```

### Connection Note

```python
CONNECTION_NOTE_PROMPT = """
Write a brief LinkedIn connection note (max 300 chars):

Lead: {first_name} {last_name}
Title: {title}
Company: {company_name}
Mutual: {mutual_connections}
Hook: {personalization_hook}

Rules:
- No sales pitch
- Reference something specific
- End with soft CTA
"""
```

---

## Post-Connection Follow-Up

### When Connection Accepted

```python
async def handle_connection_accepted(
    db: AsyncSession,
    lead_id: UUID,
    connection_id: str,
):
    """
    Handle accepted connection.

    1. Log activity
    2. Schedule follow-up message (Day +2)
    3. Update lead.linkedin_connected = True
    """
    await log_activity(
        lead_id=lead_id,
        channel='linkedin',
        action='connection_accepted',
    )

    # Schedule follow-up
    await schedule_linkedin_message(
        lead_id=lead_id,
        delay_days=2,
        message_type='introduction',
    )
```

### Follow-Up Message

```python
LINKEDIN_MESSAGE_PROMPT = """
Write a LinkedIn message (max 1000 chars) for new connection:

Lead: {first_name} {last_name}
Title: {title}
Company: {company_name}
Days since connected: {days_connected}
Previous touches: {touch_summary}

Goal: Start conversation about their challenges
Tone: Helpful, not salesy
"""
```

---

## Webhook Events

| Event | Action |
|-------|--------|
| `connection.sent` | Log pending |
| `connection.accepted` | Schedule message |
| `connection.ignored` | Mark as ignored |
| `message.sent` | Log activity |
| `message.received` | Route to reply handler |

---

## Files Involved

| File | Purpose | Status |
|------|---------|--------|
| `src/integrations/unipile.py` | LinkedIn API | ✅ |
| `src/engines/linkedin.py` | LinkedIn logic | ✅ |
| `src/engines/timing.py` | Humanized delays | ✅ |
| `src/services/linkedin_connection_service.py` | Connection tracking | 🟡 |

---

## Verification Checklist

- [x] Unipile integration works
- [x] LinkedIn engine sends requests
- [x] Timing engine provides delays
- [ ] LinkedIn seat pool allocation (RESOURCE_POOL.md)
- [ ] Connection tracking in DB
- [ ] Post-accept message flow
- [ ] Webhook handling
- [ ] Weekly limit enforcement
- [ ] Account health monitoring

---

## Configuration

### Environment Variables

```bash
UNIPILE_API_KEY=xxx
UNIPILE_ACCOUNT_ID=xxx
```

### Settings

```python
# src/config/settings.py

linkedin_max_connections_day: int = 20
linkedin_max_connections_week: int = 80
linkedin_max_messages_day: int = 50
linkedin_max_per_hour: int = 8
linkedin_min_delay_minutes: int = 8
linkedin_max_delay_minutes: int = 45
linkedin_business_hours_start: int = 8
linkedin_business_hours_end: int = 18
linkedin_weekend_reduction: float = 0.5
```

---

## Costs

| Item | Cost |
|------|------|
| Unipile seat | $99/month/seat |

Monthly cost for Velocity (1 seat):
- **$99 AUD/month**

---

## Channel Prioritization

Given LinkedIn's severe capacity constraints, prioritize:

| Lead Tier | Get LinkedIn? |
|-----------|---------------|
| Hot (85+) | ✅ Yes |
| Warm (60-84) | ✅ Yes |
| Cool (35-59) | ⚠️ If capacity |
| Cold (<35) | ❌ No |

```python
def should_use_linkedin(lead: Lead, remaining_capacity: int) -> bool:
    """
    Determine if lead should get LinkedIn touch.
    """
    if remaining_capacity <= 0:
        return False

    if lead.als_score >= 60:
        return True  # Hot + Warm always

    if lead.als_score >= 35 and remaining_capacity > 10:
        return True  # Cool if we have capacity

    return False
```
