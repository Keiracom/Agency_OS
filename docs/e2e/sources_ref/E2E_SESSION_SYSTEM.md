# E2E Session System — Hybrid Architecture

**Status:** Approved by CEO + CTO
**Date:** January 12, 2026
**Purpose:** Enable multi-session E2E testing without context window overflow
**Related:** `E2E_TEST_PLAN.md` (test agency, budget, recipients)

---

## Problem Statement

Current E2E testing requires Claude Code to:
1. Read `E2E_MASTER.md` (~140 lines)
2. Read `E2E_INSTRUCTIONS.md` (~240 lines)
3. Read journey file `JX_*.md` (~300-500 lines each)
4. Execute sub-tasks (code reading, API calls, fixes)
5. Update 3-4 markdown files per task
6. Track state by parsing markdown checkboxes

**Result:** Context window fills at ~30-40% through a journey. No automated handoff.

---

## Solution: Hybrid Approach

Keep existing markdown documentation (well-structured, human-readable) and add:
1. **`e2e_state.json`** — Machine-readable position pointer
2. **`/e2e` skill** — Smart session management
3. **Session break markers** — Natural stopping points in journey files

```
┌─────────────────────────────────────────────────────────────┐
│                    KEEP AS-IS (Markdown)                    │
│                                                             │
│  E2E_MASTER.md      <- Human dashboard                      │
│  JX_*.md            <- Detailed sub-tasks (Part A + B)      │
│  ISSUES_FOUND.md    <- Problems discovered                  │
│  FIXES_APPLIED.md   <- Changes made                         │
└─────────────────────────────────────────────────────────────┘
                              +
┌─────────────────────────────────────────────────────────────┐
│                    ADD (JSON + Skill)                       │
│                                                             │
│  e2e_state.json     <- Machine-readable position pointer    │
│  /e2e skill         <- Smart session management             │
└─────────────────────────────────────────────────────────────┘
```

---

## Session Granularity

**One sub-task GROUP per session.**

Example for J0 (Infrastructure Audit):
| Session | Group | Checks | Focus |
|---------|-------|--------|-------|
| 1 | J0.1 | 6 | Railway Services Health |
| 2 | J0.2 | 7 | Environment Variables |
| 3 | J0.3 | 6 | Prefect Configuration |
| 4 | J0.4 | 6 | Database Connection |
| 5 | J0.5 | 9 | Integration Wiring |
| 6 | J0.6 | 8 | Code Completeness |
| 7 | J0.7 | 6 | Import Hierarchy |
| 8 | J0.8 | 7 | Docker & Deployment |
| 9 | J0.9 | 7 | E2E Coverage Verification |

**Context usage per session:** ~15-25% (leaves room for fixes)

---

## Component 1: e2e_config.json (Test Configuration)

Location: `docs/e2e/e2e_config.json`

Machine-readable test parameters:

```json
{
  "test_recipients": {
    "email": "david.stephens@keiracom.com",
    "sms": "+61457543392"
  },
  "limits": {
    "leads_to_source": 50,
    "leads_to_enrich": 20,
    "emails_per_day": 15
  },
  "budget": {
    "total_aud": 65,
    "apollo_credits": 50
  },
  "approval_gates": {
    "GATE-3": { "trigger": "Lead sourcing", "cost_aud": 50, "approved": false }
  }
}
```

**Why separate from state:** Config is static (set once), state changes every session.

---

## Component 2: e2e_state.json (Position Tracking)

Location: `docs/e2e/e2e_state.json`

```json
{
  "version": "1.0",
  "current_journey": "J0",
  "current_group": "J0.1",
  "current_check": null,
  "status": "not_started",
  "session_number": 0,
  "journeys": {
    "J0": { "status": "not_started", "groups_completed": [] },
    "J1": { "status": "not_started", "groups_completed": [] },
    "J2": { "status": "not_started", "groups_completed": [] },
    "J2B": { "status": "not_started", "groups_completed": [] },
    "J3": { "status": "not_started", "groups_completed": [] },
    "J4": { "status": "not_started", "groups_completed": [] },
    "J5": { "status": "not_started", "groups_completed": [] },
    "J6": { "status": "not_started", "groups_completed": [] },
    "J7": { "status": "not_started", "groups_completed": [] },
    "J8": { "status": "not_started", "groups_completed": [] },
    "J9": { "status": "not_started", "groups_completed": [] },
    "J10": { "status": "not_started", "groups_completed": [] }
  },
  "blockers": [],
  "requires_ceo": [],
  "issues_found": [],
  "fixes_applied": [],
  "last_updated": null,
  "last_session_summary": null
}
```

**Why this works:** Claude reads ~40 lines of JSON instead of scanning 300+ lines of markdown for checkboxes.

---

## Component 3: /e2e Skill

Location: `skills/testing/E2E_SKILL.md`

### Commands

| Command | Purpose |
|---------|---------|
| `/e2e status` | Show current position and progress |
| `/e2e continue` | Start next session (next group) |
| `/e2e resume` | Resume interrupted session |
| `/e2e fix ISS-XXX` | Focus session on specific issue |
| `/e2e report` | Generate CEO summary |

### How `/e2e continue` Works

1. Read `e2e_state.json` to get current position
2. Read ONLY the relevant group section from journey file
3. Generate slim session prompt (~40-60 lines)
4. Execute checks in that group
5. Update state and markdown on completion
6. Output handoff message

### Session Prompt Template

When `/e2e continue` runs, it generates:

```markdown
## E2E Session [N] — [GROUP_ID] [GROUP_NAME]

**Journey:** [JOURNEY_ID] - [JOURNEY_NAME]
**Previous:** [PREV_GROUP] completed
**This Session:** [GROUP_ID] ([CHECK_COUNT] checks)
**After This:** [NEXT_GROUP]

### Context
[1-2 sentences about what was verified in previous groups]

### Checks This Session
1. [CHECK_ID]: [Description] -> [Expected]
2. [CHECK_ID]: [Description] -> [Expected]
...

### Files to Read
- [file1]
- [file2]

### Pass Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]

### On Completion
Update: e2e_state.json, [JOURNEY_FILE].md
Next: /e2e continue for [NEXT_GROUP]
```

**Target size:** 40-60 lines (vs 300+ for full journey file)

---

## Component 4: Session Break Markers

Add to existing journey files at natural break points:

```markdown
### J0.3 — Prefect Configuration Verification
...
**Pass Criteria:**
- [ ] Work pool exists
- [ ] All 15 flows deployed

<!-- E2E_SESSION_BREAK: J0.3 complete. Next: J0.4 Database Connection -->

---

### J0.4 — Database Connection Verification
...
```

These markers help:
1. Skill knows where to extract content
2. Humans see natural stopping points
3. Session boundaries are explicit

---

## Workflow

### Starting E2E Testing

```
User: /e2e status
Claude: Shows current state (J0.1 not started)

User: /e2e continue
Claude: Generates slim prompt for J0.1, executes 6 checks
Claude: Updates e2e_state.json with status="awaiting_approval"
Claude: Updates markdown files
Claude: "✅ J0.1 complete (6/6 passed). Awaiting approval for J0.2."
Claude: STOPS AND WAITS

User: continue
Claude: Sets status="in_progress", starts J0.2
```

### Resuming After Context Reset

```
User: /e2e continue
Claude: Reads e2e_state.json (instant)
Claude: Sees status = "awaiting_approval", current_group = J0.4
Claude: "Last session completed J0.3. Awaiting approval for J0.4."
Claude: WAITS for approval

User: yes
Claude: Sets status="in_progress", starts J0.4
```

### CEO Approval Required (EVERY SESSION)

**After completing ANY group:**
1. Update `e2e_state.json` → `status: "awaiting_approval"`
2. Report results to CEO
3. **STOP** — Do not continue automatically
4. Wait for CEO to say "continue", "yes", or "approved"
5. Only then start next group

### Handling Blockers

```
User: /e2e continue
Claude: Executing J0.5.3...
Claude: Found issue - Apollo API key invalid
Claude: Logs to ISSUES_FOUND.md
Claude: Updates e2e_state.json with blocker
Claude: "BLOCKED: ISS-E2E-001 requires CEO action"

User: [fixes API key]
User: /e2e resume
Claude: Continues J0.5 from J0.5.3
```

---

## State Transitions

```
                         CEO: "continue"
    ┌──────────────────────────────────────────────────┐
    │                                                  │
    ▼                                                  │
┌─────────┐    ┌─────────────┐    ┌─────────────────┐  │   ┌───────────┐
│   not   │───>│ in_progress │───>│    awaiting     │──┴──>│ completed │
│ started │    └─────────────┘    │    _approval    │      └───────────┘
└─────────┘           │           └─────────────────┘
                      │                    │
                      │ blocker found      │ CEO: "stop"
                      ▼                    ▼
               ┌─────────────┐      ┌─────────────┐
               │   blocked   │      │   stopped   │
               └─────────────┘      └─────────────┘
                      │
                      │ /e2e resume (after fix)
                      ▼
               ┌─────────────┐
               │ in_progress │
               └─────────────┘
```

**CRITICAL:** Every group ends in `awaiting_approval`. Claude Code MUST stop and wait for CEO to say "continue" before starting the next group. This is non-negotiable.

---

## File Updates Per Session

| File | What Gets Updated |
|------|-------------------|
| `e2e_config.json` | approval_gates (when CEO approves) |
| `e2e_state.json` | current_group, session_number, groups_completed |
| `JX_*.md` | Check status markers (✅, ❌, ⏸️) |
| `ISSUES_FOUND.md` | If issues discovered |
| `FIXES_APPLIED.md` | If fixes applied |
| `E2E_MASTER.md` | Journey-level status (only when journey completes) |

---

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| Context per session | ~60-80% (full journey) | ~15-25% (one group) |
| Handoff complexity | 5-step manual process | Single JSON read |
| State parsing | Scan markdown checkboxes | Read JSON field |
| Human readability | Good | Unchanged |
| Session boundaries | Implicit | Explicit markers |

---

## Implementation Checklist

- [x] Create `docs/e2e/e2e_config.json` (test parameters)
- [x] Create `docs/e2e/e2e_state.json` (initialized)
- [x] Add session break markers to J0_INFRASTRUCTURE.md (9 markers)
- [x] Add session break markers to J1_ONBOARDING.md (15 markers)
- [x] Add session break markers to J2_CAMPAIGN.md (12 markers)
- [x] Add session break markers to J2B_ENRICHMENT.md (8 markers)
- [x] Add session break markers to J3_EMAIL.md (12 markers)
- [x] Add session break markers to J4_SMS.md (12 markers)
- [x] Add session break markers to J5_VOICE.md (13 markers)
- [x] Add session break markers to J6_LINKEDIN.md (13 markers)
- [x] Add session break markers to J7_REPLY.md (12 markers)
- [x] Add session break markers to J8_MEETING.md (14 markers)
- [x] Add session break markers to J9_DASHBOARD.md (14 markers)
- [x] Add session break markers to J10_ADMIN.md (15 markers)
- [x] Create `skills/testing/E2E_SKILL.md`
- [x] Update `skills/SKILL_INDEX.md` to include /e2e
- [x] Update `E2E_MASTER.md` to reference this system
- [ ] Test with J0.1 session

---

## Reference: Session Counts by Journey

| Journey | Groups | Est. Sessions |
|---------|--------|---------------|
| J0 | J0.1-J0.9 | 9 |
| J1 | J1.1-J1.15 | 15 |
| J2 | J2.1-J2.12 | 12 |
| J2B | J2B.1-J2B.8 | 8 |
| J3 | J3.1-J3.12 | 12 |
| J4 | J4.1-J4.12 | 12 |
| J5 | J5.1-J5.13 | 13 |
| J6 | J6.1-J6.13 | 13 |
| J7 | J7.1-J7.12 | 12 |
| J8 | J8.1-J8.13 | 13 |
| J9 | J9.1-J9.16 | 16 |
| J10 | J10.1-J10.14 | 14 |
| **Total** | | **~139 sessions** |

Each session: ~5-10 minutes of execution time.

---

## Inspiration

This system is inspired by:

1. **Anthropic's Autonomous Coding Demo** — Multi-session persistence via JSON progress file, fresh context per session
2. **AutoMaker** — Kanban-style state machine, approval workflows, session isolation

Adapted for E2E testing where human (CEO) checkpoints are required.
