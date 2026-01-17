"""
Skill: J4.12 — Live SMS Test
Journey: J4 - SMS Outreach
Checks: 6

Purpose: Verify SMS arrives on test phone with correct content.
"""

CHECKS = [
    {
        "id": "J4.12.1",
        "part_a": "Verify sender ID configured",
        "part_b": "Check Twilio number in Railway vars",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J4.12.2",
        "part_a": "N/A",
        "part_b": "Send real SMS via TEST_MODE to +61457543392",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.12.3",
        "part_a": "N/A",
        "part_b": "Confirm SMS received on test phone",
        "key_files": []
    },
    {
        "id": "J4.12.4",
        "part_a": "N/A",
        "part_b": "Verify content and personalization correct",
        "key_files": []
    },
    {
        "id": "J4.12.5",
        "part_a": "N/A",
        "part_b": "Verify sender ID displays correctly",
        "key_files": []
    },
    {
        "id": "J4.12.6",
        "part_a": "Verify delivery status webhook received",
        "part_b": "Check activity record updated with delivery status",
        "key_files": ["src/api/routes/webhooks.py"]
    }
]

PASS_CRITERIA = [
    "SMS received on test phone (+61457543392)",
    "Content displays correctly",
    "Personalization fields replaced",
    "Sender ID correct",
    "Delivery status tracked",
    "Activity record complete"
]

KEY_FILES = [
    "src/config/settings.py",
    "src/engines/sms.py",
    "src/integrations/twilio.py",
    "src/api/routes/webhooks.py"
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
