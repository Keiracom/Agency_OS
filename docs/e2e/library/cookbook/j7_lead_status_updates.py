"""
Skill: J7.7 — Lead Status Updates
Journey: J7 - Reply Handling
Checks: 7

Purpose: Verify lead status updates based on reply intent.
"""

CHECKS = [
    {
        "id": "J7.7.1",
        "part_a": "Read `_handle_intent` method (closer.py lines 413-498)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.7.2",
        "part_a": "Verify MEETING_REQUEST → CONVERTED status",
        "part_b": "Test meeting request",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.7.3",
        "part_a": "Verify INTERESTED → stays IN_SEQUENCE",
        "part_b": "Test interested reply",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.7.4",
        "part_a": "Verify NOT_INTERESTED → pauses outreach",
        "part_b": "Test not interested",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.7.5",
        "part_a": "Verify UNSUBSCRIBE → UNSUBSCRIBED status",
        "part_b": "Test unsubscribe",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.7.6",
        "part_a": "Verify OUT_OF_OFFICE → schedules 2-week follow-up",
        "part_b": "Test OOO reply",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.7.7",
        "part_a": "Verify `last_replied_at` and `reply_count` updated",
        "part_b": "Check lead fields",
        "key_files": ["src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "Status updates correctly per intent",
    "reply_count incremented",
    "last_replied_at updated",
    "Tasks created for actionable intents"
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
    lines.append("### Intent → Status Mapping Reference")
    lines.append("| Intent | Status Update | Additional Action |")
    lines.append("|--------|--------------|-------------------|")
    lines.append("| meeting_request | CONVERTED | Created meeting task |")
    lines.append("| interested | Stay IN_SEQUENCE | Created follow-up task |")
    lines.append("| question | No change | Created response task |")
    lines.append("| not_interested | Back to ENRICHED | Paused outreach |")
    lines.append("| unsubscribe | UNSUBSCRIBED | Suppression list |")
    lines.append("| out_of_office | No change | Schedule 2-week follow-up |")
    lines.append("| auto_reply | No change | Ignored |")
    return "\n".join(lines)
