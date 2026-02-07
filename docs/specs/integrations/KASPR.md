# Kaspr Integration

**File:** `src/integrations/kaspr.py`  
**Purpose:** Verified mobile number enrichment (Tier 5 of SIEGE Waterfall)  
**Phase:** SIEGE (System Overhaul)  
**API Docs:** https://developers.kaspr.io/

---

## Overview

Kaspr provides verified mobile phone numbers for Voice AI and SMS campaigns. As Tier 5 of the SIEGE Waterfall, it's the most expensive enrichment tier and is **gated to ALS ≥ 85 (HOT leads only)**.

Primary use case: Getting direct mobile numbers when landline/generic numbers won't work for Voice AI outbound calling.

---

## Capabilities

- Verified mobile number lookup via LinkedIn URL
- Mobile confidence scoring (0-100)
- Personal email addresses (fallback)
- Full name and title enrichment
- Company association

---

## API Endpoints

| Endpoint | Method | Purpose | Cost |
|----------|--------|---------|------|
| `/v1/person/search` | POST | Find person by LinkedIn URL | $0.45 AUD |
| `/v1/person/enrich` | POST | Enrich with email/phone | $0.45 AUD |
| `/v1/credits` | GET | Check remaining credits | FREE |

**Base URL:** `https://api.kaspr.io`

---

## Cost Per Operation ($AUD)

| Operation | Cost |
|-----------|------|
| Successful mobile enrichment | $0.45 AUD |
| Failed/not found | $0.00 AUD |
| Credit check | $0.00 AUD |

**Note:** Credits are only consumed on successful enrichment with mobile number found.

---

## Rate Limits

| Plan | Limit |
|------|-------|
| Starter | 30 requests/minute |
| Pro | 60 requests/minute |
| Enterprise | Custom |

Safety buffer: 0.5s delay between requests to stay well under limits.

---

## Error Handling

```python
from src.integrations.kaspr import KasprClient, KasprError

client = KasprClient()

try:
    result = await client.enrich_mobile(
        linkedin_url="https://linkedin.com/in/johndoe"
    )
except KasprRateLimitError as e:
    # Wait and retry
    await asyncio.sleep(e.retry_after or 60)
except KasprCreditExhaustedError:
    # Plan limit reached - notify admin
    alert_admin("Kaspr credits exhausted")
except KasprError as e:
    # General Kaspr error
    logger.error(f"Kaspr error: {e}")
```

---

## Usage Pattern

```python
from src.integrations.kaspr import KasprClient

# Initialize
client = KasprClient()

# Enrich by LinkedIn URL
result = await client.enrich_mobile(
    linkedin_url="https://linkedin.com/in/johndoe"
)

if result.found and result.mobile_number_verified:
    print(f"Mobile: {result.mobile_number_verified}")
    print(f"Confidence: {result.mobile_confidence}%")
    print(f"Cost: ${result.cost_aud} AUD")
else:
    print("No mobile number found")

# Check remaining credits
credits = await client.get_credits()
print(f"Remaining credits: {credits}")
```

---

## Response Structure

```python
@dataclass
class KasprEnrichmentResult:
    found: bool
    mobile_number_verified: str | None = None
    mobile_confidence: int = 0  # 0-100 score
    email: str | None = None
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    cost_aud: float = 0.0
    source: str = "kaspr"
```

---

## Gating Rules (SIEGE Waterfall)

Kaspr is expensive ($0.45/lead) so it's gated:

```python
# Only run Tier 5 for HOT leads
if als_score >= 85:
    kaspr_result = await kaspr_client.enrich_mobile(linkedin_url)
else:
    # Skip Tier 5 - lead not hot enough
    pass
```

---

## Environment Variables

```bash
# Required
KASPR_API_KEY=your_kaspr_api_key

# Optional (defaults shown)
KASPR_API_URL=https://api.kaspr.io
KASPR_TIMEOUT=30
```

---

## Cost Tracking

The client tracks cumulative costs per session:

```python
client = KasprClient(cost_tracking_enabled=True)

# After multiple enrichments
print(f"Session total: ${client.total_cost_aud} AUD")
```

---

## Validation Threshold

Mobile confidence must meet threshold for use:

```python
VALIDATION_THRESHOLD = 0.70  # 70% confidence required

if result.mobile_confidence >= 70:
    # Use for Voice AI/SMS
    pass
else:
    # Too low confidence - fallback to other channels
    pass
```
