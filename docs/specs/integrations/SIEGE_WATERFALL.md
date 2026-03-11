# SIEGE Waterfall Integration

**File:** `src/integrations/siege_waterfall.py`  
**Purpose:** Unified 5-tier Australian B2B enrichment pipeline  
**Phase:** SIEGE (System Overhaul)  
**API Docs:** Internal architecture (orchestrates multiple providers)

---

## Overview

The SIEGE Waterfall replaces Apollo as the single source of truth for lead enrichment. It orchestrates a 5-tier waterfall with cost tracking and graceful degradation, reducing enrichment costs from ~$0.50/lead (Apollo) to ~$0.105/lead weighted average.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: ABN Bulk (data.gov.au)                                 │
│  ─────────────────────────────────────────────────────────────  │
│  • Australian Business Register lookup                          │
│  • ABN, ACN, entity type, GST status, location                  │
│  • Cost: $0.00 AUD | FREE with GUID registration                │
│  • Success: ~95% for AU businesses                              │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: GMB/Ads Signals (Google Maps scraping)                 │
│  ─────────────────────────────────────────────────────────────  │
│  • Phone, address, website, hours, reviews                      │
│  • Uses Bright Data Google Maps SERP (gd_m8ebnr0q2qlklc02fz)   │
│  • Cost: $0.001/request                                         │
│  • Success: ~80% for businesses with GMB presence               │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3: Leadmagic Email                                        │
│  ─────────────────────────────────────────────────────────────  │
│  • Email discovery and verification                             │
│  • Domain email patterns                                        │
│  • Cost: $0.015 AUD/lead | PRE_ALS_GATE ≥ 20                    │
│  • Dual-score: Propensity + Reachability (max 100 each)         │
│  • Success: ~70% for company domains                            │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 5: Leadmagic Mobile                                       │
│  ─────────────────────────────────────────────────────────────  │
│  • Verified mobile numbers for Voice AI/SMS                     │
│  • Personal email fallback                                      │
│  • Cost: $0.077 AUD/lead                                        │
│  • GATED: Only for ALS >= 85 (HOT leads)                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  DM TIERS: T-DM0 through T-DM4 (Decision-Maker Enrichment)      │
│  ─────────────────────────────────────────────────────────────  │
│  T-DM0: DataForSEO People Search — $0.0465/lead (ICP pass req.) │
│  T-DM1: Bright Data LinkedIn Profile — $0.0015 (ICP pass req.)  │
│  T-DM2: Bright Data LinkedIn People Search                      │
│  T-DM2b: Bright Data SERP LinkedIn                              │
│  T-DM3: Leadmagic LinkedIn Email                                │
│  T-DM4: Leadmagic Mobile — propensity ≥70 required              │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

Internal orchestration - no external endpoints. Calls child integrations:

| Tier | Integration | Module |
|------|-------------|--------|
| 1 | ABN Lookup | `src/integrations/abn_client.py` |
| 1.25 | ABR Trading Name | `src/integrations/abn_client.py` (trading name lookup) |
| 2 | GMB Scraper | `src/integrations/gmb_scraper.py` |
| 3 | Leadmagic Email | `src/integrations/leadmagic_email.py` |
| 5 | Leadmagic Mobile | `src/integrations/leadmagic_mobile.py` |

---

## Cost Per Operation ($AUD)

| Tier | Cost | Notes |
|------|------|-------|
| Tier 1 (ABN) | $0.00 | FREE - data.gov.au |
| Tier 2 (GMB) | $0.001 | Bright Data Google Maps SERP per request |
| Tier 3 (Leadmagic Email) | $0.015 | Per email verified, PRE_ALS_GATE ≥ 20 |
| Tier 5 (Leadmagic Mobile) | $0.077 | Only for ALS ≥ 85 |
| **Weighted Avg** | **~$0.105** | vs Apollo $0.50+ |

---

## Rate Limits

Rate limits are inherited from each tier's provider:

| Tier | Rate Limit |
|------|------------|
| ABN | Reasonable use policy (no hard limit) |
| GMB | 3 concurrent requests, 2-5s delay |
| Leadmagic Email | 15 requests/second |
| Leadmagic Mobile | 30 requests/minute |

---

## ALS (Aggregate Lead Score) Bonus

Multi-source enrichment triggers a 15-point ALS bonus:

```python
MIN_SOURCES_FOR_BONUS = 3
ALS_MULTI_SOURCE_BONUS = 15
```

Leads enriched from 3+ sources get the bonus, improving lead quality scoring.

---

## Error Handling

The waterfall gracefully degrades - tier failures don't stop enrichment:

```python
try:
    tier_result = await enrich_tier(lead_data)
except EnrichmentTierError as e:
    # Log failure, continue to next tier
    tier_results.append(TierResult(
        tier=current_tier,
        success=False,
        error=str(e),
    ))
except EnrichmentSkippedError as e:
    # Tier skipped (e.g., missing data for lookup)
    tier_results.append(TierResult(
        tier=current_tier,
        skipped=True,
        skip_reason=e.reason,
    ))
```

---

## Usage Pattern

```python
from src.integrations.siege_waterfall import SiegeWaterfall

# Initialize
waterfall = SiegeWaterfall()

# Enrich a lead
result = await waterfall.enrich(
    lead_data={
        "company_name": "Acme Pty Ltd",
        "domain": "acme.com.au",
        "state": "NSW",
    },
    propensity_score=75,  # Determines if Tier 5 runs
)

# Result contains
print(f"Total cost: ${result.total_cost_aud} AUD")
print(f"Sources used: {result.sources_used}")
print(f"ALS bonus applied: {result.als_bonus_applied}")
print(f"Enriched data: {result.enriched_data}")
```

---

## Environment Variables

```bash
# ABN Lookup (Tier 1)
ABN_GUID=your_registered_guid

# GMB/BrightData (Tier 2)
BRIGHTDATA_API_KEY=your_brightdata_key

# LeadMagic (Tier 3 - consolidated email/mobile enrichment)
LEADMAGIC_API_KEY=your_leadmagic_key
```

---

## Response Structure

```python
@dataclass
class EnrichmentResult:
    lead_id: str | None
    original_data: dict[str, Any]
    enriched_data: dict[str, Any]
    tier_results: list[TierResult]
    total_cost_aud: float
    sources_used: int
    als_bonus_applied: bool
    final_propensity_score: int | None
```
