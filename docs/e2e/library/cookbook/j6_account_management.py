"""
Skill: J6.8 — LinkedIn Account Management
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Verify LinkedIn account connection via HeyReach.
"""

CHECKS = [
    {
        "id": "J6.8.1",
        "part_a": "Read `add_linkedin_account` method",
        "part_b": "N/A",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.8.2",
        "part_a": "Read `verify_2fa` method",
        "part_b": "N/A",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.8.3",
        "part_a": "Read `remove_sender` method",
        "part_b": "N/A",
        "key_files": ["src/integrations/heyreach.py"]
    },
    {
        "id": "J6.8.4",
        "part_a": "Read `get_sender` method",
        "part_b": "N/A",
        "key_files": ["src/integrations/heyreach.py"]
    }
]

PASS_CRITERIA = [
    "Account connection methods exist",
    "2FA verification supported",
    "Account removal works"
]

KEY_FILES = [
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
