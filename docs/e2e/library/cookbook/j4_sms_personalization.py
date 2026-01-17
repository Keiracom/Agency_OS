"""
Skill: J4.6 — SMS Template Personalization
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify AI generates SMS content with length limits and personalization.
"""

CHECKS = [
    {
        "id": "J4.6.1",
        "part_a": "Read `src/engines/content.py` — verify `generate_sms` method",
        "part_b": "N/A",
        "key_files": ["src/engines/content.py"]
    },
    {
        "id": "J4.6.2",
        "part_a": "Verify 160 character limit (GSM-7)",
        "part_b": "Check prompt constraints",
        "key_files": ["src/engines/content.py"]
    },
    {
        "id": "J4.6.3",
        "part_a": "Verify personalization uses lead data (first_name, company)",
        "part_b": "Check template variable replacement",
        "key_files": ["src/engines/content.py", "src/engines/sms.py"]
    },
    {
        "id": "J4.6.4",
        "part_a": "Verify AI spend tracked",
        "part_b": "Check cost_aud in metadata",
        "key_files": ["src/engines/content.py"]
    }
]

PASS_CRITERIA = [
    "SMS content generated",
    "Character limit respected (160 GSM-7, 70 Unicode)",
    "Personalization variables replaced",
    "AI cost tracked"
]

KEY_FILES = [
    "src/engines/content.py",
    "src/engines/sms.py"
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
