"""
Skill: J8.2 — Meeting Webhook (Cal.com)
Journey: J8 - Meeting & Deals
Checks: 2

Purpose: Verify Cal.com webhooks create meetings.
"""

CHECKS = [
    {
        "id": "J8.2.1",
        "part_a": "Read `_handle_calcom_webhook` (lines 1562-1566)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J8.2.2",
        "part_a": "VERIFY: Cal.com handler NOT fully implemented",
        "part_b": "Check response",
        "key_files": ["src/api/routes/webhooks.py"]
    }
]

PASS_CRITERIA = [
    "Cal.com handler is NOT implemented — returns 'ignored'",
    "CEO Decision: Implement Cal.com or use Calendly only?"
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
    return "\n".join(lines)
