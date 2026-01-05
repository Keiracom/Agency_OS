# Twilio Integration

**File:** `src/integrations/twilio.py`  
**Purpose:** SMS sending and Voice telephony  
**API Docs:** https://www.twilio.com/docs/api

---

## Capabilities

- SMS sending (Australian numbers)
- DNCR compliance checking
- Voice call origination
- Webhooks for delivery/call events

---

## SMS Usage

```python
from twilio.rest import Client

class TwilioClient:
    def __init__(self, account_sid: str, auth_token: str):
        self.client = Client(account_sid, auth_token)
    
    async def send_sms(
        self,
        from_number: str,
        to_number: str,
        body: str
    ) -> SMSResult:
        """Send SMS message."""
        message = self.client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        
        return SMSResult(
            message_sid=message.sid,
            status=message.status
        )
```

---

## Voice Call Origination

Used by Voice Engine for Vapi integration:

```python
async def initiate_call(
    self,
    from_number: str,
    to_number: str,
    webhook_url: str
) -> CallResult:
    """Initiate outbound call with webhook for handling."""
    call = self.client.calls.create(
        url=webhook_url,  # Vapi webhook
        to=to_number,
        from_=from_number
    )
    
    return CallResult(
        call_sid=call.sid,
        status=call.status
    )
```

---

## DNCR Integration

Australian Do Not Call Register checking:

```python
async def check_dncr(self, phone: str) -> bool:
    """
    Check if number is on Australian DNCR.
    Returns True if number should NOT be contacted.
    """
    # Twilio handles DNCR wash for Australian numbers
    # when using Regulatory Bundles
    lookup = self.client.lookups.v2.phone_numbers(phone).fetch()
    return lookup.do_not_call
```

---

## Webhook Events

### SMS Events
| Event | Description |
|-------|-------------|
| `sent` | Message sent to carrier |
| `delivered` | Confirmed delivery |
| `failed` | Delivery failed |
| `received` | Inbound SMS received |

### Voice Events
| Event | Description |
|-------|-------------|
| `initiated` | Call started |
| `ringing` | Phone ringing |
| `answered` | Call answered |
| `completed` | Call ended |

---

## Australian Numbers

- **Format:** +614XXXXXXXX (mobile)
- **SMS cost:** $0.08 AUD/message
- **Voice cost:** $0.015 AUD/minute

---

## Rate Limits

- **SMS:** 1 message/second per number
- **Voice:** 1 call/second per number
