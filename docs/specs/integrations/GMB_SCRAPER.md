# GMB Scraper Integration

**File:** `src/integrations/gmb_scraper.py`  
**Purpose:** Google My Business data extraction (Tier 2 of SIEGE Waterfall)  
**Phase:** Fixed Cost Optimization  
**API Docs:** DIY scraper using Autonomous Stealth Browser

---

## Overview

The GMB Scraper extracts business data from Google Maps using the Autonomous Stealth Browser. It replaces the Apify google-maps-scraper, reducing costs by ~70%.

---

## Capabilities

- Phone number extraction
- Business address
- Website URL
- Operating hours
- Review count and average rating
- Business category
- Photos (count)
- Place ID for future lookups

---

## Cost Per Operation ($AUD)

| Method | Cost |
|--------|------|
| GMB Scraper (DIY) | **$0.006 AUD/lead** |
| Apify (deprecated) | ~$0.02/lead |

**Savings:** ~70% cost reduction by moving to DIY scraping.

---

## Architecture

```
GMB Scraper Request
        │
        ▼
┌─────────────────────┐
│ Autonomous Stealth  │
│ Browser             │
│ ─────────────────── │
│ • Chromium/Playwright│
│ • Webshare proxies  │
│ • Fingerprint spoof │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ Google Maps         │
│ ─────────────────── │
│ • Search by name    │
│ • Extract details   │
│ • Parse HTML/JSON   │
└─────────────────────┘
```

---

## Rate Limits

| Parameter | Value |
|-----------|-------|
| Max concurrent requests | 3 |
| Min delay between requests | 2,000ms |
| Max delay between requests | 5,000ms |
| Max retries | 3 |

---

## Error Handling

Block detection triggers automatic retry with new identity:

```python
BLOCK_INDICATORS = [
    "unusual traffic",
    "captcha",
    "automated queries",
    "please verify",
    "access denied",
    "rate limit",
]

# On detection:
# 1. Rotate proxy
# 2. New user agent
# 3. New fingerprint
# 4. Retry with backoff
```

---

## Usage Pattern

```python
from src.integrations.gmb_scraper import GMBScraper

scraper = GMBScraper()

# Search by business name and location
result = await scraper.search_business(
    business_name="Acme Plumbing",
    location="Sydney NSW",
)

if result.found:
    print(f"Phone: {result.phone}")
    print(f"Address: {result.address}")
    print(f"Website: {result.website}")
    print(f"Rating: {result.rating} ({result.review_count} reviews)")
    print(f"Hours: {result.hours}")
    print(f"Cost: ${result.cost_aud} AUD")
```

---

## Response Structure

```python
@dataclass
class GMBResult:
    found: bool = False
    source: str = "gmb_scraper"
    
    # Core data
    phone: str | None = None
    address: str | None = None
    website: str | None = None
    
    # Business details
    business_name: str | None = None
    category: str | None = None
    hours: dict | None = None
    
    # Reviews/Rating
    rating: float | None = None
    review_count: int | None = None
    
    # Google identifiers
    place_id: str | None = None
    maps_url: str | None = None
    
    # Cost tracking
    cost_aud: Decimal = Decimal("0.006")
```

---

## Environment Variables

```bash
# Autonomous Browser uses these
WEBSHARE_API_KEY=your_webshare_key  # Proxy rotation

# Optional browser config
PLAYWRIGHT_HEADLESS=true
BROWSER_TIMEOUT=30000
```

---

## Dependencies

The scraper uses the Autonomous Stealth Browser stack:

```python
# tools/autonomous_browser.py
from tools.autonomous_browser import (
    autonomous_fetch,
    IdentityRotator,
    create_stealth_context,
)

# tools/proxy_manager.py
from tools.proxy_manager import get_proxy_list, get_manager
```

---

## SIEGE Waterfall Integration

As Tier 2, GMB runs after ABN lookup:

```python
# Tier 2: GMB enrichment
if lead.state and lead.company_name:
    gmb_result = await gmb_scraper.search_business(
        business_name=lead.company_name,
        location=f"{lead.state} Australia",
    )
    
    if gmb_result.found:
        lead.phone = gmb_result.phone
        lead.website = gmb_result.website
        lead.address = gmb_result.address
```

---

## Anti-Detection Features

| Feature | Implementation |
|---------|----------------|
| Proxy Rotation | 215,084 residential proxies (Webshare) |
| User-Agent Spoofing | Chrome/Firefox/Safari/Edge rotation |
| Fingerprint Randomization | Viewport, timezone, locale per request |
| Burner Protocol | Auto-retry on 403/429/503 with new identity |
| JavaScript Rendering | Full Chromium browser via Playwright |
| webdriver Flag | Spoofed to avoid detection |

---

## Fallback Chain

If stealth browser fails, the scraper attempts httpx fallback:

```python
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15...",
]

# Retry with simple httpx if Playwright fails
async with httpx.AsyncClient(headers={"User-Agent": random.choice(USER_AGENTS)}) as client:
    response = await client.get(url)
```
