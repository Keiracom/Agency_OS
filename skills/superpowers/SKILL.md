# Superpowers Skill

**Trigger:** `/superpowers` command or user says "superpowers"

## Overview

Superpowers is a structured development workflow that enforces: **Brainstorm → Plan → Execute → Review**

When triggered, follow these phases in order. Do NOT skip phases unless explicitly told to.

---

## Phase 1: BRAINSTORM (Clarify Requirements)

**Goal:** Understand what we're building before writing any code.

**Actions:**
1. Ask clarifying questions if the request is ambiguous
2. Identify the core problem being solved
3. List constraints (budget, timeline, tech stack)
4. Generate 2-3 approach options with trade-offs
5. Present options and get sign-off on direction

**Output:** Clear problem statement + chosen approach

**Exit Criteria:** User confirms direction with "go", "yes", "approved", or 👍

---

## Phase 2: PLAN (Break Into Tasks)

**Goal:** Create an executable task list before any implementation.

**Actions:**
1. Break work into tasks of ≤50 lines each (LAW V compliance)
2. Assign each task to an agent from the fleet:
   - `build-1`: Frontend (Vercel, Next.js, UI)
   - `build-2`: Backend (Railway, FastAPI, API)
   - `research-1/2`: Technical or market research
   - `data-1/2`: Database or data processing
   - `test-1`: QA and validation
   - `ops-1`: Infrastructure and monitoring
3. Identify dependencies between tasks
4. Create git branch for the work: `feature/<name>`
5. Present the plan in a table

**Output Format:**
```
| # | Task | Agent | Depends On | Est. Lines |
|---|------|-------|------------|------------|
| 1 | ... | build-1 | - | 30 |
| 2 | ... | build-2 | 1 | 45 |
```

**Exit Criteria:** User approves plan

---

## Phase 3: EXECUTE (Spawn & Monitor)

**Goal:** Parallel execution via sub-agents with progress tracking.

**Actions:**
1. Spawn agents for independent tasks (no dependencies)
2. As agents complete, spawn dependent tasks
3. Collect results and track progress
4. Report status after each agent completes:
   ```
   ✅ Task 1 complete (build-1)
   ⏳ Task 2 in progress (build-2)
   ⏸️ Task 3 waiting on Task 2
   ```
5. Handle failures per contingency plan (retry with smaller scope, escalate if 2+ failures)

**Agent Spawn Pattern:**
```
sessions_spawn(
  label="<agent>",
  task="<clear objective>. Report: 1) What you did, 2) What worked, 3) What failed, 4) File paths or PR link.",
  cleanup="keep"
)
```

**Exit Criteria:** All tasks complete or escalated

---

## Phase 4: REVIEW (Quality Gate)

**Goal:** Validate work before presenting to Dave.

**Actions:**
1. Review all agent outputs
2. Run tests if applicable (`test-1` or manual)
3. Check for:
   - Code compiles/runs
   - No obvious bugs
   - Follows project patterns
   - Security considerations
4. Create PR if code changes involved
5. Present summary to Dave:
   ```
   ## Superpowers Complete ✅
   
   **Built:** [what was created]
   **Agents Used:** [list]
   **Time:** [duration]
   **PR:** [link if applicable]
   
   **Next Steps:** [recommendations]
   ```

**Exit Criteria:** Dave acknowledges or requests changes

---

## Interrupts & Overrides

- **"skip to execute"** → Jump to Phase 3 (use last known plan)
- **"stop"** → Halt all agents, preserve state
- **"status"** → Report current phase and progress
- **"restart"** → Go back to Phase 1

---

## Governance Trace

All superpowers runs must log to Supabase:
```sql
INSERT INTO audit_logs (action, resource_type, operation, metadata, success)
VALUES ('create', 'superpowers', '<phase>', '<details>', true);
```

---

*Skill Version: 1.0 | Ratified: 2026-02-08*
