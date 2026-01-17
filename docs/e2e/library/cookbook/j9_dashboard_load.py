"""
Skill: J9.1 — Dashboard Page Load
Journey: J9 - Client Dashboard
Checks: 6

Purpose: Verify dashboard loads correctly for authenticated users with proper
layout, sidebar navigation, and initial data fetching.
"""

CHECKS = [
    {
        "id": "J9.1.1",
        "part_a": "Verify dashboard page renders without errors",
        "part_b": "Navigate to /dashboard as authenticated user, check for React errors",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
    {
        "id": "J9.1.2",
        "part_a": "Verify dashboard layout renders with sidebar",
        "part_b": "Check that sidebar navigation is visible with all menu items",
        "key_files": ["frontend/app/dashboard/layout.tsx", "frontend/components/layout/sidebar.tsx"]
    },
    {
        "id": "J9.1.3",
        "part_a": "Verify header renders with user info",
        "part_b": "Check header displays user name, avatar, and credits badge",
        "key_files": ["frontend/components/layout/header.tsx", "frontend/components/layout/credits-badge.tsx"]
    },
    {
        "id": "J9.1.4",
        "part_a": "Verify loading states display during data fetch",
        "part_b": "Check skeleton loaders appear while API calls are in progress",
        "key_files": ["frontend/components/ui/loading-skeleton.tsx", "frontend/components/ui/skeleton.tsx"]
    },
    {
        "id": "J9.1.5",
        "part_a": "Verify unauthenticated users are redirected",
        "part_b": "Navigate to /dashboard without auth, verify redirect to /login",
        "key_files": ["frontend/app/dashboard/layout.tsx"]
    },
    {
        "id": "J9.1.6",
        "part_a": "Verify dashboard widgets render after data loads",
        "part_b": "Check all dashboard widgets (stats, activity, ALS) render with data",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
]

PASS_CRITERIA = [
    "Dashboard page loads without console errors",
    "Sidebar navigation displays all menu items",
    "Header shows user info and credits",
    "Loading skeletons appear during data fetch",
    "Unauthenticated users redirect to login",
    "All widgets render with data after loading",
]

KEY_FILES = [
    "frontend/app/dashboard/page.tsx",
    "frontend/app/dashboard/layout.tsx",
    "frontend/components/layout/dashboard-layout.tsx",
    "frontend/components/layout/sidebar.tsx",
    "frontend/components/layout/header.tsx",
    "frontend/components/layout/credits-badge.tsx",
    "frontend/components/ui/loading-skeleton.tsx",
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
