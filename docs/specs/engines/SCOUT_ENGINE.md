# Scout Engine — Lead Enrichment

**File:** `src/engines/scout.py`  
**Purpose:** Enrich leads with contact data using waterfall approach  
**Layer:** 3 - engines

---

## Waterfall Logic

```
Tier 0: Check Cache
    │
    ├── Cache hit (soft validation) ──► Return cached data
    │
    └── Cache miss
            │
            ▼
Tier 1: Apollo + Apify Hybrid
    │
    ├── Success (confidence ≥ 0.70) ──► Cache & return
    │
    └── Partial/failure
            │
            ▼
Tier 2: Clay Fallback (max 15% of batch)
    │
    └── Return best available data
```

---

## Validation Rules

| Field | Required | Validation |
|-------|----------|------------|
| email | Yes | Valid format, not disposable |
| first_name | Yes | Non-empty |
| last_name | Yes | Non-empty |
| company | Yes | Non-empty |
| title | No | — |
| phone | No | Valid format if present |
| linkedin_url | No | Valid LinkedIn URL if present |

**Minimum confidence threshold:** 0.70

---

## Cache Strategy

- **Key format:** `v1:enrichment:{domain}:{email_hash}`
- **TTL:** 90 days
- **Soft validation:** Check if cached data still meets minimum fields

---

## API

```python
class ScoutEngine:
    async def enrich(
        self,
        db: AsyncSession,
        domain: str,
        client_id: UUID,
        max_leads: int = 100
    ) -> list[EnrichedLead]:
        """
        Enrich leads for a domain using waterfall approach.
        
        Args:
            db: Database session (passed by caller)
            domain: Target domain to find leads
            client_id: Client for billing/tracking
            max_leads: Maximum leads to return
            
        Returns:
            List of enriched leads meeting validation threshold
        """
        ...
    
    async def enrich_single(
        self,
        db: AsyncSession,
        email: str,
        client_id: UUID
    ) -> EnrichedLead | None:
        """Enrich a single known email address."""
        ...
```

---

## Cost per Lead

| Source | Cost | When Used |
|--------|------|-----------|
| Cache | $0 | Always checked first |
| Apollo | ~$0.02 | Primary source |
| Apify | ~$0.01 | Bulk scraping supplement |
| Clay | ~$0.25-0.50 | Fallback (max 15%) |

**Blended cost:** ~$0.13/lead
