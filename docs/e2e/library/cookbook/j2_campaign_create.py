"""
Skill: J2.1 — Campaign List Page
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify campaign list displays real data from API.
"""

CHECKS = [
    {
        "id": "J2.1.1",
        "part_a": "Read `frontend/app/dashboard/campaigns/page.tsx` — verify `useCampaigns` hook",
        "part_b": "Load `/dashboard/campaigns`, check network tab",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"]
    },
    {
        "id": "J2.1.2",
        "part_a": "Verify API endpoint `GET /api/v1/campaigns` exists in `campaigns.py`",
        "part_b": "Confirm campaigns list renders",
        "key_files": ["src/api/routes/campaigns.py"]
    },
    {
        "id": "J2.1.3",
        "part_a": "Check status filter implementation (active/paused/draft/completed)",
        "part_b": "Click each filter, verify response",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"]
    },
    {
        "id": "J2.1.4",
        "part_a": "Check search functionality wiring",
        "part_b": "Search for campaign name",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"]
    },
    {
        "id": "J2.1.5",
        "part_a": "Verify channel allocation bar displays correctly",
        "part_b": "Check bar colors match allocations",
        "key_files": ["frontend/app/dashboard/campaigns/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Campaign list loads from API (not mock data)",
    "Status filters work correctly",
    "Search filters work correctly",
    "Channel allocation bar displays accurately"
]

KEY_FILES = [
    "frontend/app/dashboard/campaigns/page.tsx",
    "src/api/routes/campaigns.py"
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
