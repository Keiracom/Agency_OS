"""
Skill: J9.14 — Real-Time Updates
Journey: J9 - Client Dashboard
Checks: 4

Purpose: Verify dashboard receives real-time updates for new leads, email events,
and activity changes without requiring page refresh.
"""

CHECKS = [
    {
        "id": "J9.14.1",
        "part_a": "Verify real-time connection establishes",
        "part_b": "Check WebSocket or polling connection establishes on dashboard load",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
    {
        "id": "J9.14.2",
        "part_a": "Verify new lead appears in real-time",
        "part_b": "Create new lead via API, verify it appears in dashboard without refresh",
        "key_files": ["frontend/app/dashboard/page.tsx", "frontend/components/dashboard/ActivityTicker.tsx"]
    },
    {
        "id": "J9.14.3",
        "part_a": "Verify email event updates in real-time",
        "part_b": "Trigger email open event, verify activity feed updates without refresh",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"]
    },
    {
        "id": "J9.14.4",
        "part_a": "Verify stats update in real-time",
        "part_b": "Change lead status, verify stats widget updates without refresh",
        "key_files": ["frontend/app/dashboard/page.tsx"]
    },
]

PASS_CRITERIA = [
    "Real-time connection establishes successfully",
    "New leads appear without page refresh",
    "Email events update activity feed in real-time",
    "Stats widgets update without refresh",
]

KEY_FILES = [
    "frontend/app/dashboard/page.tsx",
    "frontend/components/dashboard/ActivityTicker.tsx",
    "src/api/routes/customers.py",
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
