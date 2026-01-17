"""
Skill: J6.6 — Connection Requests
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Verify connection request functionality.
"""

CHECKS = [
    {
        "id": "J6.6.1",
        "part_a": "Verify `action=\"connection\"` flow",
        "part_b": "Check code path",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.6.2",
        "part_a": "Verify message limit (300 chars) enforced",
        "part_b": "Check HeyReach",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.6.3",
        "part_a": "Verify activity logged as `connection_sent`",
        "part_b": "Check action",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.6.4",
        "part_a": "Send test connection request",
        "part_b": "Verify sent via HeyReach",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Connection requests work",
    "300 character limit respected",
    "Activity logged correctly"
]

KEY_FILES = [
    "src/engines/linkedin.py",
    "src/integrations/heyreach.py"
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
