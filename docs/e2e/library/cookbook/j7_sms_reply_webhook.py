"""
Skill: J7.2 — SMS Reply Webhook (Twilio)
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify SMS replies are received and processed via Twilio.
"""

CHECKS = [
    {
        "id": "J7.2.1",
        "part_a": "Read `webhooks.py` — verify `/webhooks/twilio/inbound` endpoint (line 474)",
        "part_b": "Send test SMS reply",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.2.2",
        "part_a": "Verify Twilio signature validation (lines 90-113)",
        "part_b": "Check validation passes",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.2.3",
        "part_a": "Verify `twilio.parse_inbound_webhook` call (line 511)",
        "part_b": "Check parsing",
        "key_files": ["src/api/routes/webhooks.py", "src/integrations/twilio.py"]
    },
    {
        "id": "J7.2.4",
        "part_a": "Verify lead matched by phone number",
        "part_b": "Check lead found",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.2.5",
        "part_a": "Verify `closer.process_reply` called (line 535)",
        "part_b": "Check activity created",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "Twilio inbound webhook endpoint exists",
    "Signature validation implemented",
    "Payload parsed correctly",
    "Lead matched by phone"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/integrations/twilio.py",
    "src/engines/closer.py"
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
