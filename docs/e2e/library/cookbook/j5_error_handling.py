"""
Skill: J5.12 — Error Handling
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Verify graceful error handling.
"""

CHECKS = [
    {
        "id": "J5.12.1",
        "part_a": "Verify Vapi errors caught",
        "part_b": "Check exception handling in voice.py",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.12.2",
        "part_a": "Verify EngineResult.fail returned on error",
        "part_b": "Check return structure on failures",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.12.3",
        "part_a": "Verify missing assistant_id handled",
        "part_b": "Test without assistant_id, verify error message",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.12.4",
        "part_a": "Verify missing phone handled",
        "part_b": "Test without phone, verify error message",
        "key_files": ["src/engines/voice.py"]
    }
]

PASS_CRITERIA = [
    "Errors don't crash the flow",
    "Clear error messages returned",
    "Required fields validated"
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
