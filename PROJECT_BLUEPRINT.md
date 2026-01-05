# PROJECT_BLUEPRINT.md — Agency OS v3.0

**Status:** APPROVED  
**Version:** 3.0 (Modular)  
**Last Updated:** January 5, 2026  
**Owner:** CEO  
**Purpose:** Quick reference for Claude Code. Detailed specs in `/docs/`.

---

## Document Control

| Item | Value |
|------|-------|
| Currency | AUD (Australian Dollars) |
| Primary Market | Australia |
| Scoring System | ALS (Agency Lead Score) |
| Auth Provider | Supabase Auth |
| Orchestration | Prefect (self-hosted on Railway) |
| Cache | Redis (caching ONLY, not task queues) |

---

## Architecture Decisions (LOCKED)

| Component | Decision |
|-----------|----------|
| Backend | FastAPI on Railway |
| Frontend | Next.js on Vercel |
| Database | Supabase PostgreSQL (Port 6543) |
| Auth | Supabase Auth |
| Orchestration | Prefect (self-hosted) |
| Cache | Redis (Upstash) |
| Voice AI | Vapi + Twilio + ElevenLabs |
| Agent Framework | Pydantic AI |

**Full details:** `docs/architecture/DECISIONS.md`

---

## Import Hierarchy (ENFORCED)

```
Layer 4: src/orchestration/  ─► Can import ALL below
Layer 3: src/engines/        ─► models, integrations only
Layer 2: src/integrations/   ─► models only
Layer 1: src/models/         ─► exceptions only
```

**Full details:** `docs/architecture/IMPORT_HIERARCHY.md`

---

## Phase Overview

| Phase | Name | Status | Spec |
|-------|------|--------|------|
| 1-10 | Core Platform | ✅ | `docs/phases/` |
| 11 | ICP Discovery | ✅ | `docs/phases/PHASE_11_ICP.md` |
| 16 | Conversion Intelligence | ✅ | `docs/specs/phase16/` |
| 17 | Launch Prerequisites | 🟡 | `docs/phases/PHASE_17_LAUNCH_PREREQ.md` |
| 18 | E2E Journey Test | 🟡 | `docs/phases/PHASE_18_E2E_JOURNEY.md` |
| 19 | Email Infrastructure | 🟡 | `docs/phases/PHASE_19_EMAIL_INFRA.md` |
| 20 | Platform Intelligence | 📋 | `docs/phases/PHASE_20_PLATFORM_INTEL.md` |
| 21 | Landing Page + UI | 🔴 | `docs/phases/PHASE_21_UI_OVERHAUL.md` |

**Full index:** `docs/phases/PHASE_INDEX.md`

---

## Pricing Tiers (AUD)

| Tier | Founding | Regular | Leads | Campaigns |
|------|----------|---------|-------|-----------|
| Ignition | $1,250 | $2,500 | 1,250 | 5 |
| Velocity | $2,500 | $5,000 | 2,250 | 10 |
| Dominance | $3,750 | $7,500 | 4,500 | 20 |

**All tiers include ALL features.** Only difference: volume.

**Full details:** `docs/specs/pricing/TIER_PRICING_COST_MODEL_v2.md`

---

## ALS Score Tiers (CRITICAL)

| Tier | Score | Channels |
|------|-------|----------|
| Hot | **85-100** | Email, SMS, LinkedIn, Voice, Mail |
| Warm | 60-84 | Email, LinkedIn, Voice |
| Cool | 35-59 | Email, LinkedIn |
| Cold | 20-34 | Email only |
| Dead | <20 | None |

**Hot starts at 85, NOT 80.**

**Full formula:** `docs/specs/engines/SCORER_ENGINE.md`

---

## Key Reference Files

| Topic | Location |
|-------|----------|
| Architecture Decisions | `docs/architecture/DECISIONS.md` |
| Import Rules | `docs/architecture/IMPORT_HIERARCHY.md` |
| Claude Code Rules | `docs/architecture/RULES.md` |
| File Structure | `docs/architecture/FILE_STRUCTURE.md` |
| Database Schema | `docs/specs/database/SCHEMA_OVERVIEW.md` |
| Engine Specs | `docs/specs/engines/ENGINE_INDEX.md` |
| Integration Specs | `docs/specs/integrations/INTEGRATION_INDEX.md` |
| Phase Details | `docs/phases/PHASE_INDEX.md` |
| Task Tracking | `PROGRESS.md` |
| Skills | `skills/SKILL_INDEX.md` |

---

## Quick Rules for Claude Code

1. **Read phase spec before starting** → `docs/phases/PHASE_XX.md`
2. **Read relevant skill** → `skills/[category]/SKILL.md`
3. **Follow import hierarchy** → Never import up
4. **Update PROGRESS.md** → After each task
5. **Soft deletes only** → Never hard DELETE
6. **JIT validation** → Check status before outreach

**Full rules:** `docs/architecture/RULES.md`

---

## Service Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Service   │     │ Worker Service  │     │ Prefect Server  │
│    (Railway)    │     │   (Railway)     │     │   (Railway)     │
│                 │     │                 │     │                 │
│   FastAPI       │     │  Prefect Agent  │     │  Orchestration  │
│   HTTP routes   │     │  Background     │     │  UI + API       │
│                 │     │  tasks          │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
              ┌─────┴─────┐            ┌──────┴──────┐
              │ Supabase  │            │   Redis     │
              │ PostgreSQL│            │  (Upstash)  │
              │ Port 6543 │            │  Cache only │
              └───────────┘            └─────────────┘
```

---

## Current Focus

**Phase 17:** Collecting API credentials  
**Phase 18:** E2E journey testing  
**Phase 21:** UI overhaul with v0.dev  

Check `PROGRESS.md` for detailed task status.

---

## Archive

Full original blueprint: `PROJECT_BLUEPRINT_FULL_ARCHIVE.md`
