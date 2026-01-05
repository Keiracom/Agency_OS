# DataForSEO Integration

**File:** `src/integrations/dataforseo.py`  
**Purpose:** SEO metrics for ALS scoring  
**API Docs:** https://docs.dataforseo.com/

---

## Capabilities

- Domain rank (authority metric)
- Organic traffic estimates
- Keyword rankings
- Backlink analysis
- Spam score

---

## APIs Used

| API | Endpoint | Cost | Purpose |
|-----|----------|------|---------|
| Labs | `/v3/dataforseo_labs/google/domain_rank_overview/live` | $0.01 | Traffic, keywords |
| Backlinks | `/v3/backlinks/summary/live` | $0.02 | Domain rank, backlinks |

**Total per domain:** ~$0.03 AUD

---

## Usage Pattern

```python
class DataForSEOClient:
    def __init__(self, login: str, password: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.dataforseo.com",
            auth=(login, password)
        )
    
    async def get_domain_metrics(
        self,
        domain: str
    ) -> DomainMetrics:
        """Get SEO metrics for domain."""
        
        # Labs API - traffic and keywords
        labs_response = await self.client.post(
            "/v3/dataforseo_labs/google/domain_rank_overview/live",
            json=[{"target": domain, "location_code": 2036}]  # Australia
        )
        labs_data = labs_response.json()
        
        # Backlinks API - domain rank
        backlinks_response = await self.client.post(
            "/v3/backlinks/summary/live",
            json=[{"target": domain}]
        )
        backlinks_data = backlinks_response.json()
        
        return DomainMetrics(
            domain_rank=backlinks_data["tasks"][0]["result"][0]["rank"],
            organic_traffic=labs_data["tasks"][0]["result"][0]["metrics"]["organic"]["etv"],
            top10_keywords=labs_data["tasks"][0]["result"][0]["metrics"]["organic"]["count"],
            backlinks=backlinks_data["tasks"][0]["result"][0]["backlinks"],
            spam_score=backlinks_data["tasks"][0]["result"][0]["spam_score"]
        )
```

---

## ALS Scoring Integration

### Company Fit Sub-Scoring (5 points from DataForSEO)

| Metric | Points | Threshold |
|--------|--------|-----------|
| Domain Rank | 0-2 | 0-150: 0pts, 151-500: 1pt, 501+: 2pts |
| Organic Traffic (ETV) | 0-2 | 0-200: 0pts, 201-1000: 1pt, 1001+: 2pts |
| Top 10 Keywords | 0-1 | >0 keywords in pos 1-10: 1pt |

### Risk Deductions

| Signal | Deduction | Logic |
|--------|-----------|-------|
| No Domain Rank | -5 | No web presence = suspicious |
| No Organic Traffic | -3 | Doesn't practice what they preach |
| Spam Score >50 | -3 | Low quality backlinks |

---

## Caching

- **Key:** `v1:dataforseo:{domain}`
- **TTL:** 30 days
- **Expected cache hit rate:** 40%

```python
async def get_cached_metrics(self, domain: str) -> DomainMetrics | None:
    """Check cache before API call."""
    cached = await self.redis.get(f"v1:dataforseo:{domain}")
    if cached:
        return DomainMetrics.model_validate_json(cached)
    return None

async def cache_metrics(self, domain: str, metrics: DomainMetrics):
    """Cache metrics for 30 days."""
    await self.redis.setex(
        f"v1:dataforseo:{domain}",
        60 * 60 * 24 * 30,  # 30 days
        metrics.model_dump_json()
    )
```

---

## Rate Limits

- **Standard:** 2000 requests/minute
- **Burst:** Higher for short periods
