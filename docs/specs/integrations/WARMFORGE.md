# Warmforge Integration

**File:** `src/integrations/warmforge.py`  
**Purpose:** Email domain warmup status monitoring  
**Phase:** 18 (Email Infrastructure)  
**API Docs:** https://docs.warmforge.ai/

---

## Overview

Warmforge handles email warmup to build domain reputation before cold outreach. It sits between InfraForge (domain provisioning) and Salesforge (production sending).

**Ecosystem:** InfraForge (domains) → **Warmforge (warmup)** → Salesforge (sending)

---

## Capabilities

- Track mailbox warmup progress
- Monitor warmup score (0-100)
- Daily sending volume escalation
- Warmup email network participation
- Deliverability scoring

---

## API Endpoints

**Base URL:** `https://api.warmforge.ai/public/v1`

> ⚠️ **Note:** Warmforge uses v1 API, NOT v2

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mailboxes` | GET | List all mailboxes with status |
| `/mailboxes/{id}` | GET | Get single mailbox status |
| `/mailboxes/{id}/pause` | POST | Pause warmup |
| `/mailboxes/{id}/resume` | POST | Resume warmup |

**Auth:** `Authorization` header with plain API key (no Bearer prefix)

**Pagination:** Required params: `page`, `page_size`

---

## Cost Per Operation ($AUD)

Warmforge is included with Salesforge subscription:

| Component | Cost |
|-----------|------|
| Per mailbox warmup | **Included** |
| Monitoring | **Included** |

---

## Rate Limits

No specific rate limits documented. Use reasonable request frequency (1-2 req/second).

---

## Error Handling

```python
from src.integrations.warmforge import WarmForgeClient

client = WarmForgeClient()

try:
    status = await client.get_mailbox(mailbox_id)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        # Mailbox not found
        logger.error(f"Mailbox {mailbox_id} not in Warmforge")
    elif e.response.status_code == 401:
        # Auth issue
        alert_admin("Warmforge auth failed")
    else:
        logger.error(f"Warmforge error: {e}")
```

---

## Usage Pattern

### List All Mailboxes

```python
from src.integrations.warmforge import WarmForgeClient

client = WarmForgeClient()

# Paginated list
result = await client.list_mailboxes(page=1, page_size=100)
for mailbox in result["data"]:
    print(f"{mailbox['email']}: {mailbox['warmup_score']}% warmed")
```

### Get Single Mailbox Status

```python
status = await client.get_mailbox(mailbox_id="mbx_123")
print(f"Email: {status['email']}")
print(f"Warmup Score: {status['warmup_score']}%")
print(f"Daily Limit: {status['daily_limit']}")
print(f"Status: {status['status']}")
```

### Find Mailbox by Email

```python
mailbox = await client.get_mailbox_by_email("dave@clientdomain.com")
if mailbox:
    print(f"Found: {mailbox['warmup_score']}% warmed")
else:
    print("Not found in Warmforge")
```

### Get Domain Warmup Status

```python
domain_status = await client.get_domain_warmup_status("clientdomain.com")
print(f"Domain: {domain_status['domain']}")
print(f"Mailboxes: {domain_status['mailbox_count']}")
print(f"Average Score: {domain_status['average_warmup_score']}%")
print(f"All Ready: {domain_status['all_ready']}")
```

---

## Response Structure

### Mailbox Status

```python
{
    "id": "mbx_123",
    "email": "dave@clientdomain.com",
    "status": "warming",  # warming, ready, paused
    "warmup_score": 75,   # 0-100
    "daily_limit": 50,    # Current safe sending limit
    "emails_sent_today": 23,
    "started_at": "2026-01-15T00:00:00Z",
    "estimated_ready": "2026-02-05T00:00:00Z",
    "deliverability_score": 92,
}
```

### Domain Aggregate Status

```python
{
    "domain": "clientdomain.com",
    "mailbox_count": 5,
    "average_warmup_score": 80,
    "min_warmup_score": 65,
    "max_warmup_score": 95,
    "all_ready": False,  # True when all >= 80
    "mailboxes": [...]
}
```

---

## Warmup Progression

Typical warmup timeline:

| Week | Daily Limit | Warmup Score |
|------|-------------|--------------|
| 1 | 10-20 | 20-30% |
| 2 | 20-40 | 40-50% |
| 3 | 40-80 | 60-70% |
| 4 | 80-150 | 80-90% |
| 5+ | 150-200 | 90-100% |

**Ready threshold:** Warmup score ≥ 80%

---

## Environment Variables

```bash
# Required
WARMFORGE_API_KEY=your_api_key
WARMFORGE_API_URL=https://api.warmforge.ai/public/v1
```

---

## Warmup Monitor Flow

Agency OS runs a daily flow to check warmup status:

```python
async def warmup_monitor_flow():
    """Daily check of mailbox warmup status."""
    client = WarmForgeClient()
    
    # Get all mailboxes
    mailboxes = await client.list_mailboxes()
    
    for mbx in mailboxes["data"]:
        if mbx["warmup_score"] >= 80 and mbx["status"] == "warming":
            # Ready for production - update database
            await db.execute(
                "UPDATE mailboxes SET status = 'ready' WHERE id = :id",
                {"id": mbx["id"]}
            )
            
            # Notify client
            await notify_client(
                client_id=mbx["client_id"],
                message=f"Mailbox {mbx['email']} is ready for outreach!"
            )
```

---

## Integration with Salesforge

Before sending via Salesforge, check warmup status:

```python
async def can_send(mailbox_email: str) -> bool:
    """Check if mailbox is warmed and ready for production."""
    warmforge = WarmForgeClient()
    mailbox = await warmforge.get_mailbox_by_email(mailbox_email)
    
    if not mailbox:
        return False
    
    return (
        mailbox["warmup_score"] >= 80 and
        mailbox["emails_sent_today"] < mailbox["daily_limit"]
    )
```
