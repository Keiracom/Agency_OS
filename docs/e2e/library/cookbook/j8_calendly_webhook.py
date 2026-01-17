"""
Skill: J8.1 — Meeting Webhook (Calendly)
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify Calendly webhooks create meetings.
"""

CHECKS = [
    {
        "id": "J8.1.1",
        "part_a": "Read `webhooks.py` — verify `/webhooks/crm/meeting` endpoint (line 1365)",
        "part_b": "Send test webhook",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J8.1.2",
        "part_a": "Read `_handle_calendly_webhook` (lines 1493-1559)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J8.1.3",
        "part_a": "Verify lead matched by email",
        "part_b": "Check lead lookup",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J8.1.4",
        "part_a": "Verify meeting created via MeetingService",
        "part_b": "Check meeting record",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.1.5",
        "part_a": "Verify calendar_event_id stored",
        "part_b": "Check deduplication",
        "key_files": ["src/services/meeting_service.py"]
    }
]

PASS_CRITERIA = [
    "Calendly webhook endpoint exists",
    "Meeting created on invitee.created event",
    "Meeting cancelled on invitee.canceled event",
    "Lead linked correctly"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/services/meeting_service.py"
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
