# DataForSEO ALS Enhancement Spec

**Version:** 1.0  
**Created:** January 4, 2026  
**Status:** Integration Complete - Awaiting API Enablement  
**Author:** Dave + Claude

> **Note:** DataForSEO Labs API access pending. Support ticket submitted. Integration code is ready and will activate automatically once API is enabled.

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

### Primary Signals (High Value)

| Signal | API Endpoint | ALS Component | Scoring Logic |
|--------|--------------|---------------|---------------|
| **Domain Rank** | Domain Overview | Company Fit | Higher = more established |
| **Organic Traffic** | Domain Overview | Company Fit | Monthly visitors estimate |
| **Organic Traffic Trend** | Historical Data | Timing | Growing/declining |
| **Backlink Count** | Backlinks Summary | Company Fit | Quality indicator |
| **Referring Domains** | Backlinks Summary | Company Fit | Diversity indicator |

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

## Scoring Rubric: Domain Authority

DataForSEO's Domain Rank is 0-100 scale.

| Domain Rank | Points | Interpretation |
|-------------|--------|----------------|
| 0-10 | 0 | New/invisible site |
| 11-25 | 1 | Small local presence |
| 26-40 | 2 | Established local agency |
| 41-55 | 3 | Strong regional agency |
| 56-70 | 4 | Well-known agency |
| 71+ | 5 | Industry leader |

---

## Scoring Rubric: Organic Presence

Based on estimated monthly organic traffic.

| Monthly Traffic | Points | Interpretation |
|-----------------|--------|----------------|
| 0-100 | 0 | No organic presence |
| 101-500 | 1 | Minimal presence |
| 501-2,000 | 2 | Growing presence |
| 2,001-10,000 | 3 | Solid presence |
| 10,001-50,000 | 4 | Strong presence |
| 50,001+ | 5 | Dominant presence |

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

### DataForSEO Endpoints Required

1. **Domain Overview** (`/v3/dataforseo_labs/google/domain_overview/live`)
   - Domain rank
   - Organic traffic
   - Backlinks count

2. **Historical Rank** (`/v3/dataforseo_labs/google/historical_rank_overview/live`) [Optional]
   - Traffic trend over time

### Request Example

```python
import requests

def get_domain_metrics(domain: str) -> dict:
    """Get SEO metrics for a domain from DataForSEO."""
    
    response = requests.post(
        "https://api.dataforseo.com/v3/dataforseo_labs/google/domain_overview/live",
        auth=(DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD),
        json=[{
            "target": domain,
            "location_code": 2036,  # Australia
            "language_code": "en",
        }]
    )
    
    data = response.json()
    result = data["tasks"][0]["result"][0]
    
    return {
        "domain_rank": result.get("rank"),
        "organic_traffic": result.get("organic_traffic"),
        "backlinks": result.get("backlinks"),
        "referring_domains": result.get("referring_domains"),
    }
```

### Authentication

DataForSEO uses HTTP Basic Auth with login (email) and password (API key).

```
DATAFORSEO_LOGIN=your_email@example.com
DATAFORSEO_PASSWORD=your_api_key
```

---

## Cost Analysis

### Per-Request Costs

| Endpoint | Cost | Notes |
|----------|------|-------|
| Domain Overview | $0.01 | Primary data source |
| Historical Rank | $0.02 | Optional, for trend |
| Backlinks Summary | $0.02 | If needed separately |

### Projected Monthly Costs

| Tier | Leads/Month | DataForSEO Cost | % of COGS |
|------|-------------|-----------------|-----------|
| Ignition | 1,250 | $12.50 | 1.9% |
| Velocity | 2,250 | $22.50 | 1.7% |
| Dominance | 4,500 | $45.00 | 1.8% |

**Impact on margins:** Negligible (<2% of COGS)

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

- **Balance:** $45.66
- **Estimated days:** 258 (at current usage)
- **Dashboard:** https://app.dataforseo.com/api-dashboard
- **Docs:** https://docs.dataforseo.com/

---

## Next Steps

1. [ ] Review and approve spec
2. [ ] Add DataForSEO credentials to `.env`
3. [ ] Implement `src/integrations/dataforseo.py`
4. [ ] Update Lead model with new fields
5. [ ] Enhance ScorerEngine
6. [ ] Test with real agency domains
