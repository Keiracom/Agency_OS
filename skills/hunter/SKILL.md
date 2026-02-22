# Hunter.io Skill

Email discovery and verification for outreach campaigns.

## When to Use Hunter

- **Find emails for a company** — Get all publicly available email addresses for a domain
- **Find a specific person's email** — Locate email for a person when you have their name + company domain
- **Verify email deliverability** — Check if an email is valid before sending outreach
- **Batch prospect research** — Find/verify emails for multiple prospects efficiently

**DO NOT use when:**
- You already have verified contact info
- The lead explicitly opted out of contact
- You're rate-limited (check quota first)

## Available Functions

### `domain_search(domain, limit=10, offset=0, email_type=None, seniority=None, department=None)`

Find all emails for a domain.

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | str | Yes | Company domain (e.g., "stripe.com") |
| `limit` | int | No | Max emails to return (default 10, max 100) |
| `offset` | int | No | Skip N emails for pagination |
| `email_type` | EmailType | No | Filter: "personal" or "generic" |
| `seniority` | list[Seniority] | No | Filter: junior/senior/executive |
| `department` | list[Department] | No | Filter: sales/marketing/executive/etc. |

**Returns:** `DomainSearchResult`
```python
{
    "domain": "stripe.com",
    "organization": "Stripe",
    "pattern": "{first}{last}",
    "accept_all": False,
    "disposable": False,
    "webmail": False,
    "emails": [
        {
            "email": "john.doe@stripe.com",
            "email_type": "personal",
            "confidence": 95,
            "first_name": "John",
            "last_name": "Doe",
            "position": "Sales Manager",
            "seniority": "senior",
            "department": "sales",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "sources_count": 3
        }
    ],
    "total_emails": 150,
    "cost_aud": 0.15
}
```

**Cost:** $0.15 AUD per search

---

### `email_finder(domain, first_name, last_name, company=None)`

Find the most likely email for a specific person.

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | str | Yes | Company domain |
| `first_name` | str | Yes | Person's first name |
| `last_name` | str | Yes | Person's last name |
| `company` | str | No | Company name (helps accuracy) |

**Returns:** `EmailFinderResult`
```python
{
    "found": True,
    "email": "john.doe@stripe.com",
    "score": 92,  # Confidence score 0-100
    "domain": "stripe.com",
    "accept_all": False,
    "first_name": "John",
    "last_name": "Doe",
    "position": "CTO",
    "company": "Stripe",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "cost_aud": 0.15
}
```

**Cost:** $0.15 AUD per lookup (only charged if email found)

---

### `verify_email(email)`

Verify if an email is deliverable.

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | str | Yes | Email address to verify |

**Returns:** `EmailVerificationResult`
```python
{
    "email": "john@stripe.com",
    "status": "valid",  # valid/invalid/accept_all/webmail/disposable/unknown
    "result": "valid",
    "score": 95,  # Deliverability score 0-100
    "is_valid": True,  # score >= 70 and status == valid
    "is_risky": False,  # disposable, accept_all, or score < 50
    "disposable": False,
    "webmail": False,
    "mx_records": True,
    "smtp_check": True,
    "accept_all": False,
    "cost_aud": 0.08
}
```

**Cost:** $0.08 AUD per verification

---

### `batch_find_emails(prospects, max_concurrent=5)`

Find emails for multiple prospects.

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `prospects` | list[dict] | Yes | List of {domain, first_name, last_name, company?} |
| `max_concurrent` | int | No | Concurrent requests (default 5) |

**Returns:** `list[EmailFinderResult]`

**Cost:** $0.15 AUD per successful lookup

---

### `batch_verify_emails(emails, max_concurrent=5)`

Verify multiple emails.

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `emails` | list[str] | Yes | List of email addresses |
| `max_concurrent` | int | No | Concurrent requests (default 5) |

**Returns:** `list[EmailVerificationResult]`

**Cost:** $0.08 AUD per verification

---

## How to Call It

```python
from src.integrations.hunter import get_hunter_client, HunterClient

# Option 1: Singleton (recommended for most uses)
client = get_hunter_client()
result = await client.domain_search("stripe.com")

# Option 2: Context manager (auto-cleanup)
async with HunterClient() as client:
    result = await client.email_finder("stripe.com", "John", "Doe")
    print(f"Found: {result.email} (confidence: {result.score})")
    print(f"Session cost: ${client.get_session_cost():.2f} AUD")
```

### Filtering Domain Search

```python
from src.integrations.hunter import (
    get_hunter_client, 
    EmailType, 
    Seniority, 
    Department
)

client = get_hunter_client()

# Find executives only
result = await client.domain_search(
    domain="acme.com",
    seniority=[Seniority.EXECUTIVE, Seniority.SENIOR],
    department=[Department.EXECUTIVE, Department.SALES],
    email_type=EmailType.PERSONAL,
    limit=20
)
```

## Error Handling

### Exception Types

| Exception | HTTP | Meaning |
|-----------|------|---------|
| `HunterRateLimitError` | 403 | Too many requests per second (10/s limit) |
| `HunterQuotaExceededError` | 429 | Monthly quota exhausted |
| `HunterError` | Various | General Hunter API error |
| `ValidationError` | — | Invalid input (missing domain, etc.) |
| `APIError` | Various | HTTP-level error |

### Handling Pattern

```python
from src.integrations.hunter import (
    get_hunter_client,
    HunterRateLimitError,
    HunterQuotaExceededError,
    HunterError
)
from src.exceptions import ValidationError

try:
    client = get_hunter_client()
    result = await client.email_finder("acme.com", "John", "Smith")
    
except HunterRateLimitError as e:
    # Wait and retry (auto-alerts via Directive 048)
    await asyncio.sleep(e.retry_after or 60)
    
except HunterQuotaExceededError:
    # Quota exhausted - fallback to manual research
    # Auto-alerts fired to alert service
    logger.warning("Hunter quota exceeded - falling back to manual")
    
except ValidationError as e:
    # Bad input - don't retry
    logger.error(f"Invalid input: {e}")
    
except HunterError as e:
    # Generic Hunter error - may be retryable
    logger.error(f"Hunter error: {e.message}")
```

## Rate Limit Awareness

⚠️ **CRITICAL: Free plan has ~50 calls remaining, resets March 7, 2026**

### Current Limits
- **Rate limit:** 10 requests per second (auto-handled with 0.1s delay)
- **Monthly quota:** Limited on free tier (~50 remaining)
- **Retry logic:** 3 attempts with exponential backoff (built-in)

### Best Practices
1. **Check session cost** before batch operations: `client.get_session_cost()`
2. **Use batch methods** to minimize API calls
3. **Filter by seniority/department** to get relevant results first
4. **Verify only high-confidence emails** (score > 70)

### Quota Conservation
```python
# DON'T: Verify every email
for email in emails:
    await client.verify_email(email)  # Wasteful!

# DO: Only verify high-confidence finds
results = await client.batch_find_emails(prospects)
high_confidence = [r for r in results if r.found and r.score >= 70]
verified = await client.batch_verify_emails([r.email for r in high_confidence])
```

## What to Do on Failure

### Rate Limit Hit (403)
1. Auto-alert fires via alert service (Directive 048)
2. Wait `retry_after` seconds (default 60)
3. Reduce concurrent requests

### Quota Exceeded (429)
1. Auto-alert fires
2. **Cannot retry until quota resets** (monthly)
3. Fallback strategies:
   - Use cached/previously found emails
   - Manual LinkedIn research
   - Alternative services (if available)

### API Error (5xx)
1. Built-in retry with exponential backoff
2. If persistent, check DataForSEO status page
3. Log and skip prospect, continue batch

### No Email Found
- Not an error — person may not have public email
- Check confidence in response
- Consider alternative domains (company subsidiaries)

## Cost Summary

| Operation | Cost (AUD) | Notes |
|-----------|------------|-------|
| Domain Search | $0.15 | Per search, regardless of results |
| Email Finder | $0.15 | Only if email found |
| Email Verification | $0.08 | Per verification |
| Batch Find (10) | ~$1.50 | Max if all found |
| Batch Verify (10) | $0.80 | Fixed |

**Session cost tracking:**
```python
client = get_hunter_client()
# ... do operations ...
print(f"Session total: ${client.get_session_cost():.2f} AUD")
client.reset_cost_tracking()  # Reset counter
```
