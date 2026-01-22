# SMS Engine — SMS Outreach

**File:** `src/engines/sms.py`
**Purpose:** Send SMS messages with DNCR compliance
**Layer:** 3 - engines
**Provider:** ClickSend (Australian company, Perth)

---

## Provider Choice

| Provider | Use For | Notes |
|----------|---------|-------|
| **ClickSend** | SMS + Direct Mail | Primary for Australia, native AU support |
| **Twilio** | Voice calls ONLY | Used via Vapi for voice AI |

**Important:** Twilio is NOT used for SMS in Agency OS. ClickSend is the primary SMS provider for the Australian market.

---

## DNCR Compliance (Australia)

**Do Not Call Register** check required before sending:

```python
async def check_dncr(self, phone: str) -> bool:
    """
    Check if phone number is on Australian DNCR.

    Returns True if number is on DNCR (do not contact).
    """
    # Wash against DNCR database via ACMA API
    result = await self.dncr_client.check(phone)
    return result.is_registered
```

---

## SMS Flow

```
Lead selected for SMS (Hot tier only)
        │
        ▼
┌─────────────────┐
│ Check DNCR      │
└─────────────────┘
        │
        ├── On DNCR ──► Skip, mark lead.dncr_checked = True
        │
        └── Clear
                │
                ▼
┌─────────────────┐
│ Generate        │
│ content         │ ──► Content Engine (short format)
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Send via        │
│ ClickSend       │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Store activity  │
└─────────────────┘
```

---

## Message Constraints

| Constraint | Value |
|------------|-------|
| Max length | 918 characters (splits into segments) |
| Recommended | 160 characters (1 segment) |
| No links | Avoid URL shorteners (spam filters) |
| Sender ID | Australian mobile number or alphanumeric |

---

## Rate Limiting

- **Per number:** 100 SMS/day
- **Per client:** Based on tier allocation

---

## API

```python
class SMSEngine:
    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs,
    ) -> EngineResult:
        """
        Send SMS to lead via ClickSend with DNCR check.

        Args:
            db: Database session
            lead_id: Target lead (must be Hot tier)
            campaign_id: Campaign UUID
            content: SMS message content
            **kwargs: from_number, skip_dncr, etc.

        Returns:
            EngineResult with status

        Raises:
            DNCRError: If number is on DNCR
            TierViolation: If lead is not Hot tier
        """
        ...

    async def check_dncr(
        self,
        phone: str
    ) -> EngineResult:
        """Check DNCR status for phone number."""
        ...
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CLICKSEND_USERNAME` | ClickSend account username |
| `CLICKSEND_API_KEY` | ClickSend API key |

---

## Cost

- **ClickSend SMS (AU):** ~$0.06-0.08/message outbound
- **DNCR wash:** Separate via ACMA API (see dncr.py)
- **No monthly minimums:** Pay per message

---

## ClickSend API Reference

- **Base URL:** `https://rest.clicksend.com/v3`
- **Auth:** Basic Auth (base64 of username:api_key)
- **Send SMS:** `POST /sms/send`
- **SMS History:** `GET /sms/history`
- **Docs:** https://developers.clicksend.com/docs/rest/v3/

---

## Integration File

See `src/integrations/clicksend.py` for:
- `send_sms()` - Single SMS
- `send_sms_batch()` - Batch SMS
- `check_dncr()` - DNCR compliance
- `get_sms_history()` - History retrieval
- `parse_sms_webhook()` - Delivery webhooks
- `parse_inbound_sms()` - Inbound SMS webhooks
