# SKILL: Leadmagic Email & Mobile Enrichment

**Replaces:** Hunter (T3) + Kaspr (T5)  
**Status:** ⚠️ API key present but plan unpurchased — do NOT call until credits available  
**Source:** Leadmagic API  
**Credentials Required:** `LEADMAGIC_API_KEY`

---

## Overview

Leadmagic provides email finding and mobile number enrichment, replacing both Hunter.io (T3) and Kaspr (T5) in the Siege Waterfall.

## Costs (AUD)

| Operation | Cost | Replaces |
|-----------|------|----------|
| Email Finder (T3) | $0.015 AUD/lookup | Hunter ($0.019) |
| Mobile Finder (T5) | $0.077 AUD/lookup | Kaspr ($0.45) |
| Credit Check | FREE | - |

**Monthly Plan:** ~$155 AUD/month (Essential)

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/email-finder` | POST | Find email for person at domain |
| `/mobile-finder` | POST | Find mobile from LinkedIn URL |
| `/credits` | GET | Check credit balance |

## Email Finder (T3 Replacement)

### Input
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "domain": "acme.com.au",
  "company": "Acme Pty Ltd"  // optional
}
```

### Output
```json
{
  "found": true,
  "email": "john.smith@acme.com.au",
  "confidence": 95,
  "status": "valid",
  "position": "CEO",
  "linkedin_url": "https://linkedin.com/in/johnsmith"
}
```

### Usage
```python
from src.integrations.leadmagic import get_leadmagic_client

client = get_leadmagic_client()
result = await client.find_email("John", "Smith", "acme.com.au")

if result.found:
    print(f"Email: {result.email} (confidence: {result.confidence}%)")
    print(f"Cost: ${result.cost_aud:.3f} AUD")
```

## Mobile Finder (T5 Replacement)

### Input
```json
{
  "linkedin_url": "https://linkedin.com/in/johnsmith"
}
```

### Output
```json
{
  "found": true,
  "mobile_number": "+61412345678",
  "mobile_confidence": 90,
  "status": "verified",
  "first_name": "John",
  "last_name": "Smith",
  "title": "CEO",
  "company": "Acme Pty Ltd"
}
```

### Usage
```python
from src.integrations.leadmagic import get_leadmagic_client

client = get_leadmagic_client()
result = await client.find_mobile("https://linkedin.com/in/johnsmith")

if result.found:
    print(f"Mobile: {result.mobile_number} (confidence: {result.mobile_confidence}%)")
    print(f"Cost: ${result.cost_aud:.3f} AUD")
```

## Credit Check

```python
from src.integrations.leadmagic import get_leadmagic_client

client = get_leadmagic_client()
balance = await client.get_credits()

print(f"Email credits: {balance.email_credits}")
print(f"Mobile credits: {balance.mobile_credits}")
print(f"Plan: {balance.plan}")
```

## Error Handling

| Error | Code | Action |
|-------|------|--------|
| Rate limit | 429 | Wait and retry (exponential backoff) |
| Credits exhausted | 402 | Alert Dave, pause enrichment |
| Plan not purchased | 403 | Do not call API until plan activated |
| Invalid request | 400 | Check input parameters |

## Rate Limiting

- 1 second delay between requests
- Max 10 requests/second
- Automatic retry with exponential backoff (3 attempts)

## Integration Points

| File | Usage |
|------|-------|
| `src/integrations/leadmagic.py` | Main client implementation |
| `src/integrations/siege_waterfall.py` | T3 + T5 integration |
| `src/engines/waterfall_verification_worker.py` | Waterfall orchestration |

## Governance

- **LAW II:** All costs logged in AUD
- **CEO Directive:** Hunter + Kaspr deprecated, Leadmagic is canonical source
- **WARNING:** Plan unpurchased — do not make live API calls until credits available

## Batch Operations

```python
# Batch email finder
prospects = [
    {"first_name": "John", "last_name": "Smith", "domain": "acme.com.au"},
    {"first_name": "Jane", "last_name": "Doe", "domain": "example.com.au"},
]
results = await client.batch_find_emails(prospects, max_concurrent=5)

# Batch mobile finder
urls = [
    "https://linkedin.com/in/johnsmith",
    "https://linkedin.com/in/janedoe",
]
results = await client.batch_find_mobiles(urls, max_concurrent=5)
```

## Migration Notes

1. **Hunter.io (T3)** → `leadmagic.find_email()`
2. **Kaspr (T5)** → `leadmagic.find_mobile()`
3. **Cost savings:** T3: $0.004/email, T5: $0.373/mobile
4. **No email verification endpoint** — confidence score from find_email is sufficient
