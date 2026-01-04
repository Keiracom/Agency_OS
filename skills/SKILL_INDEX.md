# SKILL INDEX — Agency OS

**Purpose:** Master index of all skills available for Claude Code agents.  
**Location:** `C:\AI\Agency_OS\skills\`  
**Last Updated:** December 27, 2025

---

## How Skills Work

Skills are structured documentation that agents read before executing tasks. They provide:
- Detailed specifications
- File structures
- Code patterns
- Implementation order
- Success criteria

**Usage:** All agents read the relevant SKILL.md before starting any related task.

---

## Agent Skills (Core)

These skills define how the 3-agent pipeline operates:

| Skill | Location | Purpose | Status |
|-------|----------|---------|--------|
| Builder Agent | `skills/agents/BUILDER_SKILL.md` | Code patterns, standards, templates | ✅ v2.0 |
| QA Agent | `skills/agents/QA_SKILL.md` | Check patterns, issue routing, reports | ✅ v2.0 |
| Fixer Agent | `skills/agents/FIXER_SKILL.md` | Fix patterns, documentation format | ✅ v2.0 |
| Pipeline Coordination | `skills/agents/COORDINATION_SKILL.md` | How 3 agents work together | ✅ v2.0 |

---

## Frontend Skills

| Skill | Location | Purpose | Status |
|-------|----------|---------|--------|
| Admin Dashboard | `skills/frontend/ADMIN_DASHBOARD.md` | Platform owner dashboard | ✅ Complete |
| **Frontend-Backend Connection** | `skills/frontend/FRONTEND_BACKEND_SKILL.md` | Phase 13 API integration | ✅ Ready |
| **Missing UI Features** | `skills/frontend/MISSING_UI_SKILL.md` | Phase 14 Replies, Meetings, Credits | ✅ Ready |
| User Dashboard | `skills/frontend/USER_DASHBOARD.md` | Client-facing dashboard | 🔴 Not Started |

---

## Backend Skills

| Skill | Location | Purpose | Status |
|-------|----------|---------|--------|
| API Routes | `skills/backend/API_SKILL.md` | FastAPI route patterns | 🔴 Not Started |
| Engines | `skills/backend/ENGINE_SKILL.md` | Engine implementation | 🔴 Not Started |
| Integrations | `skills/backend/INTEGRATION_SKILL.md` | Channel integrations | 🔴 Not Started |

---

## Phase Skills

| Skill | Location | Purpose | Status |
|-------|----------|---------|--------|
| ICP Discovery | `skills/icp/ICP_SKILL.md` | Phase 11 ICP extraction | 🔴 Not Started |
| **Campaign Generation** | `skills/campaign/CAMPAIGN_SKILL.md` | Phase 12A campaign skills | ✅ Ready |
| Onboarding | `skills/onboarding/ONBOARDING_SKILL.md` | Client onboarding flow | 🔴 Not Started |
| **Live UX Testing** | `skills/testing/LIVE_UX_TEST_SKILL.md` | Phase 15 end-to-end testing | ✅ Ready |
| **Conversion Intelligence** | `skills/conversion/CONVERSION_SKILL.md` | Phase 16 learning system | ✅ Ready |

---

## Database Skills

| Skill | Location | Purpose | Status |
|-------|----------|---------|--------|
| Migrations | `skills/database/MIGRATION_SKILL.md` | Supabase migrations | 🔴 Not Started |
| RLS Policies | `skills/database/RLS_SKILL.md` | Row-level security | 🔴 Not Started |

---

## DevOps Skills

| Skill | Location | Purpose | Status |
|-------|----------|---------|--------|
| Deployment | `skills/deployment/SKILL.md` | Production deployment | 🔴 Not Started |
| Troubleshooting | `skills/troubleshooting/SKILL.md` | Common issues | 🔴 Not Started |

---

## How Agents Use Skills

### Builder Agent
1. Reads `skills/agents/BUILDER_SKILL.md` for templates
2. Reads phase skill (e.g., `skills/icp/ICP_SKILL.md`) for requirements
3. Creates code following both

### QA Agent
1. Reads `skills/agents/QA_SKILL.md` for check patterns
2. Reads phase skill for context-specific checks
3. Routes issues correctly (MISSING→Builder, VIOLATION→Fixer)

### Fixer Agent
1. Reads `skills/agents/FIXER_SKILL.md` for fix patterns
2. Reads phase skill for context-specific fixes
3. Applies fixes, documents everything

---

## Creating New Skills

When starting a new phase, create a skill file:

```markdown
# SKILL.md — [Phase/Feature Name]

**Skill:** [Name]
**Author:** [Who created it]
**Version:** [X.X]
**Created:** [Date]

---

## Purpose

[What this skill enables]

---

## Prerequisites

[What must exist before using this skill]

---

## Required Files

[List all files that must be created]

| File | Purpose |
|------|---------|
| path/to/file.py | Description |

---

## Required Patterns

[Context-specific patterns for this skill]

---

## Implementation Order

[Step-by-step order]

---

## Success Criteria

[How to know it's done correctly]

---

## QA Checks

[Context-specific checks for QA agent]

---

## Fix Patterns

[Context-specific fix patterns for Fixer agent]
```

---

## Quick Reference: Agent Pipeline

```
Terminal 1 (Builder)        Terminal 2 (QA)          Terminal 3 (Fixer)
────────────────────       ────────────────         ─────────────────
Prompt:                    Prompt:                  Prompt:
BUILDER_AGENT_PROMPT.md    QA_AGENT_PROMPT.md       FIXER_AGENT_PROMPT.md

Reads:                     Reads:                   Reads:
- PROGRESS.md              - PROGRESS.md            - qa_reports/
- builder_tasks/           - src/, frontend/        - PROGRESS.md
- Current phase skill      - fixer_reports/         - Current phase skill

Writes:                    Writes:                  Writes:
- src/, frontend/          - qa_reports/            - src/, frontend/
- PROGRESS.md              - builder_tasks/         - fixer_reports/

Cycle:                     Cycle:                   Cycle:
On demand                  90 seconds               2 minutes
```

---

## Current Build Focus

Check PROGRESS.md to find:
- Current phase (look for 🟡)
- Active tasks
- Which skill file applies

---
