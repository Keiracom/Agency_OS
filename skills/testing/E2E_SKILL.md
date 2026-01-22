---
name: e2e
description: Manage multi-session E2E testing with automatic state persistence. Use natural language commands like "e2e status", "e2e continue", "e2e resume".
---

# E2E Testing Session Skill

**Purpose:** Manage multi-session E2E testing with automatic state persistence
**Version:** 1.2
**Last Updated:** January 12, 2026
**Config Files:** `docs/e2e/e2e_config.json`, `docs/e2e/e2e_state.json`

---

## How to Use

These are **natural language commands**, not slash commands. Say:
- `e2e status` — Show current position and progress
- `e2e continue` — Execute the next group (requires prior approval)
- `e2e resume` — Resume an interrupted session
- `e2e report` — Generate CEO summary

When Claude Code sees these phrases, it reads this skill file and executes the logic.

---

## CRITICAL RULES (READ FIRST)

### 1. JSON State is Source of Truth
- **ALWAYS** read `e2e_state.json` before starting
- **ALWAYS** update `e2e_state.json` after completing a group
- Markdown files are for humans; JSON is for machine handoff

### 2. CEO Approval Required After EVERY Group
- After completing ANY group, set `"status": "awaiting_approval"`
- Report results to CEO
- **STOP and WAIT** for explicit approval
- **DO NOT** auto-continue to next group

### 3. One Group Per Session
- Execute only the current group (e.g., J0.1)
- Do not continue to J0.2 without CEO approval
- This ensures human oversight at every step

---

## Commands

| Command | Purpose |
|---------|---------|
| `e2e status` | Show current position and progress |
| `e2e continue` | Start/continue next session (next group) |
| `e2e resume` | Resume interrupted session from last check |
| `e2e fix ISS-XXX` | Focus session on fixing specific issue |
| `e2e report` | Generate CEO summary of progress |
| `e2e reset [journey]` | Reset a journey to not_started (use carefully) |

---

## e2e status

**What it does:** Reads `e2e_state.json` and `e2e_config.json`, displays current position.

**Output format:**
```
E2E Testing Status
==================
Current Journey: J0 - Infrastructure & Wiring Audit
Current Group:   J0.3 - Prefect Configuration (6 checks)
Status:          in_progress
Session:         3 of ~139

Progress:
  J0:  [##........] 2/9 groups (J0.1 ✓, J0.2 ✓)
  J1:  [..........] 0/15 groups
  J2:  [..........] 0/12 groups
  ...

Blockers: None
Requires CEO: None

Next: Say "e2e continue" to run J0.3
```

**Implementation:**
```python
# Read state
state = read_json("docs/e2e/e2e_state.json")
config = read_json("docs/e2e/e2e_config.json")

# Display current position
print(f"Current Journey: {state['current_journey']}")
print(f"Current Group: {state['current_group']}")
print(f"Status: {state['status']}")

# Show progress bars for each journey
for journey_id, journey in state['journeys'].items():
    completed = len(journey['groups_completed'])
    total = journey['groups_total']
    # render progress bar
```

---

## e2e continue

**What it does:** Executes the next group of checks in sequence.

**Flow:**
```
1. Read e2e_state.json → Get current_group
2. Read e2e_config.json → Get limits, gates
3. Check approval gates (block if needed)
4. Read journey file → Extract ONLY current group section
5. Generate slim session prompt
6. Execute checks (Part A: wiring, Part B: live)
7. Log issues/fixes as found
8. Update state on completion
9. Output handoff message
```

**Gate Checking:**
```python
# Before J2.5 (Lead Sourcing)
if current_group == "J2.5":
    gate = config['approval_gates']['GATE-3']
    if not gate['approved']:
        print(f"BLOCKED: {gate['trigger']} requires CEO approval")
        print(f"Cost: ${gate['cost_aud']} AUD")
        state['status'] = 'blocked'
        state['requires_ceo'].append('GATE-3')
        save_state()
        return
```

**Session Prompt Generation:**

When `e2e continue` runs, generate a focused prompt:

```markdown
## E2E Session {session_number} — {group_id} {group_name}

**Journey:** {journey_id} - {journey_name}
**Previous:** {prev_group} completed
**This Session:** {group_id} ({check_count} checks)
**After This:** {next_group}

### Context
{1-2 sentences about what was verified in previous groups}

### Checks This Session
{extracted from journey file between current group header and next E2E_SESSION_BREAK}

### Config (from e2e_config.json)
- Test Email: {config.test_recipients.email}
- Lead Limit: {config.limits.leads_to_source}

### On Completion
1. Update e2e_state.json (mark group complete)
2. Update {journey_file}.md (check status markers)
3. Run: e2e continue for {next_group}
```

**State Update on Completion (MANDATORY):**
```python
# Mark group complete
state['journeys'][journey_id]['groups_completed'].append(group_id)
state['current_group'] = next_group_id
state['session_number'] += 1
state['last_updated'] = datetime.now().isoformat()
state['last_session_summary'] = f"Completed {group_id}: {pass_count}/{total_count} passed"

# CRITICAL: Set awaiting approval - DO NOT skip this
state['status'] = 'awaiting_approval'

# If journey complete
if all_groups_done:
    state['journeys'][journey_id]['status'] = 'completed'
    state['current_journey'] = next_journey_id
    state['current_group'] = f"{next_journey_id}.1"

save_state()

# STOP HERE - Report to CEO and wait for approval
print(f"✅ {group_id} complete. {pass_count}/{total_count} passed.")
print(f"⏸️ Awaiting CEO approval to continue to {next_group_id}")
print("Reply 'continue' or 'yes' to proceed.")
# DO NOT auto-continue
```

**CEO Approval Flow:**
```
1. Complete group checks
2. Update e2e_state.json with status="awaiting_approval"
3. Update markdown files
4. Report results to CEO
5. STOP and WAIT
6. On CEO approval → set status="in_progress" → run next group
```

---

## e2e resume

**What it does:** Resume an interrupted session from where it left off.

**When to use:**
- Context window filled mid-session
- Error during execution
- Manual interruption

**Flow:**
```
1. Read e2e_state.json
2. Check status == 'in_progress'
3. Check current_check (if set, resume from there)
4. Generate prompt starting from current_check
5. Continue execution
```

---

## e2e fix ISS-XXX

**What it does:** Focus session on fixing a specific logged issue.

**Flow:**
```
1. Read ISSUES_FOUND.md → Find ISS-XXX
2. Extract issue details (file, line, description)
3. Generate fix-focused prompt
4. Apply fix
5. Re-run relevant check
6. Update FIXES_APPLIED.md
7. Update e2e_state.json (remove from issues_found)
```

---

## e2e report

**What it does:** Generate a CEO-friendly progress summary.

**Output format:**
```markdown
# E2E Testing Report — {date}

## Summary
- **Sessions Completed:** 12 of ~139
- **Journeys:** J0 ✓, J1 in progress
- **Blockers:** 0
- **Issues Found:** 3 (2 fixed, 1 pending)

## Journey Progress
| Journey | Status | Groups | Issues |
|---------|--------|--------|--------|
| J0 Infrastructure | ✅ Complete | 9/9 | 0 |
| J1 Onboarding | 🟡 In Progress | 5/15 | 1 |
| J2 Campaign | ⏸️ Not Started | 0/12 | 0 |

## Pending Issues
1. **ISS-E2E-003** (J1.8): Salesforce API key invalid
   - Impact: Cannot test lead sync
   - Action: CEO to provide new API key

## Budget Used
- Apollo: 0/50 credits ($0/$50)
- Anthropic: $2.30/$9.00
- Total: $2.30/$65.00

## Next Session
Run `e2e continue` to execute J1.6 — ICP Extraction
```

---

## State File Reference

### e2e_state.json (Position)
Location: `docs/e2e/e2e_state.json`
```json
{
  "current_journey": "J0",
  "current_group": "J0.3",
  "current_check": null,
  "status": "in_progress",
  "session_number": 3,
  "journeys": {
    "J0": {
      "status": "in_progress",
      "groups_completed": ["J0.1", "J0.2"],
      "groups_total": 9
    }
  },
  "blockers": [],
  "requires_ceo": [],
  "issues_found": ["ISS-E2E-001"],
  "fixes_applied": ["FIX-E2E-001"],
  "last_updated": "2026-01-12T10:30:00Z",
  "last_session_summary": "Completed J0.2: 7/7 passed"
}
```

### e2e_config.json (Configuration)
Location: `docs/e2e/e2e_config.json`
```json
{
  "test_recipients": {
    "email": "david.stephens@keiracom.com",
    "sms": "+61457543392"
  },
  "limits": {
    "leads_to_source": 50,
    "emails_per_day": 15
  },
  "approval_gates": {
    "GATE-3": { "approved": false, "cost_aud": 50 }
  }
}
```

---

## Session Break Markers

Journey files (in `docs/e2e/`) contain markers to define session boundaries:

```markdown
### J0.3 — Prefect Configuration
...
**Pass Criteria:**
- [ ] All checks pass

<!-- E2E_SESSION_BREAK: J0.3 complete. Next: J0.4 Database Connection -->

---

### J0.4 — Database Connection
```

The skill extracts content between the group header and the next `E2E_SESSION_BREAK` marker.

---

## Error Handling

### Blocker Found
```python
if blocker_found:
    state['status'] = 'blocked'
    state['blockers'].append({
        'id': generate_issue_id(),
        'group': current_group,
        'description': blocker_description,
        'requires': 'ceo' if needs_approval else 'fix'
    })
    save_state()
    log_to_issues_found(blocker)
    print(f"BLOCKED: {blocker_description}")
    print("Fix the issue, then run e2e resume")
```

### Check Failed (Non-Blocking)
```python
if check_failed and not blocking:
    issue_id = generate_issue_id()
    state['issues_found'].append(issue_id)
    log_to_issues_found(issue_id, check_id, failure_reason)
    print(f"ISSUE: {issue_id} logged. Continuing...")
    # Continue to next check
```

### Context Window Warning
```python
if context_usage > 0.7:  # 70% used
    print("WARNING: Context at 70%. Consider completing current group.")
    print("Run e2e continue in new session if needed.")
```

---

## Best Practices

1. **One group per session** — Don't try to do multiple groups
2. **Check status first** — Always run `e2e status` after context reset
3. **Fix blockers immediately** — Don't skip to next group
4. **Update markdown** — Mark checks ✅/❌ as you go
5. **Log everything** — Issues in ISSUES_FOUND.md, fixes in FIXES_APPLIED.md

---

## Quick Reference

```
e2e status              # Where am I?
e2e continue            # Run next group
e2e resume              # Continue interrupted session
e2e fix ISS-E2E-001     # Fix specific issue
e2e report              # CEO summary
```
