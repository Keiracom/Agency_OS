"""
Skill: J8.3 — MeetingService Implementation
Journey: J8 - Meeting & Deals
Checks: 8

Purpose: Verify MeetingService is complete.
"""

CHECKS = [
    {
        "id": "J8.3.1",
        "part_a": "Read `src/services/meeting_service.py` (839 lines)",
        "part_b": "N/A",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.3.2",
        "part_a": "Verify `create` method with all fields",
        "part_b": "Test meeting creation",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.3.3",
        "part_a": "Verify `confirm` method",
        "part_b": "Test confirmation",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.3.4",
        "part_a": "Verify `send_reminder` method",
        "part_b": "Test reminder marking",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.3.5",
        "part_a": "Verify `record_show` method",
        "part_b": "Test show/no-show",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.3.6",
        "part_a": "Verify `record_outcome` method",
        "part_b": "Test outcome recording",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.3.7",
        "part_a": "Verify `reschedule` method",
        "part_b": "Test reschedule",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.3.8",
        "part_a": "Verify `cancel` method",
        "part_b": "Test cancellation",
        "key_files": ["src/services/meeting_service.py"]
    }
]

PASS_CRITERIA = [
    "All CRUD methods implemented",
    "Meeting types validated",
    "Outcomes validated",
    "Lead updated with meeting info"
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
