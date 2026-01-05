# Resend Integration

**File:** `src/integrations/resend.py`  
**Purpose:** Transactional email sending  
**API Docs:** https://resend.com/docs/api-reference

---

## Capabilities

- Send transactional emails
- Email threading (In-Reply-To headers)
- Webhooks for delivery events
- Custom domains

---

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /emails` | Send email |
| `GET /emails/{id}` | Get email status |
| `POST /domains` | Add custom domain |

---

## Usage Pattern

```python
class ResendClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.resend.com",
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        html: str,
        reply_to: str | None = None,
        headers: dict | None = None
    ) -> SendResult:
        """Send email with optional threading headers."""
        payload = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html
        }
        
        if reply_to:
            payload["reply_to"] = reply_to
        
        if headers:
            payload["headers"] = headers
        
        response = await self.client.post("/emails", json=payload)
        data = response.json()
        
        return SendResult(
            message_id=data["id"],
            status="sent"
        )
```

---

## Email Threading

For follow-up emails, include threading headers:

```python
async def send_follow_up(
    self,
    original_message_id: str,
    **kwargs
) -> SendResult:
    """Send threaded follow-up email."""
    headers = {
        "In-Reply-To": f"<{original_message_id}>",
        "References": f"<{original_message_id}>"
    }
    return await self.send_email(headers=headers, **kwargs)
```

---

## Webhook Events

| Event | Description |
|-------|-------------|
| `email.sent` | Email accepted by provider |
| `email.delivered` | Email delivered to inbox |
| `email.opened` | Email opened (if tracking enabled) |
| `email.clicked` | Link clicked (if tracking enabled) |
| `email.bounced` | Email bounced |
| `email.complained` | Marked as spam |

---

## Cost

- **Per email:** $0.0009 AUD (~$0.90 per 1000)
- **Free tier:** 100 emails/day
