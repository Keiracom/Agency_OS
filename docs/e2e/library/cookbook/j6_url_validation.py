"""
Skill: J6.5 — LinkedIn URL Validation
Journey: J6 - LinkedIn Outreach
Checks: 3

Purpose: Verify LinkedIn URLs are validated before actions.
"""

CHECKS = [
    {
        "id": "J6.5.1",
        "part_a": "Verify lead linkedin_url check (lines 137-142)",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.5.2",
        "part_a": "Verify URL format expected",
        "part_b": "linkedin.com/in/*",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.5.3",
        "part_a": "Test missing LinkedIn URL",
        "part_b": "Verify error returned",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Missing LinkedIn URL rejected",
    "Invalid URLs handled gracefully"
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
