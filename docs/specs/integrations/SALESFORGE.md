# Salesforge Integration

**File:** `src/integrations/salesforge.py`  
**Purpose:** Cold email infrastructure and sending  
**Phase:** 18 (Email Infrastructure)  
**API Docs:** https://docs.salesforge.ai/

---

## Overview

Salesforge is the primary email sending provider that works with Warmforge-warmed mailboxes. It replaced Resend for cold outreach to preserve warmup progress and deliverability.

**Ecosystem:** InfraForge (domains) → Warmforge (warmup) → **Salesforge (sending)**

---

## Capabilities

- Send emails via warmed mailboxes
- Email threading support (follow-up sequences)
- Open/click tracking
- Reply detection
- Bounce handling
- Custom headers for threading

---

## API Endpoints

**Base URL:** `https://api.salesforge.ai/public/v2`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/emails/send` | POST | Send single email |
| `/workspaces/{id}/mailboxes` | GET | List mailboxes |
| `/mailboxes/{id}` | GET | Get mailbox status |
| `/emails/{id}` | GET | Get email status |
| `/webhooks` | POST | Webhook registration |

**Auth:** `authorization` header with raw API key (no Bearer prefix)

---

## Cost Per Operation ($AUD)

Salesforge uses subscription + usage pricing:

| Component | Cost |
|-----------|------|
| Base subscription | ~$99/month AUD |
| Per email sent | ~$0.001-0.002 AUD |
| Tracking | Included |
| Warmup (via Warmforge) | Included |

---

## Rate Limits

| Limit | Value |
|-------|-------|
| Per mailbox | 50-200 emails/day (warmup dependent) |
| API requests | 100/minute |
| Burst | 300/minute |

Mailbox sending limits increase as warmup progresses:
- Week 1-2: 20-30/day
- Week 3-4: 50-100/day
- Week 5+: 100-200/day

---

## Error Handling

```python
from src.integrations.salesforge import SalesforgeClient
from src.exceptions import APIError

client = SalesforgeClient()

try:
    result = await client.send_email(
        from_email="dave@clientdomain.com",
        to_email="prospect@company.com",
        subject="Quick question",
        html_body="<p>Hi there...</p>",
    )
except APIError as e:
    if e.status_code == 429:
        # Rate limited
        await asyncio.sleep(60)
    elif e.status_code == 400:
        # Invalid request (check mailbox status)
        logger.error(f"Bad request: {e}")
    elif e.status_code == 401:
        # API key issue
        alert_admin("Salesforge auth failed")
```

---

## Usage Pattern

### Send Single Email

```python
from src.integrations.salesforge import SalesforgeClient

client = SalesforgeClient()

result = await client.send_email(
    from_email="Dave Smith <dave@clientdomain.com>",
    to_email="prospect@company.com",
    subject="Quick question about your marketing",
    html_body="<p>Hi John,</p><p>I noticed your website...</p>",
    text_body="Hi John, I noticed your website...",
    reply_to="dave@clientdomain.com",
    mailbox_id="mbx_123",
    tags={
        "lead_id": "lead_456",
        "campaign_id": "camp_789",
        "client_id": "client_012",
    },
)

print(f"Message ID: {result['message_id']}")
```

### Send Threaded Follow-up

```python
# Follow-up email with threading
result = await client.send_email(
    from_email="dave@clientdomain.com",
    to_email="prospect@company.com",
    subject="Re: Quick question about your marketing",
    html_body="<p>Hi John,</p><p>Just following up...</p>",
    in_reply_to="<original-message-id@salesforge>",
    references=["<original-message-id@salesforge>"],
)
```

### List Mailboxes

```python
mailboxes = await client.list_mailboxes(workspace_id="ws_123")
for mbx in mailboxes:
    print(f"{mbx['email']}: {mbx['status']} ({mbx['daily_limit']} emails/day)")
```

---

## Request Structure

```python
{
    "to": "prospect@company.com",
    "from": "dave@clientdomain.com",
    "fromName": "Dave Smith",
    "subject": "Quick question",
    "htmlBody": "<p>Email content...</p>",
    "textBody": "Plain text version...",
    "replyTo": "dave@clientdomain.com",
    "mailboxId": "mbx_123",
    "customHeaders": {
        "In-Reply-To": "<msg-id>",
        "References": "<msg-id1> <msg-id2>",
    },
    "metadata": {
        "lead_id": "lead_456",
        "campaign_id": "camp_789",
    }
}
```

---

## Response Structure

```python
{
    "success": True,
    "message_id": "msg_abc123",
    "provider": "salesforge",
    "salesforge_response": {
        "id": "email_xyz",
        "messageId": "<unique-id@salesforge>",
        "status": "sent",
        "sentAt": "2026-02-01T10:00:00Z"
    }
}
```

---

## Webhook Events

| Event | Description |
|-------|-------------|
| `email.sent` | Email successfully sent |
| `email.delivered` | Email delivered to inbox |
| `email.opened` | Recipient opened email |
| `email.clicked` | Recipient clicked link |
| `email.replied` | Recipient replied |
| `email.bounced` | Email bounced |
| `email.unsubscribed` | Recipient unsubscribed |

---

## Environment Variables

```bash
# Required
SALESFORGE_API_KEY=your_api_key
SALESFORGE_API_URL=https://api.salesforge.ai/public/v2

# Optional
SALESFORGE_WORKSPACE_ID=ws_default
SALESFORGE_WEBHOOK_SECRET=your_webhook_secret
```

---

## Integration with Warmforge

Mailboxes must be warmed via Warmforge before sending:

```
InfraForge                  Warmforge                   Salesforge
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│ Provision    │───────────▶│ Warmup       │───────────▶│ Production   │
│ Domain +     │            │ (2-4 weeks)  │            │ Sending      │
│ Mailbox      │            │              │            │              │
└──────────────┘            └──────────────┘            └──────────────┘
```

Check warmup status before sending:

```python
warmforge = WarmForgeClient()
status = await warmforge.get_mailbox(mailbox_id)

if status['warmup_score'] >= 80:
    # Ready for production
    await salesforge.send_email(...)
else:
    # Still warming up
    logger.info(f"Mailbox still warming: {status['warmup_score']}%")
```
