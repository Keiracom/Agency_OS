# Engine Index — Agency OS

**Location:** `src/engines/`  
**Layer:** 3 (can import models + integrations)

---

## Engine Summary

| Engine | File | Purpose | Spec |
|--------|------|---------|------|
| Base | `base.py` | Abstract base, DI pattern | — |
| Scout | `scout.py` | Lead enrichment waterfall | `SCOUT_ENGINE.md` |
| Scorer | `scorer.py` | ALS score calculation | `SCORER_ENGINE.md` |
| Allocator | `allocator.py` | Channel + timing assignment | `ALLOCATOR_ENGINE.md` |
| Email | `email.py` | Email outreach + threading | `EMAIL_ENGINE.md` |
| SMS | `sms.py` | SMS outreach + DNCR | `SMS_ENGINE.md` |
| LinkedIn | `linkedin.py` | LinkedIn automation | `LINKEDIN_ENGINE.md` |
| Voice | `voice.py` | Voice AI calls | `VOICE_ENGINE.md` |
| Mail | `mail.py` | Direct mail (AU) | `MAIL_ENGINE.md` |
| Closer | `closer.py` | Reply handling + intent | `CLOSER_ENGINE.md` |
| Content | `content.py` | AI content generation | `CONTENT_ENGINE.md` |
| Reporter | `reporter.py` | Metrics aggregation | `REPORTER_ENGINE.md` |

---

## Additional Engines (Post-Phase 10)

| Engine | File | Purpose | Phase |
|--------|------|---------|-------|
| ICP Scraper | `icp_scraper.py` | Website/portfolio scraping | 11 |
| Email Infra | `email_infrastructure.py` | Domain/mailbox provisioning | 19 |

---

## Integration Dependencies

| Engine | Primary Integration(s) |
|--------|------------------------|
| Scout | Apollo, Apify, Clay |
| Scorer | DataForSEO |
| Allocator | Redis (rate limits) |
| Email | Resend, Smartlead |
| SMS | Twilio |
| LinkedIn | HeyReach |
| Voice | Vapi, Twilio, ElevenLabs |
| Mail | ClickSend |
| Closer | Anthropic (Reply Agent) |
| Content | Anthropic (Content Agent) |
| Reporter | — |

---

## Common Patterns

### Dependency Injection

All engines accept database session as argument:

```python
class ScorerEngine:
    async def score(
        self, 
        db: AsyncSession,  # Passed by caller
        lead_id: UUID
    ) -> ScoringResult:
        ...
```

### Error Handling

```python
from src.exceptions import EnrichmentError, ScoringError, OutreachError

try:
    result = await engine.process(db, lead_id)
except EnrichmentError as e:
    # Log and continue with partial data
except OutreachError as e:
    # Retry or mark as failed
```

### Rate Limiting

Engines don't implement rate limiting directly. The Allocator engine checks limits before assigning:

```python
# In allocator.py
if await self.is_rate_limited(resource_key):
    return None  # Skip this channel
```

---

## Layer Rules (ENFORCED)

Engines are **Layer 3**:
- CAN import from `src/models/`
- CAN import from `src/integrations/`
- **NO imports from other engines** (pass data as args)
- NO imports from `src/orchestration/`

If you need data from another engine, pass it from the orchestration layer.
