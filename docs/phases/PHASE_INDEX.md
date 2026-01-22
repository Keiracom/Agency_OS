# Phase Index — Agency OS

**Last Updated:** January 8, 2026

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
| 12 | Campaign Execution | ✅ | — | `PHASE_12_CAMPAIGN_EXEC.md` |
| 13 | Frontend-Backend | ✅ | — | `PHASE_13_FRONTEND_BACKEND.md` |
| 14 | Missing UI | ✅ | — | `PHASE_14_MISSING_UI.md` |
| 15 | Live UX Testing | ✅ | — | `PHASE_15_UX_TEST.md` |
| 16 | Conversion Intelligence | ✅ | 30 | `PHASE_16_CONVERSION.md` |
| 17 | Launch Prerequisites | ✅ | 13 | `PHASE_17_LAUNCH_PREREQ.md` |
| **18** | **Email Infrastructure** | ✅ | 12 | `PHASE_18_EMAIL_INFRA.md` |
| **19** | **Scraper Waterfall** | ✅ | 9 | `SCRAPER_WATERFALL.md` (in specs/integrations) |
| **20** | **Landing Page + UI Wiring** | ✅ | 22 | `PHASE_21_UI_OVERHAUL.md` *(file needs rename)* |
| **21** | **E2E Journey Test** | 🟡 | 7 journeys | `docs/e2e/E2E_MASTER.md` |
| 22 | Marketing Automation | 📋 | 5 | `PHASE_22_MARKETING_AUTO.md` |
| 23 | Platform Intelligence | 📋 | 18 | `PHASE_23_PLATFORM_INTEL.md` |
| 24 | Lead Pool Architecture | ✅ | 15 | `PHASE_24_LEAD_POOL.md` |
| 24B | Content & Template Tracking | ✅ | 7 | See `CIS_DATA_GAPS_IMPLEMENTATION.md` |
| 24C | Email Engagement Tracking | ✅ | 7 | See `CIS_DATA_GAPS_IMPLEMENTATION.md` |
| 24D | Conversation Threading | ✅ | 8 | See `CIS_DATA_GAPS_IMPLEMENTATION.md` |
| 24E | Downstream Outcomes | ✅ | 7 | See `CIS_DATA_GAPS_IMPLEMENTATION.md` |
| 24F | CRM Push | ✅ | 12 | See `CIS_DATA_GAPS_IMPLEMENTATION.md` |
| 24G | Customer Import | ✅ | 10 | See `CIS_DATA_GAPS_IMPLEMENTATION.md` |
| 24H | LinkedIn Connection | 📋 | 10 | `PHASE_24H_LINKEDIN_CONNECTION.md` |

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

**Active Phase:** 21 (E2E Journey Test)

**Tracking:** See `PROGRESS.md` for detailed task status.

---

## Phase Dependency Chain

```
Phase 1-16 ──► Core Platform Complete
                    │
                    ▼
Phase 17 (Launch Prerequisites)
    ↓ Health checks, credentials configured
Phase 18 (Email Infrastructure)
    ↓ InfraForge/Salesforge — mailboxes warming
Phase 19 (Scraper Waterfall)
    ↓ 5-tier waterfall with Camoufox
Phase 20 (UI Wiring)
    ↓ Automation wired (ALS > 85 → Deep Research trigger)
Phase 21 (E2E Tests)          ← CURRENT
    ↓ Full journey testable with real infrastructure
Phase 22 (Marketing Automation)
    ↓ Post-launch, HeyGen + Buffer content pipeline
Phase 23 (Platform Intel)
    ↓ Post-launch, needs 10+ clients with data
```

---

## Task Totals

| Category | Phases | Tasks |
|----------|--------|-------|
| Core Platform | 1-10 | 98 |
| Post-Deploy | 11-16 | 48+ |
| Launch Prep | 17-21 | 72 |
| CIS Data | 24A-G | 66 |
| Post-Launch | 22-23 | 23 |
| **TOTAL** | — | **~310** |

---

## File Naming Note

Some phase files have mismatched names due to historical renumbering:
- ~~`PHASE_18_E2E_JOURNEY.md`~~ → Renamed to `PHASE_18_EMAIL_INFRA.md` ✅
- `PHASE_21_UI_OVERHAUL.md` → Actually describes Phase 20 UI Wiring

See `docs/progress/ISSUES.md` ISS-002 for tracking.

---

## Quick Reference

| Need | Go To |
|------|-------|
| Architecture decisions | `docs/architecture/DECISIONS.md` |
| Import rules | `docs/architecture/IMPORT_HIERARCHY.md` |
| Database schema | `docs/specs/database/SCHEMA_OVERVIEW.md` |
| Engine specs | `docs/specs/engines/ENGINE_INDEX.md` |
| Integration specs | `docs/specs/integrations/INTEGRATION_INDEX.md` |
| **E2E Testing** | `docs/e2e/E2E_MASTER.md` |
| Active tasks | `PROGRESS.md` |
| Session history | `docs/progress/SESSION_LOG.md` |
| Known issues | `docs/progress/ISSUES.md` |
| Full archive | `PROJECT_BLUEPRINT_FULL_ARCHIVE.md` |
