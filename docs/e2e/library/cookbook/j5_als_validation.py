"""
Skill: J5.5 — ALS Score Validation
Journey: J5 - Voice Outreach
Checks: 3

Purpose: Verify ALS >= 70 required for voice calls.
"""

CHECKS = [
    {
        "id": "J5.5.1",
        "part_a": "Read voice.py lines 163-171 — verify ALS check implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.5.2",
        "part_a": "Verify threshold is 70 (not 85) — check constant value",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.5.3",
        "part_a": "Verify error returned for low ALS",
        "part_b": "Test with ALS=60 lead, verify rejection",
        "key_files": ["src/engines/voice.py"]
    }
]

PASS_CRITERIA = [
    "Voice requires ALS >= 70",
    "Low ALS leads rejected",
    "Clear error message returned"
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
