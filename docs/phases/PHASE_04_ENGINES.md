# Phase 4: Engines

**Status:** ✅ Complete  
**Tasks:** 12  
**Dependencies:** Phase 2 + Phase 3 complete  
**Checkpoint:** CEO approval required

---

## Overview

Create the 12 business logic engines with tests. Engines are the core processing units.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| ENG-001 | Base engine | Abstract base, DI pattern | `src/engines/base.py` | M |
| ENG-002 | Scout engine + test | Enrichment waterfall | `src/engines/scout.py`, `tests/test_engines/test_scout.py` | L |
| ENG-003 | Scorer engine + test | ALS formula | `src/engines/scorer.py`, `tests/test_engines/test_scorer.py` | L |
| ENG-004 | Allocator engine + test | Channel + resource round-robin | `src/engines/allocator.py`, `tests/test_engines/test_allocator.py` | M |
| ENG-005 | Email engine + test | Email with threading | `src/engines/email.py`, `tests/test_engines/test_email.py` | M |
| ENG-006 | SMS engine + test | SMS with DNCR | `src/engines/sms.py`, `tests/test_engines/test_sms.py` | M |
| ENG-007 | LinkedIn engine + test | LinkedIn via HeyReach | `src/engines/linkedin.py`, `tests/test_engines/test_linkedin.py` | M |
| ENG-008 | Voice engine + test | Voice via Vapi + Twilio + ElevenLabs | `src/engines/voice.py`, `tests/test_engines/test_voice.py` | L |
| ENG-009 | Mail engine + test | Direct mail via ClickSend | `src/engines/mail.py`, `tests/test_engines/test_mail.py` | M |
| ENG-010 | Closer engine + test | Reply handling | `src/engines/closer.py`, `tests/test_engines/test_closer.py` | L |
| ENG-011 | Content engine + test | AI content generation | `src/engines/content.py`, `tests/test_engines/test_content.py` | M |
| ENG-012 | Reporter engine + test | Metrics aggregation | `src/engines/reporter.py`, `tests/test_engines/test_reporter.py` | M |

---

## Layer Rules

Engines are **Layer 3**:
- CAN import from `src/models/`
- CAN import from `src/integrations/`
- **NO imports from other engines** (pass data as args)
- NO imports from `src/orchestration/`

---

## Engine Summary

| Engine | Purpose | Key Integration |
|--------|---------|-----------------|
| Scout | Lead enrichment waterfall | Apollo, Apify, Clay |
| Scorer | ALS score calculation | DataForSEO |
| Allocator | Channel + timing assignment | Redis (rate limits) |
| Email | Email outreach + threading | Resend |
| SMS | SMS outreach + DNCR | Twilio |
| LinkedIn | LinkedIn automation | HeyReach |
| Voice | Voice AI calls | Vapi, Twilio, ElevenLabs |
| Mail | Direct mail (AU) | ClickSend |
| Closer | Reply handling + intent | Anthropic |
| Content | AI content generation | Anthropic |
| Reporter | Metrics aggregation | — |

---

## Key Pattern: Dependency Injection

```python
class ScorerEngine:
    """
    RULE: Session passed by caller, never instantiated here.
    """
    
    async def score(
        self, 
        db: AsyncSession,  # Passed by caller
        lead_id: UUID
    ) -> ScoringResult:
        ...
```

---

## Checkpoint 2 Criteria

- [ ] All 12 engines implemented
- [ ] All engine tests pass
- [ ] Scout validation threshold working (0.70)
- [ ] Spend limiter working
- [ ] Resource-level rate limits working

---

## Detailed Engine Specs

See `docs/specs/engines/` for full specifications:
- `ENGINE_INDEX.md` — Overview
- `SCORER_ENGINE.md` — ALS formula details
