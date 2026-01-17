"""
Skill: J3.9 — Open/Click Tracking
Journey: J3 - Email Outreach
Checks: 4

Purpose: Verify opens and clicks are tracked via webhooks.
"""

CHECKS = [
    {
        "id": "J3.9.1",
        "part_a": "Read `src/services/email_events_service.py` — verify open/click event handling",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/services/email_events_service.py"]
    },
    {
        "id": "J3.9.2",
        "part_a": "Verify webhook endpoint `/webhooks/email/salesforge` in webhooks.py",
        "part_b": "Test webhook endpoint with sample payload",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J3.9.3",
        "part_a": "Verify duplicate event handling via provider_event_id",
        "part_b": "Send same event twice, verify second is ignored",
        "key_files": ["src/services/email_events_service.py"]
    },
    {
        "id": "J3.9.4",
        "part_a": "Verify activity summary updated via database trigger",
        "part_b": "Check activity record open_count/click_count after events",
        "key_files": ["src/services/email_events_service.py", "src/models/activity.py"]
    }
]

PASS_CRITERIA = [
    "Email events service complete",
    "Webhook endpoints receive events correctly",
    "Duplicates handled gracefully (no double counting)",
    "Activity record updated with event counts"
]

KEY_FILES = [
    "src/services/email_events_service.py",
    "src/api/routes/webhooks.py",
    "src/models/activity.py",
    "src/models/email_event.py"
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
