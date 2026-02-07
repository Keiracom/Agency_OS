# Unipile Integration

**File:** `src/integrations/unipile.py`  
**Purpose:** LinkedIn automation (replaces HeyReach)  
**Phase:** Unipile Migration  
**API Docs:** https://docs.unipile.com/

---

## Overview

Unipile provides LinkedIn automation via hosted authentication. It replaces HeyReach with significant improvements:

- **No credential storage** - OAuth-style hosted auth flow
- **Higher rate limits** - 80-100 connections/day vs HeyReach's 17
- **SOC 2 compliant** - Enterprise security standards
- **No 2FA handling** - User authenticates directly with LinkedIn

---

## Capabilities

- Hosted auth flow for LinkedIn connection
- Connection requests (with personalized notes)
- Direct messages
- Profile data retrieval
- InMail sending (Sales Navigator accounts)
- Webhook-based status updates

---

## API Endpoints

**Base URL:** Varies by Unipile instance (set in env)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/hosted/accounts/link` | POST | Create hosted auth link |
| `/api/v1/accounts` | GET | List connected accounts |
| `/api/v1/accounts/{id}` | GET | Get account status |
| `/api/v1/users/{id}/invitation` | POST | Send connection request |
| `/api/v1/chats` | POST | Start/continue conversation |
| `/api/v1/users/{id}` | GET | Get profile data |

---

## Cost Per Operation ($AUD)

Unipile uses subscription pricing, not per-operation:

| Plan | Monthly Cost | Accounts |
|------|-------------|----------|
| Starter | ~$49 AUD | 1 account |
| Growth | ~$149 AUD | 5 accounts |
| Enterprise | Custom | Unlimited |

**Per-action cost:** Effectively $0 after subscription.

---

## Rate Limits

Recommended limits to avoid LinkedIn restrictions:

| Action | Daily Limit |
|--------|-------------|
| Connection requests | 80-100/day per account |
| Messages | 100-150/day per account |
| Profile views | 250/day per account |
| InMails | Depends on Sales Nav credits |

---

## Error Handling

```python
from src.integrations.unipile import UnipileClient
from src.exceptions import ResourceRateLimitError, APIError

client = UnipileClient()

try:
    result = await client.send_connection_request(
        account_id=account_id,
        profile_url=linkedin_url,
        note="Hi, I'd like to connect..."
    )
except ResourceRateLimitError:
    # Daily limit reached - queue for tomorrow
    await queue_for_tomorrow(linkedin_url)
except APIError as e:
    if e.status_code == 401:
        # Account disconnected - needs re-auth
        await notify_reauth_needed(account_id)
    else:
        logger.error(f"Unipile error: {e}")
```

---

## Usage Pattern

### Hosted Auth Flow

```python
# 1. Create hosted auth link (user clicks this)
auth_link = await client.create_hosted_auth_link(
    providers=["LINKEDIN"],
    success_redirect_url="https://app.keiracom.com/linkedin/success",
    failure_redirect_url="https://app.keiracom.com/linkedin/failed",
    notify_url="https://api.keiracom.com/webhooks/unipile",
    name=f"client_{client_id}",  # For matching later
)
print(f"User should visit: {auth_link['url']}")

# 2. User completes auth in browser
# 3. Webhook receives account_id when complete
```

### Send Connection Request

```python
result = await client.send_connection_request(
    account_id="acc_123",
    profile_url="https://linkedin.com/in/johndoe",
    note="Hi John, I noticed we're both in the digital marketing space...",
)
```

### Send Message

```python
result = await client.send_message(
    account_id="acc_123",
    recipient_profile_url="https://linkedin.com/in/johndoe",
    message="Thanks for connecting! I wanted to share...",
)
```

### Get Profile Data

```python
profile = await client.get_profile(
    account_id="acc_123",
    profile_url="https://linkedin.com/in/johndoe",
)
print(f"Name: {profile['first_name']} {profile['last_name']}")
print(f"Title: {profile['headline']}")
print(f"Company: {profile['company']}")
```

---

## Response Structure

### Connected Account

```python
{
    "account_id": "acc_123",
    "provider": "LINKEDIN",
    "status": "CONNECTED",  # CONNECTED, DISCONNECTED, PENDING
    "email": "user@example.com",
    "name": "John Doe",
    "profile_url": "https://linkedin.com/in/johndoe",
    "created_at": "2026-01-15T10:00:00Z",
    "daily_stats": {
        "connections_sent": 45,
        "messages_sent": 30,
        "remaining_connections": 55,
        "remaining_messages": 120,
    }
}
```

---

## Webhook Events

| Event | Description |
|-------|-------------|
| `account.connected` | LinkedIn account successfully linked |
| `account.disconnected` | Account lost connection (needs re-auth) |
| `invitation.accepted` | Connection request accepted |
| `invitation.rejected` | Connection request rejected |
| `message.received` | New message received |
| `message.sent` | Message successfully sent |

---

## Environment Variables

```bash
# Required
UNIPILE_API_URL=https://api.unipile.com  # Or your instance URL
UNIPILE_API_KEY=your_api_key

# Webhook verification (optional)
UNIPILE_WEBHOOK_SECRET=your_webhook_secret
```

---

## Migration from HeyReach

| Feature | HeyReach | Unipile |
|---------|----------|---------|
| Auth method | Credentials + 2FA | Hosted OAuth |
| Connections/day | 17 | 80-100 |
| Credential storage | Required | Not required |
| Multi-account | Separate seats | Shared pool |
| Compliance | Unknown | SOC 2 |
