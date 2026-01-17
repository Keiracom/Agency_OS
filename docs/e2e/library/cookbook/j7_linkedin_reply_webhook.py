"""
Skill: J7.3 — LinkedIn Reply Webhook (HeyReach)
Journey: J7 - Reply Handling
Checks: 4

Purpose: Verify LinkedIn replies are received and processed via HeyReach.
"""

CHECKS = [
    {
        "id": "J7.3.1",
        "part_a": "Read `webhooks.py` — verify `/webhooks/heyreach/inbound` endpoint (line 656)",
        "part_b": "Trigger test reply",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.3.2",
        "part_a": "Verify reply type check (line 687)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.3.3",
        "part_a": "Verify lead matched by LinkedIn URL",
        "part_b": "Check lead found",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.3.4",
        "part_a": "Verify `closer.process_reply` called (line 710)",
        "part_b": "Check activity created",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "HeyReach webhook endpoint exists",
    "Reply type filtered (not connections)",
    "Lead matched by LinkedIn URL",
    "Reply processed via Closer engine"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/integrations/heyreach.py",
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
