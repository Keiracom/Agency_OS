"""
Skill: J9.2 — Dashboard Stats API
Journey: J9 - Client Dashboard
Checks: 8

Purpose: Verify dashboard statistics API returns correct data for leads,
campaigns, emails sent, and response rates for the authenticated client.
"""

CHECKS = [
    {
        "id": "J9.2.1",
        "part_a": "Verify /api/v1/customers/stats endpoint exists",
        "part_b": "Make GET request to stats endpoint with valid auth token",
        "key_files": ["src/api/routes/customers.py"]
    },
    {
        "id": "J9.2.2",
        "part_a": "Verify total leads count is returned",
        "part_b": "Check response contains total_leads field with integer value",
        "key_files": ["src/api/routes/customers.py"]
    },
    {
        "id": "J9.2.3",
        "part_a": "Verify active campaigns count is returned",
        "part_b": "Check response contains active_campaigns field with integer value",
        "key_files": ["src/api/routes/customers.py"]
    },
    {
        "id": "J9.2.4",
        "part_a": "Verify emails sent count is returned",
        "part_b": "Check response contains emails_sent field with integer value",
        "key_files": ["src/api/routes/customers.py"]
    },
    {
        "id": "J9.2.5",
        "part_a": "Verify response rate is calculated correctly",
        "part_b": "Check response_rate = (replies / emails_sent) * 100",
        "key_files": ["src/api/routes/customers.py"]
    },
    {
        "id": "J9.2.6",
        "part_a": "Verify stats are scoped to authenticated client",
        "part_b": "Stats should only include data for the logged-in client's tenant",
        "key_files": ["src/api/routes/customers.py", "src/api/auth.py"]
    },
    {
        "id": "J9.2.7",
        "part_a": "Verify stats endpoint returns 401 for unauthenticated requests",
        "part_b": "Make request without auth token, expect 401 Unauthorized",
        "key_files": ["src/api/routes/customers.py"]
    },
    {
        "id": "J9.2.8",
        "part_a": "Verify stats display correctly in dashboard UI",
        "part_b": "Check KPI cards show values from API response",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
]

PASS_CRITERIA = [
    "Stats endpoint returns 200 with valid auth",
    "total_leads count matches database records for tenant",
    "active_campaigns count matches active campaign records",
    "emails_sent count matches sent email records",
    "response_rate calculated correctly",
    "Stats scoped to authenticated client only",
    "Returns 401 for unauthenticated requests",
    "Frontend displays stats from API correctly",
]

KEY_FILES = [
    "src/api/routes/customers.py",
    "src/api/auth.py",
    "frontend/app/dashboard/page.tsx",
    "frontend/components/admin/KPICard.tsx",
]


def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    lines.append("")
    lines.append("### Key Files")
    for f in KEY_FILES:
        lines.append(f"- {f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_instructions())
