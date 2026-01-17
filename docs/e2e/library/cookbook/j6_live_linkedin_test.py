"""
Skill: J6.13 — Live LinkedIn Test
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Verify real LinkedIn actions work.
"""

CHECKS = [
    {
        "id": "J6.13.1",
        "part_a": "Verify test seat available",
        "part_b": "Check HeyReach dashboard",
        "key_files": []
    },
    {
        "id": "J6.13.2",
        "part_a": "N/A",
        "part_b": "Send test connection request",
        "key_files": []
    },
    {
        "id": "J6.13.3",
        "part_a": "N/A",
        "part_b": "Verify in HeyReach dashboard",
        "key_files": []
    },
    {
        "id": "J6.13.4",
        "part_a": "N/A",
        "part_b": "Check activity logged",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "LinkedIn action sent successfully",
    "Appears in HeyReach dashboard",
    "Activity logged in database"
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
