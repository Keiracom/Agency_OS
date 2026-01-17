"""
Skill: J4.1 — TEST_MODE Verification
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Ensure TEST_MODE redirects all SMS to test recipient.
"""

CHECKS = [
    {
        "id": "J4.1.1",
        "part_a": "Read `src/config/settings.py` — verify `TEST_SMS_RECIPIENT` setting exists",
        "part_b": "Check Railway env var for TEST_SMS_RECIPIENT",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.1.2",
        "part_a": "Read `src/engines/sms.py` lines 137-141 — verify redirect logic",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.1.3",
        "part_a": "Verify redirect happens BEFORE send (not after)",
        "part_b": "Trigger send, check logs for redirect message",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.1.4",
        "part_a": "Verify original phone preserved in logs/activity",
        "part_b": "Check activity record for original_phone field",
        "key_files": ["src/engines/sms.py"]
    }
]

PASS_CRITERIA = [
    "TEST_MODE setting exists in settings.py",
    "TEST_SMS_RECIPIENT configured (+61457543392)",
    "Redirect happens before send",
    "Original phone logged for reference"
]

KEY_FILES = [
    "src/config/settings.py",
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
