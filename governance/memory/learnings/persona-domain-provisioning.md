# Retrospective: Persona & Domain Provisioning System

**Date:** 2026-01-30  
**Branch:** `feature/persona-provisioning`  
**Status:** Ready for PR

---

## What We Built

Automated system for pre-creating professional personas with matching domains, warming them via WarmForge, and allocating to clients at signup for Day 1 sending capability.

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Platform owns personas | Instant Day 1 outreach - no client setup delay | ✅ Implemented |
| Client only provides LinkedIn | Reduces onboarding friction, we control quality | ✅ Designed |
| 40% buffer rule (event-driven) | Stripe webhook triggers replenishment, not wasteful cron | ✅ Implemented |
| Daily warmup polling | WarmForge has NO webhooks - must poll | ✅ Implemented |
| Heat score ≥85 = AVAILABLE | WarmForge threshold for production-ready sending | ✅ Implemented |

---

## Learnings

### 1. Salesforge Ecosystem Auth
**Plain key, not Bearer.** All three services (InfraForge, Salesforge, WarmForge) use:
```
Authorization: {api_key}
```
NOT `Bearer {api_key}`.

### 2. WarmForge Has No Webhooks
Cannot get notified when warmup completes. Must poll daily via cron.
Warmup takes ~21 days. Heat score of 85+ indicates ready.

### 3. Salesforge Webhook Events
Available events (email only, no warmup):
- `email_sent`, `email_opened`, `link_clicked`
- `email_replied`, `email_bounced`
- `positive_reply`, `negative_reply`
- `contact_unsubscribed`, `label_changed`

### 4. Domain Naming Patterns
Persona-branded domains work best:
- `{firstname}{lastname}.io`
- `{f}{lastname}.co`
- `team{firstname}.com`

2 mailboxes per domain:
- `{firstname}@domain`
- `{f}.{lastname}@domain`

---

## Tier Allocations

| Tier | Personas | Domains | Mailboxes | Price |
|------|----------|---------|-----------|-------|
| Ignition | 2 | 3 | 6 | $2,500/mo |
| Velocity | 3 | 5 | 10 | $5,000/mo |
| Dominance | 4 | 9 | 18 | $7,500/mo |

---

## Workspace IDs

| Service | Workspace ID |
|---------|--------------|
| InfraForge | `wks_cho0dp6wypzgzkou1c0p4` |
| WarmForge | `wks_8wuh9f3b74o7o930ocoie` |
| Salesforge | `wks_b86a0iopxkzx2u3gvz9et` |

---

## Files Created

```
supabase/migrations/054_personas.sql
src/models/persona.py
src/services/persona_service.py
src/services/domain_provisioning_service.py
src/integrations/warmforge.py
src/integrations/infraforge.py (enhanced)
src/orchestration/flows/persona_buffer_flow.py
src/orchestration/flows/warmup_monitor_flow.py
docs/specs/PERSONA_DOMAIN_PROVISIONING.md
```

---

## Git Hygiene Lesson

**Always create feature branches from `main` with descriptive names.**

Bad: Piggybacking on `feature/elliot-dashboard` for unrelated work.  
Good: `feature/persona-provisioning` branched from `main`.

---

## Next Steps

1. [ ] PR `feature/persona-provisioning` → `main`
2. [ ] Apply migration 054 in Supabase
3. [ ] Wire into onboarding flow
4. [ ] Register warmup_monitor cron in Prefect (0 19 * * *)
5. [ ] Seed initial persona buffer
