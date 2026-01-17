"""
Skill: J7.14 — Live Reply Test (All Channels)
Journey: J7 - Reply Handling
Checks: 7

Purpose: Verify real replies work end-to-end.
"""

CHECKS = [
    {
        "id": "J7.14.1",
        "part_a": "N/A",
        "part_b": "Send email reply to outreach message",
        "key_files": []
    },
    {
        "id": "J7.14.2",
        "part_a": "N/A",
        "part_b": "Reply to SMS message",
        "key_files": []
    },
    {
        "id": "J7.14.3",
        "part_a": "N/A",
        "part_b": "Reply to LinkedIn connection/message",
        "key_files": []
    },
    {
        "id": "J7.14.4",
        "part_a": "N/A",
        "part_b": "Verify intent classified correctly",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.14.5",
        "part_a": "N/A",
        "part_b": "Verify thread created",
        "key_files": ["src/services/thread_service.py"]
    },
    {
        "id": "J7.14.6",
        "part_a": "N/A",
        "part_b": "Verify lead status updated",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.14.7",
        "part_a": "N/A",
        "part_b": "Verify activity logged",
        "key_files": ["src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "Email reply processed successfully",
    "SMS reply processed successfully",
    "LinkedIn reply processed successfully",
    "Intent classification accurate",
    "Conversation thread created",
    "Lead status updated per intent"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/services/thread_service.py",
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
    lines.append("### Test Recipients Reference")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append("| Test Email | david.stephens@keiracom.com |")
    lines.append("| Test Phone | +61457543392 |")
    lines.append("| Test LinkedIn | https://www.linkedin.com/in/david-stephens-8847a636a/ |")
    lines.append("| TEST_MODE Setting | `settings.TEST_MODE` |")
    lines.append("| Note | Replies must match leads created during J3-J6 testing |")
    return "\n".join(lines)
