"""
Skill: J7.6 — Conversation Threading (Phase 24D)
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify conversation threads are created and managed.
"""

CHECKS = [
    {
        "id": "J7.6.1",
        "part_a": "Read `src/services/thread_service.py` — verify complete",
        "part_b": "N/A",
        "key_files": ["src/services/thread_service.py"]
    },
    {
        "id": "J7.6.2",
        "part_a": "Verify `get_or_create_for_lead` method",
        "part_b": "Test thread creation",
        "key_files": ["src/services/thread_service.py"]
    },
    {
        "id": "J7.6.3",
        "part_a": "Verify thread status: active, stale, closed",
        "part_b": "Check status transitions",
        "key_files": ["src/services/thread_service.py"]
    },
    {
        "id": "J7.6.4",
        "part_a": "Verify `add_message` method",
        "part_b": "Test message adding",
        "key_files": ["src/services/thread_service.py"]
    },
    {
        "id": "J7.6.5",
        "part_a": "Verify message direction: inbound vs outbound",
        "part_b": "Check direction set",
        "key_files": ["src/services/thread_service.py"]
    },
    {
        "id": "J7.6.6",
        "part_a": "Verify activity linked to thread (conversation_thread_id)",
        "part_b": "Check activity.conversation_thread_id",
        "key_files": ["src/services/thread_service.py", "src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "Thread created on first reply",
    "Existing thread reused for same lead/channel",
    "Messages tracked with position",
    "Activity linked to thread"
]

KEY_FILES = [
    "src/services/thread_service.py",
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
    lines.append("")
    lines.append("### ThreadService Methods Reference")
    lines.append("- `create_thread()` — Create new conversation thread")
    lines.append("- `get_by_id()` — Get thread by UUID")
    lines.append("- `get_or_create_for_lead()` — Find existing or create new")
    lines.append("- `add_message()` — Add message with sentiment/intent/objection")
    lines.append("- `update_status()` — Update thread status")
    lines.append("- `set_outcome()` — Set final outcome (meeting_booked, rejected, etc.)")
    return "\n".join(lines)
