"""
Skill: J5.9 — Webhook Processing
Journey: J5 - Voice Outreach
Checks: 6

Purpose: Verify call webhooks are processed correctly.
"""

CHECKS = [
    {
        "id": "J5.9.1",
        "part_a": "Read `process_call_webhook` method in voice.py",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.9.2",
        "part_a": "Verify webhook endpoint exists in webhooks.py — `/webhooks/vapi/call`",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"]
    },
    {
        "id": "J5.9.3",
        "part_a": "Verify call-ended event handling",
        "part_b": "Check event processing logic",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.9.4",
        "part_a": "Verify transcript stored in activity metadata",
        "part_b": "Check activity after call ends",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.9.5",
        "part_a": "Verify recording_url stored in activity metadata",
        "part_b": "Check activity after call ends",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.9.6",
        "part_a": "Verify meeting_booked detection",
        "part_b": "Check lead status update logic",
        "key_files": ["src/engines/voice.py"]
    }
]

PASS_CRITERIA = [
    "Webhooks processed correctly",
    "Transcript captured",
    "Recording URL captured",
    "Meeting booking detected"
]

KEY_FILES = [
    "src/engines/voice.py",
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
