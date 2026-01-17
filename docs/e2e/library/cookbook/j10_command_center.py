"""
Skill: J10.2 — Command Center Page
Journey: J10 - Admin Dashboard
Checks: 6

Purpose: Verify the main admin command center dashboard page functionality.
"""

CHECKS = [
    {
        "id": "J10.2.1",
        "part_a": "Read `frontend/app/admin/page.tsx` — verify dashboard layout",
        "part_b": "Load /admin page, verify all sections render",
        "key_files": ["frontend/app/admin/page.tsx"]
    },
    {
        "id": "J10.2.2",
        "part_a": "Verify KPI cards section exists",
        "part_b": "Check KPI section displays key metrics",
        "key_files": ["frontend/app/admin/page.tsx"]
    },
    {
        "id": "J10.2.3",
        "part_a": "Verify system status section exists",
        "part_b": "Check system health indicators render",
        "key_files": ["frontend/app/admin/page.tsx"]
    },
    {
        "id": "J10.2.4",
        "part_a": "Verify alerts section exists",
        "part_b": "Check critical alerts display correctly",
        "key_files": ["frontend/app/admin/page.tsx"]
    },
    {
        "id": "J10.2.5",
        "part_a": "Verify live activity feed section exists",
        "part_b": "Check real-time activity displays",
        "key_files": ["frontend/app/admin/page.tsx", "frontend/app/admin/activity/page.tsx"]
    },
    {
        "id": "J10.2.6",
        "part_a": "Verify navigation sidebar links work",
        "part_b": "Click each nav link, verify navigation to correct page",
        "key_files": ["frontend/app/admin/layout.tsx"]
    }
]

PASS_CRITERIA = [
    "Admin dashboard loads without errors",
    "All dashboard sections render",
    "KPI cards show current data",
    "System status indicators work",
    "Navigation sidebar functions correctly",
    "Page is responsive across breakpoints"
]

KEY_FILES = [
    "frontend/app/admin/page.tsx",
    "frontend/app/admin/layout.tsx",
    "frontend/app/admin/activity/page.tsx"
]

# Dashboard Sections Reference
DASHBOARD_SECTIONS = [
    {"section": "KPIs", "purpose": "Key performance indicators at a glance"},
    {"section": "System Status", "purpose": "Health of all system components"},
    {"section": "Alerts", "purpose": "Critical issues requiring attention"},
    {"section": "Live Activity", "purpose": "Real-time event stream"},
    {"section": "Quick Actions", "purpose": "Common admin actions"}
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
