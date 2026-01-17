"""
Skill: J5.11 — Call Outcome Handling
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Verify call outcomes are classified and handled.
"""

CHECKS = [
    {
        "id": "J5.11.1",
        "part_a": "Verify ended_reason captured from webhook",
        "part_b": "Check parsing logic",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.11.2",
        "part_a": "Verify outcome stored in activity metadata",
        "part_b": "Check activity after call",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.11.3",
        "part_a": "Verify lead status updated on meeting booked",
        "part_b": "Check lead update logic",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.11.4",
        "part_a": "Verify reply_count incremented",
        "part_b": "Check lead update logic",
        "key_files": ["src/engines/voice.py"]
    }
]

PASS_CRITERIA = [
    "Outcomes captured correctly",
    "Lead status updated appropriately",
    "Meeting bookings detected"
]

KEY_FILES = [
    "src/engines/voice.py"
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
