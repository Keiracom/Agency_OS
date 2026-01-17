"""
Skill: J5.1 — TEST_MODE Verification
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Ensure TEST_MODE redirects all voice calls to test recipient.
"""

CHECKS = [
    {
        "id": "J5.1.1",
        "part_a": "Read `src/config/settings.py` — verify `TEST_VOICE_RECIPIENT` exists",
        "part_b": "Check Railway env var for TEST_VOICE_RECIPIENT",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J5.1.2",
        "part_a": "Read `src/engines/voice.py` lines 173-177 — verify redirect logic",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.1.3",
        "part_a": "Verify redirect happens BEFORE call initiation",
        "part_b": "Trigger call, check logs for redirect message",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.1.4",
        "part_a": "Verify original phone preserved in logs/activity",
        "part_b": "Check activity record for original phone number",
        "key_files": ["src/engines/voice.py"]
    }
]

PASS_CRITERIA = [
    "TEST_MODE setting exists",
    "TEST_VOICE_RECIPIENT configured",
    "Redirect happens before call",
    "Original phone logged for reference"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/voice.py"
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
