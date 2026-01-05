# Postmark Integration

**File:** `src/integrations/postmark.py`  
**Purpose:** Inbound email webhooks  
**API Docs:** https://postmarkapp.com/developer

---

## Capabilities

- Inbound email processing
- Reply detection
- Bounce handling
- Spam complaints

---

## Usage Pattern

```python
class PostmarkClient:
    def __init__(self, server_token: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.postmarkapp.com",
            headers={"X-Postmark-Server-Token": server_token}
        )
    
    async def parse_inbound(
        self,
        webhook_payload: dict
    ) -> InboundEmail:
        """Parse inbound email webhook."""
        return InboundEmail(
            from_email=webhook_payload["From"],
            to_email=webhook_payload["To"],
            subject=webhook_payload["Subject"],
            text_body=webhook_payload.get("TextBody", ""),
            html_body=webhook_payload.get("HtmlBody", ""),
            message_id=webhook_payload["MessageID"],
            in_reply_to=webhook_payload.get("Headers", {}).get("In-Reply-To"),
            date=webhook_payload["Date"]
        )
```

---

## Webhook Events

| Event | Endpoint | Description |
|-------|----------|-------------|
| Inbound | `/webhooks/postmark/inbound` | Reply received |
| Bounce | `/webhooks/postmark/bounce` | Email bounced |
| Spam | `/webhooks/postmark/spam` | Marked as spam |

---

## Inbound Email Flow

```
Email reply received
        │
        ▼
┌─────────────────┐
│ Postmark        │
│ webhook         │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Parse email     │
│ headers         │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Match to lead   │
│ via In-Reply-To │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Closer Engine   │
│ (intent class)  │
└─────────────────┘
```

---

## Setup

1. Configure inbound domain in Postmark
2. Set webhook URL to `/api/v1/webhooks/postmark/inbound`
3. Enable bounce and spam complaint webhooks
