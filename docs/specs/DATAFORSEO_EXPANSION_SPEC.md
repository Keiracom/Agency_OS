# DataForSEO Expansion Spec — Top 2 Capabilities

**Date:** 2026-01-30  
**Author:** Agent (Subagent task)  
**Status:** READY FOR IMPLEMENTATION

---

## Executive Summary

We currently use 3 of 71 DataForSEO endpoints at ~$0.03/lead:
- Labs API: `domain_rank_overview` ($0.0101)
- Backlinks API: `summary` ($0.02003)

**Recommendation:** Add 2 high-value endpoints that give marketing agencies immediately actionable competitive intelligence:

| Priority | Endpoint | Cost | Value to Agency Clients |
|----------|----------|------|------------------------|
| **#1** | Competitor Analysis | $0.0103 | "Who's beating you and why" |
| **#2** | Content Gap Analysis | $0.0103 | "Keywords your competitors rank for that you don't" |

**New cost per lead:** ~$0.05 (+$0.02)  
**Monthly cost at 1,000 leads:** $50 total (up from $30)

---

## Why These Two?

### Selection Criteria Applied:
1. **Value to agency clients** (what agencies can sell/present)
2. **Actionable output** (not just data, but recommendations)
3. **Differentiation** (what makes our agencies' pitches stand out)
4. **Cost efficiency** (high value per dollar)

### Rejected Alternatives:
| Endpoint | Why Rejected |
|----------|--------------|
| On-Page/Technical Audit | Per-site cost ($0.125/1000 pages) — better as separate product |
| SERP Tracking | Requires ongoing monitoring, different business model |
| Keyword Research | Commodity feature, every SEO tool has it |
| Backlink Gap | Useful but less actionable than content gap |
| Google Trends | Too broad, less specific to individual leads |

---

## Capability #1: Competitor Analysis

### API Details
- **Endpoint:** `/v3/dataforseo_labs/google/competitors_domain/live`
- **Cost:** $0.01 task + $0.0001 × items = **~$0.0103/request**
- **Response time:** ~0.5 seconds

### What It Returns
For a given domain, returns:
- Up to 1000 competitor domains ranked by keyword overlap
- Each competitor includes:
  - `intersections` — shared keywords count
  - `avg_position` — competitor's average rank vs target
  - `full_domain_metrics` — their organic ETV, keyword counts
  - `metrics` — overlap-specific metrics (where both rank)

### Value Proposition for Agency Clients
> "Here are the 10 companies stealing your traffic. Here's exactly how much they're getting and what content works for them."

### Use Cases
1. **Lead Enrichment:** Add "top 3 competitors" to lead profile for ALS scoring
2. **Client Reports:** Monthly competitive landscape updates
3. **Sales Pitches:** "You're losing X traffic to [competitor] because..."

### Sample Request
```python
data = [{
    "target": "clientdomain.com.au",
    "location_code": 2036,  # Australia
    "language_code": "en",
    "filters": [
        ["metrics.organic.count", ">=", 10]  # Only real competitors
    ],
    "limit": 10
}]
```

### Sample Response (condensed)
```json
{
    "result": [{
        "total_count": 847,
        "items": [{
            "domain": "competitor1.com.au",
            "avg_position": 12.5,
            "intersections": 156,
            "full_domain_metrics": {
                "organic": {
                    "etv": 45000,
                    "count": 2340
                }
            }
        }]
    }]
}
```

---

## Capability #2: Content Gap Analysis (Domain Intersection)

### API Details
- **Endpoint:** `/v3/dataforseo_labs/google/domain_intersection/live`
- **Cost:** $0.01 task + $0.0001 × items = **~$0.0103/request**
- **Response time:** ~10 seconds (complex query)

### What It Returns
Given two domains, returns:
- Keywords where BOTH rank (or optionally only one ranks)
- For each keyword:
  - Search volume, CPC, competition
  - Position of each domain
  - Keyword difficulty
  - SERP features present

### The "Gap" Query
To find keywords competitor ranks for but client doesn't:
```python
# Use exclude_filters to find where target1 doesn't rank
data = [{
    "target1": "clientdomain.com.au",
    "target2": "competitor.com.au",
    "location_code": 2036,
    "language_code": "en",
    "exclude_target1": True,  # Keywords competitor has that client doesn't
    "filters": [
        ["keyword_data.keyword_info.search_volume", ">", 100]
    ],
    "limit": 50
}]
```

### Value Proposition for Agency Clients
> "Here are 50 keywords your competitor ranks for that you don't — each one is a content opportunity. Total monthly search volume: 25,000."

### Use Cases
1. **Content Strategy:** Immediate list of blog posts to write
2. **Client Reports:** "Content opportunities missed this month"
3. **Sales Pitches:** Quantified opportunity ("$X in traffic you're missing")
4. **Campaign Planning:** Data-driven content calendar

### Sample Response (condensed)
```json
{
    "result": [{
        "total_count": 2847,
        "items": [{
            "keyword_data": {
                "keyword": "best marketing agency melbourne",
                "keyword_info": {
                    "search_volume": 880,
                    "cpc": 12.50,
                    "competition": 0.65
                },
                "keyword_properties": {
                    "keyword_difficulty": 42
                }
            },
            "second_domain_serp_element": {
                "etv": 234,
                "position": 4
            }
        }]
    }]
}
```

---

## Implementation Plan

### Phase 1: Add to DataForSEO Client (Day 1-2)

**File:** `src/integrations/dataforseo.py`

```python
async def get_competitors(
    self,
    domain: str,
    location_code: int = 2036,  # Australia
    language_code: str = "en",
    limit: int = 10,
    min_organic_count: int = 10,
) -> dict[str, Any]:
    """
    Get competitor domains for a given domain.
    
    Endpoint: /dataforseo_labs/google/competitors_domain/live
    Cost: $0.0103 per request
    
    Returns:
        Dict with competitors list, each containing:
        - domain
        - intersections (shared keyword count)
        - avg_position
        - full_domain_metrics (organic ETV, count, etc.)
    """
    clean_domain = self._clean_domain(domain)
    if not clean_domain:
        return {"competitors": [], "total_count": 0}
    
    data = [{
        "target": clean_domain,
        "location_code": location_code,
        "language_code": language_code,
        "filters": [
            ["metrics.organic.count", ">=", min_organic_count]
        ],
        "limit": limit
    }]
    
    response = await self._request(
        method="POST",
        endpoint="/dataforseo_labs/google/competitors_domain/live",
        data=data,
    )
    
    return self._parse_competitors_response(response)


async def get_content_gaps(
    self,
    client_domain: str,
    competitor_domain: str,
    location_code: int = 2036,
    language_code: str = "en",
    min_search_volume: int = 100,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Get keywords competitor ranks for that client doesn't.
    
    Endpoint: /dataforseo_labs/google/domain_intersection/live
    Cost: $0.0103 per request
    
    Returns:
        Dict with keyword opportunities, each containing:
        - keyword
        - search_volume
        - cpc
        - keyword_difficulty
        - competitor_position
        - competitor_etv
    """
    clean_client = self._clean_domain(client_domain)
    clean_competitor = self._clean_domain(competitor_domain)
    
    if not clean_client or not clean_competitor:
        return {"opportunities": [], "total_count": 0}
    
    # Get intersection, then filter for where only competitor ranks
    data = [{
        "target1": clean_client,
        "target2": clean_competitor,
        "location_code": location_code,
        "language_code": language_code,
        "filters": [
            ["first_domain_serp_element", "=", None],  # Client doesn't rank
            "and",
            ["keyword_data.keyword_info.search_volume", ">", min_search_volume]
        ],
        "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        "limit": limit
    }]
    
    response = await self._request(
        method="POST",
        endpoint="/dataforseo_labs/google/domain_intersection/live",
        data=data,
    )
    
    return self._parse_content_gaps_response(response)
```

### Phase 2: Add to Enrichment Pipeline (Day 2-3)

**Option A: Lead Enrichment (Always Run)**
- Add competitor data to every lead
- Pro: Rich data for ALS scoring
- Con: Adds $0.02/lead

**Option B: On-Demand Enrichment (Recommended)**
- Run when lead progresses to "Qualified" stage
- Run when generating client reports
- Pro: Cost-efficient, data when needed
- Con: Slightly more complex

### Phase 3: Add Reporting Endpoints (Day 3-4)

Create FastAPI endpoints for dashboard consumption:

```python
# src/api/routes/intelligence.py

@router.get("/leads/{lead_id}/competitors")
async def get_lead_competitors(lead_id: UUID):
    """Get top competitors for a lead's domain."""
    ...

@router.get("/leads/{lead_id}/content-gaps/{competitor_domain}")
async def get_content_gaps(lead_id: UUID, competitor_domain: str):
    """Get content opportunities vs specific competitor."""
    ...
```

---

## Cost Analysis

### Current State (per lead)
| API Call | Cost |
|----------|------|
| domain_rank_overview | $0.0101 |
| backlinks/summary | $0.02003 |
| **Total** | **$0.03** |

### Proposed State (per enriched lead)
| API Call | Cost |
|----------|------|
| domain_rank_overview | $0.0101 |
| backlinks/summary | $0.02003 |
| competitors_domain | $0.0103 |
| domain_intersection | $0.0103 |
| **Total** | **$0.05** |

### Monthly Projections

| Leads/Month | Current | With New APIs | Delta |
|-------------|---------|---------------|-------|
| 500 | $15 | $25 | +$10 |
| 1,000 | $30 | $50 | +$20 |
| 5,000 | $150 | $250 | +$100 |
| 10,000 | $300 | $500 | +$200 |

**Note:** If using on-demand enrichment (only qualified leads), actual cost increase will be ~30-50% of above.

---

## ALS Integration

### New Scoring Signals

```python
def score_competitive_position(self, metrics: dict) -> int:
    """
    Score based on competitive landscape.
    
    Factors:
    - Few strong competitors = easier market
    - Weak competitors = opportunity
    - Many overlapping keywords = contestable market
    """
    competitors = metrics.get("competitors", [])
    
    if not competitors:
        return 0  # No data
    
    # Fewer than 5 real competitors = easier market
    if len(competitors) < 5:
        return 3
    
    # Calculate average competitor strength
    avg_competitor_etv = mean([
        c.get("full_domain_metrics", {}).get("organic", {}).get("etv", 0)
        for c in competitors
    ])
    
    # Weak competitors = opportunity
    if avg_competitor_etv < 10000:
        return 4
    elif avg_competitor_etv < 50000:
        return 2
    else:
        return 0  # Strong competitors, harder market


def score_content_opportunity(self, gaps: dict) -> int:
    """
    Score based on content gap size.
    
    Large gaps = more opportunity = higher score
    """
    total_volume = sum([
        g.get("search_volume", 0) 
        for g in gaps.get("opportunities", [])
    ])
    
    if total_volume > 50000:
        return 5  # Massive opportunity
    elif total_volume > 10000:
        return 4
    elif total_volume > 5000:
        return 3
    elif total_volume > 1000:
        return 2
    else:
        return 1
```

---

## Testing Plan

### Unit Tests
```python
# tests/unit/test_dataforseo_competitors.py

async def test_get_competitors_returns_sorted_list():
    """Competitors should be sorted by intersection count."""
    ...

async def test_get_content_gaps_filters_low_volume():
    """Keywords under min_search_volume should be excluded."""
    ...

async def test_empty_domain_returns_empty_result():
    """Invalid domains should return empty, not error."""
    ...
```

### Integration Tests
```python
# tests/integration/test_dataforseo_live.py

@pytest.mark.integration
async def test_competitors_live_api():
    """Test against live API with known domain."""
    client = DataForSEOClient()
    result = await client.get_competitors("ahrefs.com")
    
    assert result["total_count"] > 0
    assert len(result["competitors"]) <= 10
    assert result["competitors"][0]["domain"]
```

---

## Rollout Plan

| Day | Task | Owner |
|-----|------|-------|
| 1 | Add methods to DataForSEO client | Dev |
| 1 | Add response parsing + tests | Dev |
| 2 | Add API endpoints | Dev |
| 2 | Integration tests | Dev |
| 3 | Add to enrichment pipeline (on-demand) | Dev |
| 3 | Add ALS scoring signals | Dev |
| 4 | Dashboard UI for competitor view | Frontend |
| 4 | Documentation | Dev |

---

## Success Metrics

1. **Adoption:** 80%+ of qualified leads enriched with competitor data within 2 weeks
2. **Cost:** Monthly DataForSEO spend increases by <100%
3. **Value:** Agency clients mention "competitor insights" in feedback
4. **ALS:** Competitive signals correlate with close rate

---

## Appendix: Full DataForSEO Labs Endpoint List

For reference, here are all Labs API endpoints we could add later:

| Endpoint | Cost | Use Case |
|----------|------|----------|
| keywords_for_site | $0.0103 | Full keyword profile |
| keyword_suggestions | $0.0103 | Expand keyword lists |
| related_keywords | $0.0103 | Semantic clustering |
| serp_competitors | $0.0105 | SERP-level competition |
| ranked_keywords | $0.0103 | What keywords domain ranks for |
| historical_rank | $0.106/domain | Rank trends over time |
| bulk_keyword_difficulty | $0.0103 | Batch difficulty scoring |

---

## Sign-Off

**Ready for implementation.** Recommend starting with Day 1 tasks immediately.

Cost increase is modest ($20/month at 1000 leads) for significant value add that differentiates Agency OS from competitors who only provide basic SEO metrics.
