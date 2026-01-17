"""
Skill: J10.13 — Rate Limits Page
Journey: J10 - Admin Dashboard
Checks: 3

Purpose: Verify API rate limit monitoring and display.
"""

CHECKS = [
    {
        "id": "J10.13.1",
        "part_a": "Read `frontend/app/admin/system/rate-limits/page.tsx` — verify display",
        "part_b": "Load rate limits page, verify data renders",
        "key_files": ["frontend/app/admin/system/rate-limits/page.tsx"]
    },
    {
        "id": "J10.13.2",
        "part_a": "Verify rate limit status for each API",
        "part_b": "Check Apollo, Salesforge, Unipile limits display",
        "key_files": ["frontend/app/admin/system/rate-limits/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.13.3",
        "part_a": "Verify rate limit warnings display",
        "part_b": "Check warning shows when approaching limit (>80%)",
        "key_files": ["frontend/app/admin/system/rate-limits/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Rate limits page loads correctly",
    "All API rate limits display",
    "Warnings show at threshold"
]

KEY_FILES = [
    "frontend/app/admin/system/rate-limits/page.tsx",
    "src/api/routes/admin.py"
]

# Rate Limit Reference
RATE_LIMITS = [
    {"api": "Apollo", "limit": "10,000/month", "reset": "Monthly", "current_usage_field": "apollo_credits_used"},
    {"api": "Salesforge", "limit": "Based on mailboxes", "reset": "Daily", "current_usage_field": "emails_sent_today"},
    {"api": "Unipile", "limit": "Varies by plan", "reset": "Daily", "current_usage_field": "linkedin_actions_today"},
    {"api": "Anthropic", "limit": "Based on tier", "reset": "Per minute/day", "current_usage_field": "claude_tokens_used"}
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
