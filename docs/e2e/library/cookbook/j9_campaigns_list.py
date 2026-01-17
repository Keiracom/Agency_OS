"""
Skill: J9.8 — Campaigns List Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify campaigns list page displays all campaigns for the client with
status indicators, performance metrics, and filtering options.
"""

CHECKS = [
    {
        "id": "J9.8.1",
        "part_a": "Verify campaigns list page renders",
        "part_b": "Navigate to /dashboard/campaigns, check table renders with campaign data",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"]
    },
    {
        "id": "J9.8.2",
        "part_a": "Verify campaigns API returns data for tenant",
        "part_b": "GET /api/v1/campaigns returns campaigns scoped to authenticated client",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J9.8.3",
        "part_a": "Verify campaign status indicators display",
        "part_b": "Each campaign shows status badge (draft, active, paused, completed)",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx", "frontend/components/ui/badge.tsx"]
    },
    {
        "id": "J9.8.4",
        "part_a": "Verify campaign metrics display",
        "part_b": "Table shows emails sent, open rate, reply rate for each campaign",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"]
    },
    {
        "id": "J9.8.5",
        "part_a": "Verify new campaign button navigates correctly",
        "part_b": "Click 'New Campaign' button, navigate to /dashboard/campaigns/new",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx", "frontend/app/dashboard/campaigns/new/page.tsx"]
    },
]

PASS_CRITERIA = [
    "Campaigns list page renders with table",
    "API returns campaigns for authenticated tenant",
    "Campaign status badges display correctly",
    "Campaign metrics (sent, open rate, reply rate) display",
    "New campaign navigation works",
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/page.tsx",
    "frontend/app/dashboard/campaigns/new/page.tsx",
    "frontend/app/dashboard/campaigns/[id]/page.tsx",
    "src/api/routes/campaigns.py",
    "src/models/campaign.py",
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
