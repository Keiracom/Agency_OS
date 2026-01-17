"""
Skill: J5.7 — Rate Limiting
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Verify call rate limits are enforced.
"""

CHECKS = [
    {
        "id": "J5.7.1",
        "part_a": "Check rate limit constant in voice.py — should be 50/day/number",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.7.2",
        "part_a": "Verify rate_limiter.check_and_increment called in send method",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"]
    },
    {
        "id": "J5.7.3",
        "part_a": "Verify Redis used for rate limiting — check redis.py",
        "part_b": "N/A",
        "key_files": ["src/integrations/redis.py", "src/engines/voice.py"]
    },
    {
        "id": "J5.7.4",
        "part_a": "N/A",
        "part_b": "Test hitting limit — make 51 calls, verify 51st blocked",
        "key_files": ["src/engines/voice.py"]
    }
]

PASS_CRITERIA = [
    "Rate limit enforced",
    "Redis tracks counts",
    "Excess calls blocked"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/integrations/redis.py"
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
