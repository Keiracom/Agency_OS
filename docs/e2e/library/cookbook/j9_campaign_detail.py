"""
Skill: J9.9 — Campaign Detail Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify campaign detail page displays campaign configuration, sequence
steps, performance analytics, and associated leads.
"""

CHECKS = [
    {
        "id": "J9.9.1",
        "part_a": "Verify campaign detail page renders",
        "part_b": "Navigate to /dashboard/campaigns/[id], check page renders with campaign data",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    },
    {
        "id": "J9.9.2",
        "part_a": "Verify campaign configuration displays",
        "part_b": "Page shows campaign name, status, created date, target criteria",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    },
    {
        "id": "J9.9.3",
        "part_a": "Verify sequence steps display",
        "part_b": "Page shows email sequence with step timing and status",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    },
    {
        "id": "J9.9.4",
        "part_a": "Verify performance analytics display",
        "part_b": "Page shows open rate, click rate, reply rate, bounce rate charts",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    },
    {
        "id": "J9.9.5",
        "part_a": "Verify associated leads list displays",
        "part_b": "Page shows leads enrolled in campaign with their status",
        "key_files": ["frontend/app/dashboard/campaigns/[id]/page.tsx"]
    },
]

PASS_CRITERIA = [
    "Campaign detail page renders without errors",
    "Campaign configuration displays completely",
    "Sequence steps show timing and status",
    "Performance analytics charts render",
    "Associated leads list displays with status",
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/[id]/page.tsx",
    "src/api/routes/campaigns.py",
    "src/models/campaign.py",
    "src/models/sequence_step.py",
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
