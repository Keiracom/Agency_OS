"""
Skill: J6.9 — Activity Logging
Journey: J6 - LinkedIn Outreach
Checks: 5

Purpose: Verify all actions create activity records.
"""

CHECKS = [
    {
        "id": "J6.9.1",
        "part_a": "Read `_log_activity` method in linkedin.py",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.9.2",
        "part_a": "Verify all fields populated",
        "part_b": "Check activity schema",
        "key_files": ["src/models/activity.py"]
    },
    {
        "id": "J6.9.3",
        "part_a": "Verify content_snapshot stored (Phase 16)",
        "part_b": "Check snapshot",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.9.4",
        "part_a": "Verify template_id stored (Phase 24B)",
        "part_b": "Check field",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.9.5",
        "part_a": "Verify message_type tracked",
        "part_b": "connection vs message",
        "key_files": ["src/engines/linkedin.py"]
    }
]

PASS_CRITERIA = [
    "Activity created on every action",
    "Connection vs message distinguished",
    "All fields populated"
]

KEY_FILES = [
    "src/engines/linkedin.py",
    "src/models/activity.py"
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
