"""
Skill: J4.5 — Rate Limiting
Journey: J4 - SMS Outreach
Checks: 5

Purpose: Verify 100/day/number limit is enforced (Rule 17).
"""

CHECKS = [
    {
        "id": "J4.5.1",
        "part_a": "Read `SMS_DAILY_LIMIT_PER_NUMBER` constant",
        "part_b": "Verify value = 100",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.5.2",
        "part_a": "Verify `rate_limiter.check_and_increment` call",
        "part_b": "Check sms.py rate limit logic",
        "key_files": ["src/engines/sms.py"]
    },
    {
        "id": "J4.5.3",
        "part_a": "Verify Redis used for rate limiting",
        "part_b": "Check redis.py rate limiter implementation",
        "key_files": ["src/integrations/redis.py"]
    },
    {
        "id": "J4.5.4",
        "part_a": "Verify ResourceRateLimitError raised when limit exceeded",
        "part_b": "Test hitting limit (send 101 SMS, verify 101st blocked)",
        "key_files": ["src/engines/sms.py", "src/exceptions.py"]
    },
    {
        "id": "J4.5.5",
        "part_a": "Verify remaining quota returned in response",
        "part_b": "Check EngineResult metadata",
        "key_files": ["src/engines/sms.py"]
    }
]

PASS_CRITERIA = [
    "Limit is 100/day/number",
    "Redis tracks counts",
    "101st SMS blocked with ResourceRateLimitError",
    "Remaining quota returned in response",
    "Rate limit resets daily"
]

KEY_FILES = [
    "src/engines/sms.py",
    "src/integrations/redis.py",
    "src/exceptions.py"
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
