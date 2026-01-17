"""
Skill: J3.4 — Rate Limiting
Journey: J3 - Email Outreach
Checks: 5

Purpose: Verify 50/day/domain limit is enforced (Rule 17).
"""

CHECKS = [
    {
        "id": "J3.4.1",
        "part_a": "Read `EMAIL_DAILY_LIMIT_PER_DOMAIN` constant — verify value is 50",
        "part_b": "Verify constant in email.py line 53",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.4.2",
        "part_a": "Verify `rate_limiter.check_and_increment` call in email send flow",
        "part_b": "Check email.py lines 158-171 for rate limit check",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.4.3",
        "part_a": "Verify domain extraction logic from from_email address",
        "part_b": "Test with various email formats (user@domain.com, etc.)",
        "key_files": ["src/engines/email.py"]
    },
    {
        "id": "J3.4.4",
        "part_a": "Verify Redis is used for rate limiting via redis.py",
        "part_b": "Check Redis keys after sending test email",
        "key_files": ["src/integrations/redis.py", "src/engines/email.py"]
    },
    {
        "id": "J3.4.5",
        "part_a": "Verify ResourceRateLimitError raised when limit exceeded",
        "part_b": "Attempt to send 51st email, verify it is blocked with correct error",
        "key_files": ["src/engines/email.py", "src/exceptions.py"]
    }
]

PASS_CRITERIA = [
    "Limit is 50/day/domain",
    "Redis tracks counts correctly",
    "51st email blocked with ResourceRateLimitError",
    "Remaining quota returned in response",
    "Domain extracted correctly from email address"
]

KEY_FILES = [
    "src/engines/email.py",
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
