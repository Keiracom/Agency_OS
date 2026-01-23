# /e2e — E2E Testing Command

Execute E2E testing for Agency OS.

## Command: $ARGUMENTS

---

## STEP 1: ALWAYS READ STATE FIRST

Before doing ANYTHING, read `docs/e2e/e2e_state.json`:

```json
{
  "current": "J0.2",        // Next group to run
  "status": "awaiting_approval" | "approved" | "in_progress" | "blocked",
  "completed": ["J0.1"],    // Groups already done
  "session": 1              // Session counter
}
```

---

## /e2e status (or no argument)

1. Read `docs/e2e/e2e_state.json`
2. Calculate progress for each journey from `completed` array
3. Display:

```
E2E Status
══════════
Current:  [current]
Status:   [status]
Session:  [session]

Progress:
  J0:  [X/9]  ████░░░░░░
  J1:  [X/15] ░░░░░░░░░░
  ...

Completed: [list completed groups]
Blockers:  [blockers or "None"]

Next: [what to do based on status]
```

**If status = "awaiting_approval":**
```
⏸️ Awaiting CEO approval for [current].
CEO: Run `/e2e approve` to proceed.
```

**If status = "approved":**
```
✅ Approved. Run `/e2e continue` to execute [current].
```

**If status = "blocked":**
```
🚫 BLOCKED. See blockers list. Fix issues before continuing.
```

---

## /e2e approve

**This command is for CEO only.**

1. Read `docs/e2e/e2e_state.json`
2. If status != "awaiting_approval", say "Nothing to approve" and stop
3. Update JSON: set `status` = "approved"
4. Save file
5. Output:
```
✅ Approved [current].
Claude can now run `/e2e continue`.
```

---

## /e2e continue

**ENFORCEMENT: This command REFUSES to run unless status = "approved"**

1. Read `docs/e2e/e2e_state.json`
2. **CHECK STATUS:**
   - If status = "awaiting_approval" → Output "❌ Not approved. CEO must run `/e2e approve` first." and **STOP**
   - If status = "blocked" → Output "❌ Blocked. Fix blockers first." and **STOP**
   - If status = "approved" → Continue to step 3
3. Set `status` = "in_progress" and save
4. Parse `current` to get journey (e.g., "J0" from "J0.2")
5. Read the journey file: `docs/e2e/JOURNEYS/J[X]_*.md` or `docs/e2e/J[X]_*.md`
6. Find the section for `current` group (e.g., "### J0.2 —")
7. Execute all checks in that group (Part A and Part B)
8. Log any issues to `docs/e2e/ISSUES_FOUND.md`
9. Log any fixes to `docs/e2e/FIXES_APPLIED.md`
10. Update `docs/e2e/e2e_state.json`:
    - Add `current` to `completed` array
    - Increment `session`
    - Set `current` to next group (e.g., "J0.2" → "J0.3")
    - Set `status` = "awaiting_approval"
    - Set `last_run` = current timestamp
    - Set `last_summary` = brief result
11. Output results:
```
═══════════════════════════════════════
✅ [group] COMPLETE
═══════════════════════════════════════
Checks: [X passed] / [Y total]
Issues: [count or "None"]
Fixes:  [count or "None"]

Summary: [last_summary]

⏸️ Awaiting CEO approval for [next group].
CEO: Run `/e2e approve` to continue.
═══════════════════════════════════════
```
12. **STOP. DO NOT CONTINUE TO NEXT GROUP.**

---

## /e2e fix [ISS-ID]

1. Read `docs/e2e/ISSUES_FOUND.md`
2. Find the issue by ID
3. Focus on fixing that specific issue
4. Update `docs/e2e/FIXES_APPLIED.md` with the fix
5. Re-run the relevant check to verify
6. If fixed, remove from blockers if present

---

## /e2e report

Generate CEO summary:
1. Read `docs/e2e/e2e_state.json`
2. Read `docs/e2e/ISSUES_FOUND.md`
3. Read `docs/e2e/FIXES_APPLIED.md`
4. Output formatted report

---

## CRITICAL RULES

### 1. JSON is the ONLY source of truth
- Do NOT read status from markdown files
- Do NOT track progress in markdown files
- ONLY `e2e_state.json` tracks what's complete

### 2. Approval gate is ENFORCED
- `/e2e continue` checks status FIRST
- If not "approved", it REFUSES to run
- This is not a suggestion, it's a hard gate

### 3. One group per command
- Each `/e2e continue` runs exactly ONE group
- Then it STOPS and waits for approval
- No auto-continuing, no batching

### 4. Update JSON after EVERY group
- Add to `completed`
- Update `current` to next group
- Set `status` to "awaiting_approval"
- This happens IMMEDIATELY after group completes

---

## File Locations

- State: `docs/e2e/e2e_state.json` ← ONLY SOURCE OF TRUTH
- Config: `docs/e2e/e2e_config.json`
- Journey specs: `docs/e2e/J*_*.md`
- Issues log: `docs/e2e/ISSUES_FOUND.md`
- Fixes log: `docs/e2e/FIXES_APPLIED.md`
