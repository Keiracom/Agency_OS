# Phase Index — Agency OS

**Last Updated:** January 5, 2026

---

## Phase Overview

| Phase | Name | Status | Tasks | Spec Location |
|-------|------|--------|-------|---------------|
| 1 | Foundation + DevOps | ✅ | 17 | `PHASE_01_FOUNDATION.md` |
| 2 | Models & Schemas | ✅ | 7 | `PHASE_02_MODELS.md` |
| 3 | Integrations | ✅ | 12 | `PHASE_03_INTEGRATIONS.md` |
| 4 | Engines | ✅ | 12 | `PHASE_04_ENGINES.md` |
| 5 | Orchestration (Prefect) | ✅ | 12 | `PHASE_05_ORCHESTRATION.md` |
| 6 | Agents (Pydantic AI) | ✅ | 4 | `PHASE_06_AGENTS.md` |
| 7 | API Routes | ✅ | 8 | `PHASE_07_API.md` |
| 8 | Frontend | ✅ | 15 | `PHASE_08_FRONTEND.md` |
| 9 | Integration Testing | ✅ | 5 | `PHASE_09_TESTING.md` |
| 10 | Deployment | ✅ | 8 | `PHASE_10_DEPLOYMENT.md` |
| 11 | ICP Discovery | ✅ | 18 | `PHASE_11_ICP.md` |
| 12 | Campaign Execution | ✅ | — | `PHASE_12_CAMPAIGN_EXEC.md` (merged) |
| 13 | Frontend-Backend | ✅ | — | `PHASE_13_FRONTEND_BACKEND.md` |
| 14 | Missing UI | ✅ | — | `PHASE_14_MISSING_UI.md` |
| 15 | Live UX Testing | ✅ | — | `PHASE_15_UX_TEST.md` |
| 16 | Conversion Intelligence | ✅ | 30 | `PHASE_16_CONVERSION.md` |
| 17 | Launch Prerequisites | 🟡 | 20 | `PHASE_17_LAUNCH_PREREQ.md` |
| 18 | E2E Journey Test | 🟡 | 47 | `PHASE_18_E2E_JOURNEY.md` |
| 19 | Email Infrastructure | 🟡 | 20 | `PHASE_19_EMAIL_INFRA.md` |
| 20 | Platform Intelligence | 📋 | 18 | `PHASE_20_PLATFORM_INTEL.md` |
| 21 | Landing Page + UI | 🔴 | 18 | `PHASE_21_UI_OVERHAUL.md` |

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete |
| 🟡 | In Progress |
| 🔴 | Not Started (High Priority) |
| 📋 | Planned (Post-Launch) |

---

## Current Focus

**Active Phases:**
- Phase 17: API Credentials Collection
- Phase 18: E2E Journey Testing
- Phase 19: Email Infrastructure (InfraForge + Smartlead)
- Phase 21: UI Overhaul (v0.dev + Bloomberg aesthetic)

**Tracking:** See `PROGRESS.md` for detailed task status.

---

## Checkpoints

| Checkpoint | After Phase | Key Criteria |
|------------|-------------|--------------|
| 1 | Phase 1 | Docker runs, migrations applied, connections work |
| 2 | Phase 4 | All engines implemented, tests pass |
| 3 | Phase 5 | Prefect running, flows registered |
| 4 | Phase 7 | API routes working, auth via memberships |
| 5 | Phase 8 | Frontend renders, dashboard shows data |
| 6 | Phase 10 | Production deployed, E2E test passes |
| 7 | Phase 11 | ICP extraction working end-to-end |
| 8 | Phase 16 | Conversion Intelligence patterns learning |
| 9 | Phase 19 | Email provisioning working |
| 10 | Phase 20 | Platform Intelligence aggregating |

---

## Phase Dependencies

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
                                                  │
                                                  ▼
                                              Phase 6 ──► Phase 7 ──► Phase 8
                                                                        │
                                                                        ▼
                                                    Phase 9 ──► Phase 10 ──► Phase 11
                                                                               │
                           ┌───────────────────────────────────────────────────┤
                           ▼                                                   ▼
                      Phase 12 ──► Phase 13 ──► Phase 14 ──► Phase 15 ──► Phase 16
                                                                               │
                         ┌─────────────────────────────────────────────────────┤
                         ▼                                                     ▼
                    Phase 17 ──► Phase 18 ──► Phase 19 ──► Phase 20       Phase 21
                                                                        (parallel)
```

---

## Task Totals

| Category | Phases | Tasks |
|----------|--------|-------|
| Core Platform | 1-10 | 98 |
| Post-Deploy | 11-16 | 48+ |
| Launch Prep | 17-21 | 123 |
| **TOTAL** | — | **~270** |

---

## Quick Reference

| Need | Go To |
|------|-------|
| Architecture decisions | `docs/architecture/DECISIONS.md` |
| Import rules | `docs/architecture/IMPORT_HIERARCHY.md` |
| Database schema | `docs/specs/database/SCHEMA_OVERVIEW.md` |
| Engine specs | `docs/specs/engines/ENGINE_INDEX.md` |
| Integration specs | `docs/specs/integrations/INTEGRATION_INDEX.md` |
| Active tasks | `PROGRESS.md` |
| Full archive | `PROJECT_BLUEPRINT_FULL_ARCHIVE.md` |
