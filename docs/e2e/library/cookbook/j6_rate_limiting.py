"""
Skill: J6.4 — Rate Limiting (Rule 17)
Journey: J6 - LinkedIn Outreach
Checks: 5

Purpose: Verify 17/day/seat limit is enforced.
"""

CHECKS = [
    {
        "id": "J6.4.1",
        "part_a": "Read `LINKEDIN_DAILY_LIMIT_PER_SEAT` constant",
        "part_b": "Verify = 17",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.4.2",
        "part_a": "Verify `rate_limiter.check_and_increment` call",
        "part_b": "Check linkedin.py",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.4.3",
        "part_a": "Verify limit keyed by `seat_id`",
        "part_b": "Check resource_id",
        "key_files": ["src/engines/linkedin.py"]
    },
    {
        "id": "J6.4.4",
        "part_a": "Verify Redis used for tracking",
        "part_b": "Check redis.py",
        "key_files": ["src/integrations/redis.py"]
    },
    {
        "id": "J6.4.5",
        "part_a": "Test hitting limit",
        "part_b": "Send 18 actions, verify 18th blocked",
        "key_files": []
    }
]

PASS_CRITERIA = [
    "Limit is 17/day/seat",
    "Redis tracks counts per seat",
    "18th action blocked"
]

KEY_FILES = [
    "src/engines/linkedin.py",
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
