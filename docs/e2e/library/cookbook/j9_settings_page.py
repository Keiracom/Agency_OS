"""
Skill: J9.12 — Settings Page
Journey: J9 - Client Dashboard
Checks: 3

Purpose: Verify settings page allows client to configure account preferences,
notification settings, and integration connections.
"""

CHECKS = [
    {
        "id": "J9.12.1",
        "part_a": "Verify settings page renders",
        "part_b": "Navigate to /dashboard/settings, check page renders with settings options",
        "key_files": ["frontend/app/dashboard/settings/page.tsx"]
    },
    {
        "id": "J9.12.2",
        "part_a": "Verify ICP settings link works",
        "part_b": "Click ICP settings link, navigate to /dashboard/settings/icp",
        "key_files": ["frontend/app/dashboard/settings/page.tsx", "frontend/app/dashboard/settings/icp/page.tsx"]
    },
    {
        "id": "J9.12.3",
        "part_a": "Verify LinkedIn settings link works",
        "part_b": "Click LinkedIn settings link, navigate to /dashboard/settings/linkedin",
        "key_files": ["frontend/app/dashboard/settings/page.tsx", "frontend/app/dashboard/settings/linkedin/page.tsx"]
    },
]

PASS_CRITERIA = [
    "Settings page renders without errors",
    "ICP settings navigation works",
    "LinkedIn settings navigation works",
]

KEY_FILES = [
    "frontend/app/dashboard/settings/page.tsx",
    "frontend/app/dashboard/settings/icp/page.tsx",
    "frontend/app/dashboard/settings/linkedin/page.tsx",
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
