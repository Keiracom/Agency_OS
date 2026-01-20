# Architecture Index — Agency OS

**Purpose:** Master index of all architecture documentation.
**Principle:** Architecture docs are the source of truth. Code must match specs.
**Last Updated:** 2026-01-20

---

## How to Use This Index

1. **Before coding:** Read relevant architecture doc
2. **After coding:** Verify code matches spec
3. **Found a gap:** Update architecture doc FIRST, then implement

---

## Architecture Documents

### Foundation (LOCKED — Do Not Modify)

| Document | Purpose | Status |
|----------|---------|--------|
| `DECISIONS.md` | Technology stack choices (Prefect, Salesforge, etc.) | ✅ Locked |
| `IMPORT_HIERARCHY.md` | Layer rules: models → integrations → engines → orchestration | ✅ Enforced |
| `RULES.md` | Claude Code development protocol | ✅ Enforced |
| `FILE_STRUCTURE.md` | Project directory layout | 🟡 Needs update |

### Feature Architecture

| Document | Purpose | Status | Code Status |
|----------|---------|--------|-------------|
| `SDK_AND_CONTENT_ARCHITECTURE.md` | SDK usage strategy, Smart Prompts, tiered enrichment | ✅ Spec done | ✅ Implemented |
| `AUTOMATED_DISTRIBUTION_DEFAULTS.md` | System-controlled timing, sequences, warmup | ✅ Spec done | 🔴 Not implemented |

### Distribution Channels (`distribution/`)

| Document | Purpose | Status | Code Status |
|----------|---------|--------|-------------|
| `distribution/DISTRIBUTION_INDEX.md` | Channel overview, verification protocol | ✅ Spec done | — |
| `distribution/RESOURCE_POOL.md` | Domain/phone/seat allocation from pool | ✅ Spec done | 🔴 Not implemented |
| `distribution/EMAIL_DISTRIBUTION.md` | Salesforge, warmup, threading, timezone | ✅ Spec done | 🟡 Partial |
| `distribution/SMS_DISTRIBUTION.md` | ClickSend, DNCR compliance | ✅ Spec done | 🟡 Partial |
| `distribution/VOICE_DISTRIBUTION.md` | Vapi/Twilio, voice KB generation | ✅ Spec done | 🟡 Partial |
| `distribution/LINKEDIN_DISTRIBUTION.md` | Unipile, humanized timing | ✅ Spec done | 🟡 Partial |
| `distribution/MAIL_DISTRIBUTION.md` | Direct mail (optional) | ✅ Spec done | 🔴 Not implemented |

### Missing Architecture (To Be Created)

| Document | Purpose | Priority | Governs |
|----------|---------|----------|---------|
| `ONBOARDING_ARCHITECTURE.md` | ICP extraction → sourcing → enrichment | HIGH | `onboarding_flow.py`, `icp_scraper.py`, `scout.py` |
| `SCORING_ARCHITECTURE.md` | ALS formula, tier thresholds, signals | MEDIUM | `scorer.py`, `lead_pool` table |
| `REPLY_ARCHITECTURE.md` | Intent classification, SDK response | MEDIUM | `reply_agent.py`, `email_events_service.py` |
| `MEETING_ARCHITECTURE.md` | Calendar booking, deal creation | LOW | `meeting_service.py`, `deal_service.py` |

---

## Document → Code Mapping

### `SDK_AND_CONTENT_ARCHITECTURE.md`

| Spec Section | Code Location | Status |
|--------------|---------------|--------|
| SDK for enrichment (tiered) | `src/agents/sdk_agents/sdk_eligibility.py` | ✅ |
| Smart Prompt system | `src/engines/smart_prompts.py` | ✅ |
| Email generation | `src/engines/content.py` | ✅ |
| Voice KB generation | `src/engines/voice.py` | ✅ |
| Data freshness flow | `src/orchestration/flows/stale_lead_refresh_flow.py` | ✅ |
| SDK cost tracking | `src/services/sdk_usage_service.py` | ✅ |

### `AUTOMATED_DISTRIBUTION_DEFAULTS.md`

| Spec Section | Code Location | Status |
|--------------|---------------|--------|
| Default 5-step sequence | `src/services/sequence_generator.py` | 🔴 Not created |
| Gradual warmup schedule | `src/services/warmup_scheduler.py` | 🔴 Not created |
| 9-11 AM send window | `src/engines/timing.py` | 🟡 Partial |
| Recipient timezone | `src/engines/scout.py` (enrichment) | 🔴 Not implemented |
| Weekend exclusion | `src/engines/timing.py` | ✅ Exists |

### `distribution/RESOURCE_POOL.md`

| Spec Section | Code Location | Status |
|--------------|---------------|--------|
| `resource_pool` table | `supabase/migrations/041_*.sql` | 🔴 Not created |
| `client_resources` table | `supabase/migrations/041_*.sql` | 🔴 Not created |
| `ResourcePool` model | `src/models/resource_pool.py` | 🔴 Not created |
| Assignment service | `src/services/resource_assignment_service.py` | 🔴 Not created |
| Onboarding integration | `src/orchestration/flows/onboarding_flow.py` | 🔴 Not wired |

### `distribution/EMAIL_DISTRIBUTION.md`

| Spec Section | Code Location | Status |
|--------------|---------------|--------|
| Salesforge client | `src/integrations/salesforge.py` | ✅ |
| Email engine | `src/engines/email.py` | ✅ |
| Warmup scheduler | `src/services/warmup_scheduler.py` | 🔴 Not created |
| Threading (In-Reply-To) | `src/integrations/salesforge.py` | ✅ |
| Bounce handling | `src/services/email_events_service.py` | ✅ |
| Recipient timezone | — | 🔴 Not implemented |

### `distribution/SMS_DISTRIBUTION.md`

| Spec Section | Code Location | Status |
|--------------|---------------|--------|
| ClickSend client | `src/integrations/clicksend.py` | ✅ |
| SMS engine | `src/engines/sms.py` | ✅ |
| DNCR client | `src/integrations/dncr.py` | 🟡 Created, not wired |
| DNCR check before send | `src/engines/sms.py` | 🔴 Not wired |
| Opt-out handling | `src/services/suppression_service.py` | ✅ |

### `distribution/VOICE_DISTRIBUTION.md`

| Spec Section | Code Location | Status |
|--------------|---------------|--------|
| Twilio client | `src/integrations/twilio.py` | ✅ |
| Voice engine | `src/engines/voice.py` | ✅ |
| Voice KB agent | `src/agents/sdk_agents/voice_kb_agent.py` | ✅ |
| Vapi integration | `src/integrations/vapi.py` | 🟡 Basic |
| Call outcome handling | — | 🔴 Not implemented |

### `distribution/LINKEDIN_DISTRIBUTION.md`

| Spec Section | Code Location | Status |
|--------------|---------------|--------|
| Unipile client | `src/integrations/unipile.py` | ✅ |
| LinkedIn engine | `src/engines/linkedin.py` | ✅ |
| Timing engine | `src/engines/timing.py` | ✅ |
| Connection tracking | `src/services/linkedin_connection_service.py` | 🟡 Basic |
| Post-accept messaging | — | 🔴 Not implemented |

---

## Implementation Priority

Based on dependencies and business impact:

### Phase A: Resource Foundation (Blocks Everything)
1. `RESOURCE_POOL.md` → Create tables + service
2. Wire to onboarding flow

### Phase B: Email (Core Channel)
3. `EMAIL_DISTRIBUTION.md` → Warmup scheduler
4. `EMAIL_DISTRIBUTION.md` → Recipient timezone

### Phase C: Automated Sequences
5. `AUTOMATED_DISTRIBUTION_DEFAULTS.md` → Sequence generator
6. Remove user sequence configuration from frontend

### Phase D: Secondary Channels
7. `SMS_DISTRIBUTION.md` → DNCR wiring
8. `VOICE_DISTRIBUTION.md` → Vapi full integration
9. `LINKEDIN_DISTRIBUTION.md` → Seat pool + tracking

### Phase E: Documentation
10. Create `ONBOARDING_ARCHITECTURE.md`
11. Create `SCORING_ARCHITECTURE.md`
12. Update `FILE_STRUCTURE.md`

---

## Verification Protocol

For each architecture doc:

```
□ Spec exists and is complete
□ All code locations identified
□ Code matches spec
□ Tests exist for spec'd behavior
□ No undocumented behavior in code
```

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete and verified |
| 🟡 | Partial — some gaps |
| 🔴 | Not implemented |
| — | Not applicable |

---

## Related Documentation

| Doc | Purpose |
|-----|---------|
| `CLAUDE.md` | Claude Code instructions |
| `PROJECT_BLUEPRINT.md` | Project overview |
| `PROGRESS.md` | Current task tracking |
| `docs/specs/` | Component-level specs |
| `docs/phases/` | Phase-specific tasks |
