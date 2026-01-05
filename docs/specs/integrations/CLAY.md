# Clay Integration

**File:** `src/integrations/clay.py`  
**Purpose:** Premium enrichment waterfall fallback  
**API Docs:** https://docs.clay.com/

---

## Capabilities

- Waterfall enrichment across 50+ providers
- Custom enrichment tables
- AI-powered data extraction
- Webhook triggers

---

## Usage Pattern

```python
class ClayClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.clay.com/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def enrich_contact(
        self,
        email: str | None = None,
        linkedin_url: str | None = None,
        domain: str | None = None
    ) -> ClayEnrichment:
        """
        Enrich contact using Clay's waterfall.
        Used as Tier 2 fallback (max 15% of batch).
        """
        response = await self.client.post(
            "/enrich",
            json={
                "email": email,
                "linkedin_url": linkedin_url,
                "domain": domain,
                "enrichments": [
                    "email_finder",
                    "phone_finder",
                    "company_enrichment",
                    "title_verification"
                ]
            }
        )
        return ClayEnrichment(**response.json())
    
    async def bulk_enrich(
        self,
        contacts: list[dict],
        table_id: str
    ) -> BulkResult:
        """Bulk enrich via Clay table."""
        response = await self.client.post(
            f"/tables/{table_id}/rows",
            json={"rows": contacts}
        )
        return BulkResult(**response.json())
```

---

## Waterfall Strategy

Clay is used as **Tier 2 fallback**:

```
Tier 0: Cache ──► Hit? Return
           │
           └── Miss
                 │
                 ▼
Tier 1: Apollo + Apify ──► Success? Cache & Return
           │
           └── Partial/Fail (max 15% of batch)
                 │
                 ▼
Tier 2: Clay Waterfall ──► Best available data
```

---

## Cost

| Credit Type | Cost (AUD) |
|-------------|------------|
| Basic enrichment | $0.039/credit |
| Premium enrichment | $0.077/credit |
| Waterfall (full) | ~$0.25-0.50/contact |

---

## When to Use Clay

- Apollo returned partial data
- High-value leads (Hot tier)
- Email not found by primary sources
- Phone number required
