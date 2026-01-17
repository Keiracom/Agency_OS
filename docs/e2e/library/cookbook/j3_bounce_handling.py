"""
Skill: J3.7 — Bounce Handling
Journey: J3 - Email Outreach
Checks: 4

Purpose: Verify bounced emails are handled correctly and lead status updated.
"""

CHECKS = [
    {
        "id": "J3.7.1",
        "part_a": "Read `src/services/email_events_service.py` — verify bounce event handling",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/services/email_events_service.py"]
    },
    {
        "id": "J3.7.2",
        "part_a": "Verify hard bounce vs soft bounce differentiation in event processing",
        "part_b": "Simulate both bounce types via webhook, check handling",
        "key_files": ["src/services/email_events_service.py"]
    },
    {
        "id": "J3.7.3",
        "part_a": "Verify lead status updated to BOUNCED on hard bounce",
        "part_b": "Check lead record after hard bounce event",
        "key_files": ["src/services/email_events_service.py", "src/models/lead.py"]
    },
    {
        "id": "J3.7.4",
        "part_a": "Verify bounced leads excluded from future sends (JIT validation)",
        "part_b": "Attempt send to bounced lead, verify rejection",
        "key_files": ["src/orchestration/flows/outreach_flow.py"]
    }
]

PASS_CRITERIA = [
    "Hard bounces update lead status to BOUNCED",
    "Soft bounces logged but lead status unchanged",
    "Bounced leads excluded from JIT validation",
    "Bounce events recorded in email_events table"
]

KEY_FILES = [
    "src/services/email_events_service.py",
    "src/models/lead.py",
    "src/orchestration/flows/outreach_flow.py",
    "src/api/routes/webhooks.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
