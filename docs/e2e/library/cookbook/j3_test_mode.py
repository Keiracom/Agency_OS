"""
Skill: J3.1 — TEST_MODE Verification
Journey: J3 - Email Outreach
Checks: 4

Purpose: Ensure TEST_MODE redirects all emails to test recipient.
"""

CHECKS = [
    {
        "id": "J3.1.1",
        "part_a": "Read `src/config/settings.py` — verify `TEST_MODE` and `TEST_EMAIL_RECIPIENT` settings exist",
        "part_b": "Check Railway env var TEST_MODE is set to true",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J3.1.2",
        "part_a": "Read `src/engines/email.py` lines 143-147 — verify redirect logic implementation",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.1.3",
        "part_a": "Verify redirect happens BEFORE send (not after) in email engine flow",
        "part_b": "Trigger send via Prefect flow, check logs for redirect message",
        "key_files": ["src/engines/email.py", "src/orchestration/flows/outreach_flow.py"]
    },
    {
        "id": "J3.1.4",
        "part_a": "Verify original email preserved in logs/activity record metadata",
        "part_b": "Check activity record for original_email field after test send",
        "key_files": ["src/engines/email.py"]
    }
]

PASS_CRITERIA = [
    "TEST_MODE setting exists and is `true` in Railway",
    "TEST_EMAIL_RECIPIENT configured correctly",
    "Redirect happens before send (not after)",
    "Original email logged for reference"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/email.py",
    "src/orchestration/flows/outreach_flow.py"
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
