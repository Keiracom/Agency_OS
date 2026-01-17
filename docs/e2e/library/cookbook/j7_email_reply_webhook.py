"""
Skill: J7.1 — Email Reply Webhook (Postmark)
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify email replies are received and processed via Postmark.
"""

CHECKS = [
    {
        "id": "J7.1.1",
        "part_a": "Read `webhooks.py` — verify `/webhooks/postmark/inbound` endpoint",
        "part_b": "Send test email reply",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.1.2",
        "part_a": "Verify `postmark.parse_inbound_webhook` call (line 277)",
        "part_b": "Check logs for parsing",
        "key_files": ["src/api/routes/webhooks.py", "src/integrations/postmark.py"]
    },
    {
        "id": "J7.1.3",
        "part_a": "Verify lead matched by email address",
        "part_b": "Check lead found",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.1.4",
        "part_a": "Verify `closer.process_reply` called (line 300)",
        "part_b": "Check activity created",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/closer.py"]
    },
    {
        "id": "J7.1.5",
        "part_a": "Verify `in_reply_to` header extracted",
        "part_b": "Check thread linking",
        "key_files": ["src/api/routes/webhooks.py"]
    }
]

PASS_CRITERIA = [
    "Postmark webhook endpoint exists",
    "Payload parsed correctly",
    "Lead matched by email",
    "Reply processed via Closer engine"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/integrations/postmark.py",
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
