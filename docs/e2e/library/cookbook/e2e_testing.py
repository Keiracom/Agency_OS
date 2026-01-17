"""
E2E Testing Session Skill for Agency OS

Manage multi-session E2E testing with automatic state persistence.
This module contains the INSTRUCTIONS for how to do E2E testing.
The tools/e2e.py module is the RUNNER that tracks state.

Version: 1.2
Last Updated: January 12, 2026
Config Files: docs/e2e/state/e2e_config.json, docs/e2e/state/e2e_state.json

Commands (natural language):
- e2e status   - Show current position and progress
- e2e continue - Execute the next group (requires prior approval)
- e2e resume   - Resume an interrupted session
- e2e report   - Generate CEO summary

CRITICAL RULES:
1. JSON State is Source of Truth - Always read/update e2e_state.json
2. CEO Approval Required After EVERY Group - Set status to "awaiting_approval"
3. One Group Per Session - Execute only the current group
"""

from typing import Dict, List


def get_instructions() -> str:
    """Return the key instructions for E2E testing."""
    return """
E2E TESTING INSTRUCTIONS
========================

CRITICAL RULES (READ FIRST):

1. JSON STATE IS SOURCE OF TRUTH
   - ALWAYS read e2e_state.json before starting
   - ALWAYS update e2e_state.json after completing a group
   - Markdown files are for humans; JSON is for machine handoff

2. CEO APPROVAL REQUIRED AFTER EVERY GROUP
   - After completing ANY group, set "status": "awaiting_approval"
   - Report results to CEO
   - STOP and WAIT for explicit approval
   - DO NOT auto-continue to next group

3. ONE GROUP PER SESSION
   - Execute only the current group (e.g., J0.1)
   - Do not continue to J0.2 without CEO approval
   - This ensures human oversight at every step

COMMANDS:
---------
e2e status       Show current position and progress
e2e continue     Start/continue next session (next group)
e2e resume       Resume interrupted session from last check
e2e fix ISS-XXX  Focus session on fixing specific issue
e2e report       Generate CEO summary of progress
e2e reset        Reset a journey to not_started (use carefully)

EXECUTION FLOW (e2e continue):
------------------------------
1. Read e2e_state.json -> Get current_group
2. Read e2e_config.json -> Get limits, gates
3. Check approval gates (block if needed)
4. Read journey file -> Extract ONLY current group section
5. Generate slim session prompt
6. Execute checks (Part A: wiring, Part B: live)
7. Log issues/fixes as found
8. Update state on completion
9. Output handoff message

STATE UPDATE ON COMPLETION (MANDATORY):
---------------------------------------
1. Mark group complete in state
2. Increment session_number
3. Set status = "awaiting_approval"
4. Save state
5. STOP and report to CEO

BEST PRACTICES:
---------------
1. One group per session - Don't try to do multiple groups
2. Check status first - Always run e2e status after context reset
3. Fix blockers immediately - Don't skip to next group
4. Update markdown - Mark checks with checkboxes as you go
5. Log everything - Issues in ISSUES_FOUND.md, fixes in FIXES_APPLIED.md
"""


def get_code_templates() -> Dict[str, str]:
    """Return code templates for E2E testing."""
    return {
        "state_update": STATE_UPDATE_TEMPLATE,
        "gate_check": GATE_CHECK_TEMPLATE,
        "blocker_handling": BLOCKER_HANDLING_TEMPLATE,
        "check_failed": CHECK_FAILED_TEMPLATE,
        "session_prompt": SESSION_PROMPT_TEMPLATE,
        "report_template": REPORT_TEMPLATE,
    }


def get_commands() -> Dict[str, Dict[str, str]]:
    """Return E2E command definitions."""
    return {
        "status": {
            "purpose": "Show current position and progress",
            "reads": ["e2e_state.json", "e2e_config.json"],
            "writes": [],
        },
        "continue": {
            "purpose": "Start/continue next session (next group)",
            "reads": ["e2e_state.json", "e2e_config.json", "journey files"],
            "writes": ["e2e_state.json", "markdown files"],
        },
        "resume": {
            "purpose": "Resume interrupted session from last check",
            "reads": ["e2e_state.json"],
            "writes": ["e2e_state.json"],
        },
        "fix": {
            "purpose": "Focus session on fixing specific issue",
            "reads": ["ISSUES_FOUND.md", "e2e_state.json"],
            "writes": ["FIXES_APPLIED.md", "e2e_state.json"],
        },
        "report": {
            "purpose": "Generate CEO summary of progress",
            "reads": ["e2e_state.json", "e2e_config.json"],
            "writes": [],
        },
    }


def get_state_schema() -> Dict[str, str]:
    """Return the e2e_state.json schema."""
    return {
        "current": "Current group ID (e.g., J1.4)",
        "status": "in_progress | awaiting_approval | blocked | complete",
        "session": "Session number (increments each group)",
        "completed": "List of completed group IDs",
        "issues": "List of issue IDs found",
        "fixes": "List of fix IDs applied",
        "blockers": "List of active blockers",
        "last_run": "ISO timestamp of last run",
        "last_summary": "Summary of last session",
        "journey_totals": "Dict of journey ID -> total groups",
    }


def get_config_schema() -> Dict[str, str]:
    """Return the e2e_config.json schema."""
    return {
        "test_agency": "Test agency details",
        "test_user": "Test user credentials and IDs",
        "test_recipients": "Where to send test outreach",
        "api_endpoints": "Backend, frontend, Supabase URLs",
        "approval_gates": "Cost approval gates (GATE-1 through GATE-4)",
        "limits": "Test limits (leads, emails, SMS, etc.)",
        "budget": "Budget breakdown by service",
    }


def get_journey_list() -> List[Dict[str, str]]:
    """Return the list of E2E journeys."""
    return [
        {"id": "J0", "name": "Infrastructure & Wiring Audit", "groups": 9},
        {"id": "J1", "name": "Signup & Onboarding", "groups": 15},
        {"id": "J2", "name": "Campaign Setup", "groups": 12},
        {"id": "J2B", "name": "Lead Enrichment", "groups": 8},
        {"id": "J3", "name": "Email Outreach", "groups": 12},
        {"id": "J4", "name": "SMS Outreach", "groups": 12},
        {"id": "J5", "name": "Voice Outreach", "groups": 13},
        {"id": "J6", "name": "LinkedIn Outreach", "groups": 13},
        {"id": "J7", "name": "Reply Handling", "groups": 12},
        {"id": "J8", "name": "Meeting Booking", "groups": 13},
        {"id": "J9", "name": "Dashboard & Analytics", "groups": 16},
        {"id": "J10", "name": "Admin & Billing", "groups": 14},
    ]


def get_approval_gates() -> List[Dict[str, any]]:
    """Return the approval gate definitions."""
    return [
        {"id": "GATE-1", "trigger": "Start J0", "cost_aud": 0, "journey": "J0"},
        {"id": "GATE-2", "trigger": "ICP extraction", "cost_aud": 3, "journey": "J1.10"},
        {"id": "GATE-3", "trigger": "Lead sourcing", "cost_aud": 50, "journey": "J2.5"},
        {"id": "GATE-4", "trigger": "Any outreach", "cost_aud": 1, "journey": "J3+"},
    ]


# =============================================================================
# CODE TEMPLATES
# =============================================================================

STATE_UPDATE_TEMPLATE = """
# Mark group complete
state['completed'].append(group_id)
state['current'] = next_group_id
state['session'] = state.get('session', 0) + 1
state['last_run'] = datetime.now().isoformat()
state['last_summary'] = f"Completed {group_id}: {pass_count}/{total_count} passed"

# CRITICAL: Set awaiting approval - DO NOT skip this
state['status'] = 'awaiting_approval'

# If journey complete
if all_groups_done:
    state['current'] = f"{next_journey_id}.1"

save_state()

# STOP HERE - Report to CEO and wait for approval
print(f"[x] {group_id} complete. {pass_count}/{total_count} passed.")
print(f"[!] Awaiting CEO approval to continue to {next_group_id}")
print("Reply 'continue' or 'yes' to proceed.")
# DO NOT auto-continue
"""

GATE_CHECK_TEMPLATE = """
# Before J2.5 (Lead Sourcing)
if current_group == "J2.5":
    gate = config['approval_gates']['GATE-3']
    if not gate['approved']:
        print(f"BLOCKED: {gate['trigger']} requires CEO approval")
        print(f"Cost: ${gate['cost_aud']} AUD")
        state['status'] = 'blocked'
        state['blockers'].append('GATE-3')
        save_state()
        return
"""

BLOCKER_HANDLING_TEMPLATE = """
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
"""

CHECK_FAILED_TEMPLATE = """
if check_failed and not blocking:
    issue_id = generate_issue_id()
    state['issues'].append(issue_id)
    log_to_issues_found(issue_id, check_id, failure_reason)
    print(f"ISSUE: {issue_id} logged. Continuing...")
    # Continue to next check
"""

SESSION_PROMPT_TEMPLATE = """
## E2E Session {session_number} - {group_id} {group_name}

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
"""

REPORT_TEMPLATE = """
# E2E Testing Report - {date}

## Summary
- **Sessions Completed:** {completed} of ~{total}
- **Journeys:** {journey_status}
- **Blockers:** {blocker_count}
- **Issues Found:** {issue_count} ({fixed_count} fixed, {pending_count} pending)

## Journey Progress
| Journey | Status | Groups | Issues |
|---------|--------|--------|--------|
{journey_table}

## Pending Issues
{pending_issues}

## Budget Used
{budget_usage}

## Next Session
Run `e2e continue` to execute {next_group}
"""


if __name__ == "__main__":
    print(get_instructions())
