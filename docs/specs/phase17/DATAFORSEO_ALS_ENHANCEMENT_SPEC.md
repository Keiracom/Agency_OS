# DataForSEO ALS Enhancement Spec

**Version:** 2.0  
**Created:** January 4, 2026  
**Updated:** January 4, 2026  
**Status:** ✅ VERIFIED & ACTIVE  
**Author:** Dave + Claude

> **✅ APIs VERIFIED:** Both Labs API and Backlinks API tested and working as of January 4, 2026.
> - Labs API: No subscription required, pay-as-you-go
> - Backlinks API: 14-day trial active (expires Jan 18, 2026), then $100/mo minimum

---

## Executive Summary

Enhance the Agency Lead Score (ALS) system with DataForSEO signals to better qualify marketing agencies based on their actual SEO performance—their core competency.

---

## Problem Statement

Current ALS scores marketing agencies based on:
- Contact data quality (Apollo)
- Job title/authority (Apollo)
- Company firmographics (Apollo)
- Timing signals (Apollo)
- Risk factors (internal)

**Gap:** We don't assess whether the agency is actually good at marketing. An agency with 20 employees and a CEO contact could be:
- A thriving agency with strong SEO presence
- A struggling agency with no online visibility
- A fake/shell company

For marketing agencies specifically, their own SEO performance is a direct indicator of competence and business health.

---

## Proposed Solution

Add DataForSEO enrichment to the lead scoring pipeline, contributing new signals to the **Company Fit** and **Timing** components of ALS.

---

## DataForSEO Signals

### Verified API Endpoints (Jan 4, 2026)

| API | Endpoint | Cost | Data Returned |
|-----|----------|------|---------------|
| **Labs API** | `/dataforseo_labs/google/domain_rank_overview/live` | $0.0101 | organic_etv, organic_count, pos_1, pos_2_3, pos_4_10 |
| **Backlinks API** | `/backlinks/summary/live` | $0.02003 | rank, backlinks, referring_domains, spam_score |

### Primary Signals (High Value)

| Signal | API | Field | ALS Component | Scoring Logic |
|--------|-----|-------|---------------|---------------|
| **Domain Rank** | Backlinks | `rank` | Company Fit | Higher = more established (0-1000+ scale) |
| **Organic Traffic** | Labs | `metrics.organic.etv` | Company Fit | Monthly traffic estimate |
| **Keyword Count** | Labs | `metrics.organic.count` | Company Fit | Keywords ranking |
| **Top 10 Rankings** | Labs | `pos_1 + pos_2_3 + pos_4_10` | Company Fit | SEO competence indicator |
| **Referring Domains** | Backlinks | `referring_domains` | Company Fit | Link diversity |
| **Spam Score** | Backlinks | `backlinks_spam_score` | Risk | Quality indicator (lower=better) |

### Secondary Signals (Nice to Have)

| Signal | API Endpoint | ALS Component | Scoring Logic |
|--------|--------------|---------------|---------------|
| **Top Keywords** | Ranked Keywords | Company Fit | Ranking for industry terms |
| **Local Pack Rankings** | SERP | Company Fit | "[service] + [city]" presence |
| **Tech Stack** | Technologies | Company Fit | Marketing tool sophistication |

---

## Scoring Weight Adjustments

### Current ALS Weights (Default)

```
data_quality:  20% (20 points)
authority:     25% (25 points)
company_fit:   25% (25 points)
timing:        15% (15 points)
risk:          15% (15 points)
```

### Proposed: Company Fit Breakdown (25 points total)

| Sub-Component | Points | Source |
|---------------|--------|--------|
| Industry Match | 6 | Apollo |
| Employee Count | 5 | Apollo |
| Country/Region | 4 | Apollo |
| **Domain Authority** | 5 | DataForSEO |
| **Organic Presence** | 5 | DataForSEO |

### Proposed: Timing Breakdown (15 points total)

| Sub-Component | Points | Source |
|---------------|--------|--------|
| New Role (<6mo) | 5 | Apollo |
| Company Hiring | 4 | Apollo |
| Recent Funding | 3 | Apollo |
| **Traffic Trend** | 3 | DataForSEO |

---

## Scoring Rubric: Domain Rank

DataForSEO Backlinks API returns rank on 0-1000+ scale (NOT 0-100 like Moz DA).
Higher = more authoritative.

| Domain Rank | Points | Interpretation |
|-------------|--------|----------------|
| 0-50 | 0 | New/invisible site |
| 51-150 | 1 | Small local presence |
| 151-300 | 2 | Established local agency |
| 301-500 | 3 | Strong regional agency |
| 501-800 | 4 | Well-known agency |
| 801+ | 5 | Industry leader |

**Example (verified):** webprofits.com.au = Rank 337 → 3 points

---

## Scoring Rubric: Organic Presence

Based on Estimated Traffic Value (ETV) from Labs API.

| ETV (Monthly) | Points | Interpretation |
|---------------|--------|----------------|
| 0-50 | 0 | No organic presence |
| 51-200 | 1 | Minimal presence |
| 201-1,000 | 2 | Growing presence |
| 1,001-5,000 | 3 | Solid presence |
| 5,001-20,000 | 4 | Strong presence |
| 20,001+ | 5 | Dominant presence |

**Example (verified):** webprofits.com.au = ETV 149.89 → 1 point

---

## Scoring Rubric: Traffic Trend

Based on 3-month traffic direction (requires historical data).

| Trend | Points | Interpretation |
|-------|--------|----------------|
| Declining >20% | 3 | Pain point - needs help |
| Declining 5-20% | 2 | Slight concern |
| Stable (±5%) | 1 | Maintaining |
| Growing 5-20% | 2 | Healthy growth |
| Growing >20% | 3 | Rapid growth - has budget |

**Note:** Both declining AND growing agencies get higher timing scores but for different reasons:
- Declining = pain point, might need Agency OS to fix their client acquisition
- Growing = has momentum and budget, ready to scale

---

## Risk Signals (Deductions)

| Signal | Deduction | Logic |
|--------|-----------|-------|
| Domain Rank 0 | -5 | No web presence = suspicious |
| No organic traffic | -3 | Agency doesn't practice what they preach |
| Domain age <1 year + low DR | -3 | New and unproven |

---

## Data Model Changes

### Lead Model Additions

```python
# DataForSEO enrichment fields
dataforseo_domain_rank: int | None
dataforseo_organic_traffic: int | None
dataforseo_traffic_trend: str | None  # "growing", "stable", "declining"
dataforseo_backlinks: int | None
dataforseo_referring_domains: int | None
dataforseo_enriched_at: datetime | None
```

### ALS Components Update

```python
als_components = {
    "data_quality": 18,
    "authority": 22,
    "company_fit": {
        "apollo": 15,        # industry, employees, country
        "dataforseo": 8,     # domain rank, organic presence
    },
    "timing": {
        "apollo": 10,        # new role, hiring, funding
        "dataforseo": 3,     # traffic trend
    },
    "risk": 12,
}
```

---

## API Integration

### DataForSEO Endpoints (Verified)

1. **Labs - Domain Rank Overview** (`/v3/dataforseo_labs/google/domain_rank_overview/live`)
   - Organic traffic (ETV)
   - Keyword count
   - Position distribution (pos_1, pos_2_3, pos_4_10)
   - Estimated paid traffic cost

2. **Backlinks - Summary** (`/v3/backlinks/summary/live`)
   - Domain Rank (0-1000+ scale)
   - Total backlinks
   - Referring domains
   - Spam score

### Request Example (Verified Working)

```python
import requests

def get_full_domain_metrics(domain: str) -> dict:
    """Get SEO metrics for a domain from DataForSEO."""
    
    login = "your_email@example.com"
    password = "your_api_key"
    
    # Labs API - Organic metrics
    labs_response = requests.post(
        "https://api.dataforseo.com/v3/dataforseo_labs/google/domain_rank_overview/live",
        auth=(login, password),
        json=[{
            "target": domain,
            "location_code": 2036,  # Australia
            "language_code": "en",
        }]
    )
    
    # Backlinks API - Authority metrics
    backlinks_response = requests.post(
        "https://api.dataforseo.com/v3/backlinks/summary/live",
        auth=(login, password),
        json=[{
            "target": domain,
            "include_subdomains": True,
        }]
    )
    
    # Parse Labs response
    labs_data = labs_response.json()
    labs_item = labs_data["tasks"][0]["result"][0]["items"][0]
    organic = labs_item["metrics"]["organic"]
    
    # Parse Backlinks response
    backlinks_data = backlinks_response.json()
    backlinks_result = backlinks_data["tasks"][0]["result"][0]
    
    return {
        "domain_rank": backlinks_result.get("rank"),
        "organic_etv": organic.get("etv"),
        "organic_count": organic.get("count"),
        "top_10_keywords": organic.get("pos_1", 0) + organic.get("pos_2_3", 0) + organic.get("pos_4_10", 0),
        "backlinks": backlinks_result.get("backlinks"),
        "referring_domains": backlinks_result.get("referring_domains"),
        "spam_score": backlinks_result.get("backlinks_spam_score"),
    }

# Example output for webprofits.com.au:
# {
#     "domain_rank": 337,
#     "organic_etv": 149.89,
#     "organic_count": 99,
#     "top_10_keywords": 7,
#     "backlinks": 19578,
#     "referring_domains": 1429,
#     "spam_score": 28
# }
```

### Authentication

DataForSEO uses HTTP Basic Auth with login (email) and password (API key).

```
DATAFORSEO_LOGIN=your_email@example.com
DATAFORSEO_PASSWORD=your_api_key
```

---

## Cost Analysis

### Per-Request Costs (Verified Jan 4, 2026)

| Endpoint | Cost | Notes |
|----------|------|-------|
| Labs domain_rank_overview | $0.0101 | Organic traffic, keywords |
| Backlinks summary | $0.02003 | Domain rank, backlinks |
| **Combined per lead** | **$0.03** | Both APIs |

### Projected Monthly Costs

| Tier | Leads/Month | DataForSEO Cost | % of COGS |
|------|-------------|-----------------|-----------|
| Ignition | 1,250 | $37.50 | 5.6% |
| Velocity | 2,250 | $67.50 | 5.1% |
| Dominance | 4,500 | $135.00 | 5.4% |

**With 40% cache hit rate:**

| Tier | Unique Domains | DataForSEO Cost | % of COGS |
|------|----------------|-----------------|-----------|
| Ignition | ~750 | $22.50 | 3.4% |
| Velocity | ~1,350 | $40.50 | 3.1% |
| Dominance | ~2,700 | $81.00 | 3.2% |

---

## Caching Strategy

To minimize API costs:

1. **Cache by domain** - Multiple leads from same company share one lookup
2. **TTL: 30 days** - SEO metrics don't change rapidly
3. **Store in leads table** - Persist for scoring history

### Expected Cache Hit Rate

If 40% of leads share domains with other leads:
- 1,250 leads → ~750 unique domains → $7.50/month

---

## Implementation Phases

### Phase A: Spec (This Document) ✅
- Define signals and scoring rubrics
- Cost analysis
- Data model changes

### Phase B: Integration
- Create `src/integrations/dataforseo.py`
- Add to enrichment pipeline
- Update Lead model

### Phase C: Scorer Enhancement
- Modify `src/engines/scorer.py`
- Add DataForSEO sub-components
- Update scoring logic

### Phase D: Testing
- Unit tests for DataForSEO integration
- Scoring validation with sample agencies
- A/B test against Apollo-only scoring

---

## Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| ALS correlation with conversion | Unknown | +15% improvement |
| Hot tier conversion rate | TBD | Higher than warm |
| False positive rate (high ALS, no conversion) | TBD | <20% |

---

## Open Questions

1. **Historical data cost** - Is traffic trend worth $0.02 extra per lead?
2. **Minimum threshold** - Should we skip DataForSEO for leads without domain?
3. **Weight tuning** - Should Conversion Intelligence adjust DataForSEO weights separately?

---

## Appendix: DataForSEO Account Details

- **Balance:** $45.59 USD
- **Labs API:** ✅ Active (pay-as-you-go)
- **Backlinks API:** ✅ Active (14-day trial until Jan 18, 2026)
- **Dashboard:** https://app.dataforseo.com/api-dashboard
- **Docs:** https://docs.dataforseo.com/

### Post-Trial Action Required
After Jan 18, 2026, Backlinks API requires $100/mo minimum top-up.
Alternative: Use via n8n/Make (no minimum commitment).

---

## Next Steps

- [x] Review and approve spec
- [x] Add DataForSEO credentials to `.env`
- [x] Implement `src/integrations/dataforseo.py`
- [ ] Update Lead model with new fields
- [ ] Enhance ScorerEngine with DataForSEO signals
- [ ] Add DataForSEO to Scout enrichment pipeline
- [ ] Test with real agency domains
