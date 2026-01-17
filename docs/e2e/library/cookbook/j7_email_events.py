"""
Skill: J7.12 — Email Event Webhooks (Opens/Clicks/Bounces)
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify email engagement events are tracked.
"""

CHECKS = [
    {
        "id": "J7.12.1",
        "part_a": "Read `/webhooks/postmark/bounce` endpoint (line 340)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.12.2",
        "part_a": "Read `/webhooks/postmark/spam` endpoint (line 410)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.12.3",
        "part_a": "Read `/webhooks/email/resend` endpoint (line 1169)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.12.4",
        "part_a": "Read `/webhooks/salesforge/events` endpoint (line 1003)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.12.5",
        "part_a": "Verify bounce updates lead status",
        "part_b": "Test bounce event",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J7.12.6",
        "part_a": "Verify spam complaint triggers unsubscribe",
        "part_b": "Test spam event",
        "key_files": ["src/api/routes/webhooks.py"]
    }
]

PASS_CRITERIA = [
    "Bounce webhook updates lead",
    "Spam complaint triggers unsubscribe",
    "Opens/clicks tracked in activity"
]

KEY_FILES = [
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
    lines.append("")
    lines.append("### Event Types Tracked")
    lines.append("- sent, delivered")
    lines.append("- opened (first and repeat)")
    lines.append("- clicked (with URL)")
    lines.append("- bounced (hard/soft)")
    lines.append("- complained, unsubscribed")
    return "\n".join(lines)
