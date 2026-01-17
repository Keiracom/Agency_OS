"""
Skill: J8.4 — Meeting Tracking Fields
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify meeting analytics fields are captured.
"""

CHECKS = [
    {
        "id": "J8.4.1",
        "part_a": "Verify `touches_before_booking` calculated",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.4.2",
        "part_a": "Verify `days_to_booking` calculated",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.4.3",
        "part_a": "Verify `converting_activity_id` stored",
        "part_b": "Check attribution",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.4.4",
        "part_a": "Verify `converting_channel` stored",
        "part_b": "Check attribution",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.4.5",
        "part_a": "Verify `original_scheduled_at` preserved on reschedule",
        "part_b": "Check field",
        "key_files": ["src/services/meeting_service.py"]
    }
]

PASS_CRITERIA = [
    "Touches calculated correctly",
    "Days to booking accurate",
    "Attribution fields populated",
    "Reschedule tracking works"
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
