"""
Skill: J9.5 — Meetings Widget
Journey: J9 - Client Dashboard
Checks: 4

Purpose: Verify meetings widget displays upcoming meetings, integrates with
calendar data, and shows correct meeting counts and details.
"""

CHECKS = [
    {
        "id": "J9.5.1",
        "part_a": "Verify meetings widget renders on dashboard",
        "part_b": "Check MeetingsWidget component is visible with meeting list",
        "key_files": ["frontend/components/dashboard/meetings-widget.tsx", "frontend/app/dashboard/page.tsx"]
    },
    {
        "id": "J9.5.2",
        "part_a": "Verify meetings API returns scheduled meetings",
        "part_b": "GET /api/v1/meetings returns array of upcoming meetings for tenant",
        "key_files": ["src/api/routes/meetings.py"]
    },
    {
        "id": "J9.5.3",
        "part_a": "Verify meeting details display correctly",
        "part_b": "Each meeting shows date, time, lead name, and meeting type",
        "key_files": ["frontend/components/dashboard/meetings-widget.tsx"]
    },
    {
        "id": "J9.5.4",
        "part_a": "Verify meetings count badge shows correct number",
        "part_b": "Badge shows count of meetings scheduled this week/month",
        "key_files": ["frontend/components/dashboard/meetings-widget.tsx"]
    },
]

PASS_CRITERIA = [
    "Meetings widget renders without errors",
    "Meetings API returns data for authenticated tenant",
    "Meeting details (date, time, lead, type) display correctly",
    "Meetings count badge reflects actual count",
]

KEY_FILES = [
    "frontend/components/dashboard/meetings-widget.tsx",
    "frontend/app/dashboard/page.tsx",
    "src/api/routes/meetings.py",
    "src/models/meeting.py",
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
