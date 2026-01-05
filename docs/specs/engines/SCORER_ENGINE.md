# Scorer Engine — ALS Calculation

**File:** `src/engines/scorer.py`  
**Purpose:** Calculate ALS (Agency Lead Score) for leads  
**Layer:** 3 - engines

---

## ALS Formula (5 Components, 100 points max)

| Component | Max Points | Weight | Description |
|-----------|------------|--------|-------------|
| Data Quality | 20 | 0.15 | Contact completeness |
| Authority | 25 | 0.30 | Decision-making power |
| Company Fit | 25 | 0.25 | ICP alignment + SEO signals |
| Timing | 15 | 0.20 | Intent/urgency signals |
| Risk | 15 | 0.10 | Negative indicators |

---

## Component Breakdown

### Data Quality (20 points)

| Signal | Points |
|--------|--------|
| Email verified | 8 |
| Phone number present | 6 |
| LinkedIn URL present | 4 |
| Personal email (Gmail, etc.) | 2 |

### Authority (25 points)

| Title Pattern | Points |
|---------------|--------|
| Owner, CEO, Founder | 25 |
| C-Suite (CTO, CMO, CFO) | 22 |
| VP, Vice President | 18 |
| Director | 15 |
| Senior Manager | 10 |
| Manager | 7 |
| Other | 3 |

### Company Fit (25 points)

| Signal | Points | Source |
|--------|--------|--------|
| Matching industry | 10 | Apollo |
| Employee count 5-50 | 5 | Apollo |
| Australia location | 5 | Apollo |
| **DataForSEO Domain Rank** | 0-2 | DataForSEO |
| **DataForSEO Organic Traffic** | 0-2 | DataForSEO |
| **DataForSEO Top 10 Keywords** | 0-1 | DataForSEO |

**DataForSEO Scoring:**

| Signal | Points | Threshold |
|--------|--------|-----------|
| Domain Rank | 0 | 0-150 |
| Domain Rank | 1 | 151-500 |
| Domain Rank | 2 | 501+ |
| Organic Traffic (ETV) | 0 | 0-200 |
| Organic Traffic (ETV) | 1 | 201-1000 |
| Organic Traffic (ETV) | 2 | 1001+ |
| Top 10 Keywords | 1 | >0 keywords |

### Timing (15 points)

| Signal | Points |
|--------|--------|
| New role <6 months | 6 |
| Company is hiring | 5 |
| Funded in last 12 months | 4 |

### Risk (15 points - deductions)

| Signal | Deduction |
|--------|-----------|
| Previously bounced | -8 |
| Previously unsubscribed | -15 (exclude) |
| Competitor domain | -10 |
| Irrelevant title | -5 |
| No Domain Rank (DataForSEO) | -5 |
| No Organic Traffic | -3 |
| Spam Score >50 | -3 |

---

## Tier Assignment

| ALS Score | Tier | Channels Available |
|-----------|------|-------------------|
| **85-100** | Hot | Email, SMS, LinkedIn, Voice, Direct Mail |
| **60-84** | Warm | Email, LinkedIn, Voice |
| **35-59** | Cool | Email, LinkedIn |
| **20-34** | Cold | Email only |
| **<20** | Dead | None (suppress) |

**CRITICAL:** Hot tier starts at 85, NOT 80.

---

## Weight Fallback Hierarchy (Phase 16+)

```python
async def _get_weights(self, db: AsyncSession, client_id: UUID) -> tuple[dict, str]:
    """
    Weight fallback hierarchy:
    1. Client learned weights (if confidence > 0.7 and sample >= 50)
    2. Industry-specific platform weights
    3. Global platform weights
    4. Platform priors (industry benchmarks)
    5. Default weights
    """
    
    # 1. Client's own learned weights
    client_weights = await self._get_client_learned_weights(db, client_id)
    if client_weights and client_weights.confidence > 0.7:
        return client_weights.weights, "client_learned"
    
    # 2. Industry-specific platform weights
    # ... (see PROGRESS.md Phase 20)
    
    # 5. Default weights
    return DEFAULT_WEIGHTS, "default"
```

---

## DataForSEO Integration

**APIs Used:**
- Labs API: `domain_rank_overview` ($0.01/request)
- Backlinks API: `summary` ($0.02/request)

**Cost per Lead:** ~$0.03  
**Caching:** 30-day TTL by domain

```python
async def _get_dataforseo_signals(self, domain: str) -> DataForSEOSignals:
    # Check cache first
    cached = await self.redis.get(f"dataforseo:{domain}")
    if cached:
        return DataForSEOSignals.parse_raw(cached)
    
    # Fetch fresh data
    signals = await self.dataforseo.get_domain_metrics(domain)
    
    # Cache for 30 days
    await self.redis.set(f"dataforseo:{domain}", signals.json(), ex=2592000)
    
    return signals
```

---

## API

```python
class ScorerEngine:
    async def score(
        self,
        db: AsyncSession,
        lead_id: UUID,
        force_rescore: bool = False
    ) -> ScoringResult:
        """
        Calculate ALS score for a lead.
        
        Returns:
            ScoringResult with score, tier, components, and weights_used
        """
        ...
    
    async def batch_score(
        self,
        db: AsyncSession,
        lead_ids: list[UUID]
    ) -> list[ScoringResult]:
        """Score multiple leads efficiently."""
        ...
```
