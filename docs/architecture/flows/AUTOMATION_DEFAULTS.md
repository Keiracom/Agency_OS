# Automated Distribution Defaults

**Date:** 2026-01-20
**Status:** SPECIFICATION (Not Yet Implemented)
**Principle:** Agency OS is AUTOMATED. Users configure WHAT to target, not HOW to reach them.

---

## User Controls vs System Controls

### What Users Configure (Campaign Creation Form)

```
Target Demographic:
├── Industries (e.g., "SaaS", "FinTech")
├── Titles (e.g., "CEO", "VP Sales")
├── Company sizes (e.g., "11-50", "51-200")
├── Locations (e.g., "Australia", "New Zealand")
└── ICP refinements (via onboarding)
```

### What System Controls (Automated)

```
Distribution:
├── Sequence pattern (Day 1 email → Day 4 voice → Day 7 LinkedIn)
├── Timing (9-11 AM recipient timezone)
├── Days (Monday-Friday only)
├── Warmup schedule (gradual ramp)
├── Rate limits (per channel, per resource)
└── Content generation (Claude Smart Prompt)
```

---

## Default Sequence Template

Agency OS enforces this 5-step sequence for all campaigns:

| Step | Day | Channel | Logic |
|------|-----|---------|-------|
| 1 | 0 | Email | Initial outreach |
| 2 | 3 | Voice | Follow-up call (if no reply) |
| 3 | 5 | LinkedIn | Connection request (if no reply) |
| 4 | 8 | Email | Value-add touchpoint (if no reply) |
| 5 | 12 | SMS | Final nudge (if no reply) |

### Sequence Rules

1. **Skip on reply** - If lead replies at any step, sequence stops
2. **Skip on bounce** - If email bounces, skip remaining email steps
3. **Skip on unsubscribe** - If lead opts out, sequence stops
4. **Channel fallback** - If channel unavailable (no LinkedIn seat), skip that step

---

## Timing Defaults

### Send Window

| Setting | Default | Rationale |
|---------|---------|-----------|
| Start time | 09:00 | Business hours start |
| End time | 11:00 | Morning attention peak |
| Days | Mon-Fri | No weekend outreach |
| Timezone | Recipient's | Detect from company HQ location |

### Why 9-11 AM Only?

Research shows:
- **9-10 AM**: Highest open rates (checking email first thing)
- **10-11 AM**: Good response rates (settled into work)
- **After 11 AM**: Declining attention (meetings, lunch)
- **Afternoon**: Low priority inbox time

### Timezone Detection

```python
def get_recipient_timezone(lead: Lead) -> str:
    """
    Detect recipient timezone from company location.

    Priority:
    1. lead.company_hq_timezone (if enriched)
    2. lead.company_hq_country → default timezone
    3. Client's timezone (fallback)
    """
    if lead.company_hq_timezone:
        return lead.company_hq_timezone

    country_timezones = {
        "Australia": "Australia/Sydney",
        "New Zealand": "Pacific/Auckland",
        "United States": "America/New_York",
        "United Kingdom": "Europe/London",
        # ... etc
    }

    return country_timezones.get(
        lead.company_hq_country,
        lead.client.timezone
    )
```

---

## Warmup Schedule

New email domains follow this gradual ramp:

| Day | Daily Limit | Notes |
|-----|-------------|-------|
| 1-3 | 5 | Establishing reputation |
| 4-7 | 10 | Building trust |
| 8-14 | 20 | Ramping up |
| 15-21 | 35 | Approaching full capacity |
| 22+ | 50 | Full sending (if no issues) |

### Warmup Logic

```python
def get_warmup_daily_limit(domain_created_at: datetime) -> int:
    """
    Calculate daily limit based on domain age.
    """
    days_active = (datetime.utcnow() - domain_created_at).days

    if days_active < 4:
        return 5
    elif days_active < 8:
        return 10
    elif days_active < 15:
        return 20
    elif days_active < 22:
        return 35
    else:
        return 50
```

### Warmup Health Checks

| Metric | Threshold | Action |
|--------|-----------|--------|
| Bounce rate | > 5% | Reduce limit by 50% |
| Spam complaints | > 0.1% | Pause domain, alert |
| Unsubscribe rate | > 2% | Review content quality |

---

## Channel Rate Limits

### Email

| Resource | Limit | Per |
|----------|-------|-----|
| Domain | 50/day | After warmup |
| Mailbox | 100/day | Salesforge limit |
| Client total | 200/day | Safety cap |

### Voice (Twilio)

| Resource | Limit | Per |
|----------|-------|-----|
| Phone number | 50/day | Prevent spam flags |
| Concurrent calls | 5 | Account limit |
| Call duration | 2 min | Auto-hangup |

### LinkedIn (Unipile)

| Resource | Limit | Per |
|----------|-------|-----|
| Connection requests | 20/day | LinkedIn limit |
| Messages | 50/day | After connections |
| Profile views | 100/day | Research cap |

### SMS (ClickSend)

| Resource | Limit | Per |
|----------|-------|-----|
| Phone number | 100/day | Carrier limits |
| Client total | 200/day | Cost control |

---

## Implementation Changes Required

### Phase 1: Remove User Configuration

**Files to modify:**

1. `frontend/app/campaigns/create/page.tsx`
   - Remove sequence configuration UI
   - Remove timing configuration UI
   - Keep only: name, description, target demographics

2. `src/api/routes/campaigns.py`
   - Remove sequence fields from create endpoint
   - Auto-generate sequences using defaults

3. `src/models/campaign.py`
   - Make `work_hours_start/end` read-only (system default)
   - Make `work_days` read-only (system default)
   - Make `sequence_steps` read-only (system default)

### Phase 2: Auto-Generate Sequences

**New function:**

```python
# src/services/sequence_generator.py

async def generate_default_sequence(
    db: AsyncSession,
    campaign_id: UUID,
    available_channels: list[ChannelType],
) -> list[CampaignSequence]:
    """
    Auto-generate the 5-step default sequence.

    Adapts based on available channels:
    - No LinkedIn seat? Skip LinkedIn step
    - No voice? Replace with email
    """
    default_steps = [
        {"day": 0, "channel": "email"},
        {"day": 3, "channel": "voice"},
        {"day": 5, "channel": "linkedin"},
        {"day": 8, "channel": "email"},
        {"day": 12, "channel": "sms"},
    ]

    sequences = []
    for i, step in enumerate(default_steps):
        channel = ChannelType(step["channel"])

        # Channel fallback
        if channel not in available_channels:
            if ChannelType.EMAIL in available_channels:
                channel = ChannelType.EMAIL
            else:
                continue  # Skip step if no fallback

        seq = CampaignSequence(
            campaign_id=campaign_id,
            step_number=i + 1,
            channel=channel,
            delay_days=step["day"],
            body_template="{{SMART_PROMPT}}",  # Claude generates
            skip_if_replied=True,
            skip_if_bounced=True,
        )
        sequences.append(seq)

    return sequences
```

### Phase 3: Gradual Warmup

**Modify:**

1. `src/engines/email.py`
   - Check domain age before sending
   - Apply warmup limit based on schedule

2. `src/orchestration/flows/outreach_flow.py`
   - Query warmup limit before batch selection
   - Respect gradual ramp

### Phase 4: Timezone Detection

**Add to enrichment:**

1. `src/engines/scout.py`
   - Add `company_hq_timezone` to enrichment fields
   - Detect from Apollo/Apify company data

2. `src/engines/timing.py`
   - Use recipient timezone (not campaign timezone)
   - Schedule for 9-11 AM recipient local time

---

## Migration Path

### For Existing Campaigns

1. Keep existing sequences (don't break active campaigns)
2. New campaigns use auto-generation
3. Migrate existing campaigns on user request

### Database Migration

```sql
-- 041_enforce_default_sequences.sql

-- Add flag for auto-generated sequences
ALTER TABLE campaigns
ADD COLUMN uses_default_sequence BOOLEAN DEFAULT TRUE;

-- Mark existing campaigns as custom
UPDATE campaigns SET uses_default_sequence = FALSE;

-- New campaigns will default to TRUE
```

---

## Metrics to Track

| Metric | Purpose |
|--------|---------|
| Open rate by send time | Validate 9-11 AM window |
| Reply rate by step | Optimize sequence timing |
| Bounce rate by warmup day | Validate warmup schedule |
| Channel effectiveness | Optimize channel mix |

---

## Monthly Lead Pacing

See `business/TIERS_AND_BILLING.md` for:
- Monthly lead quotas per tier
- Credit system and reset logic
- Daily pacing calculations to spread leads across the month

---

## Related Documentation

- `../business/TIERS_AND_BILLING.md` — Monthly scheduling, credits
- `../business/SCORING.md` — ALS and channel access
- `../content/SDK_AND_PROMPTS.md` — Smart Prompt system
- `docs/specs/engines/TIMING_ENGINE.md` — Humanized delays
- `src/engines/timing.py` — Current timing implementation
- `src/models/campaign.py` — Campaign model

---

## Summary

Agency OS is sold as **automated**. Users configure:
- **WHAT** (target demographic, ICP)

System controls:
- **HOW** (sequences, timing, warmup, rate limits)
- **WHEN** (9-11 AM recipient timezone, Mon-Fri)
- **CONTENT** (Claude Smart Prompt generates everything)

This is the key differentiator: **Set it and forget it.**
