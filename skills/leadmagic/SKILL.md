# Leadmagic Integration

**Purpose:** Email finder and mobile enrichment via Leadmagic API  
**Replaces:** Hunter.io (T3) + Kaspr (T5) — CEO Directive: Leadmagic is canonical source

## ⚠️ WARNING

API key present but plan unpurchased — **do not call until credits available**.

## Overview

Leadmagic is the unified source for:
- **Email finding** (replaces Hunter.io T3): Find verified work emails from name + domain
- **Mobile finding** (replaces Kaspr T5): Find mobile numbers from LinkedIn profiles

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://api.leadmagic.io/email-finder` | POST | Find email from name + domain |
| `https://api.leadmagic.io/mobile-finder` | POST | Find mobile from LinkedIn URL |
| `https://api.leadmagic.io/credits` | GET | Check credit balance |

## Costs (AUD)

| Operation | Cost per Record |
|-----------|----------------|
| Email finder | $0.015 AUD |
| Mobile finder | $0.077 AUD |

## Usage

### Email Finder (Replaces Hunter T3)

**Input:**
- `first_name`: Person's first name
- `last_name`: Person's last name  
- `domain`: Company domain (e.g., "company.com")

**Output:**
- `email`: Verified work email address
- `confidence`: Confidence score (0-100)
- `status`: found / not_found / error

```python
from src.integrations.leadmagic import LeadmagicClient

async with LeadmagicClient() as client:
    result = await client.find_email(
        first_name="John",
        last_name="Smith",
        domain="company.com.au"
    )
    print(f"Email: {result.email}")
    print(f"Confidence: {result.confidence}")
    print(f"Cost: ${result.cost_aud:.3f} AUD")
```

### Mobile Finder (Replaces Kaspr T5)

**Input:**
- `linkedin_url`: Full LinkedIn profile URL

**Output:**
- `mobile`: Mobile phone number
- `first_name`: Contact's first name
- `last_name`: Contact's last name
- `company`: Current company
- `status`: found / not_found / error

```python
from src.integrations.leadmagic import LeadmagicClient

async with LeadmagicClient() as client:
    result = await client.find_mobile(
        linkedin_url="https://linkedin.com/in/johnsmith"
    )
    print(f"Mobile: {result.mobile}")
    print(f"Company: {result.company}")
    print(f"Cost: ${result.cost_aud:.3f} AUD")
```

### Credit Check

```python
from src.integrations.leadmagic import LeadmagicClient

async with LeadmagicClient() as client:
    credits = await client.get_credits()
    print(f"Email credits: {credits.email_credits}")
    print(f"Mobile credits: {credits.mobile_credits}")
```

### Synchronous Wrappers

For compatibility with non-async code (e.g., waterfall workers):

```python
from src.integrations.leadmagic import find_email_sync, find_mobile_sync, get_credits_sync

# Email
result = find_email_sync("John", "Smith", "company.com")

# Mobile
result = find_mobile_sync("https://linkedin.com/in/johnsmith")

# Credits
credits = get_credits_sync()
```

## Rate Limits

- **Max requests:** 60 per minute
- **Built-in rate limiting:** 1 second between requests
- **Retry logic:** Exponential backoff (3 retries max)

## Error Handling

| HTTP Status | Meaning |
|-------------|---------|
| 200 | Success |
| 400 | Bad request (validation error) |
| 401 | Invalid API key |
| 402 | Insufficient credits |
| 429 | Rate limit exceeded |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LEADMAGIC_API_KEY` | Yes | Leadmagic API key |

## Migration from Hunter/Kaspr

### Hunter → Leadmagic

Old Hunter interface (deprecated stubs exist for compatibility):
```python
# OLD (deprecated)
result = await verify_domain("company.com")  # Logged warning, returns stub

# NEW (use this)
result = await client.find_email("John", "Smith", "company.com")
```

Key difference: Leadmagic requires name + domain (not just domain).

### Kaspr → Leadmagic

Kaspr was never fully implemented. Leadmagic `find_mobile()` is the canonical mobile enrichment.

## Waterfall Integration

- **T3 (Email):** Call `find_email()` with first name, last name, domain from previous enrichment
- **T5 (Mobile):** Call `find_mobile()` with LinkedIn URL from T4 enrichment

## Files

- **Integration:** `src/integrations/leadmagic.py`
- **Skill docs:** `skills/leadmagic/SKILL.md` (this file)

## Version History

- **2026-02-17:** Created to replace Hunter.io (T3) + Kaspr (T5) per CEO directive
