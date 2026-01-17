"""
Skill: J4.3 — ClickSend Integration
Journey: J4 - SMS Outreach
Checks: 6

Purpose: Verify ClickSend client is properly configured as alternative SMS provider.
"""

CHECKS = [
    {
        "id": "J4.3.1",
        "part_a": "Read `src/integrations/clicksend.py` — verify complete implementation",
        "part_b": "N/A",
        "key_files": ["src/integrations/clicksend.py"]
    },
    {
        "id": "J4.3.2",
        "part_a": "Verify `CLICKSEND_USERNAME` env var configured",
        "part_b": "Check Railway vars for CLICKSEND_USERNAME",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.3.3",
        "part_a": "Verify `CLICKSEND_API_KEY` env var configured",
        "part_b": "Check Railway vars for CLICKSEND_API_KEY",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.3.4",
        "part_a": "Verify `CLICKSEND_SENDER_ID` env var configured",
        "part_b": "Check Railway vars for CLICKSEND_SENDER_ID",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.3.5",
        "part_a": "Verify `send_sms` method complete",
        "part_b": "Call API with test data",
        "key_files": ["src/integrations/clicksend.py"]
    },
    {
        "id": "J4.3.6",
        "part_a": "Verify webhook parsing for delivery status",
        "part_b": "Test webhook parsing",
        "key_files": ["src/integrations/clicksend.py"]
    }
]

PASS_CRITERIA = [
    "ClickSend integration is complete",
    "All 3 ClickSend credentials configured (Username, API Key, Sender ID)",
    "SMS sends successfully via ClickSend",
    "Webhooks parse correctly"
]

KEY_FILES = [
    "src/integrations/clicksend.py",
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
