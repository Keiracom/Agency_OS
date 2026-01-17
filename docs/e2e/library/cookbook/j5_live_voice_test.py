"""
Skill: J5.13 — Live Voice Call Test
Journey: J5 - Voice Outreach
Checks: 8

Purpose: Verify real AI voice call works end-to-end.
"""

CHECKS = [
    {
        "id": "J5.13.1",
        "part_a": "Verify test phone ready",
        "part_b": "Have phone (+61457543392) available",
        "key_files": []
    },
    {
        "id": "J5.13.2",
        "part_a": "N/A",
        "part_b": "Initiate call via TEST_MODE",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.13.3",
        "part_a": "N/A",
        "part_b": "Answer phone, talk to AI agent",
        "key_files": []
    },
    {
        "id": "J5.13.4",
        "part_a": "N/A",
        "part_b": "Verify conversation quality",
        "key_files": []
    },
    {
        "id": "J5.13.5",
        "part_a": "N/A",
        "part_b": "Verify personalization spoken correctly",
        "key_files": []
    },
    {
        "id": "J5.13.6",
        "part_a": "N/A",
        "part_b": "Check activity record after call",
        "key_files": []
    },
    {
        "id": "J5.13.7",
        "part_a": "N/A",
        "part_b": "Check transcript captured",
        "key_files": []
    },
    {
        "id": "J5.13.8",
        "part_a": "N/A",
        "part_b": "Check recording accessible",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Call connects successfully",
    "AI agent speaks clearly",
    "AI agent responds appropriately",
    "Personalization works",
    "Transcript captured",
    "Recording accessible"
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
