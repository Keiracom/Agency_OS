"""
Skill: J4.11 — Provider Selection
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify SMS provider selection logic (Twilio vs ClickSend).
"""

CHECKS = [
    {
        "id": "J4.11.1",
        "part_a": "Verify SMS_PROVIDER setting in settings.py",
        "part_b": "Check Railway env var",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.11.2",
        "part_a": "Verify provider factory/selection logic in sms.py",
        "part_b": "Check get_sms_client method",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.11.3",
        "part_a": "Verify Twilio selected by default",
        "part_b": "Check default value",
        "key_files": ["src/config/settings.py", "src/engines/sms.py"]
    },
    {
        "id": "J4.11.4",
        "part_a": "Verify ClickSend can be selected via config",
        "part_b": "Test provider switch",
        "key_files": ["src/engines/sms.py", "src/integrations/clicksend.py"]
    }
]

PASS_CRITERIA = [
    "SMS_PROVIDER setting exists",
    "Provider selection logic implemented",
    "Twilio is default provider",
    "ClickSend selectable as alternative"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/sms.py",
    "src/integrations/twilio.py",
    "src/integrations/clicksend.py"
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
