"""
Skill: J8.6 — Show Rate Tracking
Journey: J8 - Meeting & Deals
Checks: 5

Purpose: Verify show/no-show tracking for CIS learning.
"""

CHECKS = [
    {
        "id": "J8.6.1",
        "part_a": "Read `record_show` method (lines 316-362)",
        "part_b": "Test show recording",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.6.2",
        "part_a": "Verify `showed_up` field",
        "part_b": "Check boolean",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.6.3",
        "part_a": "Verify `showed_up_confirmed_by` field",
        "part_b": "Check source",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.6.4",
        "part_a": "Verify `no_show_reason` field",
        "part_b": "Check reason",
        "key_files": ["src/services/meeting_service.py"]
    },
    {
        "id": "J8.6.5",
        "part_a": "Read `get_show_rate_analysis` method",
        "part_b": "Check analytics",
        "key_files": ["src/services/meeting_service.py"]
    }
]

PASS_CRITERIA = [
    "Show/no-show recorded",
    "Confirmation method tracked",
    "Show rate analytics available"
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
