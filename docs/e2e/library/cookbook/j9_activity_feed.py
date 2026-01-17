"""
Skill: J9.3 — Activity Feed
Journey: J9 - Client Dashboard
Checks: 6

Purpose: Verify activity feed widget displays recent actions including lead
updates, email sends, replies, and campaign events with correct timestamps.
"""

CHECKS = [
    {
        "id": "J9.3.1",
        "part_a": "Verify activity feed component renders",
        "part_b": "Check ActivityTicker or LiveActivityFeed component is visible on dashboard",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx", "frontend/components/admin/LiveActivityFeed.tsx"]
    },
    {
        "id": "J9.3.2",
        "part_a": "Verify activity feed shows lead events",
        "part_b": "Check feed displays lead creation, score updates, status changes",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"]
    },
    {
        "id": "J9.3.3",
        "part_a": "Verify activity feed shows email events",
        "part_b": "Check feed displays email sent, opened, clicked events",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"]
    },
    {
        "id": "J9.3.4",
        "part_a": "Verify activity feed shows reply events",
        "part_b": "Check feed displays new reply notifications with sentiment indicator",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"]
    },
    {
        "id": "J9.3.5",
        "part_a": "Verify timestamps are formatted correctly",
        "part_b": "Check timestamps show relative time (e.g., '2 hours ago') or formatted date",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx"]
    },
    {
        "id": "J9.3.6",
        "part_a": "Verify activity feed is scoped to client",
        "part_b": "Feed should only show activities for the authenticated client's tenant",
        "key_files": ["frontend/components/dashboard/ActivityTicker.tsx", "src/api/routes/customers.py"]
    },
]

PASS_CRITERIA = [
    "Activity feed component renders without errors",
    "Lead events appear in feed (create, update, score change)",
    "Email events appear in feed (sent, opened, clicked)",
    "Reply events appear with sentiment indicators",
    "Timestamps formatted as relative time or readable date",
    "Activities scoped to authenticated client only",
]

KEY_FILES = [
    "frontend/components/dashboard/ActivityTicker.tsx",
    "frontend/components/admin/LiveActivityFeed.tsx",
    "frontend/app/dashboard/page.tsx",
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
