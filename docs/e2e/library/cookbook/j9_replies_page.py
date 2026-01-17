"""
Skill: J9.11 — Replies Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify replies page displays all email replies with sentiment analysis,
allows reply management, and shows conversation threads.
"""

CHECKS = [
    {
        "id": "J9.11.1",
        "part_a": "Verify replies page renders",
        "part_b": "Navigate to /dashboard/replies, check page renders with reply list",
        "key_files": ["frontend/app/dashboard/replies/page.tsx"]
    },
    {
        "id": "J9.11.2",
        "part_a": "Verify replies API returns data for tenant",
        "part_b": "GET /api/v1/replies returns replies scoped to authenticated client",
        "key_files": ["src/api/routes/replies.py"]
    },
    {
        "id": "J9.11.3",
        "part_a": "Verify sentiment indicators display",
        "part_b": "Each reply shows sentiment badge (positive, neutral, negative)",
        "key_files": ["frontend/app/dashboard/replies/page.tsx", "frontend/components/ui/badge.tsx"]
    },
    {
        "id": "J9.11.4",
        "part_a": "Verify reply filtering works",
        "part_b": "Filter by sentiment or status, verify filtered results",
        "key_files": ["frontend/app/dashboard/replies/page.tsx"]
    },
    {
        "id": "J9.11.5",
        "part_a": "Verify conversation thread displays",
        "part_b": "Click reply, view full email thread with original outbound email",
        "key_files": ["frontend/app/dashboard/replies/page.tsx"]
    },
]

PASS_CRITERIA = [
    "Replies page renders without errors",
    "Replies API returns data for tenant",
    "Sentiment indicators display correctly",
    "Reply filtering works by sentiment/status",
    "Conversation thread displays full context",
]

KEY_FILES = [
    "frontend/app/dashboard/replies/page.tsx",
    "src/api/routes/replies.py",
    "src/models/reply.py",
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
