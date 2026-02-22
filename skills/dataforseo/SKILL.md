# DataForSEO Skill

SEO metrics enrichment for lead scoring (ALS).

## When to Use DataForSEO

- **Enrich lead data with SEO metrics** — Domain rank, backlinks, organic traffic
- **Score agency competence** — "Do they practice what they preach?"
- **Calculate ALS (Agency Lead Score)** — Authority/presence signals
- **Detect red flags** — High spam score, no web presence

**DO NOT use when:**
- Lead already has recent enrichment data (< 30 days)
- Domain is clearly invalid/placeholder
- Batch size would exceed budget (check costs first)

## Available Functions

### `get_domain_overview(domain, location_code=2036, language_code="en")`

Get organic search metrics from Labs API.

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | str | Yes | Target domain (e.g., "example.com.au") |
| `location_code` | int | No | Country code (2036 = Australia) |
| `language_code` | str | No | Language code (default "en") |

**Returns:**
```python
{
    "organic_etv": 149.89,         # Estimated Traffic Value (monthly)
    "organic_count": 99,           # Total ranking keywords
    "organic_pos_1": 2,            # Keywords in position 1
    "organic_pos_2_3": 0,          # Keywords in positions 2-3
    "organic_pos_4_10": 5,         # Keywords in positions 4-10
    "estimated_paid_traffic_cost": 434.26,  # Value in paid equivalent
    "enriched_at": "2026-01-04T12:00:00"
}
```

**Cost:** $0.0101 USD per request (~$0.015 AUD)

---

### `get_backlinks_summary(domain, include_subdomains=True)`

Get backlink metrics from Backlinks API.

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `domain` | str | Yes | Target domain |
| `include_subdomains` | bool | No | Include subdomains (default True) |

**Returns:**
```python
{
    "rank": 337,                   # Domain Rank (0-1000+, higher = better)
    "backlinks": 19578,            # Total backlink count
    "referring_domains": 1429,     # Unique referring domains
    "referring_ips": 864,          # Unique referring IPs
    "referring_subnets": 693,      # Unique referring subnets
    "spam_score": 28,              # Spam score (0-100, lower = better)
    "enriched_at": "2026-01-04T12:00:00"
}
```

**Cost:** $0.02003 USD per request (~$0.03 AUD)

---

### `get_full_domain_metrics(domain, location_code=2036, language_code="en")`

Get comprehensive metrics from both APIs (recommended).

**Returns:** Combined dict with all metrics:
```python
{
    # From Labs API
    "organic_etv": 149.89,
    "organic_count": 99,
    "organic_pos_1": 2,
    "organic_pos_2_3": 0,
    "organic_pos_4_10": 5,
    "estimated_paid_traffic_cost": 434.26,
    # From Backlinks API
    "domain_rank": 337,
    "backlinks": 19578,
    "referring_domains": 1429,
    "referring_ips": 864,
    "spam_score": 28,
    # Meta
    "enriched_at": "2026-01-04T12:00:00"
}
```

**Cost:** ~$0.03 USD per request (~$0.045 AUD)

---

### `health_check()`

Check API connectivity and account balance.

**Returns:**
```python
{
    "status": "healthy",
    "balance": 25.50,  # Account balance in USD
    "login": "your_login"
}
```

**Cost:** Free

---

### ALS Scoring Helpers

#### `score_domain_rank(domain_rank: int | None) -> int`

Score domain authority for ALS (0-5 points).

| Rank | Points | Interpretation |
|------|--------|----------------|
| 0-50 | 0 | New/invisible |
| 51-150 | 1 | Small local presence |
| 151-300 | 2 | Established local agency |
| 301-500 | 3 | Strong regional agency |
| 501-800 | 4 | Well-known agency |
| 801+ | 5 | Industry leader |

---

#### `score_organic_traffic(organic_etv: float | None) -> int`

Score organic traffic for ALS (0-5 points).

| ETV (Monthly) | Points | Interpretation |
|---------------|--------|----------------|
| 0-50 | 0 | No presence |
| 51-200 | 1 | Minimal |
| 201-1,000 | 2 | Growing |
| 1,001-5,000 | 3 | Solid |
| 5,001-20,000 | 4 | Strong |
| 20,001+ | 5 | Dominant |

---

#### `score_seo_competence(metrics: dict) -> int`

Score overall SEO competence (0-5 points).

- Has top 10 rankings: +2
- Has position 1 rankings: +1
- Has 50+ ranking keywords: +1
- Has 500+ referring domains: +1

---

#### `calculate_risk_deductions(metrics: dict) -> int`

Calculate ALS risk deductions.

| Condition | Deduction |
|-----------|-----------|
| Domain Rank 0 or None | -5 |
| No organic traffic | -3 |
| Spam score > 50 | -3 |

---

## How to Call It

```python
from src.integrations.dataforseo import get_dataforseo_client

# Get singleton client
client = get_dataforseo_client()

# Full enrichment (recommended)
metrics = await client.get_full_domain_metrics("example.com.au")
print(f"Domain Rank: {metrics['domain_rank']}")
print(f"Organic ETV: ${metrics['organic_etv']}")
print(f"Spam Score: {metrics['spam_score']}")

# Calculate ALS components
rank_score = client.score_domain_rank(metrics['domain_rank'])
traffic_score = client.score_organic_traffic(metrics['organic_etv'])
competence_score = client.score_seo_competence(metrics)
deductions = client.calculate_risk_deductions(metrics)

als_component = rank_score + traffic_score + competence_score + deductions
```

### Checking Account Health

```python
client = get_dataforseo_client()
health = await client.health_check()

if health["status"] == "healthy":
    print(f"Balance: ${health['balance']:.2f}")
else:
    print(f"Error: {health.get('error')}")
```

### Cleanup

```python
from src.integrations.dataforseo import close_dataforseo_client

# When done (e.g., on app shutdown)
await close_dataforseo_client()
```

## Cost Per Call

| Endpoint | USD | AUD (~1.5x) | Notes |
|----------|-----|-------------|-------|
| Labs domain_rank_overview | $0.0101 | ~$0.015 | Organic metrics |
| Backlinks summary | $0.02003 | ~$0.030 | Backlink/authority metrics |
| **Full enrichment** | **$0.03** | **~$0.045** | Both APIs combined |
| Health check | Free | Free | Account status |

### Batch Cost Example
| Leads | Cost (USD) | Cost (AUD) |
|-------|------------|------------|
| 10 | $0.30 | $0.45 |
| 100 | $3.00 | $4.50 |
| 1,000 | $30.00 | $45.00 |

## Error Handling

### Exception Types

| Exception | Meaning |
|-----------|---------|
| `APIError` | HTTP error from DataForSEO |
| `IntegrationError` | Configuration/connection error |

### Handling Pattern

```python
from src.integrations.dataforseo import get_dataforseo_client
from src.exceptions import APIError, IntegrationError

try:
    client = get_dataforseo_client()
    metrics = await client.get_full_domain_metrics(domain)
    
except IntegrationError as e:
    # Missing credentials or connection issue
    logger.error(f"DataForSEO config error: {e}")
    metrics = None  # Skip enrichment
    
except APIError as e:
    # API returned error (rate limit, invalid request, etc.)
    logger.error(f"DataForSEO API error ({e.status_code}): {e.message}")
    metrics = None  # Use cached or skip
```

### Common API Errors

| Status | Meaning | Action |
|--------|---------|--------|
| 401 | Invalid credentials | Check DATAFORSEO_LOGIN/PASSWORD |
| 402 | Insufficient balance | Top up account |
| 500 | Server error | Retry with backoff (built-in) |

## What to Do on Failure

### Insufficient Balance (402)
1. Check `health_check()` for current balance
2. Top up DataForSEO account
3. Skip enrichment and use existing data

### Invalid Domain
1. Domain returns empty results (not an error)
2. Use `_empty_labs_result()` / `_empty_backlinks_result()` structure
3. Score as 0 (no presence)

### API Unavailable
1. Built-in retry (3 attempts, exponential backoff)
2. If persistent, skip enrichment
3. Log for manual review

### Fallback Strategy

```python
async def enrich_with_fallback(domain: str) -> dict:
    """Enrich domain with graceful fallback."""
    try:
        client = get_dataforseo_client()
        return await client.get_full_domain_metrics(domain)
    except Exception as e:
        logger.warning(f"Enrichment failed for {domain}: {e}")
        # Return empty structure - scores will be 0
        return {
            "domain_rank": None,
            "organic_etv": None,
            "organic_count": None,
            "backlinks": None,
            "referring_domains": None,
            "spam_score": None,
            "enriched_at": datetime.utcnow().isoformat(),
            "enrichment_error": str(e)
        }
```

## Integration with ALS

DataForSEO metrics feed into the Agency Lead Score (ALS):

```python
async def calculate_als_seo_component(domain: str) -> dict:
    """Calculate SEO component of ALS."""
    client = get_dataforseo_client()
    metrics = await client.get_full_domain_metrics(domain)
    
    return {
        "domain_rank_score": client.score_domain_rank(metrics.get("domain_rank")),
        "traffic_score": client.score_organic_traffic(metrics.get("organic_etv")),
        "competence_score": client.score_seo_competence(metrics),
        "risk_deductions": client.calculate_risk_deductions(metrics),
        "raw_metrics": metrics
    }
```

## Notes

- **Trial period:** Backlinks API on 14-day trial (expires Jan 18, 2026)
- **Location codes:** 2036 = Australia, 2840 = USA, 2826 = UK
- **Domain cleaning:** Automatic (strips http/https, www, paths)
- **Caching:** Not built-in — implement at service layer if needed
