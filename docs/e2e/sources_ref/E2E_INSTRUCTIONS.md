# E2E Testing Instructions for Claude Code

**Purpose:** Standard operating procedure for executing E2E tests
**Version:** 1.0
**Last Updated:** January 11, 2026

---

## Before Starting Any Session

1. **Read `e2e_state.json`** — This is the source of truth for position
2. Read `E2E_MASTER.md` to understand current status
3. Read the journey file for your current group ONLY (e.g., J0.1 section)
4. Verify you're starting from `current_group` in the JSON
5. Resume from the next incomplete sub-task

**CRITICAL:** Always trust `e2e_state.json` over markdown checkboxes. The JSON is machine-readable and must be kept in sync.

---

## How to Execute Sub-Tasks

Each sub-task has two parts:

### Part A: Code & Wiring Verification

1. **Read the relevant source files** — Understand what's implemented
2. **Trace the code path** — Follow the flow from trigger to completion
3. **Check for issues:**
   - TODO, FIXME, or HACK comments
   - `pass` statements or `NotImplementedError`
   - Hardcoded values that should be config
   - Missing error handling
   - Wrong imports or circular dependencies
   - Stubbed or mock implementations
4. **Verify configuration:**
   - Environment variables exist
   - Values point to production (not dev/test)
   - API keys are valid format
5. **Document findings** in the journey file

### Part B: Live Execution Test

1. **Execute the test** — API call, UI action, or verification
2. **Observe behavior** — Check logs, database, responses
3. **Compare to expected** — Does it match the test criteria?
4. **Document result** — Pass, Fail, or Blocked

---

## When Issues Are Found

### If Claude Code CAN Fix (Within Authority)

1. Apply the fix
2. Log to `FIXES_APPLIED.md` with:
   - Fix ID (FIX-E2E-XXX)
   - What was wrong
   - What was changed
   - Files modified
   - How it was verified
3. Update journey file status
4. Continue testing

### If Claude Code CANNOT Fix (Needs CEO)

1. Log to `ISSUES_FOUND.md` with:
   - Issue ID (ISS-E2E-XXX)
   - Severity (Critical/Warning/Info)
   - What's wrong
   - Impact
   - Proposed fix
   - Why CEO approval needed
2. Update `E2E_MASTER.md` "Requires CEO Review" section
3. **STOP and report to CEO**
4. Do NOT proceed until approved

---

## Authority Levels

| Action | Claude Code Authority | Needs CEO Approval |
|--------|----------------------|-------------------|
| Read any file | ✅ | |
| Fix code bugs | ✅ | |
| Create missing source files | ✅ | |
| Create missing test files | ✅ | |
| Update documentation | ✅ | |
| Fix import errors | ✅ | |
| Add missing error handling | ✅ | |
| Complete stubbed implementations | ✅ | |
| | | |
| Add env vars to Railway | | ✅ |
| Modify database schema (migrations) | | ✅ |
| Call paid APIs (Apollo, Apify, etc.) | | ✅ + cost estimate |
| Deploy to production | | ✅ |
| Change auth configuration | | ✅ |
| Modify RLS policies | | ✅ |
| Delete data | | ✅ |

---

## Status Markers

Use these in journey files:

| Marker | Meaning |
|--------|---------|
| 🔴 | Not started |
| 🟡 | In progress |
| ✅ | Passed |
| ❌ | Failed — see ISSUES_FOUND.md |
| ⏸️ | Blocked — awaiting CEO or dependency |
| 🔧 | Fixed — see FIXES_APPLIED.md |
| ⚠️ | Warning — works but needs attention |

---

## Updating Documentation

### After Each Sub-Task

1. Update status in journey file (✅, ❌, etc.)
2. Add notes if relevant
3. If issue found → Update ISSUES_FOUND.md
4. If fix applied → Update FIXES_APPLIED.md
5. If file created → Update FILES_CREATED.md

### After Each Sub-Task Group (MANDATORY)

**You MUST update `e2e_state.json` after every group. This is not optional.**

```json
// Update these fields:
{
  "current_group": "J0.2",           // Next group
  "session_number": 2,               // Increment
  "status": "awaiting_approval",     // ALWAYS set this
  "last_updated": "2026-01-12T...",  // Current timestamp
  "last_session_summary": "Completed J0.1: 6/6 passed",
  "journeys": {
    "J0": {
      "status": "in_progress",
      "groups_completed": ["J0.1"]   // Append completed group
    }
  }
}
```

Then also:
1. Update `E2E_MASTER.md` counts
2. Update "Recent Activity" section
3. **STOP and ask CEO: "J0.1 complete. Approve to continue to J0.2?"**

### CEO Approval Gate (EVERY SESSION)

**After completing ANY group, you MUST:**

1. Update `e2e_state.json` with `"status": "awaiting_approval"`
2. Report results to CEO
3. **WAIT for explicit "yes" or "continue" before proceeding**
4. Only after approval: set `"status": "in_progress"` and start next group

**DO NOT auto-continue to the next group. EVER.**

### After Each Journey Complete

1. Update `e2e_state.json`:
   - Set journey status to `"completed"`
   - Set `current_journey` to next journey
   - Set `current_group` to `"JX.1"`
2. Update `E2E_MASTER.md` journey status to 🟢
3. Update `PROGRESS.md` with summary
4. **STOP and ask CEO: "J0 complete. Approve to start J1?"**

---

## Session Handoff Protocol

If Claude Code context resets mid-testing:

```
1. Read E2E_MASTER.md
   → What journey is active?
   → Any pending CEO reviews?

2. Read active journey file
   → Find last ✅ sub-task
   → Read notes on that sub-task

3. Read ISSUES_FOUND.md
   → Any unresolved issues blocking progress?

4. Read FIXES_APPLIED.md
   → What was recently changed?

5. Resume from next incomplete sub-task
```

---

## Reporting Format

When reporting to CEO, use this format:

```markdown
## E2E Testing Update

**Journey:** J[X] - [Name]
**Status:** [In Progress / Blocked / Complete]
**Sub-tasks:** [X/Y complete]

### Completed This Session
- J[X].[Y]: [Description] ✅
- J[X].[Z]: [Description] ✅

### Issues Found
- ISS-E2E-XXX: [Brief description] — [Severity]

### Fixes Applied
- FIX-E2E-XXX: [Brief description]

### Blocked / Needs Review
- [Item requiring CEO action]

### Next Steps
- [What will be tested next]
```

---

## File Naming Conventions

| Type | Format | Example |
|------|--------|---------|
| Issue ID | ISS-E2E-XXX | ISS-E2E-001 |
| Fix ID | FIX-E2E-XXX | FIX-E2E-001 |
| Journey file | JX_NAME.md | J1_ONBOARDING.md |

---

## Quality Standards

### Every Sub-Task Must

1. Have clear pass/fail criteria
2. Be independently executable
3. Document what was checked
4. Reference specific files/lines when issues found

### Every Fix Must

1. Be verified working
2. Not break other functionality
3. Follow existing code patterns
4. Be documented with context

### Every Issue Must

1. Have clear reproduction steps
2. State the impact
3. Propose a solution
4. Be assigned a severity

---

## Escalation Rules

**Stop immediately and ask CEO when:**

1. Database schema change needed (migration required)
2. Authentication/security change needed
3. Paid API call required (provide cost estimate)
4. Production deployment required
5. Data deletion required
6. Unclear requirement or ambiguous test
7. Risk of breaking existing functionality
8. Found security vulnerability
