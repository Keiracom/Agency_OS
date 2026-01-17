"""
Skill: J4.8 — Reply Detection
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify SMS reply detection via Twilio inbound webhooks.
"""

CHECKS = [
    {
        "id": "J4.8.1",
        "part_a": "Read `parse_inbound_webhook` method in twilio.py",
        "part_b": "N/A",
        "key_files": ["src/integrations/twilio.py"]
    },
    {
        "id": "J4.8.2",
        "part_a": "Verify webhook endpoint `/webhooks/sms/twilio/inbound` exists",
        "part_b": "Check webhooks.py",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J4.8.3",
        "part_a": "Verify reply linked to original lead by phone number",
        "part_b": "Test reply matching logic",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/sms.py"]
    },
    {
        "id": "J4.8.4",
        "part_a": "Verify reply creates activity record with action='sms_reply'",
        "part_b": "Check activity logging",
        "key_files": ["src/api/routes/webhooks.py"]
    }
]

PASS_CRITERIA = [
    "Inbound webhook endpoint configured",
    "Reply parsed correctly (from, body, timestamp)",
    "Reply matched to original lead",
    "Activity record created for reply"
]

KEY_FILES = [
    "src/integrations/twilio.py",
    "src/api/routes/webhooks.py",
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
