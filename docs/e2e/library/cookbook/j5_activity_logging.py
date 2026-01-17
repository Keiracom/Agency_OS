"""
Skill: J5.8 — Activity Logging
Journey: J5 - Voice Outreach
Checks: 5

Purpose: Verify all calls create activity records.
"""

CHECKS = [
    {
        "id": "J5.8.1",
        "part_a": "Read `_log_call_activity` method in voice.py",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.8.2",
        "part_a": "Verify activity created on call initiation",
        "part_b": "Check activity table after call",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.8.3",
        "part_a": "Verify content_snapshot stored (Phase 16)",
        "part_b": "Check snapshot field in activity",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.8.4",
        "part_a": "Verify call metadata stored (to_number, from_number, lead_name)",
        "part_b": "Check metadata field in activity",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.8.5",
        "part_a": "Verify call completion activity created",
        "part_b": "Check webhook handler creates activity",
        "key_files": ["src/engines/voice.py"]
    }
]

PASS_CRITERIA = [
    "Activity created on call start",
    "Activity created on call end",
    "All metadata captured"
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
