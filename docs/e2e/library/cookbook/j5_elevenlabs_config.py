"""
Skill: J5.3 — ElevenLabs Voice Configuration
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Verify ElevenLabs voice synthesis is configured.
"""

CHECKS = [
    {
        "id": "J5.3.1",
        "part_a": "Verify default voice ID in voice.py — `DEFAULT_VOICE_ID = \"pNInz6obpgDQGcFmaJgB\"`",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.3.2",
        "part_a": "Verify ElevenLabs provider in vapi.py — `voice.provider = \"11labs\"`",
        "part_b": "N/A",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.3.3",
        "part_a": "Verify voice stability/similarity settings — stability: 0.5, similarityBoost: 0.75",
        "part_b": "N/A",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.3.4",
        "part_a": "Verify language set to Australian English — `language: \"en-AU\"`",
        "part_b": "N/A",
        "key_files": ["src/integrations/vapi.py"]
    }
]

PASS_CRITERIA = [
    "ElevenLabs voice ID configured",
    "Voice stability settings appropriate",
    "Australian English language set"
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
