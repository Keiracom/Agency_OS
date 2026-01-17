"""
Skill: J5.10 — Call Recording
Journey: J5 - Voice Outreach
Checks: 3

Purpose: Verify call recordings are captured.
"""

CHECKS = [
    {
        "id": "J5.10.1",
        "part_a": "Verify `recordingEnabled: true` in config",
        "part_b": "Check vapi.py config",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.10.2",
        "part_a": "Verify recording_url stored in activity",
        "part_b": "Check webhook handler stores URL",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.10.3",
        "part_a": "N/A",
        "part_b": "Access recording URL, verify audio plays",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Recording enabled",
    "Recording URL stored",
    "Recording accessible"
]

KEY_FILES = [
    "src/integrations/vapi.py",
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
