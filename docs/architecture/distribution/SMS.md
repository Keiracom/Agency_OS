# SMS Distribution Architecture

**Status:** ✅ IMPLEMENTED
**Provider:** ClickSend (Australian company, DNCR compliant)
**Rate Limit:** 100/day/number
**Last Updated:** January 22, 2026

---

## Executive Summary

SMS is Step 5 in the default sequence (Day 12 - final nudge). ClickSend is the provider, chosen for Australian compliance (DNCR integration). **DNCR checking is fully implemented** with batch wash at enrichment, cached check at send-time, and quarterly re-wash.

---

## CEO Decisions (2026-01-20)

| Decision | Choice |
|----------|--------|
| DNCR strategy | **Batch wash at enrichment**, quarterly re-wash |
| Send window | **9 AM - 5 PM recipient local time** (business hours) |
| Reply handling | **Same reply_agent as email** (unified intent classification) |
| Sender identity | **Pool number + client branding in message content** |

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| ClickSend integration | ✅ | `src/integrations/clicksend.py` |
| SMS engine | ✅ | `src/engines/sms.py` |
| Outreach flow integration | 🟡 | Flow exists but SMS step untested |
| Phone pool | ❌ | Not implemented (see RESOURCE_POOL.md) |
| DNCR checking | ✅ | **Batch wash at enrichment + cached check at send + quarterly re-wash** |
| DNCR re-wash flow | ✅ | `src/orchestration/flows/dncr_rewash_flow.py` (quarterly) |
| Opt-out handling | 🟡 | Basic implementation |

---

## Architecture Flow

```
ENRICHMENT (batch wash)
    └── enrichment_flow.py calls dncr_batch_check_task
        └── Australian numbers (+61) checked via DNCR API
            └── Results cached in lead.dncr_checked + lead.dncr_result

Day 12: SMS Step Due
    └── Outreach flow queries leads due for Step 5
        └── SMS engine checks cached dncr_result (no API call if known)
            └── If on DNCR → BLOCKED (logged, skipped)
            └── If clean → Allocator selects phone number
                └── SMS engine generates content (Smart Prompt)
                    └── ClickSend sends SMS
                        └── Activity logged
                            └── Webhook receives delivery/reply

QUARTERLY (re-wash)
    └── dncr_rewash_flow.py runs 1st of Jan/Apr/Jul/Oct
        └── Re-checks leads with stale DNCR data (>90 days)
            └── Updates lead.dncr_result with fresh status
```

---

## DNCR Compliance ✅ IMPLEMENTED

### Do Not Call Register (Australia)

Australian law requires checking the DNCR before marketing SMS/calls. We batch wash during enrichment, cache the result, and re-wash quarterly.

### Batch Wash at Enrichment

**File:** `src/orchestration/flows/enrichment_flow.py` (lines 177-260)

```python
@task(name="dncr_batch_check", retries=2, retry_delay_seconds=10)
async def dncr_batch_check_task(lead_ids: list[str]) -> dict[str, Any]:
    """Batch check DNCR status for Australian phone numbers."""
    dncr_client = get_dncr_client()

    # Fetch leads with Australian phones not already checked
    stmt = select(Lead).where(
        Lead.phone.startswith("+61"),
        Lead.dncr_checked == False,
    )

    # Batch check via DNCR API
    dncr_results = await dncr_client.check_numbers_batch(phones)

    # Update lead records
    for phone, is_on_dncr in dncr_results.items():
        lead.dncr_checked = True
        lead.dncr_result = is_on_dncr
```

### Database Fields

Fields exist on both `Lead` and `LeadPool` models:

```python
# src/models/lead.py
dncr_checked: Mapped[bool] = mapped_column(Boolean, default=False)
dncr_result: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

# src/models/lead_pool.py (also has timestamp)
dncr_checked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
```

### Send-Time Check (Cached)

**File:** `src/engines/sms.py` (lines 174-199)

```python
# Check cached DNCR result before calling API
if not skip_dncr and lead.phone.startswith("+61"):
    if lead.dncr_checked and lead.dncr_result:
        # Lead is on DNCR - block immediately without API call
        return EngineResult.fail(
            error=f"Phone number {lead.phone} is on DNCR (cached)",
            metadata={"reason": "dncr", "source": "cached"},
        )
    elif lead.dncr_checked and not lead.dncr_result:
        # Already checked and clean - skip DNCR API call
        skip_dncr = True
```

### Quarterly Re-Wash

**File:** `src/orchestration/flows/dncr_rewash_flow.py`
**Schedule:** `0 5 1 1,4,7,10 *` (5 AM AEST, 1st of Jan/Apr/Jul/Oct)

```python
@flow(name="dncr_quarterly_rewash")
async def dncr_quarterly_rewash_flow(
    stale_days: int = 90,
    max_leads: int = 10000,
) -> dict[str, Any]:
    """
    Re-checks all Australian phone numbers with stale DNCR status.
    Processes both Lead and LeadPool tables.
    """
    # Get leads with stale checks (>90 days)
    leads_data = await get_leads_needing_dncr_rewash_task(stale_days=90)
    pool_leads_data = await get_pool_leads_needing_dncr_rewash_task(stale_days=90)

    # Batch re-wash via DNCR API
    for batch in batches:
        result = await dncr_rewash_batch_task(leads=batch)
        # Tracks: newly_blocked, newly_unblocked
```

### DNCR Client

```python
# src/integrations/dncr.py

class DNCRClient:
    """
    Australian Do Not Call Register client.
    API: https://api.donotcall.gov.au/
    """

    async def check_number(self, phone: str) -> dict:
        """Check single number."""
        return {
            'phone': phone,
            'on_dncr': True/False,
            'checked_at': datetime.utcnow().isoformat(),
        }

    async def wash_list(self, phones: list[str]) -> dict:
        """Batch check multiple numbers."""
        return {
            'total': len(phones),
            'clean': 95,
            'blocked': 5,
            'blocked_numbers': ['+61...'],
        }
```

---

## Phone Number Pool

### Allocation per Tier

| Tier | Phone Numbers |
|------|---------------|
| Ignition | 1 |
| Velocity | 2 |
| Dominance | 3 |

### Capacity

At 100 SMS/day/number:
- Velocity: 2 numbers × 100 = 200 SMS/day
- Monthly: 200 × 22 days = 4,400 SMS capacity

For 2,250 leads with 1 SMS step:
- Needed: ~2,000 SMS/month (with attrition)
- Capacity: 4,400 ✅ Sufficient

---

## SMS Send Window

### Business Hours (9 AM - 5 PM Recipient Local)

SMS uses a wider window than email because:
- SMS is Step 5 (Day 12) — final nudge, not first touch
- People check SMS throughout the workday
- Still avoid evenings/weekends (intrusive)

```python
# src/engines/timing.py

def get_sms_send_time(recipient_timezone: str) -> datetime:
    """
    Calculate optimal SMS send time (9 AM - 5 PM recipient local).
    """
    import random
    import pytz

    tz = pytz.timezone(recipient_timezone)
    now_local = datetime.now(tz)

    # Random time within 9 AM - 5 PM window
    target_hour = random.randint(9, 16)  # 9 AM to 4 PM (sends before 5 PM)
    target_minute = random.randint(0, 59)

    target = now_local.replace(
        hour=target_hour,
        minute=target_minute,
        second=0,
        microsecond=0,
    )

    # If past today's window, move to tomorrow
    if now_local.hour >= 17:
        target += timedelta(days=1)

    # Skip weekends
    while target.weekday() >= 5:
        target += timedelta(days=1)

    return target
```

---

## SMS Reply Handling

### Unified Reply Agent

SMS replies route to the same `reply_agent` as email for consistent intent classification.

```python
# src/services/sms_webhook_service.py

async def handle_sms_reply(db: AsyncSession, event: dict):
    """
    Handle inbound SMS reply.

    Routes to reply_agent for intent classification.
    """
    phone = event['from']
    message = event['body']

    lead = await get_lead_by_phone(db, phone)
    if not lead:
        logger.warning(f"SMS reply from unknown number: {phone}")
        return

    # Log the reply
    await log_activity(
        lead_id=lead.id,
        channel='sms',
        action='reply_received',
        metadata={'message': message}
    )

    # Route to reply_agent (same as email)
    await reply_agent.process_reply(
        lead_id=lead.id,
        channel='sms',
        content=message,
    )
```

### Reply Agent SMS Response

When reply_agent generates a response for SMS channel:

```python
# src/agents/reply_agent.py

async def generate_sms_response(
    lead: Lead,
    intent: str,
    client: Client,
    persona: Persona,
) -> str:
    """
    Generate SMS response (max 160 chars).
    """
    if intent == 'meeting_interest':
        return f"Great! Here's my calendar: {persona.calendly_url}"

    if intent == 'question':
        # SDK generates short response
        return await sdk_generate_sms_reply(lead, intent)

    if intent == 'not_interested':
        return "No problem, thanks for letting me know. All the best!"

    # Default acknowledgment
    return "Thanks for your reply! I'll get back to you shortly."
```

---

## SMS Sender Identity

### Pool Number + Client Branding in Message

The SMS comes from our pool number, but the message content clearly identifies the client.

**Example SMS:**
```
Hi Sarah, it's John from Sparro. Following up on my
email about your Q2 pipeline. Worth a quick chat?
Reply YES and I'll send times.
```

### Message Template

```python
# src/engines/smart_prompts.py

SMS_PROMPT = """
Generate a brief SMS follow-up (max 160 chars) for:

Lead: {first_name}
Company: {lead_company_name}
Persona: {persona_first_name} from {client_company_name}
Previous touches: {touch_summary}

RULES:
- Start with "Hi {first_name}, it's {persona_first_name} from {client_company_name}"
- Max 160 characters total
- Professional but casual tone
- Clear call to action (reply YES, quick chat, etc.)
- Do NOT include links (spam filter risk)
"""
```

---

## Content Generation

### Character Limits

| Encoding | Chars/Segment |
|----------|---------------|
| GSM-7 | 160 |
| Unicode | 70 |

**Rule:** Keep to 1 segment (160 chars GSM-7) to avoid extra costs.

---

## Opt-Out Handling

### ClickSend Webhooks

```
sms.delivered
sms.failed
sms.reply
sms.optout
```

### Opt-Out Flow

```python
async def handle_sms_optout(db: AsyncSession, event: dict):
    """
    Handle STOP/UNSUBSCRIBE replies.
    """
    phone = event['from']
    lead = await get_lead_by_phone(db, phone)

    if lead:
        # Update lead status
        lead.pool_status = 'unsubscribed'

        # Add to suppression
        await add_to_suppression(
            db,
            identifier=phone,
            reason='sms_optout',
            client_id=lead.client_id
        )
```

### Required Keywords

ClickSend auto-handles: STOP, UNSUBSCRIBE, CANCEL, END, QUIT

---

## Files Involved

| File | Purpose | Status |
|------|---------|--------|
| `src/integrations/clicksend.py` | API client | ✅ |
| `src/integrations/dncr.py` | DNCR checking | 🟡 Created, not wired |
| `src/engines/sms.py` | Send logic | ✅ |
| `src/engines/timing.py` | Send window calculation | 🟡 Needs SMS window |
| `src/services/suppression_service.py` | Opt-out handling | ✅ |
| `src/services/sms_webhook_service.py` | Reply handling | ❌ CREATE |
| `src/agents/reply_agent.py` | Intent classification | 🟡 Needs SMS support |
| `src/orchestration/flows/dncr_rewash_flow.py` | Quarterly DNCR re-wash | ❌ CREATE |

---

## Verification Checklist

- [x] ClickSend integration works
- [x] SMS engine sends correctly
- [ ] Phone pool allocation (see RESOURCE_POOL.md)
- [ ] DNCR batch wash at enrichment
- [ ] DNCR fields on lead_pool (`on_dncr`, `dncr_checked_at`)
- [ ] Quarterly DNCR re-wash flow
- [ ] 9 AM - 5 PM send window (recipient local)
- [ ] SMS reply routing to reply_agent
- [ ] Reply agent SMS response generation
- [ ] Opt-out webhook handling
- [ ] Character limit enforcement (160 chars)
- [ ] Client branding in message content
- [ ] Cost tracking

---

## Configuration

### Environment Variables

```bash
CLICKSEND_USERNAME=xxx
CLICKSEND_API_KEY=xxx
DNCR_API_KEY=xxx  # Australian DNCR
```

### Settings

```python
# src/config/settings.py

sms_max_per_number_day: int = 100
sms_max_chars: int = 160
sms_dncr_check_enabled: bool = True
```

---

## Costs

| Item | Cost |
|------|------|
| SMS send (AU) | $0.065 AUD |
| DNCR check | $0.001 per number |

Monthly cost for Velocity (2,000 SMS):
- SMS: 2,000 × $0.065 = $130 AUD
- DNCR: 2,000 × $0.001 = $2 AUD
- **Total: ~$132 AUD/month**
