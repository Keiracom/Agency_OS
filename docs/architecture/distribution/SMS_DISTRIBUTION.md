# SMS Distribution Architecture

**Status:** 🟡 PARTIALLY IMPLEMENTED
**Provider:** ClickSend (Australian company, DNCR compliant)
**Rate Limit:** 100/day/number

---

## Executive Summary

SMS is Step 5 in the default sequence (Day 12 - final nudge). ClickSend is the provider, chosen for Australian compliance (DNCR integration). DNCR checking is NOT yet implemented.

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| ClickSend integration | ✅ | `src/integrations/clicksend.py` |
| SMS engine | ✅ | `src/engines/sms.py` |
| Outreach flow integration | 🟡 | Flow exists but SMS step untested |
| Phone pool | ❌ | Not implemented (see RESOURCE_POOL.md) |
| DNCR checking | ❌ | Integration exists but not wired |
| Opt-out handling | 🟡 | Basic implementation |

---

## Architecture Flow

```
Day 12: SMS Step Due
    └── Outreach flow queries leads due for Step 5
        └── DNCR check (MISSING)
            └── Allocator selects phone number (round-robin)
                └── SMS engine generates content (Smart Prompt)
                    └── ClickSend sends SMS
                        └── Activity logged
                            └── Webhook receives delivery/reply
```

---

## DNCR Compliance (CRITICAL)

### Do Not Call Register (Australia)

Before sending SMS to Australian numbers, we MUST check DNCR:

```python
# src/integrations/dncr.py

class DNCRClient:
    """
    Australian Do Not Call Register client.

    API: https://api.donotcall.gov.au/
    """

    async def check_number(self, phone: str) -> dict:
        """
        Check if number is on DNCR.

        Returns:
            {
                'phone': '+61412345678',
                'on_dncr': True,
                'checked_at': '2026-01-20T10:00:00Z',
            }
        """

    async def wash_list(self, phones: list[str]) -> dict:
        """
        Batch check multiple numbers.

        Returns:
            {
                'total': 100,
                'clean': 95,
                'blocked': 5,
                'blocked_numbers': ['+61...'],
            }
        """
```

### Integration Point

```python
# src/engines/sms.py

async def send_sms(db: AsyncSession, lead_id: UUID, message: str) -> EngineResult:
    lead = await get_lead(db, lead_id)

    # DNCR check for Australian numbers
    if lead.phone.startswith('+61'):
        dncr_result = await dncr_client.check_number(lead.phone)
        if dncr_result['on_dncr']:
            # Log and skip
            await log_activity(
                lead_id=lead_id,
                channel='sms',
                action='blocked_dncr',
                metadata={'phone': lead.phone}
            )
            return EngineResult.fail(error="Number on DNCR")

    # Proceed with send
    ...
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

## Content Generation

### Smart Prompt for SMS

```python
SMS_PROMPT = """
Generate a brief SMS follow-up (max 160 chars) for:

Lead: {first_name} {last_name}
Company: {company_name}
Previous touches: {touch_history}
Original outreach: {original_email_subject}

Tone: Professional but casual
Goal: Prompt a reply or meeting booking
Do NOT include links (spam filter risk)
"""
```

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
| `src/services/suppression_service.py` | Opt-out handling | ✅ |

---

## Verification Checklist

- [x] ClickSend integration works
- [x] SMS engine sends correctly
- [ ] Phone pool allocation (RESOURCE_POOL.md)
- [ ] DNCR checking before send
- [ ] Opt-out webhook handling
- [ ] Character limit enforcement
- [ ] Reply handling
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
