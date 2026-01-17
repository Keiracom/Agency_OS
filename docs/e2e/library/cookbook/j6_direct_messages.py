"""
Skill: J6.7 — Direct Messages
Journey: J6 - LinkedIn Outreach
Checks: 3

Purpose: Verify direct message functionality.
"""

CHECKS = [
    {
        "id": "J6.7.1",
        "part_a": "Verify `action=\"message\"` flow",
        "part_b": "Check code path",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.7.2",
        "part_a": "Verify activity logged as `message_sent`",
        "part_b": "Check action",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.7.3",
        "part_a": "Send test direct message",
        "part_b": "Verify sent via HeyReach",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Direct messages work",
    "Activity logged correctly"
]

KEY_FILES = [
    "src/engines/linkedin.py"
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
