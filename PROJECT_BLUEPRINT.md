# PROJECT_BLUEPRINT.md — Agency OS v3.0

**Status:** APPROVED
**Version:** 3.2 (Phase Reorganization)
**Last Updated:** January 7, 2026  
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

### Completed Phases

| Phase | Name | Status | Spec |
|-------|------|--------|------|
| 1-10 | Core Platform | ✅ | `docs/phases/` |
| 11 | ICP Discovery | ✅ | `docs/phases/PHASE_11_ICP.md` |
| 16 | Conversion Intelligence | ✅ | `docs/specs/phase16/` |

### Active Phases (Corrected Order)

| Order | Phase | Name | Status | Blocked By | Spec |
|-------|-------|------|--------|------------|------|
| 1 | 17 | Launch Prerequisites | 🟡 | — | `docs/phases/PHASE_17_LAUNCH_PREREQ.md` |
| 2 | 18 | Email Infrastructure | 🟡 | Phase 17 | `docs/phases/PHASE_18_EMAIL_INFRA.md` |
| 3 | 19 | Scraper Waterfall | 🔴 | Phase 18 | `docs/specs/integrations/SCRAPER_WATERFALL.md` |
| 4 | 20 | Landing Page + UI Wiring | 🟡 | Phase 19 | `docs/phases/PHASE_20_UI_OVERHAUL.md` |
| 5 | 21 | E2E Journey Test | 🔴 | Phase 20 | `docs/phases/PHASE_21_E2E_JOURNEY.md` |
| 6 | 22 | Marketing Automation | 🔴 | Phase 21 | `docs/phases/PHASE_22_MARKETING_AUTO.md` |
| 7 | 23 | Platform Intelligence | 📋 | Post-Launch | `docs/phases/PHASE_23_PLATFORM_INTEL.md` |

### Phase Dependency Chain

```
Phase 17 (Prerequisites)
    ↓ Health checks, Sentry, seed prod DB
Phase 18 (Email Infra)
    ↓ InfraForge/Smartlead — CRITICAL for cold outreach
Phase 19 (Scraper Waterfall)
    ↓ Cost-efficient enrichment + Deep Research capability
Phase 20 (UI Wiring)
    ↓ Wire automation (ALS > 85 → Deep Research trigger)
Phase 21 (E2E Tests)
    ↓ Full journey testable with real infrastructure
Phase 22 (Marketing Automation)
    ↓ Smartlead, Infraforge, content generation
Phase 23 (Platform Intel)
    ↓ Post-launch, needs 10+ clients with data
```

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
| **Scraper Waterfall** | `docs/specs/integrations/SCRAPER_WATERFALL.md` |
| Phase Details | `docs/phases/PHASE_INDEX.md` |
| Task Tracking | `PROGRESS.md` |
| Skills | `skills/SKILL_INDEX.md` |

---

## Claude Code Prompt Protocol

Use this structured prompt template when assigning tasks to Claude Code:

```markdown
<role>
You are a Senior Principal Engineer and Architect.
Your Goal: Execute the following task with 100% precision, adhering to the project's existing patterns.
</role>

<context>
1. READ `PROJECT_BLUEPRINT.md` to understand the architecture.
2. READ `PROGRESS.md` to understand the current build status.
3. READ `[Specific_Spec_File.md]` to understand the task requirements.
</context>

<task_objective>
[INSERT HIGH-LEVEL GOAL HERE - e.g., "Implement the backend automation for Phase 20."]
</task_objective>

<constraints>
- DO NOT remove existing code unless explicitly instructed.
- DO NOT use placeholders (e.g., "TODO", "pass")—write complete, working code.
- MAINTAIN the "Import Hierarchy": `orchestration` -> `engines` -> `integrations` -> `models`.
- IF a file is missing, create it. IF a file exists, update it non-destructively.
</constraints>

<execution_plan>
Perform these steps sequentially. Do not skip verification.
1. **Analysis:** Check file structure to ensure paths in the spec match reality.
2. **Scaffolding:** Create any new files or database migrations required.
3. **Logic:** Implement the core functions/classes.
4. **Wiring:** Connect the new logic to the existing API or Orchestration layer.
5. **Verification:** Run a quick check (or test) to ensure no syntax errors.
6. **Documentation:** Update `PROGRESS.md` with a log of what was built.
</execution_plan>

<user_command>
[INSERT SPECIFIC INSTRUCTIONS HERE]
</user_command>
```

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

**Phase 17:** Finish launch prerequisites (health checks, Sentry, seed prod DB)  
**Phase 18:** Email infrastructure (InfraForge/Smartlead) — CRITICAL BLOCKER  

Check `PROGRESS.md` for detailed task status.

---

## Archive

Full original blueprint: `PROJECT_BLUEPRINT_FULL_ARCHIVE.md`
