"""
Skill: J5.4 — Voice Engine Implementation
Journey: J5 - Voice Outreach
Checks: 7

Purpose: Verify voice engine is fully implemented.
"""

CHECKS = [
    {
        "id": "J5.4.1",
        "part_a": "Read `src/engines/voice.py` — verify `send` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.4.2",
        "part_a": "Verify no TODO/FIXME/pass in voice.py — `grep -n \"TODO\\|FIXME\\|pass\" src/engines/voice.py`",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.4.3",
        "part_a": "Verify `create_campaign_assistant` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.4.4",
        "part_a": "Verify `get_call_status` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.4.5",
        "part_a": "Verify `get_call_transcript` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.4.6",
        "part_a": "Verify `process_call_webhook` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.4.7",
        "part_a": "Verify OutreachEngine base class extended — check class definition",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py", "src/engines/base.py"]
    }
]

PASS_CRITERIA = [
    "No incomplete implementations",
    "All methods have implementations",
    "Extends OutreachEngine correctly"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/engines/base.py"
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
