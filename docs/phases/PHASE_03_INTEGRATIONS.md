# Phase 3: Integrations

**Status:** ✅ Complete  
**Tasks:** 12  
**Dependencies:** Phase 1 complete  
**Checkpoint:** CEO approval required

---

## Overview

Create API wrapper clients for all external services.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| INT-003 | Apollo integration | Primary enrichment | `src/integrations/apollo.py` | M |
| INT-004 | Apify integration | Bulk scraping | `src/integrations/apify.py` | M |
| INT-005 | Clay integration | Premium fallback | `src/integrations/clay.py` | M |
| INT-006 | Resend integration | Email with threading | `src/integrations/resend.py` | M |
| INT-007 | Postmark integration | Inbound webhooks | `src/integrations/postmark.py` | M |
| INT-008 | Twilio integration | SMS + DNCR + Voice telephony | `src/integrations/twilio.py` | M |
| INT-009 | HeyReach integration | LinkedIn + proxy | `src/integrations/heyreach.py` | M |
| INT-010 | Vapi integration | Voice AI orchestration | `src/integrations/vapi.py` | L |
| INT-010a | ElevenLabs integration | Voice synthesis (TTS) | `src/integrations/elevenlabs.py` | M |
| INT-010b | Deepgram integration | Speech-to-text (STT) | `src/integrations/deepgram.py` | M |
| INT-011 | ClickSend integration | Australian direct mail | `src/integrations/clicksend.py` | M |
| INT-012 | Anthropic integration | AI with spend limiter | `src/integrations/anthropic.py` | L |

---

## Layer Rules

Integrations are **Layer 2**:
- CAN import from `src/models/`
- NO imports from `src/engines/`
- NO imports from `src/orchestration/`

---

## Integration Categories

### Enrichment
- **Apollo** — Primary B2B data
- **Apify** — Web scraping
- **Clay** — Premium fallback (waterfall)

### Outreach Channels
- **Resend** — Email sending
- **Postmark** — Inbound email webhooks
- **Twilio** — SMS + Voice telephony
- **HeyReach** — LinkedIn automation
- **ClickSend** — Australian direct mail

### Voice AI Stack
- **Vapi** — Voice AI orchestration
- **ElevenLabs** — Text-to-speech (TTS)
- **Deepgram** — Speech-to-text (STT)

### AI
- **Anthropic** — Claude API with spend limiter

---

## Provider Costs (AUD)

| Provider | Unit Cost | Notes |
|----------|-----------|-------|
| HeyReach | $122/seat | LinkedIn automation |
| Clay | $0.039-0.077/credit | Waterfall enrichment |
| Hunter.io | $0.023/email | Tier 1 enrichment |
| Vapi | $0.35/min | Voice AI (all-in) |
| Twilio SMS (AU) | $0.08/msg | Outbound SMS |
| ClickSend | $0.59/letter | Australian direct mail |
| Resend | $0.0009/email | Transactional email |

---

## Key Patterns

### Async HTTP Client

```python
class ApolloClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.apollo.io/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )
```

### AI Spend Limiter

```python
class AnthropicClient:
    async def complete(self, prompt: str) -> str:
        if await self.redis.get_daily_spend() > DAILY_LIMIT:
            raise SpendLimitExceeded()
        # ... make API call
```
