"""
Skill: J8.9 — Deal Auto-Creation from Meeting
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify deals auto-created from positive meeting outcomes.
"""

CHECKS = [
    {
        "id": "J8.9.1",
        "part_a": "Read `record_outcome` method (lines 364-460)",
        "part_b": "N/A",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.9.2",
        "part_a": "Verify `create_deal=True` parameter",
        "part_b": "Test auto-creation",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.9.3",
        "part_a": "Verify deal linked to meeting",
        "part_b": "Check deal.meeting_id",
        "key_files": ["src/services/deal_service.py"]
    },
    {
        "id": "J8.9.4",
        "part_a": "Verify meeting.deal_id updated",
        "part_b": "Check meeting record",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.9.5",
        "part_a": "Verify attribution carried forward",
        "part_b": "Check deal fields",
        "key_files": ["src/services/deal_service.py", "src/services/meeting_service.py"]
    }
]

PASS_CRITERIA = [
    "Deal created on good outcome",
    "Meeting and deal linked",
    "Attribution preserved"
]

KEY_FILES = [
    "src/services/meeting_service.py",
    "src/services/deal_service.py"
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
