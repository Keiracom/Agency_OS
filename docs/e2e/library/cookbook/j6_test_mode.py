"""
Skill: J6.1 — TEST_MODE Verification
Journey: J6 - LinkedIn Outreach
Checks: 4

Purpose: Ensure TEST_MODE redirects all LinkedIn actions to test recipient.
"""

CHECKS = [
    {
        "id": "J6.1.1",
        "part_a": "Read `src/config/settings.py` — verify `TEST_LINKEDIN_RECIPIENT`",
        "part_b": "Check Railway env var",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J6.1.2",
        "part_a": "Read `src/engines/linkedin.py` lines 144-148 — verify redirect logic",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.1.3",
        "part_a": "Verify redirect happens BEFORE API call",
        "part_b": "Trigger action, check logs",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.1.4",
        "part_a": "Verify original LinkedIn URL preserved in logs",
        "part_b": "Check activity record",
        "key_files": ["src/engines/linkedin.py"]
    }
]

PASS_CRITERIA = [
    "TEST_MODE setting exists",
    "TEST_LINKEDIN_RECIPIENT configured",
    "Redirect happens before HeyReach API call"
]

KEY_FILES = [
    "src/config/settings.py",
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
