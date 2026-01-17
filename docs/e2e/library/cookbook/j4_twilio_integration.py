"""
Skill: J4.2 — Twilio Integration
Journey: J4 - SMS Outreach
Checks: 6

Purpose: Verify Twilio client is properly configured.
"""

CHECKS = [
    {
        "id": "J4.2.1",
        "part_a": "Read `src/integrations/twilio.py` — verify complete implementation",
        "part_b": "N/A",
        "key_files": ["src/integrations/twilio.py"]
    },
    {
        "id": "J4.2.2",
        "part_a": "Verify `TWILIO_ACCOUNT_SID` env var configured",
        "part_b": "Check Railway vars for TWILIO_ACCOUNT_SID",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.2.3",
        "part_a": "Verify `TWILIO_AUTH_TOKEN` env var configured",
        "part_b": "Check Railway vars for TWILIO_AUTH_TOKEN",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.2.4",
        "part_a": "Verify `TWILIO_PHONE_NUMBER` env var configured",
        "part_b": "Check Railway vars for TWILIO_PHONE_NUMBER",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.2.5",
        "part_a": "Verify `send_sms` method complete",
        "part_b": "Call API with test data",
        "key_files": ["src/integrations/twilio.py"]
    },
    {
        "id": "J4.2.6",
        "part_a": "Verify `parse_inbound_webhook` for replies",
        "part_b": "Test webhook parsing",
        "key_files": ["src/integrations/twilio.py"]
    }
]

PASS_CRITERIA = [
    "Twilio integration is complete (250 lines verified)",
    "All 3 Twilio credentials configured (SID, Token, Phone)",
    "SMS sends successfully via Twilio",
    "Webhooks parse correctly"
]

KEY_FILES = [
    "src/integrations/twilio.py",
    "src/config/settings.py"
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
