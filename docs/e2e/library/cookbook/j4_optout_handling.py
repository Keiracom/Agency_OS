"""
Skill: J4.9 — Opt-out Handling
Journey: J4 - SMS Outreach
Checks: 4

Purpose: Verify STOP/opt-out keyword handling for SMS.
"""

CHECKS = [
    {
        "id": "J4.9.1",
        "part_a": "Verify STOP keyword detection in reply parsing",
        "part_b": "N/A",
        "key_files": ["src/integrations/twilio.py", "src/api/routes/webhooks.py"]
    },
    {
        "id": "J4.9.2",
        "part_a": "Verify lead status updated to 'opted_out' on STOP",
        "part_b": "Test STOP reply handling",
        "key_files": ["src/api/routes/webhooks.py", "src/engines/sms.py"]
    },
    {
        "id": "J4.9.3",
        "part_a": "Verify opted-out leads blocked from future sends",
        "part_b": "Attempt send to opted-out lead",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.9.4",
        "part_a": "Verify opt-out activity logged",
        "part_b": "Check activity record with action='sms_optout'",
        "key_files": ["src/api/routes/webhooks.py"]
    }
]

PASS_CRITERIA = [
    "STOP keyword detected (case-insensitive)",
    "Lead marked as opted_out",
    "Future sends blocked for opted-out leads",
    "Opt-out activity logged"
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
