"""
Skill: J7.10 — Activity Logging
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify all replies create comprehensive activity records.
"""

CHECKS = [
    {
        "id": "J7.10.1",
        "part_a": "Read `_log_reply_activity` method (closer.py lines 356-411)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.10.2",
        "part_a": "Verify action=\"replied\"",
        "part_b": "Check activity.action",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.10.3",
        "part_a": "Verify intent and intent_confidence stored",
        "part_b": "Check activity fields",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.10.4",
        "part_a": "Verify content_preview stored (500 chars)",
        "part_b": "Check preview",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.10.5",
        "part_a": "Verify conversation_thread_id linked",
        "part_b": "Check thread link",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.10.6",
        "part_a": "Verify provider_message_id stored",
        "part_b": "Check dedup field",
        "key_files": ["src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "Activity created for every reply",
    "Intent classification recorded",
    "Thread linked",
    "Deduplication by provider_message_id"
]

KEY_FILES = [
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
    lines.append("### Activity Fields Reference")
    lines.append("- action = \"replied\"")
    lines.append("- channel (email, sms, linkedin)")
    lines.append("- intent, intent_confidence")
    lines.append("- provider_message_id, in_reply_to")
    lines.append("- content_preview (500 chars)")
    lines.append("- conversation_thread_id (Phase 24D)")
    lines.append("- metadata: message_preview, message_length")
    return "\n".join(lines)
