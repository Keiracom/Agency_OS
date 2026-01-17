"""
Skill: J9.10 — Reports Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify reports page displays performance reports, allows date range
selection, and provides export functionality.
"""

CHECKS = [
    {
        "id": "J9.10.1",
        "part_a": "Verify reports page renders",
        "part_b": "Navigate to /dashboard/reports, check page renders with report options",
        "key_files": ["frontend/app/dashboard/reports/page.tsx"]
    },
    {
        "id": "J9.10.2",
        "part_a": "Verify reports API returns data",
        "part_b": "GET /api/v1/reports returns report data for tenant",
        "key_files": ["src/api/routes/reports.py"]
    },
    {
        "id": "J9.10.3",
        "part_a": "Verify date range selector works",
        "part_b": "Select date range, verify report data updates accordingly",
        "key_files": ["frontend/app/dashboard/reports/page.tsx"]
    },
    {
        "id": "J9.10.4",
        "part_a": "Verify report metrics display",
        "part_b": "Page shows lead generation, email performance, conversion metrics",
        "key_files": ["frontend/app/dashboard/reports/page.tsx"]
    },
    {
        "id": "J9.10.5",
        "part_a": "Verify export functionality works",
        "part_b": "Click export button, download CSV/PDF of report data",
        "key_files": ["frontend/app/dashboard/reports/page.tsx", "src/api/routes/reports.py"]
    },
]

PASS_CRITERIA = [
    "Reports page renders without errors",
    "Reports API returns data for tenant",
    "Date range selector filters data correctly",
    "Report metrics display accurately",
    "Export generates downloadable file",
]

KEY_FILES = [
    "frontend/app/dashboard/reports/page.tsx",
    "src/api/routes/reports.py",
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
