"""
Skill: J6.10 — Reply Detection
Journey: J6 - LinkedIn Outreach
Checks: 3

Purpose: Verify LinkedIn replies are detected.
"""

CHECKS = [
    {
        "id": "J6.10.1",
        "part_a": "Verify `get_new_replies` method in engine",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.10.2",
        "part_a": "Verify HeyReach API returns unread messages",
        "part_b": "Check implementation",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.10.3",
        "part_a": "Test reply detection",
        "part_b": "Check HeyReach dashboard",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "New replies detected",
    "Reply data captured correctly"
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
