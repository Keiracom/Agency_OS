# Integration Index — Agency OS

**Location:** `src/integrations/`
**Layer:** 2 (can import models only)
**Last Updated:** January 8, 2026

---

## Integration Summary

| Integration | File | Purpose | Spec |
|-------------|------|---------|------|
| Supabase | `supabase.py` | Database client | `SUPABASE.md` |
| Redis | `redis.py` | Cache + rate limits | `REDIS.md` |
| Apollo | `apollo.py` | B2B enrichment | `APOLLO.md` |
| Apify | `apify.py` | Web scraping (Tier 1-2) | `APIFY.md` |
| Camoufox | `camoufox_scraper.py` | Anti-detect scraping (Tier 3) | `SCRAPER_WATERFALL.md` |
| Clay | `clay.py` | Premium enrichment | `CLAY.md` |
| DataForSEO | `dataforseo.py` | SEO metrics | `DATAFORSEO.md` |
| Resend | `resend.py` | Email sending | `RESEND.md` |
| Postmark | `postmark.py` | Inbound email | `POSTMARK.md` |
| Twilio | `twilio.py` | SMS + Voice telephony | `TWILIO.md` |
| HeyReach | `heyreach.py` | LinkedIn automation | `HEYREACH.md` |
| Vapi | `vapi.py` | Voice AI orchestration | `VAPI.md` |
| ElevenLabs | `elevenlabs.py` | Text-to-speech | `ELEVENLABS.md` |
| ClickSend | `clicksend.py` | Direct mail (AU) | `CLICKSEND.md` |
| Anthropic | `anthropic.py` | AI + spend limiter | `ANTHROPIC.md` |
| Serper | `serper.py` | Search API | *(needs spec)* |

---

## External APIs (No Code Wrapper)

| Service | Purpose | Notes |
|---------|---------|-------|
| InfraForge | Domain/mailbox provisioning | Used via dashboard, spec: `INFRAFORGE.md` |
| Salesforge | Cold email sending | API keys configured, no wrapper needed |
| Warmforge | Email warmup | Free with Salesforge, no wrapper needed |

---

## Archived Integrations

These integrations were planned but superseded. Specs archived for historical reference.

| Integration | Replaced By | Archive Location |
|-------------|-------------|------------------|
| Smartlead | Salesforge ecosystem | `archive/SMARTLEAD.md` |
| Deepgram | Vapi internal STT | `archive/DEEPGRAM.md` |

---

## Integration Categories

### Data & Enrichment
- **Apollo** — Primary B2B contact data
- **Apify** — Web scraping Tier 1-2 (static + JS-rendered)
- **Camoufox** — Web scraping Tier 3 (Cloudflare bypass)
- **Clay** — Premium enrichment waterfall fallback
- **DataForSEO** — SEO metrics for scoring
- **Serper** — Search API for research

**See also:** `SCRAPER_WATERFALL.md` for full scraping architecture

### Outreach Channels
- **Resend** — Transactional email sending
- **Postmark** — Inbound email webhooks
- **Twilio** — SMS + Voice telephony
- **HeyReach** — LinkedIn automation
- **ClickSend** — Australian direct mail

### Voice AI Stack
- **Vapi** — Voice conversation orchestration
- **ElevenLabs** — Natural voice synthesis
- *(Deepgram STT handled internally by Vapi)*

### AI
- **Anthropic** — Claude API with spend limiter

### Email Infrastructure (External)
- **InfraForge** — Domain/mailbox provisioning (via dashboard)
- **Salesforge** — Cold email campaigns and sending
- **Warmforge** — Email warmup (free with Salesforge)

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

| Integration | Unit Cost | Notes |
|-------------|-----------|-------|
| Apollo | ~$0.02/lead | B2B enrichment |
| Clay | $0.039-0.077/credit | Waterfall |
| DataForSEO | ~$0.03/domain | SEO metrics |
| HeyReach | $122/seat/month | LinkedIn |
| Vapi | $0.35/minute | Voice AI |
| Twilio SMS | $0.08/message | Australian |
| ClickSend | $0.59/letter | Direct mail |
| Resend | $0.0009/email | Transactional |
| Salesforge | $48/month | Cold email sending |
| Warmforge | Free | Included with Salesforge |
