# Integration Index — Agency OS

**Location:** `src/integrations/`
**Layer:** 2 (can import models only)
**Last Updated:** February 6, 2026

---

## Integration Summary

| Integration | File | Purpose | Spec |
|-------------|------|---------|------|
| **SIEGE Waterfall** | `siege_waterfall.py` | 5-tier enrichment pipeline | `SIEGE_WATERFALL.md` |
| ABN Lookup | `abn_client.py` | Australian Business Register (Tier 1) | `ABN_CLIENT.md` |
| GMB Scraper | `gmb_scraper.py` | Google Maps data (Tier 2) | `GMB_SCRAPER.md` |
| Hunter | `hunter.py` | Email verification (Tier 3) | *(needs spec)* |
| Proxycurl | `proxycurl.py` | LinkedIn enrichment (Tier 4) | *(needs spec)* |
| Kaspr | `kaspr.py` | Mobile number enrichment (Tier 5) | `KASPR.md` |
| Supabase | `supabase.py` | Database client | `SUPABASE.md` |
| Redis | `redis.py` | Cache + rate limits | `REDIS.md` |
| Apollo | `apollo.py` | B2B enrichment (legacy) | `APOLLO.md` |
| Apify | `apify.py` | Web scraping (Tier 1-2) | `APIFY.md` |
| Camoufox | `camoufox_scraper.py` | Anti-detect scraping (Tier 3) | `SCRAPER_WATERFALL.md` |
| Clay | `clay.py` | Premium enrichment | `CLAY.md` |
| DataForSEO | `dataforseo.py` | SEO metrics | `DATAFORSEO.md` |
| Resend | `resend.py` | Transactional email | `RESEND.md` |
| Postmark | `postmark.py` | Inbound email | `POSTMARK.md` |
| Twilio | `twilio.py` | SMS + Voice telephony | `TWILIO.md` |
| Unipile | `unipile.py` | LinkedIn automation | `UNIPILE.md` |
| HeyReach | `heyreach.py` | LinkedIn (deprecated) | `HEYREACH.md` |
| Vapi | `vapi.py` | Voice AI orchestration | `VAPI.md` |
| ElevenLabs | `elevenlabs.py` | Text-to-speech | `ELEVENLABS.md` |
| ClickSend | `clicksend.py` | Direct mail (AU) | `CLICKSEND.md` |
| Anthropic | `anthropic.py` | AI + spend limiter | `ANTHROPIC.md` |
| Serper | `serper.py` | Search API | *(needs spec)* |
| Salesforge | `salesforge.py` | Cold email sending | `SALESFORGE.md` |
| Warmforge | `warmforge.py` | Email warmup monitoring | `WARMFORGE.md` |

---

## External APIs (No Code Wrapper)

| Service | Purpose | Notes |
|---------|---------|-------|
| InfraForge | Domain/mailbox provisioning | Used via dashboard, spec: `INFRAFORGE.md` |

---

## Archived Integrations

These integrations were planned but superseded. Specs archived for historical reference.

| Integration | Replaced By | Archive Location |
|-------------|-------------|------------------|
| Smartlead | Salesforge ecosystem | `archive/SMARTLEAD.md` |
| Deepgram | Vapi internal STT | `archive/DEEPGRAM.md` |

---

## Integration Categories

### SIEGE Enrichment Waterfall (Primary)
- **SIEGE Waterfall** — Unified 5-tier enrichment pipeline (~$0.105/lead avg)
  - **Tier 1: ABN Lookup** — Australian Business Register (FREE)
  - **Tier 2: GMB Scraper** — Google Maps data ($0.006/lead)
  - **Tier 3: Hunter** — Email verification ($0.012/lead)
  - **Tier 4: Proxycurl** — LinkedIn enrichment ($0.024/lead)
  - **Tier 5: Kaspr** — Mobile numbers ($0.45/lead, ALS ≥85 only)

**See also:** `SIEGE_WATERFALL.md` for full architecture

### Legacy Enrichment (Deprecated for new leads)
- **Apollo** — B2B contact data (replaced by SIEGE)
- **Clay** — Premium enrichment fallback

### Web Scraping
- **Apify** — Web scraping Tier 1-2 (static + JS-rendered)
- **Camoufox** — Web scraping Tier 3 (Cloudflare bypass)
- **DataForSEO** — SEO metrics for scoring
- **Serper** — Search API for research

**See also:** `SCRAPER_WATERFALL.md` for scraping architecture

### Outreach Channels
- **Salesforge** — Cold email sending (uses warmed mailboxes)
- **Warmforge** — Email warmup monitoring
- **Resend** — Transactional email
- **Postmark** — Inbound email webhooks
- **Twilio** — SMS + Voice telephony
- **Unipile** — LinkedIn automation (replaced HeyReach)
- **ClickSend** — Australian direct mail

### Voice AI Stack
- **Vapi** — Voice conversation orchestration
- **ElevenLabs** — Natural voice synthesis
- *(Deepgram STT handled internally by Vapi)*

### AI
- **Anthropic** — Claude API with spend limiter

### Email Infrastructure (External)
- **InfraForge** — Domain/mailbox provisioning (via dashboard)

### Infrastructure
- **Supabase** — PostgreSQL database
- **Redis** — Caching and rate limiting

---

## Layer Rules (ENFORCED)

Integrations are **Layer 2**:
- CAN import from `src/models/`
- NO imports from `src/engines/`
- NO imports from `src/orchestration/`

---

## Common Patterns

### Async HTTP Client

```python
class IntegrationClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.example.com",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0
        )

    async def close(self):
        await self.client.aclose()
```

### Error Handling

```python
from src.exceptions import IntegrationError, RateLimitError

async def make_request(self, endpoint: str) -> dict:
    try:
        response = await self.client.get(endpoint)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise RateLimitError(f"Rate limited by {self.name}")
        raise IntegrationError(f"{self.name} error: {e}")
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_with_retry(self, url: str) -> dict:
    return await self.make_request(url)
```

---

## Cost Summary (AUD)

### SIEGE Waterfall Tiers
| Tier | Integration | Unit Cost | Notes |
|------|-------------|-----------|-------|
| 1 | ABN Lookup | **$0.00** | FREE - data.gov.au |
| 2 | GMB Scraper | $0.006/lead | Proxy cost only |
| 3 | Hunter | $0.012/lead | Email verification |
| 4 | Proxycurl | $0.024/lead | LinkedIn data |
| 5 | Kaspr | $0.45/lead | Mobile (ALS ≥85 only) |
| — | **Weighted Average** | **~$0.105/lead** | vs Apollo $0.50+ |

### Other Integrations
| Integration | Unit Cost | Notes |
|-------------|-----------|-------|
| Apollo | ~$0.02/lead | B2B enrichment (legacy) |
| Clay | $0.039-0.077/credit | Premium fallback |
| DataForSEO | ~$0.03/domain | SEO metrics |
| Unipile | ~$49/month | LinkedIn (replaces HeyReach) |
| HeyReach | $122/seat/month | LinkedIn (deprecated) |
| Vapi | $0.35/minute | Voice AI |
| Twilio SMS | $0.08/message | Australian |
| ClickSend | $0.59/letter | Direct mail |
| Resend | $0.0009/email | Transactional |
| Salesforge | ~$99/month | Cold email sending |
| Warmforge | Free | Included with Salesforge |
