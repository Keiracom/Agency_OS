"""
Skill: J8.5 — Meeting Reminder System
Journey: J8 - Meeting & Deals
Checks: 4

Purpose: Verify meeting reminders work.
"""

CHECKS = [
    {
        "id": "J8.5.1",
        "part_a": "Read `list_needing_reminder` method",
        "part_b": "N/A",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.5.2",
        "part_a": "Verify 24-hour reminder window",
        "part_b": "Check query",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.5.3",
        "part_a": "Verify `reminder_sent` flag updated",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.5.4",
        "part_a": "Verify `reminder_sent_at` timestamp",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"]
    }
]

PASS_CRITERIA = [
    "Reminder query returns correct meetings",
    "Reminder sent tracking works",
    "24-hour window configurable"
]

KEY_FILES = [
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
