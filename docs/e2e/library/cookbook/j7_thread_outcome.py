"""
Skill: J7.9 — Thread Outcome (Phase 24D)
Journey: J7 - Reply Handling
Checks: 4

Purpose: Verify thread outcomes are set based on reply intent.
"""

CHECKS = [
    {
        "id": "J7.9.1",
        "part_a": "Read `_update_thread_outcome` method (closer.py lines 568-601)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.9.2",
        "part_a": "Verify meeting_request → outcome=\"meeting_booked\"",
        "part_b": "Test meeting reply",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.9.3",
        "part_a": "Verify not_interested/unsubscribe → outcome=\"rejected\"",
        "part_b": "Test rejection",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.9.4",
        "part_a": "Verify interested/question → thread stays active",
        "part_b": "Test positive reply",
        "key_files": ["src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "Thread outcome set correctly",
    "Outcome reason captured",
    "Positive intents keep thread active",
    "Negative intents close thread"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/services/thread_service.py"
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
