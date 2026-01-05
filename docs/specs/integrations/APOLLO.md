# Apollo Integration

**File:** `src/integrations/apollo.py`  
**Purpose:** Primary B2B contact enrichment  
**API Docs:** https://apolloio.github.io/apollo-api-docs/

---

## Capabilities

- People search by domain/company
- Contact enrichment (email, phone, title)
- Company data (size, industry, funding)
- Employment history

---

## Key Endpoints

| Endpoint | Purpose | Cost |
|----------|---------|------|
| `/v1/people/search` | Find contacts at company | 1 credit |
| `/v1/people/match` | Enrich known contact | 1 credit |
| `/v1/organizations/enrich` | Company details | 1 credit |

---

## Usage Pattern

```python
class ApolloClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.apollo.io/v1",
            headers={"X-Api-Key": api_key}
        )
    
    async def search_people(
        self,
        domain: str,
        titles: list[str] | None = None,
        limit: int = 25
    ) -> list[ApolloContact]:
        """Search for people at a company domain."""
        response = await self.client.post(
            "/people/search",
            json={
                "q_organization_domains": domain,
                "person_titles": titles,
                "per_page": limit
            }
        )
        return [ApolloContact(**p) for p in response.json()["people"]]
    
    async def enrich_contact(
        self,
        email: str
    ) -> ApolloContact | None:
        """Enrich a known email address."""
        response = await self.client.post(
            "/people/match",
            json={"email": email}
        )
        data = response.json()
        if data.get("person"):
            return ApolloContact(**data["person"])
        return None
```

---

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Verified email |
| `first_name` | string | First name |
| `last_name` | string | Last name |
| `title` | string | Job title |
| `linkedin_url` | string | LinkedIn profile |
| `phone_numbers` | array | Phone numbers |
| `organization` | object | Company details |
| `employment_history` | array | Past roles |

---

## Rate Limits

- **Standard:** 100 requests/minute
- **Burst:** 300 requests/minute (short bursts)

---

## Cost

- **Per credit:** ~$0.02 AUD
- **Monthly plans:** Volume discounts available
