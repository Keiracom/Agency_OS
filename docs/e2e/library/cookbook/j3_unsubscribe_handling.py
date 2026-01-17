"""
Skill: J3.8 — Unsubscribe Handling
Journey: J3 - Email Outreach
Checks: 4

Purpose: Verify unsubscribe requests are handled correctly and lead status updated.
"""

CHECKS = [
    {
        "id": "J3.8.1",
        "part_a": "Read `src/services/email_events_service.py` — verify unsubscribe event handling",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/services/email_events_service.py"]
    },
    {
        "id": "J3.8.2",
        "part_a": "Verify lead status updated to UNSUBSCRIBED on unsubscribe event",
        "part_b": "Simulate unsubscribe webhook, check lead record",
        "key_files": ["src/services/email_events_service.py", "src/models/lead.py"]
    },
    {
        "id": "J3.8.3",
        "part_a": "Verify unsubscribed leads excluded from future sends (JIT validation)",
        "part_b": "Attempt send to unsubscribed lead, verify rejection",
        "key_files": ["src/orchestration/flows/outreach_flow.py"]
    },
    {
        "id": "J3.8.4",
        "part_a": "Verify unsubscribe link included in emails (CAN-SPAM compliance)",
        "part_b": "Check sent email for unsubscribe link presence",
        "key_files": ["src/engines/email.py", "src/engines/content.py"]
    }
]

PASS_CRITERIA = [
    "Unsubscribe events update lead status to UNSUBSCRIBED",
    "Unsubscribed leads excluded from JIT validation",
    "Unsubscribe events recorded in email_events table",
    "Emails include unsubscribe link (CAN-SPAM)"
]

KEY_FILES = [
    "src/services/email_events_service.py",
    "src/models/lead.py",
    "src/orchestration/flows/outreach_flow.py",
    "src/engines/email.py"
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
