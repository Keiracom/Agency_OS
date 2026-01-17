"""
Skill: J9.6 — Leads List Page
Journey: J9 - Client Dashboard
Checks: 7

Purpose: Verify leads list page displays all leads for the client with filtering,
sorting, pagination, and correct ALS scores.
"""

CHECKS = [
    {
        "id": "J9.6.1",
        "part_a": "Verify leads list page renders",
        "part_b": "Navigate to /dashboard/leads, check table renders with lead data",
        "key_files": ["frontend/app/dashboard/leads/page.tsx"]
    },
    {
        "id": "J9.6.2",
        "part_a": "Verify leads API returns paginated results",
        "part_b": "GET /api/v1/leads returns leads with pagination metadata",
        "key_files": ["src/api/routes/leads.py"]
    },
    {
        "id": "J9.6.3",
        "part_a": "Verify lead columns display correctly",
        "part_b": "Table shows name, company, ALS score, status, last activity",
        "key_files": ["frontend/app/dashboard/leads/page.tsx"]
    },
    {
        "id": "J9.6.4",
        "part_a": "Verify ALS tier filter works",
        "part_b": "Filter by Hot/Warm/Cool/Cold/Dead, verify filtered results",
        "key_files": ["frontend/app/dashboard/leads/page.tsx", "src/api/routes/leads.py"]
    },
    {
        "id": "J9.6.5",
        "part_a": "Verify search functionality works",
        "part_b": "Search by lead name or company, verify matching results",
        "key_files": ["frontend/app/dashboard/leads/page.tsx", "src/api/routes/leads.py"]
    },
    {
        "id": "J9.6.6",
        "part_a": "Verify sorting works on columns",
        "part_b": "Click column header, verify sort order changes (asc/desc)",
        "key_files": ["frontend/app/dashboard/leads/page.tsx"]
    },
    {
        "id": "J9.6.7",
        "part_a": "Verify clicking lead navigates to detail",
        "part_b": "Click lead row, navigate to /dashboard/leads/[id]",
        "key_files": ["frontend/app/dashboard/leads/page.tsx", "frontend/app/dashboard/leads/[id]/page.tsx"]
    },
]

PASS_CRITERIA = [
    "Leads list page renders with table",
    "API returns paginated lead data",
    "All required columns display correctly",
    "ALS tier filter filters leads correctly",
    "Search filters leads by name/company",
    "Column sorting works (asc/desc)",
    "Click navigates to lead detail page",
]

KEY_FILES = [
    "frontend/app/dashboard/leads/page.tsx",
    "frontend/app/dashboard/leads/[id]/page.tsx",
    "src/api/routes/leads.py",
    "src/models/lead.py",
    "frontend/components/ui/table.tsx",
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
