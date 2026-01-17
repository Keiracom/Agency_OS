# E2E Task System Commands

A simple guide to running the E2E testing system.

---

## Quick Reference

| What You Want | Command |
|---------------|---------|
| See progress | `python docs/e2e/tools/progress.py status` |
| Get next task | `python docs/e2e/tools/progress.py next` |
| Mark task done | `python docs/e2e/tools/progress.py complete J1.5 --summary "What I did"` |
| Check all journeys | `python docs/e2e/tools/qa_runner.py verify_all` |

---

## Detailed Command Guide

### 1. Check Your Progress

```
python docs/e2e/tools/progress.py status
```

**What it does:** Shows a dashboard of all testing phases (J0 through J10), how many tasks are done in each, and your overall progress percentage.

**When to use:** Start of a session to see where you left off.

**Example output:**
```
PHASES:
  [x] J0: Infrastructure & Wiring Audit (9/9)
  [ ] J1: Signup & Onboarding (4/15)
  [ ] J2: Campaign Creation (0/12)
  ...
Progress: 8.6%
NEXT: J1.5 - Middleware Route Protection
```

---

### 2. Get the Next Task

```
python docs/e2e/tools/progress.py next
```

**What it does:** Shows you exactly what to test next, including:
- The task name and ID
- Step-by-step checks to perform
- Which files in the codebase are relevant
- What "passing" looks like

**When to use:** When you're ready to work on the next test.

---

### 3. Mark a Task Complete

```
python docs/e2e/tools/progress.py complete J1.5 --summary "Verified middleware redirects work"
```

**What it does:** Marks a task as done and records what you learned.

**Parts:**
- `J1.5` = The task ID (shown in the `next` command)
- `--summary "..."` = A brief note about what you did or found

**When to use:** After you've finished all checks for a task.

---

### 4. Save a Reusable Learning

```
python docs/e2e/tools/progress.py capture auth_fix "How to fix the auth redirect loop"
```

**What it does:** Creates a draft file to document a pattern or fix you discovered that might be useful later.

**Parts:**
- `auth_fix` = A short name for this learning (no spaces)
- `"..."` = Description of what you learned

**When to use:** When you solve a tricky problem and want to remember how.

**Where it saves:** `docs/e2e/library/drafts/auth_fix.py`

---

### 5. Force Complete (Skip the Summary)

```
python docs/e2e/tools/progress.py force_complete J1.5 --summary "Nothing notable"
```

**What it does:** Same as `complete`, but skips the prompt asking if you want to capture a learning.

**When to use:** For straightforward tasks where there's nothing special to note.

---

### 6. View Session History

```
python docs/e2e/tools/progress.py history
```

**What it does:** Shows a log of all tasks you've completed, with timestamps and summaries.

**When to use:** To review what's been done or remember what you worked on.

---

### 7. Verify a Single Journey

```
python docs/e2e/tools/qa_runner.py verify J1
```

**What it does:** Checks that all task files for a journey (like J1) exist and are properly formatted.

**Parts:**
- `J1` = The journey ID (J0, J1, J2, J2B, J3, J4, J5, J6, J7, J8, J9, J10)

**When to use:** After creating or editing task files to make sure nothing is broken.

---

### 8. Verify All Journeys

```
python docs/e2e/tools/qa_runner.py verify_all
```

**What it does:** Runs verification on all 12 journeys at once and shows a summary.

**When to use:** For a full system health check.

**Example output:**
```
QA SUMMARY - ALL JOURNEYS
  [PASS] J0: Infrastructure (9/9 tasks, 62 checks)
  [PASS] J1: Signup & Onboarding (15/15 tasks, 87 checks)
  ...
OVERALL: ALL PASSED
```

---

## Typical Workflow

1. **Start session:**
   ```
   python docs/e2e/tools/progress.py status
   ```

2. **Get task:**
   ```
   python docs/e2e/tools/progress.py next
   ```

3. **Do the testing** (follow the checks shown)

4. **Mark complete:**
   ```
   python docs/e2e/tools/progress.py complete J1.5 --summary "All checks passed"
   ```

5. **Repeat** steps 2-4

---

## Journey Reference

| ID | Name | Tasks |
|----|------|-------|
| J0 | Infrastructure & Wiring Audit | 9 |
| J1 | Signup & Onboarding | 15 |
| J2 | Campaign Creation & Management | 12 |
| J2B | Lead Enrichment Pipeline | 8 |
| J3 | Email Outreach | 12 |
| J4 | SMS Outreach | 12 |
| J5 | Voice Outreach | 13 |
| J6 | LinkedIn Outreach | 13 |
| J7 | Reply Handling | 14 |
| J8 | Meeting & Deals | 14 |
| J9 | Client Dashboard | 14 |
| J10 | Admin Dashboard | 15 |

**Total: 141 tasks, 790 checks**

---

## Troubleshooting

### "Task not found"
Make sure you're using the correct task ID format: `J1.5` not `j1.5` or `J1-5`

### Command not working
Make sure you're running from the `C:\AI\Agency_OS` directory.

### Want to redo a task
The system doesn't have an "uncomplete" command. Edit `docs/e2e/state/process.json` and remove the task ID from the `"completed"` list.
