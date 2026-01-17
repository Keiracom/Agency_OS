"""
Skill: J5.6 — Assistant Configuration
Journey: J5 - Voice Outreach
Checks: 5

Purpose: Verify AI assistant is properly configured.
"""

CHECKS = [
    {
        "id": "J5.6.1",
        "part_a": "Read `_build_system_prompt` method in voice.py",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.6.2",
        "part_a": "Verify system prompt includes conversation rules",
        "part_b": "Check prompt content for rules",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.6.3",
        "part_a": "Verify max_duration_seconds = 300 (5 min)",
        "part_b": "Check config value",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.6.4",
        "part_a": "Verify model = claude-sonnet-4-20250514",
        "part_b": "Check config value",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.6.5",
        "part_a": "Verify recording enabled in config",
        "part_b": "Check config value",
        "key_files": ["src/integrations/vapi.py"]
    }
]

PASS_CRITERIA = [
    "System prompt well-defined",
    "Max duration appropriate",
    "Recording enabled for review"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/integrations/vapi.py"
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
